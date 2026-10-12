from datetime import date

from antar_engine import window_guard as wg

TODAY = date(2026, 10, 12)


def test_parse_label():
    assert wg.parse_label("Nov 2026 – Apr 2027") == (date(2026, 11, 1), date(2027, 4, 30))
    assert wg.parse_label("late 2027") == (date(2027, 9, 1), date(2027, 12, 31))
    assert wg.parse_label("Jan 2027") == (date(2027, 1, 1), date(2027, 1, 31))
    assert wg.parse_label("2024-11 to 2027-02") == (date(2024, 11, 1), date(2027, 2, 28))
    assert wg.parse_label("soon") is None and wg.parse_label(None) is None


def test_a_window_already_open_reads_now_through_the_end():
    for src, want in (
            ("Several methods point to late 2024 through late 2027 as your strongest window.", "now through late 2027"),
            ("The window runs from late 2024 to late 2027.", "from now through late 2027"),
            ("It sits between Nov 2024 and Sep 2027.", "between now and Sep 2027"),
            ("Your window is Oct 2026 – Jan 2027 and holds.", "now through Jan 2027"),          # starts this month: already under way
            ("The strongest window is Nov 2024 – Apr 2027.", "now through Apr 2027")):
        out = wg.clip_forward(src + " Make one move.", TODAY)
        assert want in out and "2024" not in out, (src, out)


def test_future_and_day_level_dates_are_left_alone():
    t = "A window opens Nov 2026 – Jan 2027. Calm days: Oct 18–23. The inner period runs Dec 19 through Feb 1."
    assert wg.clip_forward(t, TODAY) == t


def test_a_wholly_past_window_offered_as_coming_is_dropped_but_not_below_two_sentences():
    t = "The foundation is thin. The next window opens Nov 2024 – Mar 2025. Make one direct move."
    out = wg.clip_forward(t, TODAY)
    assert "2024" not in out and "foundation is thin" in out and "direct move" in out
    short = "The next window opens Nov 2024 – Mar 2025. Make one move."
    assert wg.clip_forward(short, TODAY) == short                    # would leave one sentence: unchanged


def test_history_is_not_rewritten():
    t = "You were laid off in June 2025. Your bond started between 2019 and 2021. The window opens Nov 2026 – Jan 2027."
    assert wg.clip_forward(t, TODAY) == t


def test_conflicting_window_sentence_is_dropped_the_headline_one_is_kept():
    canon = "Nov 2026 – Apr 2027"
    t = ("Likely — the partnership window is Nov 2026 – Apr 2027. The strongest window for a serious step runs now through September 2028. "
         "The foundation is mixed. Make one honest move.")
    out = wg.drop_conflicting_window_sentences(t, canon, TODAY)
    assert "2028" not in out and "Nov 2026 – Apr 2027" in out and "foundation is mixed" in out
    inside = "The window is Dec 2026 – Mar 2027. Make one honest move."
    assert wg.drop_conflicting_window_sentences(inside, canon, TODAY) == inside
    no_word = "The sub-period runs Oct 2026 – Sep 2028. Make one honest move."
    assert wg.drop_conflicting_window_sentences(no_word, canon, TODAY) == no_word          # not announced as a window
    assert wg.drop_conflicting_window_sentences(t, None, TODAY) == t


def test_reconcile_block_replaces_competing_lines_with_one_headline():
    block = ("RELATIONSHIP QUESTION — x\n"
             "TIMING (multiple methods converge): The strongest partnership window opens around 2024-11 — 4 independent systems agree. Basis: a | b.\n"
             "The next sub-period genuinely tied to partnership runs Oct 2026 – Sep 2027 (it is already under way): that is when a serious step is best supported.\n"
             "Close with ONE concrete next step.")
    out = wg.reconcile_relationship_block(block, "Nov 2026 – Apr 2027")
    assert "2024-11" not in out and "the ONE headline window is Nov 2026 – Apr 2027" in out
    assert "(WIDER CONTEXT, not the headline window) The next sub-period" in out
    assert out.rstrip().endswith("is 'now through <end>'.") and "ONE WINDOW:" in out
    assert wg.reconcile_relationship_block(block, None) == block and wg.reconcile_relationship_block(block, "soon") == block


def test_never_raises():
    for bad in (None, "", 5, "no dates here at all."):
        wg.clip_forward(bad, TODAY); wg.drop_conflicting_window_sentences(bad, "Nov 2026 – Apr 2027", TODAY); wg.reconcile_relationship_block(bad, "x")


