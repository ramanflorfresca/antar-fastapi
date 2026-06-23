"""
kp_significators.py  —  Agent 2: significator + house-grouping verdict engine
=============================================================================

Consumes a KP chart from kp_chart.compute_kp_chart() and produces a structured,
jargon-free verdict bundle. Python decides everything; narration only renders.

----------------------------------------------------------------------------
THE 4-LEVEL KP SIGNIFICATOR HIERARCHY (strongest -> weakest), per house H
----------------------------------------------------------------------------
  L1  planets in the STAR (nakshatra) of the OCCUPANTS of H   (strongest)
  L2  the OCCUPANTS of H                                       (planets in H)
  L3  planets in the STAR of the OWNER of H                    (cusp sign-lord)
  L4  the OWNER of H                                           (weakest)

NODE AGENCY (Rahu / Ketu) — explicit, deterministic rule:
  A node is a powerful agent. It signifies the union of:
    (a) the house it OCCUPIES,
    (b) the houses signified by its STAR-LORD (planet in whose nakshatra it sits),
    (c) the houses signified by any planet it is CONJOINED with (same house),
    (d) the house owned (by sign) by the sign-lord of the sign it tenants
        — only via that sign-lord's own significations.
  A node is also counted as an OCCUPANT (L2) of its house. When a node is itself
  the star-lord of a planet, that planet inherits the node's agency houses (the
  node "passes through" to the planets it represents). This is the standard KP
  treatment and is applied symmetrically in build_significators().

----------------------------------------------------------------------------
HOUSE GROUPING PER QUESTION TYPE (QUESTION_TYPES table below)
----------------------------------------------------------------------------
  GAIN / deal-closes / speculation  -> favourable {2,6,11}; spoilers {8,12}.
        MATERIALIZATION GATE: the 11th cuspal sub-lord must signify the 11th
        (fulfilled desire flows through the 11th). Hard gate on any "will it
        happen / will I gain" question.
  LOSS / negation  -> Bhavat Bhavam: loss of house X = 12th-from-X.

VERDICT RULE: the relevant CUSPAL SUB-LORD's significators decide yes/no — NOT
house strength. confidence = count of independent KP confirmations (0-3).

Output: {verdict: 'yes'|'no'|'conditional', confidence: 0-3,
         drivers: [structured, jargon-free], debug: {...}}
"""

from .kp_chart import SIGN_LORDS, SIGNS  # noqa: F401  (SIGNS handy for callers)

CLASSICAL = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
NODES = ["Rahu", "Ketu"]
ALL_PLANETS = CLASSICAL + NODES


# --------------------------------------------------------------------------
# Question-type house groupings.  primary_cusp = the cusp whose sub-lord rules.
# favour = houses that mean YES for the matter; against = spoilers (NO).
# materialization_gate = require 11th CSL to signify 11 (desire-fulfilment).
# --------------------------------------------------------------------------
QUESTION_TYPES = {
    # gain / money / deal / speculation / "will it happen"
    "gain": {
        "primary_cusp": 11, "favour": [2, 6, 11], "against": [5, 8, 12],
        "materialization_gate": True,
        "label": {"yes": "It comes through", "no": "It does not come through"},
    },
    "money": {
        "primary_cusp": 11, "favour": [2, 6, 11], "against": [5, 8, 12],
        "materialization_gate": True,
        "label": {"yes": "Money flows in", "no": "Money does not flow in"},
    },
    "deal_closes": {
        "primary_cusp": 11, "favour": [2, 6, 11], "against": [5, 8, 12],
        "materialization_gate": True,
        "label": {"yes": "The deal closes", "no": "The deal does not close"},
    },
    "speculation": {
        "primary_cusp": 11, "favour": [2, 5, 6, 11], "against": [8, 12],
        "materialization_gate": True,
        "label": {"yes": "The bet pays", "no": "The bet does not pay"},
    },
    # new job / employment secured
    "job_new": {
        "primary_cusp": 6, "favour": [2, 6, 10, 11], "against": [5, 8, 9, 12],
        "materialization_gate": True,
        "label": {"yes": "The role lands", "no": "The role does not land"},
    },
    # promotion / advancement
    "promotion": {
        "primary_cusp": 10, "favour": [2, 6, 10, 11], "against": [5, 8, 9, 12],
        "materialization_gate": True,
        "label": {"yes": "The step up comes", "no": "The step up stalls"},
    },
    # marriage / serious partnership begins
    "marriage": {
        "primary_cusp": 7, "favour": [2, 7, 11], "against": [1, 6, 10],
        "materialization_gate": True,
        "label": {"yes": "The union forms", "no": "The union does not form"},
    },
    # property / vehicle acquisition
    "property": {
        "primary_cusp": 4, "favour": [4, 11], "against": [3, 8, 12],
        "materialization_gate": True,
        "label": {"yes": "The purchase happens", "no": "The purchase falls through"},
    },
    # litigation / dispute won
    "litigation_win": {
        "primary_cusp": 6, "favour": [6, 11], "against": [5, 8, 12],
        "materialization_gate": False,
        "label": {"yes": "The dispute goes your way", "no": "The dispute does not"},
    },
    # health recovery
    "recovery": {
        "primary_cusp": 1, "favour": [1, 5, 11], "against": [6, 8, 12],
        "materialization_gate": False,
        "label": {"yes": "Recovery holds", "no": "Recovery is not supported"},
    },
    # generic LOSS / separation / ending — handled via Bhavat Bhavam at runtime
    # by passing question_type='loss' with a loss_house argument to verdict().
}


