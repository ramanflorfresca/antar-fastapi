"""Follow-ups to the rung-depth work (observed on production 2026-10-10): the long reads lead with the
NEXT open window, month advice never names a date already behind today, the year detail has one row per
month, the chapter rung carries `ahead` / `next_months`, the chapter chip says 'Life chapter', and
Right-now `do` is one list."""
import re
from datetime import date, timedelta

import pytest

from antar_engine import topic_copy as C
from antar_engine import topic_detail as D
from antar_engine import topic_engine as T

LANGS = ("en", "es", "pt", "hinglish")
TODAY = date(2026, 10, 10)

_JARGON = re.compile(
    r"\b(dasha|dasa|mahadasha|antardasha|pratyantar\w*|jaimini|vimsottari|vimshottari|chara|malefic\w*|benefic\w*|"
    r"transits?|gochar|karakas?|lagna|nakshatra|navamsa|dusthana|kendra|trikona|ascendant|houses?|d-?\d{1,2}|"
    r"sun|moon|mars|mercury|jupiter|venus|saturn|rahu|ketu|season)\b", re.I)


def _ctx():
    ctx = T.TopicContext("syn", {"lagna": {"sign": "Aries", "sign_index": 0}, "planets": {}},
                         {"vimsottari": [
                             {"lord_or_sign": "Venus", "planet_or_sign": "Venus", "level": "antardasha",
                              "start_date": "2026-08-13", "end_date": "2029-04-25", "start": "2026-08-13", "end": "2029-04-25"}]},
                         birth_date="1990-10-15")
    ctx.events = lambda s, e, fast: []
    return ctx


def _bucket(i):
    s = TODAY + timedelta(days=30 * i)
    return (s, s + timedelta(days=29))


def _scan_with(monkeypatch, ctx, lit):
    """lit = {bucket index: (mode, score)}; only the long scan finds anything."""
    base = T.assess(ctx, "money", TODAY, [])

    def fake(c, key, scale, per, today):
        if scale != "season":
            return []
        out = []
        for i in range(24):
            b = _bucket(i)
            if i in lit:
                out.append((b, dict(base, lit=True, mode=lit[i][0], score=lit[i][1], n_signals=1)))
            else:
                out.append((b, dict(base, lit=False, mode="steady", score=0.0, n_signals=0)))
        return out
    monkeypatch.setattr(T, "_scan", fake)


# ── 1. the long read leads with the NEXT window ──────────────────────────────
def test_season_leads_with_the_earliest_upcoming_window_not_the_strongest(monkeypatch):
    ctx = _ctx()
    # opens: buckets 3-6 (Jan 2027, weaker), 13-15 (2027-11), 21-23 (2028-07, the strongest)
    _scan_with(monkeypatch, ctx, {**{i: ("open", 2.0) for i in (3, 4, 5, 6, 13, 14)}, **{i: ("open", 4.0) for i in (21, 22, 23)}})
    r = T.read_topic(ctx, "money", "season", TODAY, "en", with_best_fit=False)
    first = _bucket(3)[0]
    assert r["best_window"]["start"] == first.isoformat()
    assert r["window_phase"] == "later"
    dlab = C.day_label_y(first, "en")
    assert dlab in r["claim"] and dlab in r["your_move"]
    strongest = _bucket(21)[0]
    assert r["strongest_window"]["start"] == strongest.isoformat()
    assert r["claim"].endswith(C.pick(C.STRONGEST_TAIL, "en")["open"].format(
        start=C.day_label_y(strongest, "en"), end=C.day_label_y(_bucket(23)[1], "en")))
    # the read and the windows list name the same windows
    w = T.windows_for(ctx, "money", "season", TODAY)
    assert min(x["start"] for x in w["open"]) == first
    assert any(x["start"] == strongest for x in w["open"])


def test_no_second_sentence_when_the_later_window_is_not_stronger(monkeypatch):
    ctx = _ctx()
    _scan_with(monkeypatch, ctx, {**{i: ("open", 3.0) for i in (3, 4)}, **{i: ("open", 3.0) for i in (21, 22, 23)}})
    r = T.read_topic(ctx, "money", "season", TODAY, "en", with_best_fit=False)
    assert r["best_window"]["start"] == _bucket(3)[0].isoformat()
    assert r["strongest_window"] is None and "strongest" not in r["claim"].lower()


def test_a_window_running_now_with_days_left_is_the_lead(monkeypatch):
    ctx = _ctx()
    _scan_with(monkeypatch, ctx, {**{i: ("open", 2.0) for i in (0, 1)}, **{i: ("open", 5.0) for i in (21, 22)}})
    r = T.read_topic(ctx, "money", "season", TODAY, "en", with_best_fit=False)
    assert r["best_window"]["start"] == TODAY.isoformat() and r["window_phase"] == "now"


