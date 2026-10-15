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
