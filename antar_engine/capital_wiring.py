"""
antar_engine/capital_wiring.py

Capital WIRING: which house-lords of a chart are connected to which, read as a
DESCRIPTION of how capital moves for this person — channel, live connections,
drains, cautions. Deterministic, no LLM, no DB. Never raises.

HARD BOUNDARY (same as domain_fit / money_flow): this module emits SHAPE and
CAUTIONS only. It emits no funding verdict, no capacity tier and no timing
window. The classical wealth-timing rules and dhana-yoga linkage rules were
case-control tested in this repo and came out at chance (see
tests/negative_result_success_prediction.md, tests/negative_result_d2_wealth_chain.md);
nothing here is validated until tests/capital_wiring_casecontrol.py says so.
Every result carries "validated": False.

SIGNAL INDEPENDENCE: one physical fact can satisfy several house-pair wires
(a planet ruling the 5th and 8th that aspects the 11th makes 8-11 AND 5-11).
Wires therefore carry an `evidence` key; `independent_count` counts distinct
evidence, never wires.

Connection kinds between two houses X, Y (lords lx, ly):
    conjunction   lx and ly share a house
    exchange      each sits in a sign the other rules (parivartana)
    mutual_aspect each casts a graha-drishti on the other
    aspect        one-way graha-drishti (lx on ly or ly on lx)
    placement     lx sits in house Y, or ly sits in house X
`strict` = conjunction | exchange | mutual_aspect. The harness compares the
strict-only and the inclusive definitions, because the spec counts one-way
aspect and the earlier failed dhana test did not.

Public API:
    analyze_capital_wiring(chart_data) -> dict
"""
from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
SIGN_LORD = ["Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
             "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"]
EXALT = {"Sun": "Aries", "Moon": "Taurus", "Mars": "Capricorn",
         "Mercury": "Virgo", "Jupiter": "Cancer", "Venus": "Pisces",
         "Saturn": "Libra"}
DEBIL = {"Sun": "Libra", "Moon": "Scorpio", "Mars": "Cancer",
         "Mercury": "Pisces", "Jupiter": "Capricorn", "Venus": "Virgo",
         "Saturn": "Aries"}
OWN = {"Sun": ("Leo",), "Moon": ("Cancer",), "Mars": ("Aries", "Scorpio"),
       "Mercury": ("Gemini", "Virgo"), "Jupiter": ("Sagittarius", "Pisces"),
       "Venus": ("Taurus", "Libra"), "Saturn": ("Capricorn", "Aquarius")}
# Combustion orbs in degrees from the Sun (standard Parashari set).
COMBUST_ORB = {"Moon": 12, "Mars": 17, "Mercury": 14, "Jupiter": 11,
               "Venus": 10, "Saturn": 15}
DUSTHANA = (6, 8, 12)
_SPECIAL_ASPECT = {"Mars": (4, 8), "Jupiter": (5, 9), "Saturn": (3, 10)}

# ── The wires (spec sections 3.1-3.3) ───────────────────────────────────
GOLDEN = [  # (houses, label)
    ((8, 11), "raised capital becomes gains"),
    ((6, 11), "debt-funded growth"),
    ((8, 10), "leverage builds public standing"),
    ((10, 11), "career generates revenue"),
    ((5, 11), "equity and speculation convert to gains"),
    ((2, 11), "income compounds"),
    ((9, 8), "grace capital: grants, mentors, foreign money"),
    ((9, 11), "grace capital: grants, mentors, foreign money"),
]
DRAIN = [  # (houses, label)
    ((8, 12), "raised money evaporates in burn or bad deployment"),
    ((6, 8), "debt on debt; refinancing spiral"),
    ((2, 12), "savings erode"),
    ((11, 12), "gains leak to expenditure"),
]
EVENT = [
    ((5, 8), "equity raises, share issuance, ESOP wealth"),
    ((7, 8), "investment or acquisition through a partner"),
    ((12, 8), "foreign capital (clean only when the 11th is also sound)"),
]


# ── primitives ──────────────────────────────────────────────────────────
def _planets(cd: dict) -> Dict[str, dict]:
    return {p: v for p, v in ((cd or {}).get("planets") or {}).items()
            if isinstance(v, dict)}


def _lagna_index(cd: dict) -> Optional[int]:
    lg = (cd or {}).get("lagna") or {}
    i = lg.get("sign_index")
    if isinstance(i, int) and 0 <= i <= 11:
        return i
    s = lg.get("sign")
    return SIGNS.index(s) if s in SIGNS else None


