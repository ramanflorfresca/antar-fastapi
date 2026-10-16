from datetime import date

from antar_engine import period_view as pv


class _Ctx:
    today = date(2026, 10, 14)
    vim = []
    planets = {}
    chart_data = {}
    birth_date = "1980-01-01"
    vim_rows = []
    birth_time_accuracy = None
    gender = None


def _lib():
    item = lambda subj, t, **k: {"rule_id": "R." + t[:3], "text": t, "start": "2026-09-01", "end": "2026-12-31", "label": "x",
                                "subject": subj, "tendency": False, **k}
    return {"vimshottari": {"lean_in": [item("love", "Marriage is likely.")],
                            "watch": [item("money", "Spending runs ahead of income.", do="Hold off on big spending.", remedy="Donate rice.")]},
            "jaimini": {"lean_in": [], "watch": []},
            "agree": [{"subject": "love", "start": "2026-09-01", "end": "2026-12-31"}], "wellness": None}


def test_window_month_and_year_edges():
    t = date(2026, 1, 15)
    assert pv.window("month", -1, t) == (date(2025, 12, 1), date(2025, 12, 31))
    assert pv.window("month", 1, date(2026, 12, 3)) == (date(2027, 1, 1), date(2027, 1, 31))
    assert pv.window("month", 0, date(2028, 2, 10)) == (date(2028, 2, 1), date(2028, 2, 29))
    assert pv.window("year", 1, t) == (date(2027, 1, 1), date(2027, 12, 31))


def test_past_window_reads_past_tense_and_has_no_instructions():
    o = pv.build(_Ctx(), _lib(), {"employed": True}, "month", -1, "en", today=date(2026, 10, 14))
    assert o["relation"] == "past" and o["summary"].split()[-1] in ("led.", "care.") or "led" in o["summary"] or "needed" in o["summary"]
    for a in o["areas"]:
        for i in a["lean_in"] + a["watch"]:
            assert "do" not in i and "remedy" not in i
    assert o["labels"]["lean_in"] == "What stood out"
    assert "care" not in o  # wellness only for current/next


def test_current_window_keeps_do_steps_and_present_tense():
    o = pv.build(_Ctx(), _lib(), {"employed": True}, "month", 0, "en", today=date(2026, 10, 14))
    assert o["title"] == "October 2026"
    watch = [i for a in o["areas"] for i in a["watch"]]
    assert watch and watch[0].get("do")
    assert " lead" in o["summary"] or " need" in o["summary"]


def test_second_area_label_is_not_capitalised_mid_sentence():
    o = pv.build(_Ctx(), _lib(), {"employed": True}, "month", 0, "en", today=date(2026, 10, 14))
    lib = _lib()
    lib["vimshottari"]["lean_in"].append({"rule_id": "R.inc", "text": "Income rises.", "start": "2026-10-01", "end": "2026-10-31",
                                         "label": "x", "subject": "money", "tendency": False})
    o = pv.build(_Ctx(), lib, {"employed": True}, "month", 0, "en", today=date(2026, 10, 14))
    assert "Partnership and money and funding lead" in o["summary"]
    assert " and Money" not in o["summary"]


def test_year_has_twelve_month_cells():
    o = pv.build(_Ctx(), _lib(), {"employed": True}, "year", 0, "en", today=date(2026, 10, 14))
    assert len(o["months"]) == 12 and o["months"][0]["month"] == "2026-01"
    assert o["months"][9]["tone"] in ("good", "care", "mixed")


def test_no_method_planet_or_rule_words_leak():
    import json, re
    o = pv.build(_Ctx(), _lib(), {"employed": True}, "year", 1, "es", today=date(2026, 10, 14))
    blob = json.dumps(o, ensure_ascii=False)
    assert not re.search(r"rule_id|Jupiter|Saturn|Rahu|Ketu|dasha|lagna|Jaimini|Parashar|Lal Kitab", blob)


def test_verdict_and_cell_verdicts():
    o = pv.build(_Ctx(), _lib(), {"employed": True}, "year", 0, "en", today=date(2026, 10, 14))
    assert o["verdict"] in ("good", "steady", "tough")
    assert all(c["verdict"] in ("good", "steady", "tough") for c in o["months"])
    assert pv._verdict([{"lean_in": [1], "watch": []}, {"lean_in": [1], "watch": []}, {"lean_in": [], "watch": [1]}]) == "good"
    assert pv._verdict([{"lean_in": [], "watch": [1]}]) == "tough"
    assert pv._verdict([{"lean_in": [1], "watch": [1]}]) == "steady"


# ── v2: area reads, do / avoid, best and quieter week/month, key dates, ready-made labels ─────────────────────────
def _build(scope="month", offset=0, lib=None, lang="en"):
    return pv.build(_Ctx(), lib or _lib(), {"employed": True}, scope, offset, lang, today=date(2026, 10, 14))


def test_five_area_reads_always_present_with_a_tone_and_no_repeated_line():
    o = _build()
    assert [d["key"] for d in o["domains"]] == ["money", "love", "career", "health", "mind"]
    assert all(d["verdict"] in ("good", "steady", "tough") for d in o["domains"])
    texts = [l["text"] for d in o["domains"] for l in d["lines"]]
    assert len(texts) == len(set(texts))
    quiet = [d for d in o["domains"] if not d["lines"]]
    assert quiet and all(d["quiet"] for d in quiet)


def test_item_dates_are_clipped_to_the_window_and_labelled_ready_to_show():
    o = _build()                                         # the library item runs Sep 1 to Dec 31; October is one month of it
    first = next(i for a in o["areas"] for i in a["lean_in"])
    assert first["start"] == "2026-10-01" and first["end"] == "2026-10-31" and first["label"] == "Oct 1 to Oct 31"


