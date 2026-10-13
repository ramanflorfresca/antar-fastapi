"""
Deterministic Jaimini event engine following K.N. Rao ("Predicting through Jaimini's
Chara Dasha"). No LLM: every output is computed from sign/degree arithmetic, and every
fired rule carries a stable rule id so user feedback can grade rules later.

Not gated on accuracy by owner decision (2026-10-13): gating waits for user feedback.
Rules come from Rao's method (ledger: RULES_LEDGER_kn_rao_chara_dasha section 2).

For each antardasha (sub-period) sign we test Rao's eligibility rules per event and
report which fired. The major-period sign is tested too and counts as context. Ranking
is by number of independent rules fired (a count, not a probability).

Events: marriage, children, education, career, caution (Rao's warning rules).
Optional: Vimshottari rows (cross-check, Rao's "composite technique") and a transit
overlay (Jupiter, Saturn, Rahu, Ketu over/aspecting the sub-period sign).
"""
from datetime import datetime
from typing import Dict, List, Optional

from antar_engine.jaimini_engine import (
    Planet, SIGN_NAMES, SIGN_LORDS, DashaPeriod, compute_7_karakas,
    compute_chara_dasha, get_rashi_drishti, _get_sign_lord, BENEFICS,
)

KENDRA = (1, 4, 7, 10)
TRIKONA = (1, 5, 9)


def _h(frm: int, to: int) -> int:
    """House number (1-12) of sign `to` counted from sign `frm`."""
    return (to - frm) % 12 + 1


def _sign_of(h: int, frm: int) -> int:
    return (frm + h - 1) % 12


def arudha(house_sign: int, planets: Dict[str, Planet]) -> int:
    """Arudha (pada) of a house: lord's distance projected again; if it lands in the
    house itself or its 7th, take the 10th from the house."""
    lord = _get_sign_lord(house_sign, planets)
    lsign = planets[lord].sign
    d = (lsign - house_sign) % 12
    proj = (lsign + d) % 12
    if proj == house_sign or proj == (house_sign + 6) % 12:
        proj = (house_sign + 9) % 12
    return proj


