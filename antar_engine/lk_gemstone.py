"""
lk_gemstone.py — two-layer gemstone logic.

LIFELONG (Parashari): the chart's core-strength stone — yogakaraka / lagna lord /
strongest functional benefic (the planets that run the 9/10/11/5/2/7 fortune,
career, gains, home and partnership houses). Reuses practice_engine's existing
Parashari selector. Worn ongoing.

TIMED (Lal Kitab): a situational stone for a planet that is UNDER STRAIN this
year/month — but only when strengthening it is logically sound:
  • only a FUNCTIONAL BENEFIC that is struggling (feed a weak friend), and
  • NEVER a functional malefic in trouble (feeding a malefic that's already
    biting amplifies the harm — those get action-remedies instead), except
  • the shadow planets (Rahu/Ketu) only inside their maturation window, with a
    "test first / under guidance" caveat.
The reason is constructed from the affliction (which life area is weak and why),
not from dogma — and the finger/metal follow the planet's energy channel.
"""
from antar_engine import lk_year_rules as R

try:
    from antar_engine.practice_engine import (
        select_chart_gemstone, is_functional_benefic, is_functional_malefic, GEM_DOMAINS,
    )
except Exception:  # pragma: no cover
    select_chart_gemstone = None

    def is_functional_benefic(*a, **k):
        return False

    def is_functional_malefic(*a, **k):
        return False

    GEM_DOMAINS = {}

# stone · finger · metal per planet (classical correspondence; some confirmed by
# the LK measures, e.g. ruby/copper-ring for the Sun, coral for Mars).
PLANET_STONE = {
    "Sun":     {"stone": "ruby",                     "finger": "ring finger",   "metal": "gold or copper"},
    "Moon":    {"stone": "natural pearl",            "finger": "little finger", "metal": "silver"},
    "Mars":    {"stone": "red coral",                "finger": "ring finger",   "metal": "gold or copper"},
    "Mercury": {"stone": "emerald",                  "finger": "little finger", "metal": "gold"},
    "Jupiter": {"stone": "yellow sapphire",          "finger": "index finger",  "metal": "gold"},
    "Venus":   {"stone": "diamond or white sapphire", "finger": "little finger", "metal": "silver"},
    "Saturn":  {"stone": "blue sapphire",            "finger": "middle finger", "metal": "iron or silver", "test_first": True},
    "Rahu":    {"stone": "hessonite (gomed)",        "finger": "middle finger", "metal": "silver"},
    "Ketu":    {"stone": "cat's eye",                "finger": "little finger", "metal": "silver"},
}

# WHY this finger — the energy channel each finger carries (reasoned, not dogma).
FINGER_WHY = {
    "index finger":  "the finger tied to expansion, wisdom and good judgment",
    "middle finger": "the finger tied to discipline, patience and structure",
    "ring finger":   "the finger tied to vitality, confidence and the heart",
    "little finger": "the finger tied to communication, skill and relating",
}


def _domain(planet):
    return R.PLAIN_DOMAIN.get(planet) or GEM_DOMAINS.get(planet) or "your core strength"


def lifelong(planets, lagna):
    if not select_chart_gemstone:
        return None
    try:
        g = select_chart_gemstone(planets, lagna)
    except Exception:
        g = None
    if not g:
        return None
    p = g.get("_planet")
    st = PLANET_STONE.get(p, {})
    return {
        "type": "lifelong",
        "stone": g.get("stone") or st.get("stone"),
        "finger": st.get("finger"),
        "finger_reason": FINGER_WHY.get(st.get("finger")),
        "metal": g.get("metal") or st.get("metal"),
        "for": _domain(p),
        "window": "wear ongoing",
        "why": g.get("why"),
        "test_first": g.get("risk_tier") == "test_first",
    }


def timed(strained_planets, lagna, age, period="year"):
    pw = "this year" if period == "year" else "this month"
    out = []
    for p in strained_planets:
        st = PLANET_STONE.get(p)
        if not st:
            continue
        if p in ("Rahu", "Ketu"):
            mat = R.LK_PLANET_AGES.get(p, 0)   # Rahu matures ~42, Ketu ~48
            lo, hi = mat - 3, mat + 5
            if age is None or not (lo <= age <= hi):
                continue  # shadow stones only inside the maturation window
            window = f"a sensitive window (ages {lo}-{hi})"
            caveat = "test it first, ideally under guidance — this is a strong, shadowy energy"
        else:
            if is_functional_malefic(p, lagna):
                continue  # don't strengthen a malefic that's already causing trouble
            if not is_functional_benefic(p, lagna):
                continue  # only feed a benefic that's struggling
            mat = R.LK_PLANET_AGES.get(p, 0)
            window = f"a key window (around age {mat})" if (age is not None and abs(age - mat) <= 3) else pw
            caveat = "test it first" if st.get("test_first") else None
        out.append({
            "type": "timed",
            "stone": st["stone"],
            "finger": st["finger"],
            "finger_reason": FINGER_WHY.get(st["finger"]),
            "metal": st["metal"],
            "for": _domain(p),
            "why": f"the part of you that governs {_domain(p)} is under strain {pw}; "
                   f"this stone feeds that strength so the area holds steady",
            "window": window,
            "caveat": caveat,
        })
    return out


def build(planets, lagna, strained_planets, age, period="year"):
    """Return {'lifelong': {...}|None, 'timed': [...]}. Never raises."""
    try:
        return {
            "lifelong": lifelong(planets or {}, lagna),
            "timed": timed(strained_planets or [], lagna, age, period),
        }
    except Exception:
        return {"lifelong": None, "timed": []}