def test_month_scale_still_leads_with_its_strongest(monkeypatch):
    runs = [{"start": TODAY, "end": TODAY, "score": 1.0, "assessments": []},
            {"start": TODAY + timedelta(days=9), "end": TODAY + timedelta(days=15), "score": 3.0, "assessments": []}]
    assert T._best_run(runs) is runs[1]


# ── 5. chip + labels ─────────────────────────────────────────────────────────
@pytest.mark.parametrize("lang,chip,label", [
    ("en", "Life chapter", "Your current life chapter · to Apr 2029"),
    ("es", "Capítulo de vida", "Tu capítulo de vida actual · hasta abr 2029"),
    ("pt", "Capítulo de vida", "O seu capítulo de vida atual · até abr 2029"),
    ("hinglish", "Life chapter", "Aapka maujooda life chapter · Apr 2029 tak")])
def test_long_stretch_chip_and_label(lang, chip, label):
    p = T._period(_ctx(), "season", TODAY, lang)
    assert (p["chip"], p["rung"], p["label"]) == (chip, "stretch", label)
    assert p["span_label"] == C.pick(C.SPAN_END, lang).format(
        span=C.season_text(C.SPAN_TEXT, lang, p["span"]), end=C.month_year_short(date(2029, 4, 25), lang))
    r = T.read_topic(_ctx(), "money", "season", TODAY, lang, with_best_fit=False)
    assert r["period"]["span_label"] == p["span_label"] and r["period"]["rung"] == "stretch"


def test_hindi_falls_back_to_english_for_the_chip():
    assert T._period(_ctx(), "season", TODAY, T.C.serve_language("hi"))["chip"] == "Life chapter"


@pytest.mark.parametrize("lang", LANGS)
def test_new_strings_are_complete_and_jargon_free(lang):
    for tbl in (C.STRONGEST_TAIL, C.WINDOW_ITEM):
        assert set(tbl[lang]) == {"open", "care"} == set(tbl["en"])
        for v in tbl[lang].values():
            assert not _JARGON.search(v), v
    assert "{start}" in C.STRONGEST_TAIL[lang]["open"] and "{end}" in C.STRONGEST_TAIL[lang]["care"]
    assert not _JARGON.search(C.CHIP[lang]["season"])


# ── 2. month advice never names a date already behind today ──────────────────
MONTH = {
    "month_theme": "Your income moves this month.",
    "overview": "Your income looks strong from mid-month. Cap your money exposure before October 8.",
    "best_week": "Week of October 26 — income and a payout converge.",
    "caution_week": "Week of October 10 — a money bet can backfire fast.",
    "priority_actions": [
        {"action": "Cap your exposure on any bet before October 8.", "domain": "Money & wealth"},
        {"action": "Lock in a payout between October 14 and 23.", "domain": "Money & wealth"},
        {"action": "Delay the purchase until after October 8.", "domain": "Money & wealth"},
        {"action": "Review your savings this month.", "domain": "Money & wealth"}],
    "highlights": [{"domain": "money", "text": "Your payout window closed on October 9.", "priority": 1},
                   {"domain": "money", "text": "Income is where the month rewards you.", "priority": 2}],
    "active_domains": [{"key": "money", "label": "Money & wealth", "window": "2026-10-07 – 2026-10-08", "caution": False}],
}


def test_month_items_dated_before_today_never_appear():
    m = D.build_detail("money", "month", {"month": MONTH}, TODAY)
    acts = [a["action"] for a in m["priority_actions"]]
    assert acts == ["Lock in a payout between October 14 and 23.", "Delay the purchase until after October 8.",
                    "Review your savings this month."]          # 'after' points forward; 'before October 8' is gone
    assert [h["text"] for h in m["highlights"]] == ["Income is where the month rewards you."]
    assert "October 8" not in (m["overview"] or "")
    assert m["caution_week"].startswith("Week of October 10") and m["best_week"].startswith("Week of October 26")
    assert m["focus"] is None                                   # the whole window ended Oct 8 and nothing is careful


def test_focus_window_is_clamped_to_start_today():
    mo = dict(MONTH, active_domains=[{"key": "money", "label": "Money & wealth", "window": "2026-10-07 – 2026-10-18", "caution": True}])
    f = D.build_detail("money", "month", {"month": mo}, TODAY)["focus"]
    assert f == {"window": "2026-10-10 – 2026-10-18", "careful": True}


