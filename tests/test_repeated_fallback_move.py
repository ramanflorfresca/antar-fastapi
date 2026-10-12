from antar_engine.answer_polish import _pick_fallback, _FALLBACK_NEXT, _FALLBACK_ALT


def test_second_day_question_gets_a_different_move():
    first = _pick_fallback("work", "en", "", [])
    second = _pick_fallback("work", "en", "", [first])
    assert first != second


def test_every_group_and_language_has_an_alternate():
    for grp in ("work", "people", "health"):
        for lg in ("en", "es", "pt", "hi"):
            assert _FALLBACK_ALT[grp][lg] != _FALLBACK_NEXT[grp][lg]
            nxt = _pick_fallback(grp, lg, "", [_FALLBACK_NEXT[grp][lg]])
            assert nxt == _FALLBACK_ALT[grp][lg]
