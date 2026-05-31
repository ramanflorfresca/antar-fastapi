"""
antar_engine/lk_cross_conditions.py

Phase-2 — Lal Kitab / cross-chart condition library for the compatibility surface.

⚠️  SHIPPED DISABLED.  ENABLED = False.

Every condition below is a DRAFT (founder_confirmed=False). The trigger logic uses
conservative, standard-literature interpretations as a starting point — it has NOT
been founder-confirmed, and Antar's house rule is that all LK trigger predicates are
founder-confirmed before they reach user-facing output (see lk_trigger.py /
the Business-Fit Signatures precedent: build, gate, confirm, then enable).

While ENABLED is False, `evaluate_cross_conditions(...)` always returns [], so nothing
here can affect the live /api/v1/compat response. The scaffold lets the founder review
each predicate in isolation and flip `founder_confirmed=True` + `ENABLED=True` when ready.

Each condition declares which of the 6 contract layers it would inform:
    soul | chemistry | public | lifepath | communication | friction
so that, once enabled, a matched condition's `line` can be appended to that layer's
`detail` (Phase-2 deep_read) without changing the layer scoring.
"""

from antar_engine.Compatibility import SIGNS, SIGN_RULER

# ── MASTER GATE ──────────────────────────────────────────────────────────────
ENABLED = False  # do NOT flip until per-condition founder_confirmed=True below


# ── helpers (pure; whole-sign) ───────────────────────────────────────────────

def _lagna_idx(chart):
    lg = chart.get("lagna", {})
    s = lg.get("sign", "Aries") if isinstance(lg, dict) else "Aries"
    return SIGNS.index(s) if s in SIGNS else 0


def _house_of(chart, planet, from_lagna_of=None):
    """Whole-sign house of `planet` measured from `from_lagna_of`'s lagna (default own)."""
    base = _lagna_idx(from_lagna_of if from_lagna_of is not None else chart)
    sign = (chart.get("planets", {}) or {}).get(planet, {}).get("sign", "")
    if sign not in SIGNS:
        return None
    return ((SIGNS.index(sign) - base) % 12) + 1


def _same_sign(chart_a, planet_a, chart_b, planet_b):
    sa = (chart_a.get("planets", {}) or {}).get(planet_a, {}).get("sign", "")
    sb = (chart_b.get("planets", {}) or {}).get(planet_b, {}).get("sign", "")
    return bool(sa) and sa == sb


def _planet_in_houses_of_other(owner, other, planet, houses):
    """Is `other`'s `planet` sitting in one of `owner`'s `houses` (whole-sign)?"""
    h = _house_of(other, planet, from_lagna_of=owner)
    return h in houses


# ── DRAFT condition predicates (NOT founder-confirmed) ───────────────────────
# Each returns True if the (draft) pattern is present between A and B.

def _d_sleeping_awakened(a, b):
    # DRAFT: a malefic of A sitting (asleep) in A's 6/8/12 gets a benefic of B
    # arriving in that same house from A's lagna.
    benefics = ("Jupiter", "Venus", "Mercury", "Moon")
    for h in (6, 8, 12):
        b_benefic_here = any(_planet_in_houses_of_other(a, b, p, {h}) for p in benefics)
        a_malefic_here = any(_house_of(a, p) == h for p in ("Saturn", "Mars", "Rahu", "Ketu", "Sun"))
        if a_malefic_here and b_benefic_here:
            return True
    return False


def _d_pitri_rin_partial_clear(a, b):
    # DRAFT: A shows a Pitri-rin marker (Sun afflicted by Rahu/Saturn by sign-join);
    # B's Jupiter lands on A's 9th (dharma/father) from A's lagna.
    a_sun_afflicted = _same_sign(a, "Sun", a, "Rahu") or _same_sign(a, "Sun", a, "Saturn")
    b_jupiter_on_a_9 = _planet_in_houses_of_other(a, b, "Jupiter", {9})
    return a_sun_afflicted and b_jupiter_on_a_9


