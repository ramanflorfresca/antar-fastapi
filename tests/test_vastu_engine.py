"""Vastu-Jyotish engine: rules table integrity, safe envelopes, dasha line,
plain-language and faith-neutral guards."""
import re
from datetime import date

import pytest

from antar_engine import vastu_rules as R
from antar_engine.vastu_engine import (
    vastu_guidance, period_line, _active_vim_periods, _pick, _direction)

TODAY = date(2026, 10, 14)
SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
OPPOSITE = {"E": "W", "W": "E", "N": "S", "S": "N",
            "NE": "SW", "SW": "NE", "SE": "NW", "NW": "SE"}


def _chart(placements: dict, lagna="Aries"):
    """placements: planet -> house (whole-sign from lagna)."""
    li = SIGNS.index(lagna)
    planets = {p: {"house": h, "sign": SIGNS[(li + h - 1) % 12], "degree": 10.0 + i}
               for i, (p, h) in enumerate(placements.items())}
    return {"lagna": {"sign": lagna}, "planets": planets}


# Aries lagna. Mars (lagna lord) 1st; Jupiter (9th lord) own in 9th; Sun (5th lord)
# own in 5th -> supportive. Saturn in the 8th, Venus in the 12th, Ketu in the 8th
# -> strained.
BASE = _chart({"Sun": 5, "Moon": 4, "Mars": 1, "Mercury": 3, "Jupiter": 9,
               "Venus": 12, "Saturn": 8, "Rahu": 2, "Ketu": 8})


def _dashas(md, ad, md_level="mahadasha", ad_level="antardasha"):
    return {"vimsottari": [
        {"lord_or_sign": md, "start_date": "2020-01-01", "end_date": "2039-01-01",
         "level": md_level},
        {"lord_or_sign": ad, "start_date": "2026-01-01", "end_date": "2028-03-01",
         "level": ad_level},
    ]}


def _strings(obj, skip=("src", "scope", "zone", "id", "status", "until", "tradition", "version")):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in skip:
                continue
            yield from _strings(v, skip)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _strings(v, skip)
    elif isinstance(obj, str):
        yield obj


# ── rules table integrity ────────────────────────────────────────────────────
def test_ketu_is_opposite_rahu():
    assert R.PLANET_ZONE["Rahu"] == "SW"
    assert R.PLANET_ZONE["Ketu"] == "NE"
    assert OPPOSITE[R.PLANET_ZONE["Rahu"]] == R.PLANET_ZONE["Ketu"]


def test_every_zone_has_lord_label_and_meaning():
    assert set(R.ZONE_ORDER) == set(R.ZONE_LORDS) == set(R.ZONE_LABEL) == set(R.ZONE_GOVERNS)
    assert len(R.ZONE_ORDER) == 8


def test_object_rows_are_valid():
    ids = [o["id"] for o in R.OBJECTS]
    assert len(ids) == len(set(ids))
    for o in R.OBJECTS:
        assert set(o["best"]) <= set(R.ZONE_ORDER)
        assert set(o["avoid"]) <= set(R.ZONE_ORDER)
        assert not (set(o["best"]) & set(o["avoid"])), o["id"]
        assert o["note"]


def test_rules_not_marked_verified_until_owner_signs_off():
    assert R.VERIFIED is False
    assert vastu_guidance(BASE, _dashas("Saturn", "Mars"), today=TODAY)["meta"]["rules_verified"] is False


# ── directions ───────────────────────────────────────────────────────────────
def test_base_chart_zone_classes():
    out = vastu_guidance(BASE, today=TODAY)
    st = {z["zone"]: z["status"] for z in out["zones"]}
    assert st["S"] == "strong"        # Mars: ascendant lord, own sign, 1st
    assert st["E"] == "strong"        # Sun: 5th lord, own sign
    assert st["NE"] == "strong"       # Jupiter leads; strained Ketu does not override
    assert st["W"] == "needs_care"    # Saturn in the 8th
    # Saturn (8th), Ketu (8th) and Venus (12th) are all strained, but only the worst
    # two surface; Venus is the mildest, so it is capped down to neutral
    assert st["SE"] == "steady"


def test_sleep_head_never_north_and_inside_envelope_for_every_lagna():
    for lagna in SIGNS:
        for placement in (BASE["planets"], ):
            cd = {"lagna": {"sign": lagna}, "planets": placement}
            out = vastu_guidance(cd, today=TODAY)
            assert out["available"]
            assert out["directions"]["sleep_head"]["zone"] in R.SLEEP_HEAD_ENVELOPE
            assert out["directions"]["sleep_head"]["zone"] != "N"
            assert out["directions"]["work_facing"]["zone"] in R.WORK_FACING_ENVELOPE
            assert out["directions"]["eat_facing"]["zone"] in R.EAT_FACING_ENVELOPE


