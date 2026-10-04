"""[money-not-funding 2026-10-04] Money questions score on the 'funding' recipe but the
narrator must never be told it's a funding event (Andres: 'one raise', 'funding conversation')."""
from antar_engine import event_narrator as en


def test_money_concerns_get_money_noun_and_label():
    for c in ("finance", "wealth", "money"):
        g = {"event": "funding", "concern": c}
        assert en._event_noun(g) == "money window"
        assert "NOT raising outside capital" in en._event_label(g)
    s = en._opening_sentence_for({"client_verdict": "YES", "window": {"label": "Oct 2026 – Dec 2026"}},
                                 {"event": "funding", "concern": "finance"})
    assert "money window" in s and "funding" not in s


def test_real_funding_question_keeps_funding():
    g = {"event": "funding", "concern": "funding"}
    assert en._event_noun(g) == "funding window" and en._event_label(g) == "funding"
    assert en._event_noun({"event": "career", "concern": "career"}) == "career window"