def _d_matri_rin_partial_clear(a, b):
    # DRAFT: A shows a Matri-rin marker (Moon afflicted by Ketu/Rahu by sign-join);
    # B's Moon/Venus lands on A's 4th (mother/home) from A's lagna.
    a_moon_afflicted = _same_sign(a, "Moon", a, "Ketu") or _same_sign(a, "Moon", a, "Rahu")
    b_on_a_4 = _planet_in_houses_of_other(a, b, "Moon", {4}) or _planet_in_houses_of_other(a, b, "Venus", {4})
    return a_moon_afflicted and b_on_a_4


def _d_mutual_6_8(a, b):
    # DRAFT: each person's lagna-lord sits in the other's 6th or 8th.
    def lord_house(owner, other):
        lg = owner.get("lagna", {})
        s = lg.get("sign", "Aries") if isinstance(lg, dict) else "Aries"
        lord = SIGN_RULER.get(s, "Sun")
        return _house_of(other, lord, from_lagna_of=other)
    return lord_house(a, b) in (6, 8) and lord_house(b, a) in (6, 8)


def _d_cross_vish(a, b):
    # DRAFT (Vish = Moon+Saturn): A's Moon shares a sign with B's Saturn (or vice versa).
    return _same_sign(a, "Moon", b, "Saturn") or _same_sign(b, "Moon", a, "Saturn")


def _d_cross_guru_chandala(a, b):
    # DRAFT (Guru-Chandala = Jupiter+Rahu): A's Jupiter shares a sign with B's Rahu (or vice versa).
    return _same_sign(a, "Jupiter", b, "Rahu") or _same_sign(b, "Jupiter", a, "Rahu")


def _d_cross_shrapit(a, b):
    # DRAFT (Shrapit = Saturn+Rahu): A's Saturn shares a sign with B's Rahu (or vice versa).
    return _same_sign(a, "Saturn", b, "Rahu") or _same_sign(b, "Saturn", a, "Rahu")


def _d_manglik_balance(a, b):
    # DRAFT: both carry a Mars-in-1/4/7/8/12 marker — mutual Manglik often read as
    # cancelling. Present if BOTH show the marker.
    mh = {1, 4, 7, 8, 12}
    a_mang = _house_of(a, "Mars") in mh
    b_mang = _house_of(b, "Mars") in mh
    return a_mang and b_mang


def _d_kaal_sarp_relief(a, b):
    # DRAFT: A in a Kaal-Sarp-like wrap (all classical planets between Rahu and Ketu
    # signs) and B places a benefic outside that axis onto A's lagna — read as relief.
    # Conservative proxy: B's Jupiter on A's 1st while A's Sun and Moon share the
    # Rahu/Ketu hemisphere is hard to verify here → keep strict, rarely fires.
    return _planet_in_houses_of_other(a, b, "Jupiter", {1}) and _same_sign(a, "Rahu", a, "Sun")