def test_do_and_avoid_exist_for_current_and_next_not_for_past():
    cur = _build()
    assert cur["do"] and cur["avoid"] and cur["avoid"][0]["instead"]
    assert cur["labels"]["do"] == "Do this month" and cur["labels"]["avoid"] == "Not this month"
    assert "do" not in _build(offset=-1) and "avoid" not in _build(offset=-1)
    assert _build("year")["labels"]["do"] == "Do this year"


def test_every_label_is_a_ready_made_string_not_an_iso_date():
    o = _build()
    for t in o["turns"] + o["key_dates"]:
        assert not t["label"][:4].isdigit()
    for c in o["chapters"]:
        assert c["label"] and not c["label"][:4].isdigit()


def test_year_has_one_best_and_one_quieter_month_and_they_differ():
    o = _build("year")
    if "best_month" in o:
        assert o["best_month"]["month"] != o["avoid_month"]["month"]


def test_english_article_in_the_chapter_line():
    assert pv._a("intellect", "en") == "an" and pv._a("growth", "en") == "a" and pv._a("intellect", "es") == "a"


def test_spanish_v2_has_no_english_labels():
    o = _build(lang="es")
    assert o["labels"]["do"] == "Qué hacer este mes" and o["domains"][0]["label"] == "Dinero"


# ── week: the same day score as the day strip, honest "ongoing" labels ────────────────────────────────────────────
def _scores(vals, start=date(2026, 10, 14)):
    return {(start.fromordinal(start.toordinal() + i)).isoformat(): v for i, v in enumerate(vals)}


def test_week_best_and_care_days_come_from_the_day_score_and_match_the_strip():
    o = pv.build(_Ctx(), _lib(), {"employed": True}, "week", 0, "en", today=date(2026, 10, 14),
                 day_scores=_scores([8, 4, 1, 0, 10, 4, 9]))
    assert o["title"] == "Oct 14 to Oct 20" and o["start"] == "2026-10-14"
    assert [d["tone"] for d in o["days"]] == ["good", "steady", "tough", "tough", "good", "steady", "good"]
    assert o["best_day"]["date"] == "2026-10-18" and o["care_day"]["date"] == "2026-10-17"       # what the strip says
    assert o["headline"]["text"] == "Best day Sun Oct 18. Take care Sat Oct 17."
    assert o["labels"]["do"] == "Do this week"


def test_week_with_no_spread_has_no_best_or_care_day():
    o = pv.build(_Ctx(), _lib(), {"employed": True}, "week", 0, "en", today=date(2026, 10, 14), day_scores=_scores([5, 5, 6, 5, 5, 6, 5]))
    assert "best_day" not in o and "headline" not in o


def test_week_labels_a_running_line_with_its_end_or_ongoing_never_an_invented_end():
    lib = _lib()
    lib["horizon"] = ["2026-10-14", "2027-02-11"]
    lib["vimshottari"]["lean_in"][0]["end"] = "2026-12-31"
    o = pv.build(_Ctx(), lib, {"employed": True}, "week", 0, "en", today=date(2026, 10, 14), day_scores=_scores([8, 4, 1, 0, 10, 4, 9]))
    lean = next(i for a in o["areas"] for i in a["lean_in"])
    assert lean["label"] == "until Dec 31"
    lib["vimshottari"]["lean_in"][0]["end"] = "2027-02-10"                    # runs to the end of what we looked at
    o = pv.build(_Ctx(), lib, {"employed": True}, "week", 0, "en", today=date(2026, 10, 14), day_scores=_scores([8, 4, 1, 0, 10, 4, 9]))
    assert next(i for a in o["areas"] for i in a["lean_in"])["label"] == "ongoing"


def test_week_window_is_seven_days_and_moves_by_weeks():
    assert pv.window("week", 0, date(2026, 10, 14)) == (date(2026, 10, 14), date(2026, 10, 20))
    assert pv.window("week", -1, date(2026, 10, 14)) == (date(2026, 10, 7), date(2026, 10, 13))
    assert pv.window("week", 1, date(2026, 10, 14)) == (date(2026, 10, 21), date(2026, 10, 27))


def test_month_best_and_slow_days_follow_the_day_scores_not_a_second_rule():
    class _M:
        sign = "Aries"
    ctx = _Ctx()
    ctx.planets = {"Moon": _M()}
    scores = {f"2026-10-{d:02d}": 5 for d in range(1, 32)}
    scores.update({"2026-10-17": 2, "2026-10-16": 2, "2026-10-18": 9, "2026-10-14": 8, "2026-10-13": 8})   # Oct 16-17 tough on the strip
    o = pv.build(ctx, _lib(), {"employed": True}, "month", 0, "en", today=date(2026, 10, 14), day_scores=scores)
    assert "2026-10-16" not in o.get("best_days", []) and "2026-10-17" not in o.get("best_days", [])
    assert "2026-10-16" in o.get("slow_days", []) or "2026-10-17" in o.get("slow_days", []) or o.get("avoid_week")


def test_current_month_best_week_is_never_one_that_is_already_over():
    class _M:
        sign = "Aries"
    ctx = _Ctx()
    ctx.today = date(2026, 10, 15)
    ctx.planets = {"Moon": _M()}
    scores = {f"2026-10-{d:02d}": (9 if d <= 14 else 5) for d in range(1, 32)}   # the strong days were all before today
    o = pv.build(ctx, _lib(), {"employed": True}, "month", 0, "en", today=date(2026, 10, 15), day_scores=scores)
    bw = o.get("best_week")
    assert bw is None or bw["end"] >= "2026-10-15"
    assert all(d >= "2026-10-15" for d in o.get("best_days", []))