@pytest.mark.parametrize("text,past", [
    ("Cap your exposure before October 8.", True), ("Limita tu exposición antes del 8 de octubre.", True),
    ("Limite a exposição antes de 8 de outubro.", True), ("Week of October 10 — care.", False),
    ("Week of October 3 — care.", True), ("Wait until after October 8.", False), ("No dates here.", False),
    ("Lock in a payout between October 14 and 23.", False), ("Done by 2026-10-09.", True)])
def test_is_past(text, past):
    assert D.is_past(text, TODAY) is past


def test_a_date_months_behind_is_next_year_not_past():
    assert D.is_past("Review it in January 5.", TODAY) is False


# ── 3. year duplicates ───────────────────────────────────────────────────────
def test_year_key_months_merge_rows_with_the_same_when_and_empty_sections_are_null():
    y = {"year_theme": "A year of income.",
         "critical_dates": [{"date": "November 2026", "event": "Your income comes under pressure."},
                            {"date": "November 2026", "event": "Your income comes under pressure — protect savings."},
                            {"date": "March 2027", "event": "A payout arrives for your income."}],
         "arcs": [{"key": "money", "trend": "pressure", "when": "peaks Nov 2026"}]}
    d = D.build_detail("money", "year", {"year": y}, TODAY)
    assert [(k["when"]) for k in d["key_months"]] == ["November 2026", "March 2027"]
    assert d["key_months"][0]["text"] == "Your income comes under pressure — protect savings."
    assert d["strong"] is None and d["caution"] is None and d["prioritise"] is None
    assert d["trend"] == {"trend": "pressure", "when": "peaks Nov 2026"}


# ── 4. chapter rung: ahead + next_months ─────────────────────────────────────
ARC = {
    "gist": "Build your path steadily.",
    "cycle_timeline": [
        {"kind": "now", "start": "2026-08-13", "end": "2027-01-08", "title": "The tightest stretch of this",
         "body": "Pressure concentrates on income and a sibling. Hold steady.", "when_label": "until early Jan 2027", "events": []},
        {"kind": "sub_chapter", "start": "2026-08-13", "end": "2029-04-25", "title": "A restless, ambitious undercurrent",
         "body": "Boundary-pushing, unconventional moves. One window to watch here:", "events": []},
        {"kind": "turn", "start": "2029-04-25", "end": "2031-09-19", "title": "The pressure lifts; the tone lightens",
         "body": "The undercurrent gives way to expansion and mentorship.", "when_label": "around late Apr 2029", "events": []},
        {"kind": "turn", "start": "2031-09-19", "end": "2033-01-01", "title": "A new home settles",
         "body": "A move and family matters take over.", "events": []}],
    "predicted_events": [{"title": "A meaningful moment", "category": "WORK", "window_start": "2027-10-22"}],
}
FEED = {"tracks": [{"topic": "money", "windows": [
    {"kind": "open", "start": "2026-10-10", "end": "2026-10-10"},
    {"kind": "open", "start": "2027-01-08", "end": "2027-05-07"},
    {"kind": "care", "start": "2027-06-01", "end": "2027-06-20"},
    {"kind": "open", "start": "2028-07-01", "end": "2028-10-09"}]}]}


@pytest.mark.parametrize("lang", LANGS)
def test_season_ahead_and_next_months_are_filled_for_a_topic_with_no_events(lang):
    d = D.build_detail("money", "season", {"arc": ARC, "feed": FEED, "lang": lang}, TODAY)
    assert [a["title"] for a in d["ahead"]] == ["The pressure lifts; the tone lightens"]   # not the topic-less other turn
    assert d["tightest_stretch"]["title"] == "The tightest stretch of this"
    assert [m["start"] for m in d["next_months"]] == ["2026-10-10", "2027-01-08", "2027-06-01"]   # within 12 months
    assert d["next_months"][1]["title"] == C.pick(C.WINDOW_ITEM, lang)["open"].format(area=C.pick(C.AREA, lang)["money"])
    assert d["next_months"][1]["when"] == (
        f"{C.day_label_y(date(2027, 1, 8), lang)} – {C.day_label_y(date(2027, 5, 7), lang)}")


def test_next_months_is_null_when_nothing_is_available():
    d = D.build_detail("money", "season", {"arc": {"gist": "A story.", "cycle_timeline": []}}, TODAY)
    assert d["next_months"] is None


def test_a_body_that_trails_into_a_colon_is_trimmed():
    arc = dict(ARC, cycle_timeline=[dict(ARC["cycle_timeline"][1], start="2027-02-01")])
    assert D.build_detail("money", "season", {"arc": arc}, TODAY)["ahead"][0]["body"] == "Boundary-pushing, unconventional moves."