def test_sleep_head_picks_stronger_of_s_and_e():
    cd = _chart({"Sun": 5, "Moon": 4, "Mars": 6, "Mercury": 3, "Jupiter": 9,
                 "Venus": 2, "Saturn": 10, "Rahu": 2, "Ketu": 8})   # Mars in the 6th: strained
    out = vastu_guidance(cd, today=TODAY)
    assert out["directions"]["sleep_head"]["zone"] == "E"


def _zones(**cls):
    base = {z: {"cls": "steady", "score": 0.0, "dig": 0} for z in R.ZONE_ORDER}
    for z, (c, sc) in cls.items():
        base[z] = {"cls": c, "score": sc, "dig": 0}
    return base


def test_classical_default_wins_a_true_tie():
    zones = _zones()                                     # everything steady
    assert _pick(R.SLEEP_HEAD_ENVELOPE, zones) == "S"
    assert _pick(R.WORK_FACING_ENVELOPE, zones) == "N"
    assert _pick(R.EAT_FACING_ENVELOPE, zones) == "E"


def test_dig_bala_only_breaks_a_score_tie():
    zones = _zones(S=("strong", 2.0), E=("strong", 2.0))
    zones["E"]["dig"] = 1
    assert _pick(R.SLEEP_HEAD_ENVELOPE, zones) == "E"
    zones["S"]["score"] = 2.5                            # a better score beats dig bala
    assert _pick(R.SLEEP_HEAD_ENVELOPE, zones) == "S"


def test_both_sleep_options_strained_uses_milder_and_says_so():
    zones = _zones(S=("needs_care", -3.0), E=("needs_care", -2.0))
    z = _pick(R.SLEEP_HEAD_ENVELOPE, zones)
    assert z == "E"                                      # the milder of the two
    assert z in R.SLEEP_HEAD_ENVELOPE and z != "N"
    assert "milder" in _direction(z, zones, both_strained=True)["why"]


def test_strained_zone_recommends_nothing_to_place_there():
    out = vastu_guidance(BASE, today=TODAY)
    w = next(c for c in out["zones"] if c["zone"] == "W")
    assert w["status"] == "needs_care" and w["place_here"] == []
    assert "lighter" in w["status_label"] or "light" in w["care_note"]


def test_keep_light_lists_strained_zones_worst_first():
    out = vastu_guidance(BASE, today=TODAY)
    kl = [k["zone"] for k in out["directions"]["keep_light"]]
    assert kl == ["W"]


def test_object_tip_redirects_from_strained_best_zone():
    out = vastu_guidance(BASE, today=TODAY)
    water = next(o for o in out["objects"] if o["id"] == "water_features")
    assert water["for_you"]["best"][0] in ("North-East", "East")   # strong zones lead
    elephants = next(o for o in out["objects"] if o["id"] == "elephant_statues")
    assert "West" in elephants["best"]
    assert "West" not in elephants["for_you"]["best"]        # Saturn strained -> West flagged
    assert "lighter touch" in elephants["for_you"]["tip"]


def test_everything_emitted_is_sourced():
    out = vastu_guidance(BASE, _dashas("Saturn", "Mars"), today=TODAY)

    def walk(o):
        if isinstance(o, dict):
            if "zone" in o and "label" in o and "src" in o:
                assert o["src"].startswith("VJ-")
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(out)
    assert all(c["src"].startswith("VJ-ZONE-") for c in out["zones"])
    assert all(c["src"].startswith("VJ-OBJ-") for c in out["objects"])


def test_surfacing_is_capped_even_when_the_chart_is_harsh():
    # every planet in a dusthana, for every lagna: never more than the caps
    for lagna in SIGNS:
        harsh = _chart({"Sun": 6, "Moon": 8, "Mars": 12, "Mercury": 6, "Jupiter": 8,
                        "Venus": 12, "Saturn": 6, "Rahu": 8, "Ketu": 12}, lagna=lagna)
        out = vastu_guidance(harsh, _dashas("Saturn", "Mercury"), today=TODAY)
        n_care = sum(z["status"] == "needs_care" for z in out["zones"])
        n_strong = sum(z["status"] == "strong" for z in out["zones"])
        assert n_care <= R.MAX_NEEDS_CARE
        assert n_strong <= R.MAX_STRONG
        assert len(out["directions"]["keep_light"]) <= 2


