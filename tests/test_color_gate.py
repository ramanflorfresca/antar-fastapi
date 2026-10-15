"""[colour-gate 2026-10-15] the daily card's colour must suit THIS chart: favourable first, never an avoid colour."""
from antar_engine import color_therapy as CT

# Raman-like: only the Venus colours are favourable; everything else the engine calls neutral; blue is refused below
FAV = {"white", "pink", "sky blue"}


def _assess(nm):
    k = nm.lower()
    return "favor" if k in FAV else ("avoid" if k in ("red", "crimson") else "neutral")


GATE = {"assess": _assess, "favor_shades": ["White", "Pink", "Sky Blue"]}


def _c(nak, wd, tq=None, gate=GATE, refused=None):
    return CT.color_for_day(nak, wd, tq, gate=gate, refused=refused)


def test_a_favourable_colour_beats_the_days_own_neutral_colour():
    # Anuradha is ruled by Saturn (dark blue / black): neutral for this chart, so a favourable colour leads
    c = _c("Anuradha", 2)                       # Wednesday
    assert c["primary"].lower() in FAV and c["gated"] and c["verdict"] == "favor"
    assert "dark blue" not in (c["wear"] or "").lower()


def test_never_an_avoid_colour_and_it_is_named_to_skip():
    gate = {"assess": lambda n: "avoid" if n.lower() in ("white", "pink", "sky blue", "silver") else "neutral",
            "favor_shades": ["White", "Pink"]}
    for wd in range(7):
        for nak in ("Anuradha", "Rohini", "Ashwini", "Magha"):
            c = CT.color_for_day(nak, wd, None, gate=gate)
            assert c is None or gate["assess"](c["primary"]) != "avoid"


def test_the_weekday_colour_leads_when_it_suits_the_chart():
    gate = {"assess": lambda n: "favor" if n.lower() in ("green", "white") else "neutral", "favor_shades": ["White"]}
    c = CT.color_for_day("Anuradha", 2, None, gate=gate)       # Wednesday ruler = Mercury = green
    assert c["primary"] == "Green" and "Wednesday suits green" in c["why"]


def test_nothing_eligible_shows_nothing_not_a_generic_colour():
    gate = {"assess": lambda n: "avoid", "favor_shades": ["White"]}
    assert CT.color_for_day("Anuradha", 2, None, gate=gate) is None


def test_a_stone_only_when_the_days_own_planet_is_a_favourable_choice():
    assert _c("Anuradha", 2)["gem"] is None                      # pink came from the chart's list, not the day's planet
    gate = {"assess": lambda n: "favor" if n.lower() == "green" else "neutral", "favor_shades": []}
    assert CT.color_for_day("Anuradha", 2, None, gate=gate)["gem"]       # Mercury green on a Mercury day: stone allowed


def test_adverse_tara_does_not_amplify_the_nakshatra_lord():
    gate = {"assess": lambda n: "favor" if n.lower() in ("black", "dark blue", "purple") else "neutral",
            "favor_shades": []}
    ok = CT.color_for_day("Anuradha", 2, "favorable", gate=gate)             # Saturn star leads
    bad = CT.color_for_day("Anuradha", 2, "adverse", gate=gate)               # Saturn dropped, Mercury weekday frame
    assert ok["primary_from"] == "Saturn"
    assert bad is None or bad["primary_from"] != "Saturn"


def test_without_a_gate_the_legacy_colour_is_unchanged():
    c = CT.color_for_day("Anuradha", 2, "favorable")
    assert c and c["primary_from"] == "Saturn" and "gated" not in c


def test_gate_needs_a_real_chart_else_none_and_legacy_stays():
    assert CT.chart_colour_gate(None) is None and CT.chart_colour_gate({"planets": {}}) is None
