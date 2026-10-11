"""[divorced-marriage 2026-10-11] one answer, two windows — from the same engines the ex / marriage questions use."""
from datetime import date

import main
from antar_engine import divorced_union as DU

TODAY = date(2026, 10, 11)


def _ee(client, start, end):
    return {"client_verdict": client, "verdict": {"window": {"start": start, "end": end}}}


REBUILD_OPEN = _ee("YES", "2026-08-13", "2027-01-08")
NEW_LATER = _ee("NOT_YET", "2027-11-10", "2028-02-24")


def test_open_rebuild_window_and_a_later_new_partnership_window_are_both_named():
    r = DU.compose(REBUILD_OPEN, NEW_LATER, "divorced", "en", TODAY)
    t = r["read"]
    assert t.startswith("You're divorced, so there are two separate questions")
    assert "Rebuilding with your former spouse: a window is open now, through Jan 2027." in t
    assert "A new partnership: the next supportive window is Nov 2027 – Feb 2028; before it, build the ground rather than the commitment." in t
    assert t.endswith("it cannot show what the other person will do.")
    assert (r["rebuild_state"], r["new_state"]) == ("open_now", "upcoming") and r["timing"] == "Oct 2026 – Jan 2027"


def test_never_says_the_marriage_is_over_or_claims_what_the_other_person_feels():
    for ms in ("divorced", "separated"):
        for rb in (REBUILD_OPEN, _ee("NO", None, None), None):
            t = DU.compose(rb, NEW_LATER, ms, "en", TODAY)["read"].lower()
            assert not any(w in t for w in ("over for good", "it's over", "no hope", "will come back", "loves you", "still loves", "wants you"))


def test_no_supported_window_is_said_plainly_and_points_at_what_the_reader_controls():
    r = DU.compose(_ee("NO", None, None), _ee("NO", None, None), "divorced", "en", TODAY)
    assert "no supported window in the next two years — put your effort into what you can decide yourself" in r["read"] and r["timing"] is None


def test_a_window_that_already_ended_is_not_offered():
    r = DU.compose(_ee("YES", "2025-01-01", "2026-01-01"), NEW_LATER, "divorced", "en", TODAY)
    assert r["rebuild_state"] == "none"


def test_separated_says_your_spouse_and_single_or_widowed_get_nothing():
    assert "Rebuilding with your spouse:" in DU.compose(REBUILD_OPEN, NEW_LATER, "separated", "en", TODAY)["read"]
    for ms in ("single", "widowed", "married", "", None):
        assert DU.compose(REBUILD_OPEN, NEW_LATER, ms, "en", TODAY) is None
    assert DU.compose(None, None, "divorced", "en", TODAY) is None and DU.compose(REBUILD_OPEN, NEW_LATER, "divorced", "hi", TODAY) is None


def test_spanish_and_portuguese_are_native_with_localised_months():
    es = DU.compose(REBUILD_OPEN, NEW_LATER, "divorced", "es", TODAY)
    assert "ene 2027" in es["read"] and "nov 2027 – feb 2028" in es["read"] and "Reconstruir el vínculo con tu ex pareja" in es["read"]
    pt = DU.compose(REBUILD_OPEN, NEW_LATER, "divorced", "pt", TODAY)
    assert "jan 2027" in pt["read"] and "fev 2028" in pt["read"] and "Reconstruir o vínculo com seu ex-cônjuge" in pt["read"]
    for t in (es["read"], pt["read"]):
        for en in ("window is open", "Rebuilding", "You're"):
            assert en not in t


def test_the_married_life_wording_counts_as_an_existing_union_question():
    for q in ("Is there any problem in my married life?", "Will my married life get better?", "¿Mejorará mi vida matrimonial?"):
        assert main._suppress_union_window("marriage", "divorced", q), q
    assert not main._suppress_union_window("marriage", "divorced", "Will I get married again?")


def test_the_lane_is_wired_before_polish():
    src = open(main.__file__, encoding="utf-8").read()
    i, j = src.index("[divorced-marriage 2026-10-11]"), src.index("# [audit 2026-10-04] one final deterministic pass")
    assert i < j and "_existing_union_lane" in src[i:j] and 'in ("divorced", "separated")' in src[i:j]


def test_retrospective_questions_stay_out_of_the_lane():
    assert main._DU_PAST_RX.search("Why did my marriage fail?") and main._DU_PAST_RX.search("What went wrong in my marriage?")
    assert not main._DU_PAST_RX.search("Is there any problem in my married life?") and not main._DU_PAST_RX.search("Will my marriage improve?")
    assert main._EXISTING_UNION_RX.search("Is there any problem in my married life?")
