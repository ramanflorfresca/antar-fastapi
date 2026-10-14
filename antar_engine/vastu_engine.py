"""
antar_engine/vastu_engine.py

Vastu-Jyotish (Parashari-based) directions + dasha line. 2026-10-14

Three outputs, all deterministic, all built from antar_engine/vastu_rules.py:
  1. the chart's eight compass zones — which support this person, which need a
     lighter touch;
  2. personal directions — sleep head / work facing / eat facing / keep-light
     zones — chosen from the chart INSIDE the classical safe envelopes;
  3. the dasha line — which zone the running Vimsottari period puts in focus.
Plus an object-placement guide (where common household objects sit best),
re-ranked by the zones that are strong or strained for THIS chart.

Scoring is REUSED from material_advice._affliction_and_support so the Vastu
read can never contradict the colour/gem/metal read (a planet that is a
"favourable colour" is a "supportive zone", and vice versa).

Honesty rules (product-wide):
  - traditional guidance, never a prediction (no falsifiable claim);
  - no planet, house, sign or Sanskrit reaches the user — only compass words and
    plain life areas;
  - a neutral period is suppressed rather than padded;
  - never raises: {available: False} when the chart is incomplete.
LLM never decides anything here; this module is the whole decision.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from antar_engine import vastu_rules as R

try:
    from antar_engine.material_advice import (
        _house_lords_from_lagna, _affliction_and_support,
    )
except Exception:  # pragma: no cover - engine must degrade, never crash the app
    def _house_lords_from_lagna(_s): return {}
    def _affliction_and_support(*a, **k): return 0.0, 0.0, "", ""
try:
    from antar_engine.relationships import _house_of
except Exception:  # pragma: no cover
    def _house_of(_p, _pl): return None

_RANK = {"strong": 2, "steady": 1, "needs_care": 0}
_PLANETS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu")


# ── planet / zone classification ─────────────────────────────────────────────
def _planet_class(planet: str, cd: dict, lk, house_lords: dict) -> dict:
    """{cls, score, dig}. Same thresholds as material_advice.material_guidance:
    hard-avoid wins on a real affliction (never against the ascendant lord unless
    heavily afflicted); favourable needs a clear support lead."""
    fav, avo, _fr, _av = _affliction_and_support(planet, cd, lk, house_lords)
    hard_avoid = avo >= 2.0 and avo >= fav
    if planet == house_lords.get(1) and avo < 3.0:
        hard_avoid = False
    if hard_avoid:
        cls = "needs_care"
    elif fav >= 2.0 and fav > avo:
        cls = "strong"
    else:
        cls = "steady"
    house = _house_of(planet, cd.get("planets") or {})
    dig = 1 if (house is not None and R.DIG_BALA_HOUSE.get(planet) == house) else 0
    return {"cls": cls, "score": round(fav - avo, 2), "dig": dig}


def _cap_classes(pc: dict) -> dict:
    """Keep only the worst MAX_NEEDS_CARE and best MAX_STRONG planets; the rest
    become steady. Deterministic: ties keep planet order."""
    for cls, limit, key in (
            ("needs_care", R.MAX_NEEDS_CARE, lambda p: pc[p]["score"]),    # worst first
            ("strong", R.MAX_STRONG, lambda p: -pc[p]["score"])):          # best first
        ranked = sorted((p for p in pc if pc[p]["cls"] == cls), key=key)
        for p in ranked[limit:]:
            pc[p]["cls"] = "steady"
    return pc


def _zone_class(zone: str, pc: dict) -> dict:
    """Primary lord decides; a secondary lord only breaks a NEUTRAL primary."""
    lords = R.ZONE_LORDS[zone]
    primary = pc[lords[0]]
    cls, score, dig = primary["cls"], primary["score"], primary["dig"]
    if len(lords) > 1:
        sec = pc[lords[1]]
        if cls == "steady":
            cls = sec["cls"]
        score = round(score + 0.5 * sec["score"], 2)
    return {"cls": cls, "score": score, "dig": dig}


def _pick(envelope: list, zones: dict) -> str:
    """Best zone inside a safe envelope: class, then score, then dig bala, then
    the envelope's own order (so the classical default wins a true tie)."""
    return max(envelope, key=lambda z: (_RANK[zones[z]["cls"]], zones[z]["score"],
                                        zones[z]["dig"], -envelope.index(z)))