def _d_benefic_on_blank_house(a, b):
    # DRAFT (LK "pakka ghar / blank house"): B's strong benefic lands on a house of A
    # that A leaves empty — read as B "filling" what A lacks. Proxy: B's Jupiter/Venus
    # on A's 2nd or 11th (wealth/gains) from A's lagna, with no A planet there.
    for h in (2, 11):
        a_empty = not any(_house_of(a, p) == h for p in
                          ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"))
        b_benefic = _planet_in_houses_of_other(a, b, "Jupiter", {h}) or _planet_in_houses_of_other(a, b, "Venus", {h})
        if a_empty and b_benefic:
            return True
    return False


# ── condition registry ───────────────────────────────────────────────────────
# layer: which contract layer this would inform. severity: support|watch.
CROSS_CONDITIONS = [
    {"id": "sleeping_awakened",    "name": "A dormant strength of yours, woken by them", "layer": "soul",          "severity": "support", "detect": _d_sleeping_awakened,      "founder_confirmed": False,
     "line": "{b_name} tends to wake up a strength in you that usually sits quiet."},
    {"id": "pitri_rin_clear",      "name": "They ease an old paternal-line weight",      "layer": "lifepath",      "severity": "support", "detect": _d_pitri_rin_partial_clear, "founder_confirmed": False,
     "line": "Being around {b_name} seems to lighten an old family-line weight for you."},
    {"id": "matri_rin_clear",     "name": "They ease an old maternal-line weight",       "layer": "soul",          "severity": "support", "detect": _d_matri_rin_partial_clear, "founder_confirmed": False,
     "line": "{b_name} brings a settling, nurturing note to a tender part of your story."},
    {"id": "mutual_6_8",          "name": "Mutual strain axis",                          "layer": "friction",      "severity": "watch",   "detect": _d_mutual_6_8,             "founder_confirmed": False,
     "line": "There's a built-in strain axis between you and {b_name} — name it early and it stays manageable."},
    {"id": "cross_vish",          "name": "A heaviness one can cast on the other",        "layer": "communication", "severity": "watch",   "detect": _d_cross_vish,             "founder_confirmed": False,
     "line": "Under stress, one of you can pull the other's mood down — watch the heavy days."},
    {"id": "cross_guru_chandala", "name": "Belief-and-ambition tension",                  "layer": "soul",          "severity": "watch",   "detect": _d_cross_guru_chandala,    "founder_confirmed": False,
     "line": "Your sense of meaning and {b_name}'s drive can pull against each other — keep the 'why' explicit."},
    {"id": "cross_shrapit",       "name": "A slow, testing knot",                         "layer": "friction",      "severity": "watch",   "detect": _d_cross_shrapit,          "founder_confirmed": False,
     "line": "There's a slow, testing knot between you and {b_name} that rewards patience over force."},
    {"id": "manglik_balance",     "name": "Matched intensity",                            "layer": "chemistry",     "severity": "support", "detect": _d_manglik_balance,        "founder_confirmed": False,
     "line": "You and {b_name} carry a matched intensity that tends to balance rather than clash."},
    {"id": "kaal_sarp_relief",    "name": "They open a stuck door",                       "layer": "lifepath",      "severity": "support", "detect": _d_kaal_sarp_relief,       "founder_confirmed": False,
     "line": "{b_name} has a way of opening a door that tends to feel stuck for you."},
    {"id": "benefic_on_blank",    "name": "They fill a gap you carry",                    "layer": "public",        "severity": "support", "detect": _d_benefic_on_blank_house, "founder_confirmed": False,
     "line": "{b_name} naturally fills an area you tend to leave open — a genuine complement."},
]


def evaluate_cross_conditions(chart_a: dict, chart_b: dict,
                              dashas_a=None, dashas_b=None,
                              a_name: str = "You", b_name: str = "they") -> list:
    """
    Return matched cross-conditions as
        [{id, name, layer, severity, line}]  (line already name-substituted)
    Returns [] whenever ENABLED is False or a condition is not founder_confirmed,
    so nothing unverified can reach the live response.
    """
    if not ENABLED:
        return []
    out = []
    for cond in CROSS_CONDITIONS:
        if not cond.get("founder_confirmed"):
            continue
        try:
            if cond["detect"](chart_a, chart_b):
                out.append({
                    "id": cond["id"], "name": cond["name"],
                    "layer": cond["layer"], "severity": cond["severity"],
                    "line": cond["line"].format(a_name=a_name, b_name=b_name),
                })
        except Exception:
            continue
    return out


def status() -> dict:
    """Introspection for the verification harness / founder review."""
    return {
        "enabled": ENABLED,
        "total_conditions": len(CROSS_CONDITIONS),
        "founder_confirmed": sum(1 for c in CROSS_CONDITIONS if c.get("founder_confirmed")),
        "ids": [c["id"] for c in CROSS_CONDITIONS],
    }
