"""
antar_engine/people_links.py

Relationship Integration Engine, Phase 1 (Antar.world/SPEC_relationship_integration_engine.md).

Three separate things:
  * person chart   - charts row (chart_type='compatibility', user_id NULL, parent_chart_id = owner)
  * relationship   - person_links row, owner -> person, typed, time-bounded (ended_at NULL = current)
  * aliases        - person_aliases rows (name, first name, user nicknames) for the Ask resolver

Pure helpers (normalise_relation, build_aliases, ...) plus DB functions that take a
supabase-style client `sb` and are BLOCKING: async callers must wrap them in
asyncio.to_thread.  Only columns that exist in Antar.world/SQL_person_links.sql and
the charts / chart_connections tables are touched (phantom-column rule).
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from antar_engine import compatibility_reasons as _R
from antar_engine import compatibility_types as _CT
from antar_engine.ask_subject import norm_name

RELATIONS = ("child", "spouse", "romantic", "parent", "sibling", "family",
             "employee", "boss", "cofounder", "business", "advisor", "friend")

# word -> (relation, detail). Only words where the detail matters or that the
# compat alias table would map differently (boss, report, ...). Everything else
# goes through compatibility_reasons.resolve_reason (no duplicated alias table).
_DETAIL_WORDS: Dict[str, Tuple[str, str]] = {
    "son": ("child", "son"), "daughter": ("child", "daughter"),
    "husband": ("spouse", "husband"), "wife": ("spouse", "wife"),
    "girlfriend": ("romantic", "girlfriend"), "boyfriend": ("romantic", "boyfriend"),
    "partner": ("romantic", "partner"),
    "mother": ("parent", "mother"), "mom": ("parent", "mother"), "mum": ("parent", "mother"),
    "father": ("parent", "father"), "dad": ("parent", "father"),
    "brother": ("sibling", "brother"), "sister": ("sibling", "sister"),
    "boss": ("boss", "boss"), "manager": ("boss", "manager"),
    "employee": ("employee", "employee"), "report": ("employee", "report"),
    "direct report": ("employee", "report"), "direct-report": ("employee", "report"),
    "in-law": ("family", None), "in-laws": ("family", None), "inlaws": ("family", None),
    "business partner": ("business", None),
}

# reason keys returned by resolve_reason -> person_links.relation
_REASON_TO_RELATION = {"boss-or-manager": "boss"}

_DETAIL_GENDER = {"son": "male", "husband": "male", "boyfriend": "male", "father": "male",
                  "brother": "male",
                  "daughter": "female", "wife": "female", "girlfriend": "female",
                  "mother": "female", "sister": "female"}

DEFAULT_ROLE = "managerial"   # employee / boss readings need a role; sensible default


def normalise_relation(relation: Any, detail: Any = None) -> Optional[Tuple[str, Optional[str]]]:
    """('son', None) -> ('child', 'son');  ('romantic','girlfriend') -> same;
    unknown -> None (caller rejects with 422)."""
    key = re.sub(r"\s+", " ", str(relation or "").strip().lower())
    det = re.sub(r"\s+", " ", str(detail or "").strip().lower()) or None
    if not key:
        return None
    if key in _DETAIL_WORDS:
        rel, d = _DETAIL_WORDS[key]
        return rel, (det or d)
    reason = _R.resolve_reason(key)          # strict, alias-tolerant
    if not reason:
        return None
    if reason in _CT.STORED_RELATION:        # business_partner: no relation of its own
        return _CT.STORED_RELATION[reason], reason
    rel = _REASON_TO_RELATION.get(reason, reason)
    if rel not in RELATIONS:
        return None
    if det:
        d2 = _DETAIL_WORDS.get(det)
        if d2 and d2[0] == rel:
            det = d2[1] or det
    return rel, det


def relation_to_compat_type(relation: str, detail: Any = None) -> str:
    """person_links.relation (+ relation_detail) -> compatibility reason key. The
    detail only matters for business_partner (stored under 'business')."""
    if relation == "business" and str(detail or "").strip().lower() == "business_partner":
        return "business_partner"
    return "boss-or-manager" if relation == "boss" else relation


def compat_type_to_relation(compat_type: Any) -> Optional[str]:
    """Legacy compat_type (chart_connections / sessions) -> relation, for the
    backfill. marriage->spouse, family->family; others keep. None when unknown."""
    raw = str(compat_type or "").strip().lower()
    if not raw:
        return None
    if raw in ("marriage", "married"):
        return "spouse"
    if raw in ("partner", "relationship", "love", "dating"):
        return "romantic"
    n = normalise_relation(raw)
    return n[0] if n else None


def gender_from_detail(detail: Optional[str]) -> Optional[str]:
    return _DETAIL_GENDER.get((detail or "").strip().lower())


def norm_gender(g: Any) -> Optional[str]:
    s = str(g or "").strip().lower()
    if s in ("m", "male", "man", "boy", "he"):
        return "male"
    if s in ("f", "female", "woman", "girl", "she"):
        return "female"
    return None


def build_aliases(name: str, extra: Optional[List[str]] = None,
                  source: str = "name") -> List[Dict[str, str]]:
    """Full name + first name (source 'name'); `extra` are user nicknames."""
    out: List[Dict[str, str]] = []
    seen = set()

    def add(text: str, src: str):
        text = (text or "").strip()
        norm = norm_name(text)
        if text and norm and norm not in seen:
            seen.add(norm)
            out.append({"alias": text, "alias_norm": norm, "source": src})

    nm = (name or "").strip()
    if nm:
        add(nm, source)
        parts = nm.split()
        if len(parts) > 1:
            add(parts[0], source)
    for e in extra or []:
        add(e, "user")
    return out


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rows(res) -> list:
    return list(getattr(res, "data", None) or [])


# ── links ────────────────────────────────────────────────────────────────────
def get_link(sb, link_id: str) -> Optional[dict]:
    r = _rows(sb.table("person_links").select("*").eq("id", link_id).limit(1).execute())
    return r[0] if r else None


def get_current_link(sb, owner_chart_id: str, person_chart_id: str) -> Optional[dict]:
    rows = _rows(sb.table("person_links").select("*")
                 .eq("owner_chart_id", owner_chart_id)
                 .eq("person_chart_id", person_chart_id).execute())
    cur = [r for r in rows if not r.get("ended_at")]
    return cur[0] if cur else None


def create_link(sb, owner_chart_id: str, person_chart_id: str, relation: str,
                detail: Optional[str] = None) -> Tuple[dict, bool]:
    """-> (row, created). Idempotent: an existing CURRENT link is returned as-is."""
    if owner_chart_id == person_chart_id:
        raise ValueError("owner and person must be different charts")
    cur = get_current_link(sb, owner_chart_id, person_chart_id)
    if cur:
        return cur, False
    row = {"owner_chart_id": owner_chart_id, "person_chart_id": person_chart_id,
           "relation": relation, "relation_detail": detail, "started_at": _now()}
    ins = _rows(sb.table("person_links").insert(row).execute())
    return (ins[0] if ins else row), True


def end_link(sb, link_id: str, reason: str = "removed") -> None:
    sb.table("person_links").update({"ended_at": _now(), "ended_reason": reason}) \
        .eq("id", link_id).execute()


def change_relation(sb, link_id: str, relation: str,
                    detail: Optional[str] = None) -> Tuple[Optional[dict], bool]:
    """End the current row (reason 'changed') and insert the new one. Returns
    (new_current_row, changed). Same relation+detail is a no-op (changed False).
    Rolls the old row back open if the insert fails (never leaves a person with no
    current link)."""
    old = get_link(sb, link_id)
    if not old or old.get("ended_at"):
        return None, False
    if old.get("relation") == relation and (old.get("relation_detail") or None) == (detail or None):
        return old, False
    end_link(sb, link_id, "changed")
    try:
        row = {"owner_chart_id": old["owner_chart_id"], "person_chart_id": old["person_chart_id"],
               "relation": relation, "relation_detail": detail, "started_at": _now()}
        ins = _rows(sb.table("person_links").insert(row).execute())
        return (ins[0] if ins else row), True
    except Exception:
        sb.table("person_links").update({"ended_at": None, "ended_reason": None}) \
            .eq("id", link_id).execute()
        raise


# ── aliases ──────────────────────────────────────────────────────────────────
def list_aliases(sb, owner_chart_id: str, person_chart_id: str) -> List[dict]:
    return _rows(sb.table("person_aliases").select("id,alias,alias_norm,source")
                 .eq("owner_chart_id", owner_chart_id)
                 .eq("person_chart_id", person_chart_id).execute())


def add_aliases(sb, owner_chart_id: str, person_chart_id: str,
                aliases: List[Dict[str, str]]) -> List[dict]:
    have = {a.get("alias_norm") for a in list_aliases(sb, owner_chart_id, person_chart_id)}
    added = []
    for a in aliases:
        if not a.get("alias_norm") or a["alias_norm"] in have:
            continue
        row = {"owner_chart_id": owner_chart_id, "person_chart_id": person_chart_id,
               "alias": a["alias"], "alias_norm": a["alias_norm"],
               "source": a.get("source") or "name"}
        ins = _rows(sb.table("person_aliases").insert(row).execute())
        added.append(ins[0] if ins else row)
        have.add(a["alias_norm"])
    return added


def delete_alias(sb, owner_chart_id: str, person_chart_id: str, alias_id: str) -> bool:
    rows = [a for a in list_aliases(sb, owner_chart_id, person_chart_id)
            if str(a.get("id")) == str(alias_id)]
    if not rows:
        return False
    sb.table("person_aliases").delete().eq("id", alias_id).execute()
    return True


def sync_name_aliases(sb, owner_chart_id: str, person_chart_id: str, old_name: str,
                      new_name: str) -> None:
    """After a rename: drop the old auto ('name') aliases, add the new ones.
    User nicknames are kept."""
    if (old_name or "").strip() == (new_name or "").strip():
        return
    for a in list_aliases(sb, owner_chart_id, person_chart_id):
        if a.get("source") == "name":
            sb.table("person_aliases").delete().eq("id", a["id"]).execute()
    add_aliases(sb, owner_chart_id, person_chart_id, build_aliases(new_name))


# ── reading ──────────────────────────────────────────────────────────────────
def _person_name(row: dict) -> str:
    return (row.get("name") or row.get("first_name") or "").strip()


def latest_score(sb, owner_chart_id: str, person_chart_id: str,
                 compat_type: str) -> Optional[dict]:
    """Latest score for the CURRENT relation only (older types are never returned)."""
    rows = _rows(sb.table("chart_connections")
                 .select("compat_type,overall_score,verdict,score_breakdown,session_id,updated_at")
                 .eq("chart_id_a", owner_chart_id).eq("chart_id_b", person_chart_id).execute())
    rows = [r for r in rows if r.get("compat_type") == compat_type]
    if not rows:
        return None
    rows.sort(key=lambda r: str(r.get("updated_at") or ""), reverse=True)
    r = rows[0]
    bd = r.get("score_breakdown") if isinstance(r.get("score_breakdown"), dict) else {}
    return {"score": r.get("overall_score"), "badge": r.get("verdict"),
            "headline": bd.get("headline"), "compat_type": compat_type,
            "session_id": r.get("session_id"), "updated_at": r.get("updated_at")}


def list_current_links(sb, owner_chart_id: str, with_scores: bool = True) -> List[dict]:
    """Current links only (ended rows are kept in the table but never returned)."""
    links = [l for l in _rows(sb.table("person_links").select("*")
                              .eq("owner_chart_id", owner_chart_id).execute())
             if not l.get("ended_at")]
    out = []
    for l in links:
        pid = l["person_chart_id"]
        ch = _rows(sb.table("charts").select("id,name,first_name,gender,deleted_at")
                   .eq("id", pid).limit(1).execute())
        ch = ch[0] if ch else {}
        if not ch or ch.get("deleted_at"):
            continue
        gender = norm_gender(ch.get("gender")) or gender_from_detail(l.get("relation_detail"))
        item = {"link_id": l["id"], "person_chart_id": pid, "relation": l["relation"],
                "relation_detail": l.get("relation_detail"), "name": _person_name(ch),
                "gender": gender, "started_at": l.get("started_at"),
                "aliases": [{"id": a.get("id"), "alias": a.get("alias"), "source": a.get("source")}
                            for a in list_aliases(sb, owner_chart_id, pid)]}
        if with_scores:
            item["score"] = latest_score(sb, owner_chart_id, pid,
                                         relation_to_compat_type(l["relation"], l.get("relation_detail")))
        out.append(item)
    return out


def load_people_for_ask(sb, owner_chart_id: str) -> Optional[list]:
    """People for the Ask resolver, from person_links (+aliases + person gender).
    Returns None when this chart has NO person_links rows at all (caller falls back
    to chart_connections). When it has some, returns links PLUS any legacy
    chart_connections rows for people that have no link row yet (partial backfill)."""
    all_links = _rows(sb.table("person_links").select("*")
                      .eq("owner_chart_id", owner_chart_id).execute())
    if not all_links:
        return None
    linked_ids = {l["person_chart_id"] for l in all_links}
    people = []
    for l in all_links:
        if l.get("ended_at"):
            continue
        pid = l["person_chart_id"]
        ch = _rows(sb.table("charts").select("id,name,first_name,gender,deleted_at")
                   .eq("id", pid).limit(1).execute())
        ch = ch[0] if ch else {}
        name = _person_name(ch)
        if not ch or ch.get("deleted_at") or not name:
            continue
        aliases = [a.get("alias") for a in list_aliases(sb, owner_chart_id, pid) if a.get("alias")]
        people.append({"chart_id_b": pid, "name_b": name,
                       "compat_type": relation_to_compat_type(l["relation"], l.get("relation_detail")),
                       "relation": l["relation"], "relation_detail": l.get("relation_detail"),
                       "gender": norm_gender(ch.get("gender"))
                       or gender_from_detail(l.get("relation_detail")),
                       "aliases": aliases})
    legacy = _rows(sb.table("chart_connections").select("chart_id_b,name_b,compat_type")
                   .eq("chart_id_a", owner_chart_id).execute())
    for r in legacy:
        if r.get("chart_id_b") and r["chart_id_b"] not in linked_ids and (r.get("name_b") or "").strip():
            people.append(r)
    return people


# ── removal ──────────────────────────────────────────────────────────────────
def person_referenced_elsewhere(sb, person_chart_id: str, owner_chart_id: str) -> bool:
    """True if anything other than this owner's (already removed) link still
    references the person chart."""
    for l in _rows(sb.table("person_links").select("id,owner_chart_id,ended_at")
                   .eq("person_chart_id", person_chart_id).execute()):
        if not l.get("ended_at") and l.get("owner_chart_id") != owner_chart_id:
            return True
    for t in ("compatibility_sessions", "chart_connections"):
        for c in ("chart_id_a", "chart_id_b"):
            if _rows(sb.table(t).select("id").eq(c, person_chart_id).limit(1).execute()):
                return True
    return False


# ── dashas for a (re)computed person chart ───────────────────────────────────
def _flat_dashas(raw) -> list:
    flat = []
    for p in raw or []:
        if not isinstance(p, dict):
            continue
        sd = str(p.get("start_date", "") or p.get("start", ""))[:10]
        ed = str(p.get("end_date", "") or p.get("end", ""))[:10]
        lord = p.get("lord", "") or p.get("lord_or_sign", "") or p.get("planet_or_sign", "")
        if "sub" in p:
            flat.append({"lord": lord, "start_date": sd, "end_date": ed,
                         "duration_years": p.get("duration_years", 0),
                         "level": "mahadasha", "parent_lord": ""})
            for s in p.get("sub", []):
                flat.append({"lord": s.get("lord", ""),
                             "start_date": str(s.get("start_date", "") or s.get("start", ""))[:10],
                             "end_date": str(s.get("end_date", "") or s.get("end", ""))[:10],
                             "duration_years": s.get("duration_years", 0),
                             "level": "antardasha", "parent_lord": s.get("parent_lord", "")})
        else:
            flat.append({"lord": lord, "start_date": sd, "end_date": ed,
                         "duration_years": p.get("duration_years", 0),
                         "level": p.get("level", "mahadasha"),
                         "parent_lord": p.get("parent_lord", "")})
    return flat


def build_dasha_rows(chart_id: str, chart: dict) -> list:
    """dasha_periods rows (vimsottari + ashtottari) for a person chart, same shape
    compatibility_start stores. Each system fails independently."""
    from antar_engine import vimsottari as _vim, ashtottari as _ash
    rows = []
    for system, fn in (("vimsottari", _vim.calculate_vimsottari_from_chart),
                       ("ashtottari", _ash.calculate_ashtottari_from_chart)):
        try:
            periods = _flat_dashas(fn(chart, chart.get("birth_jd")))
        except Exception:
            periods = []
        for i, p in enumerate(periods):
            lvl = p["level"]
            rows.append({
                "chart_id": chart_id, "system": system, "type": lvl,
                "level": 1 if lvl == "mahadasha" else (2 if lvl == "antardasha" else 3),
                "planet_or_sign": p["lord"], "start_date": p["start_date"],
                "end_date": p["end_date"], "duration_years": p["duration_years"],
                "sequence": i, "parent_id": None,
                "metadata": {"parent_lord": p["parent_lord"], "type": lvl},
            })
    return rows
