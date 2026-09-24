"""
antar_engine/chara_dasha.py
Proper Jaimini Chara-daśā activation — event-prediction logic, not a boolean. 2026-09-24

Owner's direction (chart-owner, experienced): the running chara sign is read as
the period's lagna, and the PERIOD'S QUALITY comes from where the Ātmakāraka (AK,
the soul/direction) and Amātyakāraka (AmK, the career/minister — the worldly-event
karaka) fall FROM that sign:

  • kendra (1/4/7/10), trikoṇa (1/5/9), and the 11th  → a strong, delivering period
  • dusthāna (6/8/12)                                 → weaker for that karaka…
      …BUT SOFT: own-/exalted-/friendly-sign and a Jaimini rāśi-dṛṣṭi from AK/AmK
      or a benefic can lift a dusthāna karaka back to neutral or positive. So an
      AmK in the 8th that is well-supported (the owner's Elon example) reads strong,
      never auto-weak.

This replaces the old `jaimini_active = houses & {chara-sign's house}` boolean in
house_activation. It returns a GRADED per-house activation the scorer folds in,
plus a plain "why" (no planet/house/Sanskrit ever reaches the user).

Deterministic; never raises. The AmK weighs more than the AK for worldly domain
activation (the minister runs events); the AK tilts self/direction.
"""
from __future__ import annotations

from typing import Optional

_SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
          "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
_SIGN_IDX = {s: i for i, s in enumerate(_SIGNS)}

_OWN = {"Mars": {0, 7}, "Venus": {1, 6}, "Mercury": {2, 5}, "Moon": {3},
        "Sun": {4}, "Jupiter": {8, 11}, "Saturn": {9, 10}}
_EXALT = {"Sun": 0, "Moon": 1, "Mars": 9, "Mercury": 5,
          "Jupiter": 3, "Venus": 11, "Saturn": 6}
_BENEFICS = {"Jupiter", "Venus", "Mercury", "Moon"}

_KENDRA = {1, 4, 7, 10}
_TRIKONA = {1, 5, 9}
_DUSTHANA = {6, 8, 12}


def _sign_idx(name) -> Optional[int]:
    if name is None:
        return None
    if isinstance(name, int):
        return name % 12
    return _SIGN_IDX.get(str(name).strip().title())


def _house_from(ref_idx: int, sign_idx: int) -> int:
    """1..12: which house `sign_idx` is, counting the ref sign as the 1st."""
    return ((sign_idx - ref_idx) % 12) + 1


def _rashi_aspects(idx: int) -> set:
    """Jaimini rāśi-dṛṣṭi: movable signs aspect the fixed signs (bar the adjacent
    one), fixed aspect the movable (bar the adjacent), dual aspect the other dual."""
    movable, fixed, dual = {0, 3, 6, 9}, {1, 4, 7, 10}, {2, 5, 8, 11}
    if idx in movable:
        return {f for f in fixed if f != (idx + 1) % 12}
    if idx in fixed:
        return {m for m in movable if m != (idx - 1) % 12}
    return {d for d in dual if d != idx}


def _occupied_signs(chart_data: dict) -> dict:
    """sign_idx -> set of planets occupying it (for aspect-support checks)."""
    out: dict = {}
    for p, v in ((chart_data or {}).get("planets") or {}).items():
        si = _sign_idx((v or {}).get("sign"))
        if si is not None:
            out.setdefault(si, set()).add(str(p).title())
    return out


def _karaka_strength(planet: str, karaka_sign_idx: int, house_from_dasha: int,
                     occupied: dict) -> tuple:
    """(score in ~[-0.5, +1.0], plain-note) for one karaka, from its house
    relative to the chara sign. Dusthāna is a SOFT negative that own/exalted/
    friendly-sign and a benefic (or AK/AmK) rāśi-aspect can lift back up."""
    h = house_from_dasha
    # base by house
    if h == 11:
        base, why = 0.9, "brings gains and things coming to fruition"
    elif h in _KENDRA:
        base, why = 0.7, "gives it real footing to act from"
    elif h in _TRIKONA:            # 5th/9th (1 already covered by kendra)
        base, why = 0.65, "carries fortune and support"
    elif h in _DUSTHANA:
        base, why = -0.4, "runs against some friction this period"
    elif h == 3:
        base, why = 0.3, "asks for effort but rewards it"
    elif h in (2,):
        base, why = 0.25, "steadies resources"
    else:                          # 12 handled in dusthana; leftover neutral
        base, why = 0.1, "sits quietly"

    lift = 0.0
    lifts = []
    own = karaka_sign_idx in _OWN.get(planet, set())
    exalt = _EXALT.get(planet) == karaka_sign_idx
    if own:
        lift += 0.4; lifts.append("in its own sign")
    elif exalt:
        lift += 0.45; lifts.append("exalted")
    # [upachaya 2026-09-24] Owner's rule: the growing/fighting grahas do WELL in
    # the upachaya houses (3/6/10/11) — "Mars or Mercury in the 6th is good."
    # So a karaka that is one of those planets in an upachaya house from the
    # chara sign gets a lift that offsets the 6th's dusthāna base.
    if h in (3, 6, 10, 11) and planet in ("Mars", "Saturn", "Mercury", "Sun", "Rahu", "Ketu"):
        lift += 0.35; lifts.append("a fighter's house that suits it")
    # Jaimini rāśi-aspect support: any benefic occupying a sign that aspects the
    # karaka's sign (own aspects excluded) softens/strengthens it.
    aspect_support = False
    for si, planets in (occupied or {}).items():
        if si == karaka_sign_idx:
            continue
        if karaka_sign_idx in _rashi_aspects(si) and (planets & _BENEFICS):
            aspect_support = True
            break
    if aspect_support:
        lift += 0.3; lifts.append("held up by a supportive aspect")

    final = base + lift
    # SOFT rule: a dusthāna karaka that is own/exalted/aspect-supported climbs to
    # neutral-or-better rather than staying penalised (the Elon AmK-in-8th case).
    if h in _DUSTHANA and lift > 0:
        final = min(0.5, base + lift)   # cap the rescued dusthāna at moderate-good
    final = max(-0.5, min(1.0, final))  # bound to [-0.5, 1.0]
    note = why + ((" — " + ", ".join(lifts)) if lifts else "")
    return round(final, 3), note