def test_capping_never_flips_a_class_to_its_opposite():
    from antar_engine.vastu_engine import _cap_classes
    pc = {p: {"cls": "needs_care", "score": -float(i), "dig": 0}
          for i, p in enumerate(["Sun", "Moon", "Mars", "Mercury"], start=1)}
    capped = _cap_classes(pc)
    assert {p for p, v in capped.items() if v["cls"] == "needs_care"} == {"Mercury", "Mars"}
    assert {v["cls"] for v in capped.values()} <= {"needs_care", "steady"}


# ── dasha line ───────────────────────────────────────────────────────────────
def test_period_leads_with_the_running_stretch():
    out = vastu_guidance(BASE, _dashas("Saturn", "Mars"), today=TODAY)
    p = out["period"]
    assert p["available"]
    assert p["focus"]["zone"] == "S" and p["focus"]["status"] == "strong"
    assert p["focus"]["until"] == "2028-03-01"
    assert p["background"]["zone"] == "W" and p["background"]["status"] == "needs_care"
    assert "South" in p["focus"]["do"]


def test_neutral_period_is_suppressed():
    # Moon and Mercury are steady in BASE -> both zones neutral -> no line
    p = vastu_guidance(BASE, _dashas("Moon", "Mercury"), today=TODAY)["period"]
    assert p["available"] is False


def test_same_zone_chapter_is_dropped():
    p = vastu_guidance(BASE, _dashas("Mars", "Mars"), today=TODAY)["period"]
    assert p["available"] and p["background"] is None


def test_ketu_period_points_at_north_east():
    cd = _chart({"Sun": 5, "Moon": 4, "Mars": 1, "Mercury": 3, "Jupiter": 9,
                 "Venus": 12, "Saturn": 8, "Rahu": 2, "Ketu": 8})
    p = vastu_guidance(cd, _dashas("Saturn", "Ketu"), today=TODAY)["period"]
    assert p["focus"]["zone"] == "NE" and p["focus"]["status"] == "needs_care"


def test_only_vimsottari_counts():
    d = _dashas("Saturn", "Mars")
    d["yogini"] = [{"lord_or_sign": "Rahu", "start_date": "2026-01-01",
                    "end_date": "2030-01-01", "level": "mahadasha"}]
    act = _active_vim_periods(d, TODAY)
    assert act["md"][0] == "Saturn" and act["ad"][0] == "Mars"


def test_missing_levels_fall_back_to_span_length():
    d = _dashas("Saturn", "Mars", md_level="", ad_level="")
    act = _active_vim_periods(d, TODAY)
    assert act["md"][0] == "Saturn" and act["ad"][0] == "Mars"


def test_expired_periods_are_ignored():
    assert period_line(BASE, None, _dashas("Saturn", "Mars"), date(2045, 1, 1))["available"] is False


def test_no_dashas_still_returns_directions():
    out = vastu_guidance(BASE, None, today=TODAY)
    assert out["available"] and out["period"]["available"] is False


# ── guards ───────────────────────────────────────────────────────────────────
def test_incomplete_chart_is_unavailable_not_an_error():
    assert vastu_guidance({}, today=TODAY) == {"available": False}
    assert vastu_guidance({"lagna": {"sign": "Aries"}}, today=TODAY) == {"available": False}
    assert vastu_guidance(None, today=TODAY) == {"available": False}   # type: ignore[arg-type]


def test_deterministic():
    a = vastu_guidance(BASE, _dashas("Saturn", "Mars"), today=TODAY)
    b = vastu_guidance(BASE, _dashas("Saturn", "Mars"), today=TODAY)
    assert a == b


_JARGON = re.compile(
    r"\b(sun|moon|mars|mercury|jupiter|venus|saturn|rahu|ketu|graha|dasha|dasa|"
    r"mahadasha|antardasha|lagna|ascendant|house|nakshatra|vimsottari|parashari|"
    r"dig bala|karaka)\b", re.I)


def test_no_planet_house_or_sanskrit_reaches_the_user():
    out = vastu_guidance(BASE, _dashas("Saturn", "Mars"), today=TODAY)
    # the INFO panel and tradition label are the only places "birth chart" prose
    # is allowed; none of them may name a planet either
    for s in _strings(out):
        m = _JARGON.search(s)
        assert not m, f"jargon {m.group(0)!r} in user text: {s!r}"


_NAMED_FAITH = ("church", "temple", "mosque", "gurdwara", "gurudwara", "synagogue",
                "mandir", "masjid", "murti", "pooja", "puja", "shiva", "ganesh",
                "krishna", "hanuman", "lakshmi", "jesus", "buddha", "allah")


def test_faith_neutral_wording():
    out = vastu_guidance(BASE, _dashas("Saturn", "Mars"), today=TODAY)
    blob = " ".join(_strings(out)).lower()
    for w in _NAMED_FAITH:
        assert w not in blob, w