def _direction(zone: str, zones: dict, both_strained: bool = False) -> dict:
    cls = zones[zone]["cls"]
    why = R.DIRECTION_WHY[cls]
    if both_strained:
        why = ("both safe options need a lighter touch for you; this is the milder one, "
               "so just keep the area tidy and light")
    return {"zone": zone, "label": R.ZONE_LABEL[zone], "status": cls, "why": why,
            "src": f"VJ-ENV-{zone}"}


# ── objects ──────────────────────────────────────────────────────────────────
def _labels(codes) -> list:
    return [R.ZONE_LABEL[z] for z in codes]


def _objects_view(zones: dict) -> list:
    out = []
    for o in R.OBJECTS:
        best = list(o["best"])
        usable = [z for z in best if zones[z]["cls"] != "needs_care"]
        usable.sort(key=lambda z: -_RANK[zones[z]["cls"]])      # stable: strong first
        flagged = [z for z in best if zones[z]["cls"] == "needs_care"]
        tip = ""
        if flagged and usable:
            tip = (f"Your chart asks for a lighter touch in the {_labels(flagged)[0]}, "
                   f"so favour the {R.ZONE_LABEL[usable[0]]} instead.")
        elif flagged and not usable:
            tip = ("The traditional spots for this need a lighter touch for you, so keep it "
                   "small and the area tidy.")
        out.append({
            "id": o["id"], "label": o["label"],
            "best": _labels(best), "avoid": _labels(o["avoid"]),
            "note": o["note"], "contested": bool(o["contested"]),
            "for_you": {"best": _labels(usable), "tip": tip},
            "src": f"VJ-OBJ-{o['id']}",
        })
    return out


def _zone_cards(zones: dict) -> list:
    cards = []
    for z in R.ZONE_ORDER:
        info = zones[z]
        # a zone that needs a lighter touch recommends nothing to put there
        place = ([] if info["cls"] == "needs_care"
                 else [o["label"] for o in R.OBJECTS if z in o["best"]][:3])
        # "avoid everywhere" rows (distressing images) would repeat on all 8 cards
        keep_out = [o["label"] for o in R.OBJECTS
                    if z in o["avoid"] and len(o["avoid"]) < len(R.ZONE_ORDER)][:3]
        card = {
            "zone": z, "label": R.ZONE_LABEL[z], "status": info["cls"],
            "status_label": R.CLASS_LABEL[info["cls"]],
            "governs": R.ZONE_GOVERNS[z],
            "place_here": place, "keep_out": keep_out,
            "src": f"VJ-ZONE-{z}",
        }
        if info["cls"] == "needs_care":
            card["care_note"] = ("Keep this area light, tidy and uncluttered, and avoid putting "
                                 "your bed head, desk or prayer corner here.")
        elif info["cls"] == "strong":
            card["care_note"] = ("A good place for the things that matter most to you — "
                                 "keep it bright and open.")
        cards.append(card)
    return cards


# ── dasha line ───────────────────────────────────────────────────────────────
def _d(v) -> Optional[date]:
    try:
        return date.fromisoformat(str(v)[:10])
    except Exception:
        return None


def _active_vim_periods(dashas: dict, today: date) -> dict:
    """{'md': (lord, end), 'ad': (lord, end)} for the running VIMSOTTARI period
    ONLY (Raman's MD is Rahu — never let Yogini/chara lords stand in for it).
    Reads the row's level; if levels are missing, falls back to span length."""
    rows = []
    for sysname in ("vimsottari", "vimshottari"):
        for p in (dashas or {}).get(sysname) or []:
            if not isinstance(p, dict):
                continue
            lord = p.get("lord_or_sign") or p.get("planet_or_sign") or p.get("lord")
            s = _d(p.get("start_date") or p.get("start"))
            e = _d(p.get("end_date") or p.get("end"))
            if lord and s and e and s <= today <= e:
                rows.append((str(lord).title(), s, e, str(p.get("level") or "").lower()))
    out = {}
    for lord, s, e, lvl in rows:
        if lvl.startswith("maha"):
            out.setdefault("md", (lord, e))
        elif lvl.startswith("antar"):
            out.setdefault("ad", (lord, e))
    if "md" not in out and rows and not any(r[3] for r in rows):
        by_span = sorted(rows, key=lambda r: (r[2] - r[1]).days, reverse=True)
        out["md"] = (by_span[0][0], by_span[0][2])
        if len(by_span) > 1:
            out["ad"] = (by_span[1][0], by_span[1][2])
    return out