def chara_activation(chart_data: dict, jaimini_data: dict, dashas: dict,
                     lagna_idx: int, today_iso: str) -> dict:
    """Graded activation from the running Jaimini chara dāśā.

    Returns {available, sign, sign_house, strength (-1..1), houses {h: weight 0..1},
    karaka_reads[], why}. `houses` is what house_activation folds into scoring;
    everything else is for narration/debug. Empty/degraded → available False."""
    try:
        cd = chart_data if isinstance(chart_data, dict) else {}
        jd = jaimini_data if isinstance(jaimini_data, dict) else {}
        if not cd.get("planets"):
            return {"available": False}

        # --- current chara sign (running today) ---
        chara_sign_idx = None
        for key in ("jaimini", "chara"):
            for p in ((dashas or {}).get(key) or []):
                if not isinstance(p, dict):
                    continue
                s = str(p.get("start_date") or p.get("start") or "")[:10]
                e = str(p.get("end_date") or p.get("end") or "")[:10]
                sign = p.get("lord_or_sign") or p.get("planet_or_sign") or p.get("sign")
                if s and e and s <= today_iso <= e and _sign_idx(sign) is not None:
                    chara_sign_idx = _sign_idx(sign)
                    break
            if chara_sign_idx is not None:
                break
        if chara_sign_idx is None:
            return {"available": False}

        # --- AK / AmK from the karaka scheme ---
        kar = jd.get("karakas") or jd.get("chara_karakas") or []
        ak = next((k for k in kar if str(k.get("karaka")).upper() == "AK"), None)
        amk = next((k for k in kar if str(k.get("karaka")).upper() == "AMK"), None)

        occupied = _occupied_signs(cd)
        planets = cd.get("planets") or {}

        def _natal_house(planet):
            v = planets.get(planet) or {}
            return v.get("house")

        houses: dict = {}
        karaka_reads = []
        strength = 0.0

        # weights: the AmK (minister) drives worldly events; the AK tilts direction
        for karaka, weight in ((amk, 0.62), (ak, 0.38)):
            if not karaka:
                continue
            planet = str(karaka.get("planet") or "").title()
            ksi = _sign_idx(karaka.get("sign_name") or karaka.get("sign"))
            if ksi is None:
                continue
            hfrom = _house_from(chara_sign_idx, ksi)
            sc, note = _karaka_strength(planet, ksi, hfrom, occupied)
            strength += sc * weight
            # route the activation to the karaka's NATAL house (where it delivers)
            nh = _natal_house(planet)
            if isinstance(nh, int) and 1 <= nh <= 12:
                # positive karaka lights its house; a weak/negative one barely does
                houses[nh] = max(houses.get(nh, 0.0), round(max(0.0, sc) * weight + 0.2, 3))
            karaka_reads.append({
                "karaka": karaka.get("karaka"), "planet": planet,
                "house_from_chara": hfrom, "score": sc, "note": note,
            })

        # the chara sign's own house + its 7th (the dāśā axis) always carry a base
        sign_house = _house_from(lagna_idx, chara_sign_idx) if lagna_idx is not None else None
        base_axis = round(0.3 + max(0.0, strength) * 0.4, 3)
        if sign_house:
            houses[sign_house] = max(houses.get(sign_house, 0.0), base_axis)
            seventh = ((sign_house - 1 + 6) % 12) + 1
            houses[seventh] = max(houses.get(seventh, 0.0), round(base_axis * 0.7, 3))

        return {
            "available": True,
            "sign": _SIGNS[chara_sign_idx],
            "sign_house": sign_house,
            "strength": round(max(-1.0, min(1.0, strength)), 3),
            "houses": {int(h): float(w) for h, w in houses.items() if w > 0},
            "karaka_reads": karaka_reads,
            "why": _plain_why(strength, karaka_reads),
        }
    except Exception as e:
        return {"available": False, "error": str(e)[:160]}


def _plain_why(strength: float, karaka_reads: list) -> str:
    """One plain sentence — no planet/house/Sanskrit. Describes the period's tenor."""
    if strength >= 0.45:
        lead = "This is a genuinely delivering stretch — the timing supports real moves"
    elif strength >= 0.15:
        lead = "This is a workable stretch — steady progress if you stay engaged"
    elif strength >= -0.1:
        lead = "This is a mixed stretch — some doors open, some ask for patience"
    else:
        lead = "This is a demanding stretch — better for consolidating than launching"
    return lead + "."