def _sign_idx(v: dict) -> Optional[int]:
    if isinstance(v.get("sign_index"), int):
        return v["sign_index"] % 12
    if v.get("sign") in SIGNS:
        return SIGNS.index(v["sign"])
    lon = v.get("longitude")
    return int(lon // 30) % 12 if isinstance(lon, (int, float)) else None


class _Chart:
    """Whole-sign view: house of each planet, lord of each house."""

    def __init__(self, cd: dict):
        self.cd = cd
        self.li = _lagna_index(cd)
        pl = _planets(cd)
        self.house: Dict[str, int] = {}
        self.sign: Dict[str, int] = {}
        self.lon: Dict[str, float] = {}
        if self.li is None:
            return
        for p, v in pl.items():
            si = _sign_idx(v)
            if si is None:
                continue
            self.sign[p] = si
            self.house[p] = ((si - self.li) % 12) + 1
            if isinstance(v.get("longitude"), (int, float)):
                self.lon[p] = float(v["longitude"])

    @property
    def ok(self) -> bool:
        return self.li is not None and len(self.house) >= 7

    def lord(self, h: int) -> str:
        return SIGN_LORD[(self.li + h - 1) % 12]

    def sign_name(self, p: str) -> Optional[str]:
        return SIGNS[self.sign[p]] if p in self.sign else None

    def aspects(self, a: str, b: str) -> bool:
        """Graha-drishti by house distance. Nodes cast none (contested)."""
        if a not in self.house or b not in self.house or a in ("Rahu", "Ketu"):
            return False
        dist = ((self.house[b] - self.house[a]) % 12) + 1
        return dist == 7 or dist in _SPECIAL_ASPECT.get(a, ())

    def combust(self, p: str) -> bool:
        orb = COMBUST_ORB.get(p)
        if orb is None or p not in self.lon or "Sun" not in self.lon:
            return False
        sep = abs(((self.lon[p] - self.lon["Sun"] + 180) % 360) - 180)
        return sep <= orb

    def dignity(self, p: str) -> str:
        s = self.sign_name(p)
        if s is None:
            return "unknown"
        if EXALT.get(p) == s:
            return "exalted"
        if DEBIL.get(p) == s:
            return "debilitated"
        if s in OWN.get(p, ()):
            return "own"
        return "neutral"

    def weak(self, p: str) -> bool:
        """Weak = debilitated or combust. Deliberately NOT 'in a dusthana':
        malefics in 6/8 are not weak (Harsha), and Saturn-in-8th is a
        specialisation, not a deficiency (spec section 2)."""
        return self.dignity(p) == "debilitated" or self.combust(p)


def _house_link(c: _Chart, x: int, y: int) -> Optional[dict]:
    """How the lords of houses x and y are connected, or None.

    Returns {kinds, strict, evidence, planets}. A planet ruling both houses is
    reported as shared_lord=True and is NOT a connection (no independent fact).
    """
    lx, ly = c.lord(x), c.lord(y)
    if lx == ly:
        return {"kinds": ["shared_lord"], "strict": False, "shared_lord": True,
                "evidence": (), "planets": (lx, ly)}
    if lx not in c.house or ly not in c.house:
        return None
    kinds: List[str] = []
    ev: List[tuple] = []
    pair = tuple(sorted((lx, ly)))
    if c.house[lx] == c.house[ly]:
        kinds.append("conjunction"); ev.append(("pair", pair))
    if (c.sign_name(lx) is not None and c.sign_name(ly) is not None
            and SIGN_LORD[c.sign[lx]] == ly and SIGN_LORD[c.sign[ly]] == lx):
        kinds.append("exchange"); ev.append(("pair", pair))
    a_xy, a_yx = c.aspects(lx, ly), c.aspects(ly, lx)
    if a_xy and a_yx:
        kinds.append("mutual_aspect"); ev.append(("pair", pair))
    elif a_xy or a_yx:
        kinds.append("aspect"); ev.append(("pair", pair))
    if c.house[lx] == y:
        kinds.append("placement"); ev.append(("in", lx, y))
    if c.house[ly] == x:
        kinds.append("placement"); ev.append(("in", ly, x))
    if not kinds:
        return None
    strict = any(k in ("conjunction", "exchange", "mutual_aspect") for k in kinds)
    return {"kinds": sorted(set(kinds)), "strict": strict, "shared_lord": False,
            "evidence": tuple(sorted(set(ev), key=repr)), "planets": (lx, ly)}


def _wires(c: _Chart, table) -> List[dict]:
    out = []
    for (x, y), label in table:
        lk = _house_link(c, x, y)
        if lk and not lk["shared_lord"]:
            out.append({"houses": (x, y), "label": label, "lords": lk["planets"],
                        "kinds": lk["kinds"], "strict": lk["strict"],
                        "evidence": lk["evidence"]})
    return out


def _independent(wires: List[dict], strict_only: bool = False) -> int:
    keys: Set[tuple] = set()
    for w in wires:
        if strict_only and not w["strict"]:
            continue
        keys.update(w["evidence"])
    return len(keys)


def _linked(c: _Chart, x: int, y: int, strict_only: bool = False) -> bool:
    lk = _house_link(c, x, y)
    return bool(lk and not lk["shared_lord"] and (lk["strict"] or not strict_only))


# ── drains / hard flags (spec 3.2) ──────────────────────────────────────
def _hard_flags(c: _Chart) -> List[dict]:
    flags = []
    l11 = c.lord(11)
    if c.house.get(l11) in DUSTHANA:
        flags.append({"id": "gains_in_dusthana", "severity": "hard",
                      "text": f"The lord of gains ({l11}) sits in the {c.house[l11]}th "
                              "house, so gains tend to get trapped."})
    for w in _wires(c, DRAIN):
        sev = "caution"
        if (w["houses"] == (6, 8)) and not _saturn_sound(c):
            sev = "hard"
        flags.append({"id": "drain_%d_%d" % w["houses"], "severity": sev,
                      "text": w["label"], "kinds": w["kinds"]})
    return flags


def _saturn_sound(c: _Chart) -> bool:
    return "Saturn" in c.house and not c.weak("Saturn")


# ── blowup audit (spec section 6) ───────────────────────────────────────
def _audit(c: _Chart) -> List[dict]:
    out = []
    node_h = c.house.get("Rahu")
    if node_h == 8 and not _saturn_sound(c):
        out.append({"id": "rahu8_weak_saturn", "text":
                    "Capital can be raised, but with Saturn weak the leverage tends "
                    "to come due later."})
    elif node_h == 8:
        out.append({"id": "rahu8_saturn_ok", "text":
                    "Rahu in the 8th delivers raises; Saturn is sound, which is "
                    "what keeps the structure from outrunning itself."})
    if c.house.get("Jupiter") == 8 and not _linked(c, 8, 11):
        out.append({"id": "jupiter8_custodian", "text":
                    "Jupiter in the 8th without a link to the gains house: handles "
                    "other people's money more easily than it keeps any."})
    if c.house.get("Jupiter") == 8:
        out.append({"id": "jupiter8_guarantee", "text":
                    "Raising is easy here; watch guarantees, co-signing and "
                    "exposure to other people's defaults."})
    if _linked(c, 6, 8) and not _saturn_sound(c):
        out.append({"id": "spiral_6_8", "text":
                    "Debt-on-debt wiring with a weak Saturn: refinancing spiral "
                    "risk. Don't lean on borrowed money."})
    if c.house.get("Ketu") in (2, 11):
        out.append({"id": "ketu_2_11", "text":
                    "Ketu in a money house undercuts retention: equity or income "
                    "can slip away (splits, secondaries)."})
    for h in (2, 11):
        l = c.lord(h)
        if c.combust(l):
            out.append({"id": "combust_%d" % h, "text":
                        f"The lord of the {h}th is combust: money exists on paper "
                        "but realising it takes friction."})
    return out


# ── viparita (spec 3.4), natal only ─────────────────────────────────────
def _viparita(c: _Chart) -> List[dict]:
    out = []
    for src in DUSTHANA:
        l = c.lord(src)
        h = c.house.get(l)
        if h in DUSTHANA and h != src:
            out.append({"lord_of": src, "in_house": h, "planet": l})
    return out


# ── arudha (spec section 4) ─────────────────────────────────────────────
def _arudha(cd: dict, c: _Chart) -> dict:
    try:
        from antar_engine.special_lagnas import all_references
        ref = (all_references(cd) or {}).get("arudha")
    except Exception:
        ref = None
    if not ref:
        return {"available": False}
    al = ref["sign_index"]
    li = c.li
    house = lambda s: ((s - li) % 12) + 1
    from_al = lambda n: (al + n - 1) % 12
    l11_al = SIGN_LORD[from_al(11)]
    l2_al = SIGN_LORD[from_al(2)]
    occ11 = [p for p, s in c.sign.items() if s == from_al(11)]
    occ2 = [p for p, s in c.sign.items() if s == from_al(2)]
    lagna_gain_ok = c.house.get(c.lord(11)) not in DUSTHANA
    al_gain_ok = (c.house.get(l11_al) not in DUSTHANA) and not c.weak(l11_al)
    return {
        "available": True,
        "al_sign": SIGNS[al], "al_house_from_lagna": house(al),
        "second_from_al": {"sign": SIGNS[from_al(2)], "lord": l2_al, "occupants": occ2},
        "eleventh_from_al": {"sign": SIGNS[from_al(11)], "lord": l11_al, "occupants": occ11},
        "lagna_gains_sound": lagna_gain_ok,
        "al_gains_sound": al_gain_ok,
        "diverges": lagna_gain_ok != al_gain_ok,
    }


# ── archetype (spec section 8): strongest WIRING pattern ────────────────
def _archetypes(c: _Chart, wires_by: Dict[tuple, dict], vip: List[dict]) -> List[str]:
    has = lambda x, y: (x, y) in wires_by or (y, x) in wires_by
    l8 = c.lord(8)
    rahu_wired = c.house.get("Rahu") in (8, 11, 5) or any(
        c.house.get("Rahu") == c.house.get(c.lord(h)) for h in (8, 11, 5))
    found = []
    if has(8, 11) and has(5, 11) and rahu_wired:
        found.append("vc_backed")
    if has(6, 11) and has(6, 10) and not _linked(c, 6, 8) and _saturn_sound(c):
        found.append("debt_financed_operator")
    if has(2, 11) and not has(8, 11):
        found.append("bootstrapper")
    if has(7, 8) and has(7, 11):
        found.append("strategic_partner_builder")
    if has(10, 11) and c.dignity("Sun") in ("exalted", "own") and "Moon" in c.house:
        found.append("public_market_founder")
    # custodian: strong 8th (lord not weak, not in 12th), but NO 8-11 link.
    if (not has(8, 11) and not c.weak(l8) and c.house.get(l8) != 12
            and (c.house.get("Jupiter") == 8 or c.house.get(l8) == 8
                 or c.dignity(l8) in ("exalted", "own"))):
        found.append("custodian")
    if vip and c.house.get(c.lord(11)) in DUSTHANA:
        found.append("comeback")
    return found


_CHANNEL_TEXT = {
    "vc_backed": "outside equity capital: investors and raises",
    "debt_financed_operator": "credit and working capital",
    "bootstrapper": "your own income compounding; leverage is optional here",
    "strategic_partner_builder": "partners and strategic money",
    "public_market_founder": "public standing and market capital",
    "custodian": "other people's money passes through you more easily than it stays",
    "comeback": "recovery from a low: turnarounds and distressed situations",
}


def analyze_capital_wiring(chart_data: dict) -> dict:
    """Descriptive capital wiring. Never raises. validated is always False."""
    base = {"available": False, "validated": False}
    try:
        c = _Chart(chart_data if isinstance(chart_data, dict) else {})
        if not c.ok:
            return base
        golden = _wires(c, GOLDEN)
        event = _wires(c, EVENT)
        flags = _hard_flags(c)
        audit = _audit(c)
        vip = _viparita(c)
        wires_by = {w["houses"]: w for w in golden}
        # A wire the archetype test may look up in either order.
        archetypes = _archetypes(c, wires_by, vip)

        # Top live connections: strict first, then by independent evidence.
        ranked = sorted(golden, key=lambda w: (not w["strict"], -len(w["evidence"])))
        top, seen = [], set()
        for w in ranked:
            if set(w["evidence"]) <= seen:
                continue   # restates a connection already listed
            seen.update(w["evidence"])
            top.append({"houses": w["houses"], "meaning": w["label"],
                        "lords": w["lords"], "kinds": w["kinds"]})
            if len(top) == 3:
                break

        hard = [f for f in flags if f["severity"] == "hard"]
        sentence = ("This describes how capital is wired in the chart. It is not "
                    "a forecast of funding, and no timing rule behind it has been "
                    "validated.")
        return {
            "available": True,
            "validated": False,
            "archetypes": archetypes,
            "channel": [_CHANNEL_TEXT[a] for a in archetypes],
            "wiring": top,
            "wires": [{k: v for k, v in w.items() if k != "evidence"} for w in golden],
            "event_wires": [{"houses": w["houses"], "meaning": w["label"],
                             "kinds": w["kinds"]} for w in event],
            "independent_count": _independent(golden),
            "independent_count_strict": _independent(golden, strict_only=True),
            "drains": flags,
            "has_hard_drain": bool(hard),
            "audit": audit,
            "viparita": vip,
            "arudha": _arudha(chart_data, c),
            "honest_line": sentence,
        }
    except Exception as e:
        base["error"] = str(e)[:160]
        return base