def _period_item(scope: str, scope_label: str, lord: str, end: date,
                 cls: str) -> dict:
    zone = R.PLANET_ZONE[lord]
    label = R.ZONE_LABEL[zone]
    t = R.PERIOD_TEXT[cls]
    return {
        "scope": scope, "scope_label": scope_label,
        "zone": zone, "label": label,
        "status": cls, "status_label": R.CLASS_LABEL[cls],
        "until": end.isoformat(), "until_label": end.strftime("%b %Y"),
        "do": t["do"].format(zone=label), "avoid": t["avoid"],
        "src": f"VJ-PERIOD-{scope}-{zone}",
    }


def period_line(cd: dict, lk, dashas: dict, today: Optional[date] = None,
                pc: Optional[dict] = None, house_lords: Optional[dict] = None) -> dict:
    """The dasha line. Surfaces the running sub-period first (the actionable one),
    then the long chapter if it points at a different zone. A neutral period is
    suppressed. Class comes from the PERIOD LORD itself."""
    today = today or date.today()
    active = _active_vim_periods(dashas, today)
    if not active:
        return {"available": False, "note": ""}
    if house_lords is None:
        house_lords = _house_lords_from_lagna(((cd.get("lagna") or {}).get("sign")))
    items = []
    for key, scope, scope_label in (("ad", "stretch", "This stretch"),
                                    ("md", "chapter", "This chapter")):
        if key not in active:
            continue
        lord, end = active[key]
        if lord not in R.PLANET_ZONE:
            continue
        cls = (pc or {}).get(lord, {}).get("cls") or \
            _planet_class(lord, cd, lk, house_lords)["cls"]
        if cls == "steady":
            continue
        items.append(_period_item(scope, scope_label, lord, end, cls))
    # the long chapter is dropped when it points at the same zone as the stretch
    if len(items) == 2 and items[0]["zone"] == items[1]["zone"]:
        items = items[:1]
    if not items:
        return {"available": False,
                "note": "No direction needs special attention during your current life period."}
    return {"available": True, "focus": items[0],
            "background": items[1] if len(items) > 1 else None}


# ── public entry ─────────────────────────────────────────────────────────────
def vastu_guidance(chart_data: dict, dashas: Optional[dict] = None,
                   lk_data: Optional[dict] = None,
                   today: Optional[date] = None) -> dict:
    """{available, directions, zones[], objects[], period, info, meta}. Never raises."""
    try:
        cd = chart_data if isinstance(chart_data, dict) else {}
        lagna = ((cd.get("lagna") or {}).get("sign"))
        if not (cd.get("planets") and lagna):
            return {"available": False}
        house_lords = _house_lords_from_lagna(lagna)
        if not house_lords:
            return {"available": False}

        pc = _cap_classes({p: _planet_class(p, cd, lk_data, house_lords) for p in _PLANETS})
        zones = {z: _zone_class(z, pc) for z in R.ZONE_ORDER}

        sleep_z = _pick(R.SLEEP_HEAD_ENVELOPE, zones)
        work_z = _pick(R.WORK_FACING_ENVELOPE, zones)
        eat_z = _pick(R.EAT_FACING_ENVELOPE, zones)
        sleep_strained = all(zones[z]["cls"] == "needs_care" for z in R.SLEEP_HEAD_ENVELOPE)

        strained = sorted((z for z in R.ZONE_ORDER if zones[z]["cls"] == "needs_care"),
                          key=lambda z: zones[z]["score"])[:2]
        keep_light = [{
            "zone": z, "label": R.ZONE_LABEL[z],
            "why": ("keep your bed head, desk and prayer corner out of this direction; "
                    "tidy and light is all it needs"),
            "src": f"VJ-ZONE-{z}",
        } for z in strained]

        return {
            "available": True,
            "headline": "Your Vastu",
            "directions": {
                "sleep_head": _direction(sleep_z, zones, both_strained=sleep_strained),
                "work_facing": _direction(work_z, zones),
                "eat_facing": _direction(eat_z, zones),
                "keep_light": keep_light,
            },
            "zones": _zone_cards(zones),
            "objects": _objects_view(zones),
            "period": period_line(cd, lk_data, dashas or {}, today, pc, house_lords),
            "info": dict(R.INFO),
            "disclaimer": R.INFO["what_it_isnt"],
            "meta": {"tradition": R.TRADITION, "rules_verified": R.VERIFIED,
                     "version": "0.1"},
        }
    except Exception as e:  # pragma: no cover - degrade, never crash the route
        return {"available": False, "error": str(e)[:160]}