# --------------------------------------------------------------------------
# Significator construction
# --------------------------------------------------------------------------
def _occupants(chart, house):
    return [p for p in ALL_PLANETS
            if chart["planets"][p].get("house") == house]


def _owner(chart, house):
    return chart["cusps"][house]["sign_lord"]


def _star_lord(chart, planet):
    return chart["planets"][planet]["star_lord"]


def _planets_in_star_of(chart, lord):
    """Planets whose star-lord == `lord`."""
    return [p for p in ALL_PLANETS if _star_lord(chart, p) == lord]


def build_house_significators(chart):
    """
    Return {H: {'L1':[...], 'L2':[...], 'L3':[...], 'L4':[...], 'ranked':[...]}}.
    `ranked` is a strongest-first de-duplicated list across the 4 levels.
    """
    result = {}
    for h in range(1, 13):
        occ = _occupants(chart, h)
        owner = _owner(chart, h)
        l1 = []
        for o in occ:
            l1.extend(_planets_in_star_of(chart, o))
        l2 = list(occ)
        l3 = _planets_in_star_of(chart, owner)
        l4 = [owner]

        ranked = []
        for grp in (l1, l2, l3, l4):
            for p in grp:
                if p not in ranked:
                    ranked.append(p)
        result[h] = {"L1": l1, "L2": l2, "L3": l3, "L4": l4, "ranked": ranked,
                     "occupants": occ, "owner": owner}
    return result


def build_significators(chart):
    """
    Build both directions:
      house_sig  : {H: {...levels..., ranked:[...]}}
      planet_sig : {planet: sorted([houses it signifies])}

    Node agency is then layered on planet_sig per the documented rule, and the
    node's agency houses are propagated to any planet whose star-lord is that
    node (the node 'passes through').
    """
    house_sig = build_house_significators(chart)

    # base planet -> houses (a planet signifies house H if it appears anywhere
    # in H's four levels)
    planet_sig = {p: set() for p in ALL_PLANETS}
    for h in range(1, 13):
        for lvl in ("L1", "L2", "L3", "L4"):
            for p in house_sig[h][lvl]:
                planet_sig[p].add(h)

    # ---- node agency ----
    for node in NODES:
        np = chart["planets"][node]
        agency = set()
        agency.add(np.get("house"))                       # (a) occupied house
        star = np["star_lord"]                             # (b) star-lord's sigs
        agency |= planet_sig.get(star, set())
        # (c) conjoined planets (same house), (d) sign-lord of tenanted sign
        same_house = [p for p in ALL_PLANETS
                      if p != node and chart["planets"][p].get("house") == np.get("house")]
        for cp in same_house:
            agency |= planet_sig.get(cp, set())
        sign_lord = np["sign_lord"]
        agency |= planet_sig.get(sign_lord, set())
        agency.discard(None)
        planet_sig[node] |= agency

    # ---- propagate node agency to planets in the node's star ----
    for node in NODES:
        for p in _planets_in_star_of(chart, node):
            planet_sig[p] |= planet_sig[node]

    planet_sig = {p: sorted(hs) for p, hs in planet_sig.items()}
    return house_sig, planet_sig


# --------------------------------------------------------------------------
# Verdict engine
# --------------------------------------------------------------------------
def _bhavat_bhavam_loss(loss_house):
    """Loss of house X manifests through 12th-from-X."""
    return ((loss_house - 1 + 11) % 12) + 1