def test_marriage_timing_says_open_now_for_a_window_already_under_way():
    import pathlib
    src = (pathlib.Path(__file__).resolve().parents[1] / "antar_engine" / "relationships.py").read_text()
    assert "The strongest partnership window is open now, through" in src and 'best["start"][:10] <= anchor.date().isoformat()' in src


def test_polish_applies_both_guards_and_keeps_the_rest():
    from antar_engine.answer_polish import polish_answer
    pay = {"read": ("Reaching out is supported right now. Several independent methods point to late 2024 through late 2027 as your strongest window. "
                    "The bond's foundation is mixed. Best calm days to start the conversation: Oct 15 – Oct 23."),
           "next": "Send one honest message.", "timing": "Nov 2026 – Apr 2027"}
    polish_answer(pay, language="en", typed_question="Will he or she come back?", concern="love")
    assert "2024" not in pay["read"] and "late 2027" not in pay["read"]               # the competing window is gone
    assert "foundation is mixed" in pay["read"] and "Oct 15 – Oct 23" in pay["read"]    # everything else survives, day-level dates included
    no_timing = {"read": "The strongest window runs late 2024 through late 2027. Make one move.", "next": "x"}
    polish_answer(no_timing, language="en", typed_question="x", concern="love")
    assert "now through late 2027" in no_timing["read"]                                  # no headline window: just forward-only


def test_event_engine_window_reconciles_the_block_in_main():
    import pathlib
    src = (pathlib.Path(__file__).resolve().parents[1] / "main.py").read_text()
    i = src.index("[one-window 2026-10-12] the event engine's window is THE window")
    assert "reconcile_relationship_block(_ask_relationship_block, _ee_timing)" in src[i:i + 900]
    assert i > src.index("_ask_conv_block = _ee[\"narrator_prompt\"]") - 50


def test_reunion_is_timed_by_the_reconciliation_engine_not_the_marriage_convergence():
    import pathlib
    src = (pathlib.Path(__file__).resolve().parents[1] / "main.py").read_text()
    i = src.index("[one-window 2026-10-12] A REUNION is timed by the RECONCILIATION engine")
    chunk = src[i:i + 3500]
    assert '"reconciliation"' in chunk and "_DUw._state(_rr, date.today())" in chunk
    assert "not _is_reconcile" in chunk                                      # the marriage convergence line no longer fires for a reunion
    assert "reconcile_relationship_block(_ask_relationship_block, _rel_headline_window)" in src


def test_a_rewritten_reunion_question_counts_as_a_reunion():
    import pathlib
    src = (pathlib.Path(__file__).resolve().parents[1] / "main.py").read_text()
    i = src.index("_is_reconcile = (_detect_concern(question) == \"reconciliation\"")
    assert '_ASK_REFRAMED.get() or {}).get("kind") in ("reunion", "contact")' in src[i:i + 300]


def test_unchanged_text_is_returned_untouched_line_breaks_included():
    t = "Here is what the timing supports for each.\nRebuilding with your former spouse: the window opens Mar 2028."
    assert wg.clip_forward(t, TODAY) == t
    assert wg.drop_conflicting_window_sentences(t, "Mar 2028", TODAY) == t
    assert wg.drop_conflicting_window_sentences(t, "Nov 2026 – Apr 2027", TODAY) != "" 


def test_the_divorced_answer_names_two_windows_on_purpose():
    from antar_engine.answer_polish import polish_answer
    from tests.data.relationship_lane_checks import lane_checks
    read = ("You're deciding between waiting on your former spouse and building something new.\n"
            "Rebuilding with your former spouse: the supportive window opens Mar 2028 – May 2028; until then it is groundwork.\n"
            "A new partnership: the next supportive window is Nov 2026 – Jan 2027; before it, build the ground.\n"
            "The timing shows what supports you; it cannot show what the other person will do.")
    pay = {"read": read, "next": "Decide what you want.", "timing": "Nov 2026 – Jan 2027"}
    polish_answer(pay, language="en", typed_question="Should I wait or move on?", concern="love", existing_union=True)
    assert "Mar 2028" in pay["read"] and "Nov 2026" in pay["read"]
    q = {"id": 30, "lane": "reframe", "q": "Should I wait for him or her, or move on?"}
    assert "WINDOW_CONFLICT" not in lane_checks(q, {"read": read, "next": "x", "concern": "love", "timing": "Nov 2026 – Jan 2027"})