def navamsa_sign(longitude: float) -> int:
    return int((longitude % 360) // (30 / 9)) % 12


def _aspects(src_sign: int, dst_sign: int) -> bool:
    return dst_sign in get_rashi_drishti(src_sign)


def _touches(planet_sign: int, dasha_sign: int) -> bool:
    """Planet in the dasha sign or aspecting it by rasi drishti."""
    return planet_sign == dasha_sign or _aspects(planet_sign, dasha_sign)


class Chart:
    """Pre-computed Jaimini points for one natal chart."""

    def __init__(self, lagna_sign: int, lagna_longitude: float, planets: Dict[str, Planet]):
        self.lagna = lagna_sign
        self.planets = planets
        ks = {k.karaka: k for k in compute_7_karakas(planets)}
        self.k = {name: k.planet for name, k in ks.items()}          # karaka -> planet
        self.k_sign = {name: planets[p].sign for name, p in self.k.items()}
        self.ul = arudha((lagna_sign + 11) % 12, planets)             # upapada
        self.a7 = arudha((lagna_sign + 6) % 12, planets)              # darapada
        self.d9_lagna = navamsa_sign(lagna_longitude)
        self.lord7 = _get_sign_lord((lagna_sign + 6) % 12, planets)
        self.lord5 = _get_sign_lord((lagna_sign + 4) % 12, planets)
        self.lord10 = _get_sign_lord((lagna_sign + 9) % 12, planets)


def rules_for_sign(c: Chart, s: int) -> Dict[str, List[str]]:
    """Which of Rao's rules fire when `s` is the running sign. Returns {event: [rule_id]}."""
    out: Dict[str, List[str]] = {"marriage": [], "children": [], "education": [],
                                 "career": [], "caution": []}
    P = c.planets

    # ---- Marriage eligibility (any of; wide by Rao's own admission) ----
    dk = c.k_sign["DK"]
    if s == (c.lagna + 6) % 12:
        out["marriage"].append("MAR.7th_from_lagna")
    if _aspects(dk, s):
        out["marriage"].append("MAR.aspected_by_DK")
    if s in ((c.a7 + 6) % 12, (c.ul + 6) % 12):
        out["marriage"].append("MAR.7th_from_darapada_or_upapada")
    if s in (c.d9_lagna, (c.d9_lagna + 6) % 12):
        out["marriage"].append("MAR.navamsa_lagna_or_its_7th")
    if s == (dk + 6) % 12:
        out["marriage"].append("MAR.7th_from_DK")
    if P[c.lord7].sign == s:
        out["marriage"].append("MAR.contains_7th_lord")

    # ---- Children: Putrakaraka in the 5th from the running sign ----
    if _h(s, c.k_sign["PK"]) == 5:
        out["children"].append("CHI.PK_in_5th_from_dasha_sign")

    # ---- Education ----
    ben = [p for p in ("Jupiter", "Venus", "Mercury") if p in P]
    kend_4 = {_sign_of(h, s) for h in (1, 4, 7, 10)}
    if any(P[p].sign in kend_4 for p in ben):
        out["education"].append("EDU.benefic_in_kendra_or_4th")
    fifth = _sign_of(5, s)
    if any(_touches(P[p].sign, fifth) and P[p].sign != fifth for p in ben) or \
            any(P[p].sign == fifth for p in ben):
        out["education"].append("EDU.benefic_on_5th")
    if _touches(c.k_sign["AmK"], fifth):
        out["education"].append("EDU.AmK_on_5th")

    # ---- Career ----
    amk_h = _h(s, c.k_sign["AmK"])
    if amk_h in (10, 11):
        out["career"].append("CAR.AmK_10th_or_11th_from_dasha_sign")   # Rao: peak
    elif amk_h in KENDRA or amk_h in TRIKONA:
        out["career"].append("CAR.AmK_kendra_or_trikona_from_dasha_sign")  # smooth
    if _touches(c.k_sign["AmK"], s) and c.k_sign["AmK"] != s:
        out["career"].append("CAR.AmK_aspects_dasha_sign")
    # Rajayoga: both members of an AK/AmK/PK/DK/5th-lord pair touch the sign
    pair_signs = {"AK": c.k_sign["AK"], "AmK": c.k_sign["AmK"], "PK": c.k_sign["PK"],
                  "DK": c.k_sign["DK"], "5L": P[c.lord5].sign}
    names = list(pair_signs)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            if pair_signs[a] != pair_signs[b] and \
                    _touches(pair_signs[a], s) and _touches(pair_signs[b], s):
                out["career"].append(f"CAR.rajayoga_{a}_{b}_on_dasha_sign")

    # ---- Rao's caution rules ----
    if _h(s, c.k_sign["AK"]) == 8:
        out["caution"].append("CAU.AK_8th_from_running_sign")
    if s == c.k_sign["AK"]:
        out["caution"].append("CAU.AK_sign_period_fall_risk")
    if s == 8:
        out["caution"].append("CAU.sagittarius_period_accident_or_sudden_illness")
    if s == _sign_of(6, c.lagna):
        out["caution"].append("CAU.sixth_house_sign_period")
    return out


def _vim_planets(c: Chart) -> Dict[str, List[str]]:
    P = c.planets
    return {
        "marriage": [c.k["DK"], c.lord7, "Venus"],
        "children": [c.k["PK"], c.lord5, "Jupiter"],
        "education": [c.k["AmK"], c.lord5, "Mercury", "Jupiter"],
        "career": [c.k["AmK"], c.lord10],
    }


def _vim_hit(c: Chart, event: str, vim_rows: Optional[list], start: datetime, end: datetime):
    if not vim_rows or event not in _vim_planets(c):
        return None
    want = set(_vim_planets(c)[event])
    mid = start + (end - start) / 2
    for r in vim_rows:
        s = r["start_date"]; e = r["end_date"]
        if s <= mid < e and (r.get("planet") in want or r.get("lord") in want):
            return r.get("planet") or r.get("lord")
    return None


def _transit_context(sign: int, when: datetime) -> List[str]:
    """Jupiter/Saturn/Rahu/Ketu over or aspecting the sub-period sign (sidereal Lahiri)."""
    try:
        import swisseph as swe
    except ImportError:
        return []
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    jd = swe.julday(when.year, when.month, when.day, 12.0)
    flags = swe.FLG_SIDEREAL | swe.FLG_SWIEPH
    pos = {"Jupiter": swe.JUPITER, "Saturn": swe.SATURN, "Rahu": swe.MEAN_NODE}
    notes = []
    for name, pid in pos.items():
        lon = swe.calc_ut(jd, pid, flags)[0][0]
        ts = int(lon // 30) % 12
        if name == "Rahu":
            for nm, t in (("Rahu", ts), ("Ketu", (ts + 6) % 12)):
                if t == sign:
                    notes.append(f"{nm} transits {SIGN_NAMES[sign]}")
                elif _aspects(t, sign):
                    notes.append(f"{nm} (in {SIGN_NAMES[t]}) aspects {SIGN_NAMES[sign]}")
        elif ts == sign:
            notes.append(f"{name} transits {SIGN_NAMES[sign]}")
        elif _aspects(ts, sign):
            notes.append(f"{name} (in {SIGN_NAMES[ts]}) aspects {SIGN_NAMES[sign]}")
    return notes


def predict_windows(lagna_sign: int, lagna_longitude: float, planets: Dict[str, Planet],
                    birth_date: datetime, start: datetime, end: datetime,
                    vim_rows: Optional[list] = None, with_transits: bool = True,
                    min_rules: int = 2) -> List[dict]:
    """All antardasha windows in [start, end] where an event has >= min_rules rules fired
    (sub-period sign) — ordered by date. Each window lists events with rule ids."""
    c = Chart(lagna_sign, lagna_longitude, planets)
    mds = compute_chara_dasha(lagna_sign, planets, birth_date, num_cycles=3)
    md_rules = {md.sign: rules_for_sign(c, md.sign) for md in mds}
    results = []
    for md in mds:
        for ad in md.sub_periods:
            if ad.end_date < start or ad.start_date > end:
                continue
            ar = rules_for_sign(c, ad.sign)
            events = []
            for ev in ("marriage", "children", "education", "career"):
                fired = ar[ev]
                if len(fired) < min_rules:
                    continue
                ctx = md_rules[md.sign][ev]
                vim = _vim_hit(c, ev, vim_rows, ad.start_date, ad.end_date)
                events.append({
                    "event": ev,
                    "rules": fired,
                    "md_context_rules": ctx,
                    "vimshottari_agrees": vim,
                    "score": len(fired) + 0.5 * len(ctx) + (1 if vim else 0),
                })
            cautions = ar["caution"] + [r for r in md_rules[md.sign]["caution"] if r not in ar["caution"]]
            if _h(md.sign, ad.sign) in (6, 8):
                cautions.append("CAU.sub_sign_6th_or_8th_from_major_sign")
            if not events and not cautions:
                continue
            mid = ad.start_date + (ad.end_date - ad.start_date) / 2
            results.append({
                "start": ad.start_date, "end": ad.end_date,
                "major": SIGN_NAMES[md.sign], "sub": SIGN_NAMES[ad.sign],
                "events": sorted(events, key=lambda e: -e["score"]),
                "cautions": cautions,
                "transits": _transit_context(ad.sign, mid) if with_transits and events else [],
            })
    return results