def verdict(chart, question_type, loss_house=None):
    """
    Compute the KP verdict bundle for a matter.

    question_type: a key in QUESTION_TYPES, OR 'loss' with loss_house set
                   (e.g. loss_house=7 for 'will the relationship end').

    Returns:
      {
        "verdict": "yes" | "no" | "conditional",
        "confidence": 0-3,          # independent KP confirmations
        "drivers": [str, ...],      # structured, jargon-free
        "debug": {...}              # CSL, signified houses, gate result (audit)
      }
    """
    house_sig, planet_sig = build_significators(chart)

    if question_type == "loss":
        if loss_house is None:
            raise ValueError("question_type='loss' requires loss_house")
        bb = _bhavat_bhavam_loss(loss_house)
        spec = {
            "primary_cusp": bb,
            "favour": [bb],
            "against": [loss_house],
            "materialization_gate": False,
            "label": {"yes": "The ending / separation is supported",
                      "no": "The ending / separation is not supported"},
        }
    else:
        spec = QUESTION_TYPES.get(question_type)
        if spec is None:
            raise ValueError(f"unknown question_type {question_type!r}; "
                             f"known: {sorted(QUESTION_TYPES)} or 'loss'")

    primary_cusp = spec["primary_cusp"]
    favour = set(spec["favour"])
    against = set(spec["against"])

    csl = chart["cusps"][primary_cusp]["sub_lord"]
    csl_houses = set(planet_sig.get(csl, []))

    favour_hit = sorted(csl_houses & favour)
    against_hit = sorted(csl_houses & against)

    # materialization gate: 11th CSL must signify the 11th
    gate_required = bool(spec.get("materialization_gate"))
    eleventh_csl = chart["cusps"][11]["sub_lord"]
    eleventh_csl_houses = set(planet_sig.get(eleventh_csl, []))
    gate_ok = 11 in eleventh_csl_houses

    # ---- independent confirmations (0-3) ----
    confirmations = 0
    if favour_hit:
        confirmations += 1
    if not against_hit:
        confirmations += 1
    if not gate_required or gate_ok:
        confirmations += 1
    confidence = confirmations

    # ---- verdict logic: CSL significators decide ----
    if not favour_hit:
        v = "no"
    elif gate_required and not gate_ok:
        v = "conditional"
    elif against_hit and len(against_hit) >= len(favour_hit):
        v = "conditional"
    elif against_hit:
        v = "yes"          # favour outweighs, but a spoiler exists -> still yes
    else:
        v = "yes"

    if v == "no":
        confidence = min(confidence, 1)

    # ---- structured, jargon-free drivers (no houses/planets/sub-lords) ----
    drivers = []
    headline = spec["label"]["yes"] if v == "yes" else (
        spec["label"]["no"] if v == "no" else
        spec["label"]["yes"] + " — but only if a condition clears")
    drivers.append(headline)
    if v == "yes":
        drivers.append("The deciding factor leans in your favour.")
        if against_hit:
            drivers.append("One drag is present; it does not block the outcome.")
    elif v == "conditional":
        if gate_required and not gate_ok:
            drivers.append("The follow-through that turns effort into result "
                           "isn't lit up — line that up first.")
        else:
            drivers.append("Support and resistance are roughly even; the edge "
                           "is thin.")
    else:
        drivers.append("The deciding factor does not back this right now.")

    return {
        "verdict": v,
        "confidence": confidence,
        "drivers": drivers,
        "debug": {
            "question_type": question_type,
            "primary_cusp": primary_cusp,
            "cuspal_sub_lord": csl,
            "csl_signifies": sorted(csl_houses),
            "favour": sorted(favour),
            "against": sorted(against),
            "favour_hit": favour_hit,
            "against_hit": against_hit,
            "materialization_gate_required": gate_required,
            "eleventh_sub_lord": eleventh_csl,
            "materialization_gate_ok": gate_ok,
            "loss_house": loss_house,
        },
    }


if __name__ == "__main__":
    try:
        from .kp_chart import compute_kp_chart
    except ImportError:
        from kp_chart import compute_kp_chart  # type: ignore
    try:
        ch = compute_kp_chart("1974-11-26", "11:59", 28.6139, 77.2090,
                              tz_offset=5.5)
        for q in ("gain", "job_new", "marriage"):
            r = verdict(ch, q)
            print(f"{q:>10}: {r['verdict']:<11} conf={r['confidence']} "
                  f"CSL={r['debug']['cuspal_sub_lord']} "
                  f"signifies={r['debug']['csl_signifies']}")
        rl = verdict(ch, "loss", loss_house=7)
        print(f"{'loss(7)':>10}: {rl['verdict']:<11} conf={rl['confidence']}")
    except Exception as e:
        print(f"[ephemeris unavailable in this env: {e}]")
