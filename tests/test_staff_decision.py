"""[staff-decision 2026-10-11] 'Should I fire someone?' — coach / reassign / exit / document, from your 6th house and the person's role fit. No window, no date."""
import re

from antar_engine import staff_decision as SD
from tests.test_partner_roles import _chart, _built, _dashas

HIER = lambda fit, d, strengths=("ops", "finance"): {"kind": "hierarchy", "type": "employee", "fit": fit, "direction": d,
                                                    "other": {"strengths": list(strengths), "thin": ["creative", "vision"], "style": "structured"}, "you": {"strengths": ["tech"]}}


def test_the_lean_follows_fit_and_direction_and_exit_needs_evidence():
    L = SD.lean_for
    assert L(HIER("strong", "easy")) == L(HIER("strong", "own")) == "coach"
    assert L(HIER("ok", "easy")) == L(HIER("ok", "scope")) == "coach" and L(HIER("ok", "own")) == "reassign"
    assert L(HIER("weak", "easy")) == "reassign" and L(HIER("weak", "scope")) == L(HIER("weak", "own")) == "exit"
    assert L(HIER(None, "easy")) == L(HIER(None, "scope")) == "coach" and L(HIER(None, "own")) == "reassign"      # no role named: never an exit
    assert L(None) == L({}) == L({"kind": "partners"}) == "document"


def test_handling_reads_the_sixth_house_lord_and_saturn():
    # Capricorn lagna -> 6th = Gemini, lord Mercury
    strong = _chart(planets={"Mercury": {"sign": "Virgo", "house": 10}, "Saturn": {"sign": "Capricorn", "house": 10}})
    weak = _chart(planets={"Mercury": {"sign": "Pisces", "house": 12}, "Saturn": {"sign": "Aries", "house": 12}})
    hs, hw = SD.handling(strong), SD.handling(weak)
    assert hs["lord"] == "Mercury" and hs["level"] == "clean" and hw["level"] == "messy" and hw["house"] == 12
    assert SD.handling({}) is None and SD.handling(None) is None


def test_a_weakened_sixth_lord_never_reads_clean():
    chart = _chart(planets={"Mercury": {"sign": "Pisces", "house": 10}, "Saturn": {"sign": "Capricorn", "house": 10}})       # Mercury debilitated in a kendra
    assert SD.handling(chart)["level"] in ("careful", "messy")


def test_each_lean_says_why_and_gives_its_own_next_step_without_a_window():
    chart = _built(["Saturn", "Mars"])
    for fit, d, lean in (("strong", "easy", "coach"), ("weak", "easy", "reassign"), ("weak", "own", "exit")):
        r = SD.compose(chart, HIER(fit, d), "Dev", "en")
        assert r["lean"] == lean and r["read"].startswith(f"Lean: {SD._TX['en']['lean'][lean]}.") and "Dev" in r["read"]
        assert r["next"] and not re.search(r"(?i)\bwindow\b|\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b\s*20\d\d|\d{4}", r["read"] + r["next"])
    nxts = {SD.compose(chart, HIER(f, d), "Dev", "en")["next"] for f, d in (("strong", "easy"), ("weak", "easy"), ("weak", "own"))}
    assert len(nxts) == 3


def test_document_is_the_lean_without_a_reading_and_keeps_the_generic_move():
    r = SD.compose(_chart(), None, "", "en")
    assert r["lean"] == "document" and r["next"] is None and "decide from the record, not from timing" in r["read"]
    assert "It works if the expectations were written down and missed before the decision." in r["read"] and "It breaks if the exit is made in frustration" in r["read"]


def test_handling_changes_the_process_not_the_lean():
    messy = _chart(planets={"Mercury": {"sign": "Pisces", "house": 12}, "Saturn": {"sign": "Aries", "house": 12}})
    clean = _chart(planets={"Mercury": {"sign": "Virgo", "house": 10}, "Saturn": {"sign": "Capricorn", "house": 10}})
    a, b = SD.compose(messy, HIER("strong", "easy"), "Dev", "en"), SD.compose(clean, HIER("strong", "easy"), "Dev", "en")
    assert a["lean"] == b["lean"] == "coach" and "take advice before any exit" in a["read"] and "stay clean on your side" in b["read"]


def test_basis_names_the_chart_fact_and_the_persons_read():
    r = SD.compose(_built(["Saturn"]), HIER("weak", "own"), "Dev", "en")
    assert r["basis"].startswith("Your 6th house (staff and service) is ruled by Mercury, in house") and "Dev's read: a stretch for the role, wants a defined area to own." in r["basis"]
    assert "read:" not in SD.compose(_chart(), None, "", "en")["basis"]


def test_spanish_is_native():
    r = SD.compose(_built(["Saturn", "Mars"]), HIER("weak", "own"), "Dev", "es")
    assert r["read"].startswith("Inclinación: Salida, por escrito.") and "Se rompe si la salida se hace con frustración" in r["read"]
    for en in ("Lean:", "It works", "Coach", "Your 6th"):
        assert en not in r["read"] + r["basis"]


def test_the_lane_is_wired_after_the_filters_and_only_for_the_fire_family():
    import main
    src = open(main.__file__, encoding="utf-8").read()
    i = src.index("[staff-final 2026-10-11]")
    assert i > src.index("[divorced-final 2026-10-11]") and '_f2[0] == "fire"' in src[i:i + 900] and 'compat_type") == "employee"' in src[i:i + 2500]
    j = src.index('payload["basis"] = _plain or _basis')      # [basis-plain] the line people read is plain; the staff-decision basis is still appended after it
    assert "_sd_basis" in src[j:j + 700]


def test_without_a_role_reassign_is_worded_as_a_defined_area_not_as_a_poor_fit():
    r = SD.compose(_built(["Saturn"]), HIER(None, "own"), "Dev", "en")
    assert r["lean"] == "reassign" and "better suited to other work" not in r["read"] and "defined area of their own" in r["read"]
