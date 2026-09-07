"""
antar_engine/house_activation.py  — [ranked-sweep 2026-09-07]

Convergence-based per-domain ACTIVATION scorer for the monthly / yearly ranked
sweep.

Methodology (owner-approved, KN-Rao-aligned):
  • Parāśari core PREDICTS — Vimśottarī daśā (what's lit now) + gochar transits
    (the date windows) + D-1 house framework (D-9 confirmation handled upstream).
  • Jaimini chara-daśā CONFIRMS — a domain is scored higher when the running
    chara sign's house AND the Vimśottarī lord's house both point at it. That
    agreement ("regardless of paddhati the answer should be the same") is the
    CONFIDENCE dial, not a second independent bet.
  • Lal Kitab stays on remedies, not here.

Product rule (see memory forecast-surfacing-principle): rank domains and surface
the STRONG (opportunity) AND the genuinely AT-RISK, suppress the neutral middle —
never a flat 9-domain dump. `rank_and_tier` returns {active:[...], quiet:[...]}.

Pure-Python, deterministic, no LLM, no IO. Same discipline as verdict_resolver:
inputs → score. Never raises; degrades to empty/neutral.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Dict, List, Optional, Any

from antar_engine.d10_career import SIGNS, SIGN_LORD, _sign_n_from
from antar_engine.life_area_map import LIFE_AREA_MAP

# The life-domains we sweep, in a stable display order. Each maps to a
# LIFE_AREA_MAP key (houses + karakas) and a user-facing label.
DOMAIN_SWEEP: List[Dict[str, str]] = [
    {"key": "career",      "label": "Work & reputation"},
    {"key": "finance",     "label": "Money"},
    {"key": "wealth",      "label": "Wealth & gains"},
    {"key": "property",    "label": "Home"},
    {"key": "foreign",     "label": "Travel & foreign"},
    {"key": "marriage",    "label": "Relationship"},
    {"key": "family",      "label": "Family"},
    {"key": "health",      "label": "Health"},
    {"key": "speculation", "label": "Risk & speculation"},
    {"key": "spiritual",   "label": "Inner life"},
]

_BENEFICS = {"Jupiter", "Venus", "Mercury", "Moon"}
_MALEFICS = {"Saturn", "Mars", "Rahu", "Ketu", "Sun"}
_DUSTHANAS = {6, 8, 12}          # houses whose activation leans risk
_NODES = {"Rahu", "Ketu"}


# ── chart primitives ─────────────────────────────────────────────────────────
def _lagna_index(chart_data: dict) -> int:
    lg = (chart_data or {}).get("lagna") or {}
    si = lg.get("sign_index")
    if isinstance(si, int):
        return si % 12
    try:
        return SIGNS.index(str(lg.get("sign") or "").strip().title())
    except Exception:
        return 0


def _house_of_sign(sign_name: str, lagna_idx: int) -> Optional[int]:
    try:
        si = SIGNS.index(str(sign_name).strip().title())
    except ValueError:
        return None
    return ((si - lagna_idx) % 12) + 1


def _house_lord(lagna_sign: str, house: int) -> Optional[str]:
    """Lord of the Nth house from the lagna sign."""
    try:
        return SIGN_LORD.get(_sign_n_from(lagna_sign, house))
    except Exception:
        return None


def _occupants(chart_data: dict) -> Dict[int, List[str]]:
    out: Dict[int, List[str]] = {}
    for p, v in ((chart_data or {}).get("planets") or {}).items():
        if isinstance(v, dict) and isinstance(v.get("house"), int):
            out.setdefault(v["house"], []).append(str(p).title())
    return out


# ── daśā activation ──────────────────────────────────────────────────────────
def _active_today(periods, today_iso: str) -> List[dict]:
    out = []
    for p in periods if isinstance(periods, list) else []:
        if not isinstance(p, dict):
            continue
        s = str(p.get("start_date") or p.get("start") or "")[:10]
        e = str(p.get("end_date") or p.get("end") or "")[:10]
        if s and e and s <= today_iso <= e:
            out.append(p)
    return out


def _vim_active_planets(dashas: dict, today_iso: str) -> set:
    """Vimśottarī MD+AD+PD lords running today (planets)."""
    out = set()
    for key in ("vimsottari", "vimshottari"):
        for p in _active_today((dashas or {}).get(key) or [], today_iso):
            lord = p.get("lord_or_sign") or p.get("lord") or p.get("planet_or_sign")
            if lord:
                out.add(str(lord).title())
    return out


def _jaimini_active_houses(dashas: dict, lagna_idx: int, today_iso: str) -> set:
    """Houses lit by the running Jaimini chara sign(s)."""
    out = set()
    for key in ("jaimini", "chara"):
        for p in _active_today((dashas or {}).get(key) or [], today_iso):
            sign = p.get("lord_or_sign") or p.get("planet_or_sign") or p.get("sign")
            h = _house_of_sign(sign, lagna_idx) if sign else None
            if h:
                out.add(h)
    return out


# ── main scorer ──────────────────────────────────────────────────────────────
def score_domains(chart_data: dict, dashas: dict, transit_events: list,
                  today: Optional[date] = None) -> List[dict]:
    """Score every DOMAIN_SWEEP domain for activation. Returns a list of dicts:
      {key, label, houses, score, polarity ('opportunity'|'risk'|'neutral'),
       confidence (0-1), convergence (bool), vim, jaimini, transit_count,
       window (ISO date-range str or ''), drivers[]}.
    Ordered by DOMAIN_SWEEP; caller ranks/tiers with rank_and_tier."""
    today = today or datetime.utcnow().date()
    today_iso = today.isoformat()
    lg = (chart_data or {}).get("lagna") or {}
    lagna_sign = str(lg.get("sign") or "").strip().title()
    lagna_idx = _lagna_index(chart_data)

    occ = _occupants(chart_data)
    vim_planets = _vim_active_planets(dashas, today_iso)
    jaimini_houses = _jaimini_active_houses(dashas, lagna_idx, today_iso)
    md_is_malefic = bool(vim_planets & _MALEFICS) and not (vim_planets & _BENEFICS)

    # index transit events by natal house
    ev_by_house: Dict[int, List[dict]] = {}
    for ev in (transit_events or []):
        h = ev.get("natal_house")
        if isinstance(h, int):
            ev_by_house.setdefault(h, []).append(ev)

    results = []
    for dom in DOMAIN_SWEEP:
        spec = LIFE_AREA_MAP.get(dom["key"]) or {}
        primary = spec.get("primary")
        houses = [primary] + list(spec.get("secondary") or []) if primary else list(spec.get("secondary") or [])
        houses = [h for h in houses if isinstance(h, int)]
        karakas = {str(k).title() for k in (spec.get("karaka") or [])}

        # significators of this domain: house lords + occupants + karakas
        lords = {_house_lord(lagna_sign, h) for h in houses if lagna_sign}
        lords.discard(None)
        occupants = set()
        for h in houses:
            occupants.update(occ.get(h, []))
        significators = (lords | occupants | karakas)

        # --- Parāśari daśā activation (Vimśottarī) ---
        vim_hit = bool(significators & vim_planets)
        vim_house_hit = any(h in {occ_h for occ_h, ps in occ.items()
                                  for pl in ps if pl in vim_planets} for h in houses)
        # a vim planet SITTING in one of the domain's houses also lights it
        vim_house_hit = any(any(pl in vim_planets for pl in occ.get(h, [])) for h in houses)
        vim_active = vim_hit or vim_house_hit

        # --- Jaimini chara confirmation ---
        jaimini_active = bool(set(houses) & jaimini_houses)

        # --- gochar transits over the domain's houses ---
        dom_events = [e for h in houses for e in ev_by_house.get(h, [])]
        transit_count = len(dom_events)

        # --- polarity (opportunity vs risk) ---
        tone = 0.0
        for e in dom_events:
            pl = str(e.get("planet") or "").title()
            w = 1.0
            if e.get("event_type") == "aspect":
                w = 1.2
            if pl in _BENEFICS:
                tone += w
            elif pl in _MALEFICS:
                tone -= w
        # structural lean: dusthana houses + a malefic mahadasha tilt toward risk
        dusthana_share = sum(1 for h in houses if h in _DUSTHANAS) / max(1, len(houses))
        if dusthana_share >= 0.5:
            tone -= 0.5
        if md_is_malefic:
            tone -= 0.3

        # --- score ---
        score = 0.0
        if vim_active:
            score += 3.0
        if jaimini_active:
            score += 1.5
        score += min(3.0, transit_count * 0.75)
        if karakas & vim_planets:
            score += 0.75
        convergence = vim_active and jaimini_active
        if convergence:
            score += 2.0                      # the moat: systems agree

        polarity = "neutral"
        if score >= 2.0:
            polarity = "risk" if tone < -0.4 else ("opportunity" if tone > 0.4 else
                       ("risk" if dusthana_share >= 0.5 else "opportunity"))

        # [polarity-nuance 2026-09-07] A speculation / dusthana (8,12) theme lit
        # under a malefic mahādaśā (esp. Rahu) is high-reward AND high-risk. Keep
        # it surfaced as opportunity, but flag caution so the narration frames it
        # as lean-in-WITH-a-stop, never a pure green light.
        caution = (polarity == "opportunity" and md_is_malefic
                   and (dom["key"] == "speculation"
                        or any(h in _DUSTHANAS for h in houses)))

        # confidence rises with convergence + transit corroboration
        confidence = 0.35
        if vim_active:
            confidence += 0.25
        if jaimini_active:
            confidence += 0.15
        if transit_count:
            confidence += 0.15
        if convergence:
            confidence += 0.10
        confidence = round(min(1.0, confidence), 2)

        # date window from the domain's transit events (earliest→latest)
        window = ""
        if dom_events:
            ds = sorted(str(e.get("date") or "")[:10] for e in dom_events if e.get("date"))
            if ds:
                window = ds[0] if ds[0] == ds[-1] else f"{ds[0]} – {ds[-1]}"

        drivers = []
        if vim_active:
            drivers.append(f"Vimśottarī {'/'.join(sorted(vim_planets))} activates it")
        if jaimini_active:
            drivers.append("Jaimini chara agrees")
        if transit_count:
            drivers.append(f"{transit_count} transit event(s) hitting houses {houses}")

        results.append({
            "key": dom["key"], "label": dom["label"], "houses": houses,
            "score": round(score, 2), "polarity": polarity, "caution": caution,
            "confidence": confidence, "convergence": convergence,
            "vim": vim_active, "jaimini": jaimini_active,
            "transit_count": transit_count, "window": window, "drivers": drivers,
            "tone": round(tone, 2),
        })
    return results


def rank_and_tier(domain_scores: List[dict], max_active: int = 3,
                  min_score: float = 2.0) -> Dict[str, Any]:
    """Surface the STRONG (opportunity) and the AT-RISK, suppress the neutral
    middle. Returns {active:[...], quiet:[...], headline_domains:[labels]}.
    `active` = top opportunities + top risks (each above min_score), ranked by
    score; `quiet` = everything else (one-liner material for the frontend)."""
    scored = [d for d in domain_scores if d["score"] >= min_score]
    quiet = [d for d in domain_scores if d["score"] < min_score]

    opps = sorted([d for d in scored if d["polarity"] == "opportunity"],
                  key=lambda d: (-d["score"], -d["confidence"]))
    risks = sorted([d for d in scored if d["polarity"] == "risk"],
                   key=lambda d: (-d["score"], -d["confidence"]))

    active: List[dict] = []
    # always surface at least the single biggest risk if any exists
    if risks:
        active.append(risks[0])
    # fill with strongest opportunities
    for d in opps:
        if len(active) >= max_active:
            break
        if d not in active:
            active.append(d)
    # a second risk if room and strong
    for d in risks[1:]:
        if len(active) >= max_active + 1:
            break
        if d not in active:
            active.append(d)
    # de-dupe, keep ranked by score
    seen = set()
    active = [d for d in sorted(active, key=lambda d: -d["score"])
              if not (d["key"] in seen or seen.add(d["key"]))]

    # Quiet = everything NOT surfaced as active (the neutral middle), ranked so
    # the frontend one-liner names them ("home, health, relationships hold
    # steady"). Was `score < min_score`, which silently dropped mid-tier domains
    # that didn't make the active cut — leaving the quiet line empty.
    active_keys = {d["key"] for d in active}
    quiet = sorted([d for d in domain_scores if d["key"] not in active_keys],
                   key=lambda d: -d["score"])

    return {
        "active": active,
        "quiet": quiet,
        "headline_domains": [d["label"] for d in active],
    }