# ── 6. Right now: one `do` list ──────────────────────────────────────────────
def test_right_now_do_is_one_deduped_list_with_topic_items_first():
    daily = {"do_today": ["take a short walk", "handle a money task", "take a short walk"], "dont_today": ["a large purchase"],
             "domains": []}
    d = D.build_detail("money", "today", {"daily": daily}, TODAY)
    assert d["do"] == ["handle a money task", "take a short walk"]
    assert not (d.get("day") or {}).get("do")


@pytest.mark.parametrize("lang", LANGS)
def test_the_two_long_rungs_have_different_chips_and_labels(lang):
    st, ch = T._period(_ctx(), "season", TODAY, lang), T._period(_ctx(), "chapter", TODAY, lang)
    assert st["chip"] != ch["chip"] and st["label"] != ch["label"] and (st["rung"], ch["rung"]) == ("stretch", "chapter")


def test_long_read_with_care_before_open_leads_with_the_care_window(monkeypatch):
    ctx = _ctx()
    _scan_with(monkeypatch, ctx, {**{i: ("care", 2.0) for i in (3, 4)}, **{i: ("open", 3.0) for i in (13, 14)}})
    r = T.read_topic(ctx, "money", "season", TODAY, "en", with_best_fit=False)
    first = _bucket(3)[0]
    assert r["tone"] == "care" and r["window_phase"] == "later"
    assert C.day_label_y(first, "en") in r["claim"] and r["claim"].startswith("Over the next 2½ years, money asks for care from")
    assert r["best_window"]["start"] == _bucket(13)[0].isoformat()      # the later open window is still returned
    assert r["watch_window"]["start"] == first.isoformat()


def test_long_read_with_open_before_care_still_leads_with_open(monkeypatch):
    ctx = _ctx()
    _scan_with(monkeypatch, ctx, {**{i: ("open", 3.0) for i in (3, 4)}, **{i: ("care", 2.0) for i in (13, 14)}})
    r = T.read_topic(ctx, "money", "season", TODAY, "en", with_best_fit=False)
    assert r["tone"] == "open" and "best stretch for money starts" in r["claim"]


# ── a window about to end is not a long read's headline ─────────────────────
def test_a_one_day_window_is_not_the_year_or_season_headline(monkeypatch):
    ctx = _ctx()
    _scan_with(monkeypatch, ctx, {0: ("open", 3.0)})
    # the only window is the bucket running today; shrink it to a single day
    monkeypatch.setattr(T, "_runs", lambda res, mode: [{"start": TODAY, "end": TODAY, "score": 3.0,
                                                         "assessments": [res[0][1]]}] if mode == "open" else [])
    r = T.read_topic(ctx, "money", "season", TODAY, "en", with_best_fit=False)
    assert r["tone"] == "steady" and r["best_window"] is None and "nothing sharp" in r["claim"]


def test_lead_run_none_when_only_a_short_live_window():
    run = {"start": TODAY, "end": TODAY + timedelta(days=2), "score": 1.0, "assessments": []}
    assert T._lead_run([run], TODAY) is None
    later = {"start": TODAY + timedelta(days=40), "end": TODAY + timedelta(days=60), "score": 1.0, "assessments": []}
    assert T._lead_run([run, later], TODAY) is later


# ── a steady month the engine marks careful no longer says 'nothing sharp' ──
def _careful_month(window):
    m = {"month_theme": "x", "active_domains": [{"key": "work", "label": "Work & reputation", "window": window, "caution": True}]}
    d = D.build_detail("career", "month", {"month": m}, TODAY)
    return {"topic": "career", "scale": "month", "language": "en", "tone": "steady", "detail": d,
            "claim": "Over the next 30 days, nothing sharp is pulling on your work, so keep your usual pace."}


@pytest.mark.parametrize("lang", LANGS)
def test_steady_month_with_a_careful_focus_names_the_stretch(lang):
    base = _careful_month("2026-10-12 – 2026-10-24")
    base["language"] = lang
    out = D.reconcile_month(base, lang)
    assert "nothing sharp" not in out["claim"] and out["claim"].startswith(C.SPAN_LEAD[lang]["month"])
    assert C.range_label(date(2026, 10, 12), date(2026, 10, 24), lang) in out["claim"]
    assert not _JARGON.search(out["claim"])
    assert D.reconcile_month(out, lang)["claim"] == out["claim"]          # idempotent


def test_steady_month_careful_without_a_window_and_untouched_cases():
    out = D.reconcile_month(_careful_month(None), "en")
    assert out["claim"] == "Over the next 30 days, it is steady overall for your work, with one stretch to watch."
    calm = _careful_month(None)
    calm["detail"]["focus"] = None
    assert D.reconcile_month(calm, "en") == calm
    openm = dict(_careful_month(None), tone="open")
    assert D.reconcile_month(openm, "en") == openm
