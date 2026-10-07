"""Topic picker + topic read: ranking, independence, dating, language, jargon.

Deterministic: fixed `today`, fixed births, no network (swisseph only)."""
import asyncio
import re
from datetime import date, timedelta

import pytest
from fastapi import HTTPException

from antar_engine import topic_copy as C
from antar_engine import topic_engine as T
from antar_engine.places_concern import CONCERN_MAP

TODAY = date(2026, 10, 7)
LANGS = ("en", "es", "pt", "hinglish")

# Words that must never reach a user in a topic string. Planet/sign names are
# banned too; the mantra step is the one place a Sanskrit mantra is quoted
# verbatim, so its kind is exempt from the planet-name check only.
_JARGON = re.compile(
    r"\b(dasha|dasa|mahadasha|antardasha|pratyantar\w*|jaimini|vimsottari|vimshottari|"
    r"chara|malefic\w*|benefic\w*|transits?|gochar|karakas?|lagna|nakshatra|navamsa|"
    r"dusthana|kendra|trikona|ascendant|houses?|d-?\d{1,2}|"
    r"sun|moon|mars|mercury|jupiter|venus|saturn|rahu|ketu|"
    r"sol|luna|marte|mercurio|j[úu]piter|saturno|"
    r"aries|taurus|gemini|cancer|leo|virgo|libra|scorpio|sagittarius|capricorn|aquarius|pisces)\b",
    re.I)


def _rows(d):
    out = []
    for lvl, key in (("mahadasha", "mahadashas"), ("antardasha", "antardashas")):
        for m in d[key]:
            out.append({"lord_or_sign": m["lord"], "planet_or_sign": m["lord"],
                        "start_date": m["start_date"], "end_date": m["end_date"],
                        "start": m["start_date"], "end": m["end_date"], "level": lvl})
    return out


def _real_ctx(birth="1990-10-15", time="14:10", acc=None):
    from antar_engine.chart import calculate_chart
    from antar_engine.vimsottari import calculate_vimsottari_from_chart
    cd = calculate_chart(birth, time, 17.38, 78.48, 5.5)
    d = calculate_vimsottari_from_chart(cd, cd["birth_jd"])
    return T.TopicContext("c1", cd, {"vimsottari": _rows(d)}, birth_date=birth,
                          birth_time_accuracy=acc)


BIRTHS = [("1985-03-15", "08:30"), ("1990-10-15", "14:10"), ("1978-07-02", "22:45"),
          ("2001-12-30", "05:05")]


@pytest.fixture(scope="module")
def ctxs():
    return [_real_ctx(b, t) for b, t in BIRTHS]


def _synth(dashas_planet=None, events=None, acc=None, lagna="Aries"):
    """Aries lagna: 10th lord Saturn, 6th lord Mars, 2nd Venus, 11th Saturn …"""
    dashas = {"vimsottari": []}
    if dashas_planet:
        dashas["vimsottari"] = [
            {"lord_or_sign": dashas_planet, "planet_or_sign": dashas_planet, "level": "mahadasha",
             "start_date": "2020-01-01", "end_date": "2040-01-01", "start": "2020-01-01", "end": "2040-01-01"},
            {"lord_or_sign": dashas_planet, "planet_or_sign": dashas_planet, "level": "antardasha",
             "start_date": "2026-06-01", "end_date": "2027-03-10", "start": "2026-06-01", "end": "2027-03-10"},
        ]
    ctx = T.TopicContext("syn", {"lagna": {"sign": lagna, "sign_index": 0}, "planets": {}},
                         dashas, birth_date="1990-10-15", birth_time_accuracy=acc)
    ctx.events = lambda s, e, fast, _ev=list(events or []): [
        x for x in _ev if s.isoformat() <= x["date"] <= e.isoformat()]
    return ctx


def _ev(d, planet, house, kind="aspect"):
    return {"date": d, "planet": planet, "natal_house": house, "event_type": kind,
            "natal_target": "X", "aspect_kind": "trine"}


# ── spec / independence ─────────────────────────────────────────────────────
def test_spec_mirrors_places_concern_map():
    assert set(T.TOPIC_KEYS) == set(CONCERN_MAP)
    for k in T.TOPIC_KEYS:
        assert set(T._topic_houses(k)) == set(CONCERN_MAP[k]["houses"]), k
        assert T.TOPIC_SPEC[k]["karakas"] == CONCERN_MAP[k]["karakas"], k


def test_movement_on_a_shared_house_is_credited_once_across_topics():
    # Family & Peace share the 4th, Love & Business the 7th: one event = one point of credit
    for house in range(1, 13):
        total = sum(T._CLAIM.get((k, house), 0.0) for k in T.TOPIC_KEYS)
        assert total <= 1.0 + 1e-9, (house, total)
    assert T._CLAIM[("family", 4)] == T._CLAIM[("peace", 4)] == 0.5
    assert T._CLAIM[("love", 7)] == T._CLAIM[("business", 7)] == 0.5


def test_one_event_on_a_shared_house_does_not_double_count():
    ctx = _synth(events=[_ev("2026-10-12", "Jupiter", 4)])
    fam = T.assess(ctx, "family", TODAY, ctx.events(TODAY, TODAY + timedelta(days=29), False))
    peace = T.assess(ctx, "peace", TODAY, ctx.events(TODAY, TODAY + timedelta(days=29), False))
    assert fam["score"] + peace["score"] == pytest.approx(0.75, abs=0.02)  # one 0.75 point split in two


def test_chapter_counts_once_even_when_lord_and_key_planet_coincide():
    # Aries lagna, Saturn runs: Saturn is the 10th lord AND a career key planet
    ctx = _synth("Saturn")
    a = T.assess(ctx, "career", TODAY, [])
    assert a["dasha_pts"] == 3.0 and a["score"] == 3.0


def test_second_timeline_only_confirms(monkeypatch):
    ctx = _synth()  # no running chapter at all
    monkeypatch.setattr(T, "_chara_weight", lambda *a, **k: 1.0)
    alone = T.assess(ctx, "career", TODAY, [])
    assert alone["score"] <= 0.5 and not alone["lit"] and not alone["chara_confirm"]
    ctx2 = _synth("Saturn")
    both = T.assess(ctx2, "career", TODAY, [])
    assert both["chara_confirm"] and both["chara_pts"] <= 1.0 and both["score"] <= 4.0


def test_motion_subevents_of_one_passage_count_once():
    evs = [_ev("2026-10-10", "Jupiter", 2, "ingress"), _ev("2026-10-11", "Jupiter", 2, "nakshatra_shift"),
           _ev("2026-10-14", "Jupiter", 2, "nakshatra_shift")]
    ctx = _synth(events=evs)
    a = T.assess(ctx, "money", TODAY, evs)
    assert a["n_signals"] == 1


# ── ranking + fallback ──────────────────────────────────────────────────────
def test_rank_shape_order_and_contiguous_ranks(ctxs):
    for ctx in ctxs:
        out = T.rank_topics(ctx, TODAY, "en")
        assert [r["rank"] for r in out] == list(range(1, 8))
        assert {r["key"] for r in out} == set(T.TOPIC_KEYS)
        assert set(out[0]) == {"key", "label", "status", "tag", "tone", "rank"}
        order = {"active": 0, "upcoming": 1, "steady": 2, "quiet": 3}
        st = [order[r["status"]] for r in out]
        assert st == sorted(st)
        assert all(r["tag"] for r in out)


def test_topics_tone_equals_topic_read_tone_at_best_fit_scale(ctxs):
    """A tile's colour and the read it opens can never disagree (4 real charts, 7 topics)."""
    for ctx in ctxs:
        out = {r["key"]: r for r in T.rank_topics(ctx, TODAY, "en")}
        for k in T.TOPIC_KEYS:
            assert out[k]["tone"] in ("open", "care", "steady")
            full = T.read_topic(ctx, k, T.best_fit_scale(ctx, k, TODAY), TODAY, "en")
            assert out[k]["tone"] == full["tone"], (ctx.chart_id, k)


def _tag_class(lang, tag):
    """care | open | calm — which family a served tag belongs to, in `lang`."""
    t = T.C.TAG[lang]
    def is_(name):
        pat = t[name]
        if "{mon}" in pat:
            pre, post = pat.split("{mon}")
            return tag.startswith(pre) and tag.endswith(post)
        return tag == pat
    if any(is_(n) for n in ("care", "care_from", "steady_care")):
        return "care"
    if any(is_(n) for n in ("active", "open", "steady_open")):
        return "open"
    return "calm"


_DATES3 = [TODAY, date(2027, 1, 15), date(2027, 6, 2)]


@pytest.mark.parametrize("lang", ["en", "es", "pt", "hinglish"])
def test_tag_never_contradicts_tone_and_tone_is_the_best_fit_read(ctxs, lang):
    """4 charts x 7 topics x 3 dates: the words and the colour come from the same read."""
    for ctx in ctxs:
        for d in _DATES3:
            for r in T.rank_topics(ctx, d, lang):
                cls = _tag_class(lang, r["tag"])
                if r["tone"] == "open":
                    assert cls != "care", (ctx.chart_id, d, r)
                if r["tone"] == "care":
                    assert cls != "open", (ctx.chart_id, d, r)
                if r["tone"] != "care":
                    assert not r["tag"].startswith(T.C.TAG[lang]["care"]), (ctx.chart_id, d, r)
                if lang == "en":
                    full = T.read_topic(ctx, r["key"], T.best_fit_scale(ctx, r["key"], d), d, "en")
                    assert r["tone"] == full["tone"], (ctx.chart_id, d, r["key"])


def test_the_maya_money_case_active_open_never_says_needs_care():
    """Regression: status active + tone open used to carry 'needs care now'."""
    ctx = _synth("Jupiter", [_ev("2026-10-12", "Jupiter", 2)])
    for r in T.rank_topics(ctx, TODAY, "en"):
        assert not (r["tone"] == "open" and "care" in r["tag"]), r
        assert not (r["tone"] == "care" and r["tag"] == "active now"), r


def test_tags_follow_tone_for_each_status(monkeypatch):
    now = {k: {"score": 0.0, "lit": False, "mode": "steady"} for k in T.TOPIC_KEYS}
    now["money"] = {"score": 5.0, "lit": True, "mode": "care"}   # old logic: care tag
    now["love"] = {"score": 4.5, "lit": True, "mode": "open"}    # old logic: active tag
    monkeypatch.setattr(T, "_now_assessments", lambda c, t: now)
    monkeypatch.setattr(T, "_next_opening", lambda c, k, t: None)
    tones = {"money": "open", "love": "care"}
    monkeypatch.setattr(T, "_tile_read", lambda c, k, t: (tones.get(k, "steady"), None))
    rows = {r["key"]: r for r in T.rank_topics(_synth(), TODAY, "en")}
    assert rows["money"]["tag"] == "active now" and rows["money"]["tone"] == "open"
    assert rows["love"]["tag"] == "needs care now" and rows["love"]["tone"] == "care"


def test_topics_tone_can_be_care_while_status_is_active():
    ctx = _synth("Saturn", [_ev("2026-10-12", "Saturn", 10, "conjunction")])
    rows = {r["key"]: r for r in T.rank_topics(ctx, TODAY, "en")}
    assert rows["career"]["status"] == "active" and rows["career"]["tone"] == "care"


def test_fallback_topics_carry_a_steady_tone():
    assert {r["tone"] for r in T.fallback_topics("en")} == {"steady"}


def _fake_now(scores):
    return {k: {"score": scores.get(k, 0.0), "lit": scores.get(k, 0.0) >= T.ACTIVE_MIN, "mode": "open"}
            for k in T.TOPIC_KEYS}


def test_active_is_capped_at_three_by_relative_strength():
    now = _fake_now({"money": 4.7, "business": 4.58, "career": 4.33, "love": 4.2, "health": 3.9})
    assert T.active_set(now) == {"money", "business", "career"}


def test_active_needs_to_be_near_the_charts_strongest():
    # 4.0 is "lit" on its own but far below 5.3 → falls to steady (relative cut)
    now = _fake_now({"business": 5.3, "career": 4.3, "love": 3.6})
    assert T.active_set(now) == {"business", "career"}


def test_a_genuinely_strong_signal_is_never_demoted_by_the_cap():
    now = _fake_now({"money": 6.5, "business": 6.0, "career": 5.8, "love": 5.6, "health": 3.6})
    assert T.active_set(now) == {"money", "business", "career", "love"}   # all >= STRONG_MIN, health cut


def test_ties_at_the_cap_break_by_fixed_topic_order():
    now = _fake_now({"money": 4.4, "career": 4.4, "love": 4.4, "health": 4.4})
    assert T.active_set(now) == {"money", "career", "love"}


def test_rank_topics_never_shows_more_than_three_active_and_demotes_to_steady(monkeypatch):
    ctx = _synth()
    monkeypatch.setattr(T, "_now_assessments", lambda c, t: {
        k: dict(T.assess(c, k, t, []), **v) for k, v in _fake_now(
            {"money": 4.7, "business": 4.58, "career": 4.33, "love": 4.2, "health": 3.9}).items()})
    out = {r["key"]: r["status"] for r in T.rank_topics(ctx, TODAY, "en")}
    assert sorted(k for k, v in out.items() if v == "active") == ["business", "career", "money"]
    assert out["love"] == "steady" and out["health"] == "steady"


def test_a_chart_where_only_one_topic_is_lit_shows_exactly_one_active():
    ctx = _synth("Mars", [_ev("2026-10-12", "Jupiter", 1)])   # Aries: Mars rules the 1st/6th → health only
    rows = {r["key"]: r["status"] for r in T.rank_topics(ctx, TODAY, "en")}
    assert [k for k, v in rows.items() if v == "active"] == ["health"]


def test_real_charts_stay_within_the_cap(ctxs):
    from datetime import date as _d
    for ctx in ctxs:
        for on in (TODAY, _d(2027, 1, 15), _d(2027, 8, 10)):
            out = T.rank_topics(ctx, on, "en")
            n = sum(r["status"] == "active" for r in out)
            now = T._now_assessments(ctx, on)
            strong = sum(now[k]["lit"] and now[k]["score"] >= T.STRONG_MIN for k in now)
            assert n <= max(T.ACTIVE_CAP, strong)


def test_rank_is_deterministic(ctxs):
    assert T.rank_topics(ctxs[1], TODAY, "en") == T.rank_topics(ctxs[1], TODAY, "en")


def test_fallback_is_all_steady_in_fixed_order(monkeypatch, ctxs):
    monkeypatch.setattr(T, "_now_assessments", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    out = T.rank_topics(ctxs[0], TODAY, "es")
    assert [r["key"] for r in out] == list(C.TOPIC_KEYS)
    assert {r["status"] for r in out} == {"steady"}
    assert [r["rank"] for r in out] == list(range(1, 8))
    assert out[0]["label"] == "Dinero"


def test_neutral_topics_are_never_padded_into_activity():
    out = T.rank_topics(_synth(), TODAY, "en")   # no chapter, no movement
    assert {r["status"] for r in out} == {"quiet"}


def test_active_topic_needs_real_activation():
    ctx = _synth("Saturn", [_ev("2026-10-12", "Jupiter", 10)])  # chapter + a supportive aspect on the 10th
    out = {r["key"]: r for r in T.rank_topics(ctx, TODAY, "en")}
    assert out["career"]["status"] == "active" and out["career"]["tag"] == "active now"
    assert T.rank_topics(ctx, TODAY, "en")[0]["key"] == "career"


# ── watch only when real ────────────────────────────────────────────────────
def test_structural_lean_alone_never_makes_a_watch_window():
    ctx = _synth("Saturn")   # a demanding chapter, but nothing dated against career
    for scale in T.SCALES:
        r = T.read_topic(ctx, "career", scale, TODAY, "en")
        assert r["watch_window"] is None, scale


def test_dated_demanding_movement_makes_a_watch_window():
    ctx = _synth("Saturn", [_ev("2026-10-20", "Saturn", 10)])
    r = T.read_topic(ctx, "career", "month", TODAY, "en")
    assert r["watch_window"] and r["watch_window"]["start"] <= "2026-10-20" <= r["watch_window"]["end"]
    assert r["best_window"] is None and r["tone"] == "care"


def test_supportive_movement_makes_best_window_and_no_watch():
    ctx = _synth("Saturn", [_ev("2026-10-20", "Jupiter", 10)])
    r = T.read_topic(ctx, "career", "month", TODAY, "en")
    assert r["best_window"] and r["watch_window"] is None and r["tone"] == "open"
    assert r["best_window"]["reasoning"]["bullets"]


# ── dating ──────────────────────────────────────────────────────────────────
def test_clamp_window_never_returns_a_past_date():
    assert T.clamp_window(date(2026, 9, 1), date(2026, 10, 2), TODAY) is None
    assert T.clamp_window(date(2026, 9, 25), date(2026, 10, 20), TODAY) == (TODAY, date(2026, 10, 20))
    assert T.clamp_window(date(2026, 10, 9), date(2026, 10, 12), TODAY) == (date(2026, 10, 9), date(2026, 10, 12))


@pytest.mark.parametrize("today", [date(2026, 10, 7), date(2026, 10, 14), date(2027, 1, 31)])
def test_no_deadline_or_window_is_ever_in_the_past(ctxs, today):
    # the old bug: on Oct 7 a 15th-anchored chart showed "Oct 15 – Nov 15" with
    # deadlines "before October 2". A rolling 30 days from today can't do that.
    for ctx in ctxs:
        for key in T.TOPIC_KEYS:
            for scale in T.SCALES:
                r = T.read_topic(ctx, key, scale, today, "en", with_best_fit=False)
                if scale == "month":
                    assert r["period"]["start"] == today.isoformat()
                    assert r["period"]["end"] == (today + timedelta(days=29)).isoformat()
                for w in (r["best_window"], r["watch_window"]):
                    if w:
                        assert w["start"] >= today.isoformat(), (key, scale, w)
                        assert w["end"] >= w["start"]
                        assert w["end"] <= r["period"]["end"], (key, scale, w, r["period"])


def test_year_is_the_solar_return_year_with_its_range():
    ctx = _real_ctx("1990-10-15", "14:10")
    r = T.read_topic(ctx, "money", "year", TODAY, "en", with_best_fit=False)
    assert (r["period"]["start"], r["period"]["end"]) == ("2025-10-15", "2026-10-14")
    assert "2025" in r["period"]["label"] and "2026" in r["period"]["label"]
    r2 = T.read_topic(ctx, "money", "year", date(2026, 10, 15), "en", with_best_fit=False)
    assert (r2["period"]["start"], r2["period"]["end"]) == ("2026-10-15", "2027-10-14")


def test_season_is_the_current_sub_period_with_its_end_date():
    ctx = _synth("Saturn")
    r = T.read_topic(ctx, "career", "season", TODAY, "en", with_best_fit=False)
    assert r["period"]["end"] == "2027-03-10" and not r["period"]["approximate"]
    assert r["period"]["label"] == "This season, to Mar 10"


def test_season_without_sub_period_is_flagged_approximate():
    r = T.read_topic(_synth(), "career", "season", TODAY, "en", with_best_fit=False)
    assert r["period"]["approximate"] is True


def test_whole_period_window_needs_two_agreeing_timelines(monkeypatch):
    ctx = _synth("Venus")   # Aries lagna: Venus rules the 2nd — a supportive money chapter
    assert T.read_topic(ctx, "money", "month", TODAY, "en")["best_window"] is None
    monkeypatch.setattr(T, "_chara_weight", lambda *a, **k: 0.9)
    w = T.read_topic(ctx, "money", "month", TODAY, "en")["best_window"]
    assert w and w["start"] == TODAY.isoformat() and w["label"] == "All of the next 30 days"
    # a demanding chapter, even if both timelines agree, is never sold as a green window
    assert T.read_topic(_synth("Saturn"), "career", "month", TODAY, "en")["best_window"] is None


# ── language ────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("raw,served", [("en", "en"), ("es", "es"), ("pt-BR", "pt"), ("hi-Latn", "hinglish"),
                                        ("hinglish", "hinglish"), ("hi", "en"), ("fr", "en"), ("xx", "en"),
                                        (None, "en"), ("", "en")])
def test_language_fallback_is_whole_english_never_mixed(raw, served):
    r = T.read_topic(_synth("Saturn", [_ev("2026-10-20", "Jupiter", 10)]), "career", "month", TODAY, raw)
    assert r["language"] == served
    if served == "en":
        assert r["label"] == "Career" and r["claim"].startswith("This month")


def test_each_language_is_actually_translated():
    ctx = _synth("Saturn", [_ev("2026-10-20", "Jupiter", 10)])
    claims = {l: T.read_topic(ctx, "career", "month", TODAY, l)["claim"] for l in LANGS}
    assert len(set(claims.values())) == 4
    assert claims["es"].startswith("Este mes") and claims["pt"].startswith("Este mês")
    assert claims["hinglish"].startswith("Is mahine")


def test_copy_tables_are_complete_for_every_language_topic_and_scale():
    for l in LANGS:
        assert set(C.LABEL[l]) == set(C.AREA[l]) == set(C.FREE_STEPS[l]) == set(C.TOPIC_KEYS)
        assert set(C.CORE[l]) == set(C.MOVE[l]) == set(C.TOPIC_KEYS)
        for k in C.TOPIC_KEYS:
            assert set(C.CORE[l][k]) == {"open", "care"}
            assert set(C.MOVE[l][k]) == {"open", "care", "steady"}
            assert len(C.FREE_STEPS[l][k]) == 2
        for tbl in (C.SPAN_LEAD, C.PERIOD_LABEL, C.WHOLE_SPAN):
            assert set(tbl[l]) == set(C.SCALES)
        assert set(C.TAG[l]) == set(C.TAG["en"])
        assert set(C.WHY_BULLET[l]) == set(C.WHY_BULLET["en"])
        assert set(C.CONFIDENCE_NOTE[l]) == {"high", "medium", "low"}
        assert len(C.MONTHS[l]) == 12


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("mode", ["open", "care"])
def test_single_day_window_never_says_between_x_and_x(lang, mode):
    ctx = _synth("Saturn", [_ev("2026-10-07", "Jupiter", 10)])
    a = dict(T.assess(ctx, "career", TODAY, ctx.events(TODAY, TODAY, False)), mode=mode, n_signals=1)
    one = T._reasoning(ctx, "career", a, "today", lang, TODAY, TODAY)["bullets"][-1]
    rng = T._reasoning(ctx, "career", a, "month", lang, TODAY, TODAY + timedelta(days=6))["bullets"][-1]
    day = C.day_label(TODAY, lang)
    assert day in one and one.count(day) == 1          # the date appears once
    assert one != rng                                  # a real range keeps its own wording
    if lang == "en":
        area = C.AREA["en"]["career"]
        assert one == (f"Slow-moving influences support {area} on Oct 7." if mode == "open"
                       else f"Slow-moving influences press on {area} on Oct 7.")
        assert "between" not in one


def test_single_day_window_end_to_end_reads_on_the_day():
    ctx = _synth("Saturn", [_ev("2026-10-07", "Jupiter", 10)])
    r = T.read_topic(ctx, "career", "today", TODAY, "en")
    w = r["best_window"] or r["watch_window"]
    assert w and w["start"] == w["end"] == "2026-10-07"
    assert all("between" not in b for b in w["reasoning"]["bullets"])
    assert any(" on Oct 7." in b for b in w["reasoning"]["bullets"])


def _both_windows_ctx():
    return _synth("Saturn", [_ev("2026-10-12", "Jupiter", 10), _ev("2026-10-13", "Venus", 10),
                             _ev("2026-10-30", "Saturn", 10), _ev("2026-11-02", "Mars", 10)])


def test_top_level_reasoning_is_the_primary_windows_and_each_window_is_distinct():
    r = T.read_topic(_both_windows_ctx(), "career", "month", TODAY, "en")
    best, watch = r["best_window"], r["watch_window"]
    assert best and watch and r["tone"] == "open"
    assert r["reasoning"] == best["reasoning"]                   # primary = the window `tone` names
    assert r["reasoning"] != watch["reasoning"]
    assert best["reasoning"] != watch["reasoning"]               # each window carries its own
    assert "support" in best["reasoning"]["bullets"][-1] and "press" in watch["reasoning"]["bullets"][-1]
    assert r["why"] == " ".join(r["reasoning"]["bullets"][:2])


def test_care_only_read_top_level_reasoning_is_the_watch_windows():
    ctx = _synth("Saturn", [_ev("2026-10-30", "Saturn", 10), _ev("2026-11-02", "Mars", 10)])
    r = T.read_topic(ctx, "career", "month", TODAY, "en")
    assert r["tone"] == "care" and r["best_window"] is None
    assert r["reasoning"] == r["watch_window"]["reasoning"]


def test_today_windows_carry_no_invented_clock_times():
    """The dated feed has no clock times and the day's best hour is topic-agnostic,
    so a today window stays date-only (the UI then draws the whole day)."""
    ctx = _synth("Saturn", [_ev("2026-10-07", "Jupiter", 10)])
    r = T.read_topic(ctx, "career", "today", TODAY, "en")
    w = r["best_window"] or r["watch_window"]
    assert w and "start_time" not in w and "end_time" not in w
    assert len(w["start"]) == len(w["end"]) == 10


def test_topic_labels_and_tags_localised():
    out = T.rank_topics(_synth("Saturn", [_ev("2026-10-12", "Jupiter", 10)]), TODAY, "pt")
    assert out[0]["label"] == "Carreira" and out[0]["tag"] == "ativo agora"


# ── no jargon, no prices, honesty wording ───────────────────────────────────
def _strings(obj, skip_mantra=True):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        if skip_mantra and obj.get("kind") == "mantra":
            return
        for k, v in obj.items():
            if k in ("key", "topic", "scale", "language", "chart_id", "start", "end", "as_of", "view",
                     "level", "tone", "kind", "status", "best_fit_scale"):
                continue
            yield from _strings(v, skip_mantra)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _strings(v, skip_mantra)


def test_no_jargon_in_any_copy_table():
    for name in dir(C):
        tbl = getattr(C, name)
        if name.isupper() and isinstance(tbl, dict) and name not in ("PLANET", "MONTHS"):
            for s in _strings(tbl, skip_mantra=False):
                if name == "MANTRA_STEP":
                    continue
                assert not _JARGON.search(s), (name, s)


def test_no_jargon_in_any_topic_read_string(ctxs):
    seen = 0
    synth = [_synth("Saturn", [_ev("2026-10-20", "Jupiter", 10), _ev("2026-11-02", "Saturn", 2),
                               _ev("2026-10-25", "Saturn", 4)]),
             _synth("Mars", [_ev("2026-10-15", "Saturn", 7)], acc="unknown"),
             _synth("Jupiter", [], acc="approximate")]
    for ctx in ctxs + synth:
        for lang in LANGS:
            for key in T.TOPIC_KEYS:
                for scale in T.SCALES:
                    r = T.read_topic(ctx, key, scale, TODAY, lang)
                    for s in _strings(r):
                        assert not _JARGON.search(s), (lang, key, scale, s)
                        seen += 1
            for row in T.rank_topics(ctx, TODAY, lang):
                for s in _strings(row):
                    assert not _JARGON.search(s), (lang, row)
    assert seen > 1000


def test_no_prices_and_no_consent_wording_in_remedies(ctxs):
    bad = re.compile(r"(\$|€|₹|£|\bprice|\bprecio|\bpre[çc]o|\bcost|\bbuy\b|\bcomprar|\bcomprar|\bconsent|"
                     r"\bsubscri|\bplan\b|\bfree trial|\d+\s?(usd|inr|eur))", re.I)
    for ctx in ctxs:
        for lang in LANGS:
            for key in T.TOPIC_KEYS:
                rem = T.build_remedy(ctx, key, TODAY, lang)
                for st in rem["steps"]:
                    assert not bad.search(st["text"]), st
                assert not bad.search(rem["summary"])


def test_remedy_free_steps_first_and_stone_only_optional_last(ctxs):
    for ctx in ctxs:
        rem = T.build_remedy(ctx, "money", TODAY, "en")
        kinds = [s["kind"] for s in rem["steps"]]
        assert kinds[0] == "practice" and kinds[1] == "practice"
        assert not rem["steps"][0]["optional"]
        if "stone" in kinds:
            assert kinds[-1] == "stone" and kinds.count("stone") == 1
            assert rem["steps"][-1]["optional"] is True
            assert "skip" in rem["steps"][-1]["text"]


def test_remedy_mantra_and_stone_are_for_the_same_planet_or_no_stone(ctxs):
    from antar_engine.practice_engine import GEM_BY_PLANET
    from antar_engine.practice_library import get_planet_content
    seen_stone = seen_dropped = 0
    for ctx in ctxs:
        gem = T._chart_gem(ctx)
        for on in (TODAY, date(2027, 6, 1), date(2029, 1, 1)):
            for k in T.TOPIC_KEYS:
                rem = T.build_remedy(ctx, k, on, "en")
                planet = T.remedy_planet(ctx, k, on, gem)
                mantra = [s for s in rem["steps"] if s["kind"] == "mantra"]
                stone = [s for s in rem["steps"] if s["kind"] == "stone"]
                assert len(mantra) == 1 and get_planet_content(planet, "en")["mantra"]["name"] in mantra[0]["text"]
                if stone:
                    seen_stone += 1
                    assert gem["_planet"] == planet and GEM_BY_PLANET[planet]["stone"] in stone[0]["text"]
                    assert rem["steps"][-1]["kind"] == "stone"
                else:
                    seen_dropped += 1
                    assert not gem or gem["_planet"] != planet
    assert seen_stone and seen_dropped      # both branches are exercised by the fixtures


def test_mismatched_stone_is_dropped_not_shown(monkeypatch):
    # Jupiter runs (a money key planet) but the chart's stone is Emerald (Mercury)
    ctx = _synth("Jupiter")
    monkeypatch.setattr(T, "_chart_gem", lambda c: {"stone": "Emerald", "_planet": "Mercury"})
    kinds = [s["kind"] for s in T.build_remedy(ctx, "money", TODAY, "en")["steps"]]
    assert kinds == ["practice", "practice", "mantra"]


def test_remedy_prefers_the_charts_stone_planet_when_it_is_also_running(monkeypatch):
    ctx = _synth("Jupiter")
    ctx.dashas["vimsottari"].append(dict(ctx.dashas["vimsottari"][-1], lord_or_sign="Mercury",
                                         planet_or_sign="Mercury", level="pratyantardasha"))
    monkeypatch.setattr(T, "_vim_active_planets", lambda d, on: {"Jupiter", "Mercury"})
    monkeypatch.setattr(T, "_chart_gem", lambda c: {"stone": "Emerald", "_planet": "Mercury"})
    rem = T.build_remedy(ctx, "money", TODAY, "en")["steps"]
    assert [s["kind"] for s in rem] == ["practice", "practice", "mantra", "stone"]
    assert "Emerald" in rem[-1]["text"]


def test_money_business_health_never_promise_outcomes():
    promise = re.compile(r"(rich|wealth|fortune|millionaire|guarantee|will succeed|diagnos|cure|disease|"
                         r"rico|riqueza|garant|enferm|diagn|doen)", re.I)
    for l in LANGS:
        for k in ("money", "business", "health"):
            for s in list(C.CORE[l][k].values()) + list(C.MOVE[l][k].values()) + list(C.FREE_STEPS[l][k]):
                assert not promise.search(s), (l, k, s)


def test_reasoning_object_shape(ctxs):
    r = T.read_topic(_synth("Saturn", [_ev("2026-10-20", "Jupiter", 10)]), "career", "month", TODAY, "en")
    for rs in (r["reasoning"], r["best_window"]["reasoning"]):
        assert isinstance(rs["bullets"], list) and rs["bullets"]
        assert rs["based_on"] and all(b["view"] in ("today", "month", "year", "chapter") and b["label"]
                                      for b in rs["based_on"])
        assert rs["confidence"]["level"] in ("high", "medium", "low") and rs["confidence"]["note"]
    assert r["confidence_note"] == r["reasoning"]["confidence"]["note"]
    assert r["best_fit_scale"] in T.SCALES


def test_unknown_birth_time_lowers_confidence():
    ev = [_ev("2026-10-20", "Jupiter", 10)]
    known = T.read_topic(_synth("Saturn", ev), "career", "month", TODAY, "en")
    unk = T.read_topic(_synth("Saturn", ev, acc="unknown"), "career", "month", TODAY, "en")
    assert unk["reasoning"]["confidence"]["level"] == "low"
    assert any("birth time" in b for b in unk["reasoning"]["bullets"])
    assert known["reasoning"]["confidence"]["level"] in ("medium", "high", "low")


def test_engine_failure_in_read_degrades_to_steady_read(monkeypatch):
    monkeypatch.setattr(T, "assess", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")))
    r = T.read_topic(_synth("Saturn"), "love", "month", TODAY, "en")
    assert r["best_window"] is None and r["watch_window"] is None and r["tone"] == "steady"
    assert r["claim"] and r["your_move"] and r["remedy"]["steps"]


# ── routes ──────────────────────────────────────────────────────────────────
@pytest.fixture
def main_mod(monkeypatch):
    import main
    T.cache_clear()
    return main


def _run(coro):
    return asyncio.run(coro)


def test_topics_route_returns_list_and_caches(main_mod, monkeypatch):
    ctx = _synth("Saturn", [_ev("2026-10-12", "Jupiter", 10)])
    calls = []
    monkeypatch.setattr(main_mod, "_topic_ctx_load", lambda cid: (calls.append(cid) or (ctx, {"language": "es"})))
    monkeypatch.setattr(main_mod, "_prac_local_date", lambda tz: TODAY)
    a = _run(main_mod.get_chart_topics("c1", None, None))
    b = _run(main_mod.get_chart_topics("c1", None, None))
    assert a == b and a[0]["key"] == "career" and a[0]["label"] == "Carrera"   # chart's stored language wins over a missing param
    assert len(calls) == 2    # context is rebuilt, the ranking itself is cached
    assert all(set(r) == {"key", "label", "status", "tag", "tone", "rank"} for r in a)


def test_topics_route_falls_back_on_load_failure(main_mod, monkeypatch):
    def boom(cid): raise RuntimeError("db down")
    monkeypatch.setattr(main_mod, "_topic_ctx_load", boom)
    out = _run(main_mod.get_chart_topics("c1", "en", None))
    assert [r["key"] for r in out] == list(C.TOPIC_KEYS) and {r["status"] for r in out} == {"steady"}


def test_topics_route_404_for_unknown_chart(main_mod, monkeypatch):
    monkeypatch.setattr(main_mod, "_topic_ctx_load", lambda cid: (None, None))
    with pytest.raises(HTTPException) as e:
        _run(main_mod.get_chart_topics("nope", "en", None))
    assert e.value.status_code == 404


def test_topic_read_route_validates_and_returns(main_mod, monkeypatch):
    ctx = _synth("Saturn", [_ev("2026-10-20", "Jupiter", 10)])
    monkeypatch.setattr(main_mod, "_topic_ctx_load", lambda cid: (ctx, {}))
    monkeypatch.setattr(main_mod, "_prac_local_date", lambda tz: TODAY)
    out = _run(main_mod.get_chart_topic_read("c1", "Career", "MONTH", "en", None))
    assert out["topic"] == "career" and out["scale"] == "month" and out["best_window"]
    for bad in (("legal", "month"), ("career", "decade")):
        with pytest.raises(HTTPException) as e:
            _run(main_mod.get_chart_topic_read("c1", bad[0], bad[1], "en", None))
        assert e.value.status_code == 422


# ── reveal lines ────────────────────────────────────────────────────────────
_SYSTEM_WORDS = re.compile(r"\b(dasha|dasa|mahadasha|antardasha|jaimini|vimsottari|vimshottari|chara|"
                           r"malefic|benefic|transit|karaka|lagna|nakshatra|houses?)\b", re.I)


def _reveal_dashas():
    return {
        "vimsottari": [{"lord_or_sign": "Jupiter", "level": "mahadasha", "start_date": "2024-03-10",
                        "end_date": "2028-08-20"},
                       {"lord_or_sign": "Saturn", "level": "mahadasha", "start_date": "2028-08-20",
                        "end_date": "2047-08-20"}],
        "jaimini": [{"lord_or_sign": "Capricorn", "level": "mahadasha", "start_date": "2026-01-05",
                     "end_date": "2027-11-20"}],
    }


def test_reveal_two_lines_with_real_dates(monkeypatch):
    monkeypatch.setenv("REVEAL_LINES_PLANET_NAMES", "1")
    from antar_engine.reveal_lines import reveal_lines
    cd = {"lagna": {"sign": "Aries", "sign_index": 0}}     # Capricorn = 10th from Aries → work
    out = reveal_lines(cd, _reveal_dashas(), "1990-10-15", "exact", TODAY, "en")
    assert out == ["Since March 2024 you are in a Jupiter chapter. It runs until August 2028.",
                   "A work-focused stretch, from January 2026 to November 2027."]


def test_reveal_default_uses_the_plain_energy_phrase_not_the_planet(monkeypatch):
    from antar_engine.reveal_lines import reveal_lines
    monkeypatch.delenv("REVEAL_LINES_PLANET_NAMES", raising=False)
    cd = {"lagna": {"sign": "Aries", "sign_index": 0}}
    d = {"vimsottari": [{"lord_or_sign": "Saturn", "level": "mahadasha", "start_date": "2008-03-10",
                         "end_date": "2027-03-20"}]}
    assert reveal_lines(cd, d, "1991-03-14", "exact", TODAY, "en") == [
        "Since March 2008 you are in a discipline-and-time chapter. It runs until March 2027."]
    assert reveal_lines(cd, d, "1991-03-14", "exact", TODAY, "es") == [
        "Desde marzo de 2008 estás en una etapa de disciplina y tiempo. Dura hasta marzo de 2027."]
    assert reveal_lines(cd, d, "1991-03-14", "exact", TODAY, "pt") == [
        "Desde março de 2008 você está em uma fase de disciplina e tempo. Ela vai até março de 2027."]
    assert reveal_lines(cd, d, "1991-03-14", "exact", TODAY, "hinglish") == [
        "March 2008 se aap discipline-and-time ke daur mein hain. Ye March 2027 tak chalega."]
    # Hindi falls back to the whole English read
    assert reveal_lines(cd, d, "1991-03-14", "exact", TODAY, "hi") == reveal_lines(cd, d, "1991-03-14", "exact", TODAY, "en")
    for lang in LANGS:
        for line in reveal_lines(cd, d, "1991-03-14", "exact", TODAY, lang):
            assert not _JARGON.search(line), line


@pytest.mark.parametrize("planet,phrase", [
    ("Sun", "identity-and-purpose"), ("Moon", "emotion-and-instinct"), ("Mars", "drive-and-courage"),
    ("Mercury", "mind-and-communication"), ("Jupiter", "growth-and-wisdom"), ("Venus", "love-and-value"),
    ("Saturn", "discipline-and-time"), ("Rahu", "ambition-and-the-unfamiliar"),
    ("Ketu", "detachment-and-the-past")])
def test_reveal_every_planet_has_a_plain_phrase_matching_the_identity_table(monkeypatch, planet, phrase):
    from antar_engine.reveal_lines import reveal_lines
    from antar_engine.chart_identity import _PLANET_PLAIN
    monkeypatch.delenv("REVEAL_LINES_PLANET_NAMES", raising=False)
    d = {"vimsottari": [{"lord_or_sign": planet, "level": "mahadasha", "start_date": "2008-03-10",
                         "end_date": "2027-03-20"}]}
    out = reveal_lines({"lagna": {"sign": "Aries"}}, d, "1991-03-14", "exact", TODAY, "en")
    assert phrase in out[0] and phrase.replace("-", " ") == _PLANET_PLAIN[planet]


def test_reveal_planet_names_switch_keeps_the_name_in_every_language(monkeypatch):
    from antar_engine.reveal_lines import reveal_lines
    monkeypatch.setenv("REVEAL_LINES_PLANET_NAMES", "true")
    d = {"vimsottari": [{"lord_or_sign": "Saturn", "level": "mahadasha", "start_date": "2008-03-10",
                         "end_date": "2027-03-20"}]}
    cd = {"lagna": {"sign": "Aries"}}
    assert reveal_lines(cd, d, "1991-03-14", "exact", TODAY, "en") == [
        "Since March 2008 you are in a Saturn chapter. It runs until March 2027."]
    assert "Saturno" in reveal_lines(cd, d, "1991-03-14", "exact", TODAY, "es")[0]
    assert "Saturno" in reveal_lines(cd, d, "1991-03-14", "exact", TODAY, "pt")[0]
    assert "Saturn" in reveal_lines(cd, d, "1991-03-14", "exact", TODAY, "hinglish")[0]


def test_reveal_skips_line_two_without_birth_time_and_never_fills(monkeypatch):
    monkeypatch.setenv("REVEAL_LINES_PLANET_NAMES", "1")
    from antar_engine.reveal_lines import reveal_lines
    cd = {"lagna": {"sign": "Aries", "sign_index": 0}}
    out = reveal_lines(cd, _reveal_dashas(), "1990-10-15", "unknown", TODAY, "en")
    assert len(out) == 1 and "Jupiter" in out[0]
    assert reveal_lines(cd, {}, "1990-10-15", "exact", TODAY, "en") == []
    only_j = {"jaimini": _reveal_dashas()["jaimini"]}
    assert len(reveal_lines(cd, only_j, "1990-10-15", "exact", TODAY, "en")) == 1


def test_reveal_first_chapter_does_not_claim_a_start_at_birth(monkeypatch):
    monkeypatch.setenv("REVEAL_LINES_PLANET_NAMES", "1")
    from antar_engine.reveal_lines import reveal_lines
    d = {"vimsottari": [{"lord_or_sign": "Venus", "level": "mahadasha", "start_date": "1990-10-15",
                         "end_date": "2027-02-01"}]}
    out = reveal_lines({"lagna": {"sign": "Aries"}}, d, "1990-10-15", "exact", date(1995, 1, 1), "en")
    assert out == ["You are in a Venus chapter. It runs until February 2027."]


def test_reveal_never_shows_an_ended_chapter_and_has_no_system_words(monkeypatch):
    monkeypatch.setenv("REVEAL_LINES_PLANET_NAMES", "1")
    from antar_engine.reveal_lines import reveal_lines
    cd = {"lagna": {"sign": "Aries", "sign_index": 0}}
    assert reveal_lines(cd, _reveal_dashas(), "1990-10-15", "exact", date(2030, 1, 1), "en")[0:1] != []
    stale = {"vimsottari": [{"lord_or_sign": "Jupiter", "level": "mahadasha",
                             "start_date": "2010-01-01", "end_date": "2020-01-01"}]}
    assert reveal_lines(cd, stale, "1990-10-15", "exact", TODAY, "en") == []
    for lang in LANGS:
        for line in reveal_lines(cd, _reveal_dashas(), "1990-10-15", "exact", TODAY, lang):
            assert not _SYSTEM_WORDS.search(line), line
    es = reveal_lines(cd, _reveal_dashas(), "1990-10-15", "exact", TODAY, "es")
    assert "Júpiter" in es[0] and "agosto de 2028" in es[0] and "centrado en el trabajo" in es[1]
    assert reveal_lines(cd, _reveal_dashas(), "1990-10-15", "exact", TODAY, "hi") == \
        reveal_lines(cd, _reveal_dashas(), "1990-10-15", "exact", TODAY, "en")


def test_reveal_route_empty_on_failure_and_404_unknown(main_mod, monkeypatch):
    def boom(cid): raise RuntimeError("down")
    monkeypatch.setattr(main_mod, "_topic_ctx_load", boom)
    assert _run(main_mod.get_chart_reveal_lines("c1", "en", None)) == {"lines": []}
    monkeypatch.setattr(main_mod, "_topic_ctx_load", lambda cid: (None, None))
    with pytest.raises(HTTPException) as e:
        _run(main_mod.get_chart_reveal_lines("c1", "en", None))
    assert e.value.status_code == 404


# ── tile status/tag come from the read the tile opens ────────────────────────
def _fast_ctx(slow, fast):
    """Aries lagna, Jupiter chapter. `fast` events only reach the 'today' scan
    (include_fast=True); `slow` events are the multi-week feed."""
    ctx = _synth("Jupiter", [])
    ctx.events = lambda s, e, fast_on, _s=list(slow), _f=list(fast): [
        x for x in (_s + (_f if fast_on else [])) if s.isoformat() <= x["date"] <= e.isoformat()]
    return ctx


def _burst(day):
    return [_ev(day, "Jupiter", 2), _ev(day, "Venus", 2), _ev(day, "Mercury", 11), _ev(day, "Jupiter", 11)]


def _january():
    return [_ev(d, p, h) for d in ("2027-01-08", "2027-01-20", "2027-02-10")
            for p, h in (("Jupiter", 2), ("Venus", 11), ("Mercury", 2), ("Jupiter", 11))]


def _primary(read):
    return read["best_window"] if read["tone"] == "open" else read["watch_window"] if read["tone"] == "care" else None


def test_the_observed_money_case_is_not_upcoming_when_today_is_already_open():
    """2026-10-07: tile said 'window opens Jan' while its own read said today is a good stretch."""
    ctx = _fast_ctx(_january(), _burst("2026-10-07"))
    read = T.read_topic(ctx, "money", T.best_fit_scale(ctx, "money", TODAY), TODAY, "en")
    assert read["tone"] == "open" and _primary(read)["start"] == "2026-10-07"
    money = {r["key"]: r for r in T.rank_topics(ctx, TODAY, "en")}["money"]
    assert (money["status"], money["tag"], money["tone"]) == ("steady", "open this week", "open")


def _stub(monkeypatch, reads, opening=None):
    now = {k: {"score": 0.0, "lit": False, "mode": "steady"} for k in T.TOPIC_KEYS}
    monkeypatch.setattr(T, "_now_assessments", lambda c, t: now)
    monkeypatch.setattr(T, "_next_opening", lambda c, k, t: opening)
    monkeypatch.setattr(T, "_tile_read", lambda c, k, t: reads.get(k, ("steady", None)))


def test_upcoming_names_the_month_of_the_reads_own_window(monkeypatch):
    win = {"start": "2027-01-05", "end": "2027-06-03"}
    _stub(monkeypatch, {"money": ("open", {"best_window": win, "watch_window": None})},
          opening=(date(2026, 11, 20), "open"))
    row = {r["key"]: r for r in T.rank_topics(_synth(), TODAY, "en")}["money"]
    assert row["status"] == "upcoming" and row["tag"] == "window opens Jan"   # not Nov, the unrelated opening


def test_a_read_without_a_window_is_never_upcoming(monkeypatch):
    _stub(monkeypatch, {"money": ("steady", {"best_window": None, "watch_window": None})},
          opening=(date(2026, 11, 20), "open"))
    row = {r["key"]: r for r in T.rank_topics(_synth(), TODAY, "en")}["money"]
    assert row["status"] != "upcoming"


def test_window_within_two_days_gets_near_term_words_then_a_month_after(monkeypatch):
    mk = lambda s: {"health": ("care", {"best_window": None, "watch_window": {"start": s, "end": "2026-10-20"}})}
    _stub(monkeypatch, mk("2026-10-09"), opening=(date(2027, 1, 5), "care"))
    row = {r["key"]: r for r in T.rank_topics(_synth(), TODAY, "en")}["health"]
    assert (row["status"], row["tag"], row["tone"]) == ("steady", "take care this week", "care")
    _stub(monkeypatch, mk("2026-10-10"), opening=(date(2027, 1, 5), "care"))
    row = {r["key"]: r for r in T.rank_topics(_synth(), TODAY, "en")}["health"]
    assert (row["status"], row["tag"]) == ("upcoming", "take care from Oct")


def test_running_windows_never_enter_active_and_keep_rank_order(monkeypatch):
    """`active` stays the 30-day set (cap + relative cut untouched); a window running
    today on any other tile is steady with near-term words."""
    w = {"start": TODAY.isoformat(), "end": TODAY.isoformat()}
    _stub(monkeypatch, {k: ("open", {"best_window": w, "watch_window": None}) for k in T.TOPIC_KEYS})
    rows = {r["key"]: r for r in T.rank_topics(_synth(), TODAY, "en")}
    assert all(r["status"] == "steady" and r["tag"] == "open this week" for r in rows.values())
    assert sorted(r["rank"] for r in rows.values()) == list(range(1, 8))


def _tag_is(lang, tag, name):
    pat = T.C.TAG[lang][name]
    if "{mon}" in pat:
        pre, post = pat.split("{mon}")
        return tag.startswith(pre) and tag.endswith(post)
    return tag == pat


@pytest.mark.parametrize("lang", ["en", "es", "pt", "hinglish"])
def test_tile_status_tag_tone_and_read_agree(ctxs, lang):
    """4 charts x 7 topics x 3 dates x 4 languages. The window a tag names exists
    in topic-read at best_fit_scale, and nothing 'upcoming' is already running."""
    care_names, open_names = ("care", "care_from", "steady_care", "care_soon"), ("active", "open", "steady_open", "open_soon")
    for ctx in ctxs:
        for d in _DATES3:
            lim = d + timedelta(days=T.NEAR_DAYS)
            for r in T.rank_topics(ctx, d, lang):
                k = r["key"]
                fit = T.best_fit_scale(ctx, k, d)
                read = T.read_topic(ctx, k, fit, d, "en")
                where = (ctx.chart_id, str(d), k, r)
                assert read["best_fit_scale"] == fit and r["tone"] == read["tone"], where
                w = _primary(read)
                if r["status"] == "upcoming":
                    assert w, where
                    s = date.fromisoformat(w["start"])
                    assert s > lim, where
                    name = "care_from" if r["tone"] == "care" else "open"
                    assert r["tag"] == T.C.TAG[lang][name].format(mon=T.C.month_name(s, lang)), where
                elif w and r["status"] != "active" and date.fromisoformat(w["start"]) <= lim:
                    assert r["status"] == "steady" and r["tone"] in ("open", "care"), where
                for name, tone in (("open_soon", "open"), ("care_soon", "care")):
                    if _tag_is(lang, r["tag"], name):
                        assert r["tone"] == tone and w and date.fromisoformat(w["start"]) <= lim, where
                if r["tone"] == "open":
                    assert not any(_tag_is(lang, r["tag"], n) for n in care_names), where
                if r["tone"] == "care":
                    assert not any(_tag_is(lang, r["tag"], n) for n in open_names), where


def test_best_fit_scale_is_the_scale_that_shows_the_window():
    """Nothing today or this month, a window in the season: the default chip is the season."""
    ctx = _fast_ctx(_january(), [])
    assert T.best_fit_scale(ctx, "money", TODAY) == "season"
    read = T.read_topic(ctx, "money", "season", TODAY, "en")
    assert read["best_window"]["start"].startswith("2027-01") and read["best_fit_scale"] == "season"
    row = {r["key"]: r for r in T.rank_topics(ctx, TODAY, "en")}["money"]
    assert (row["status"], row["tag"]) == ("upcoming", "window opens Jan")


def test_near_term_copy_exists_in_every_language_and_hindi_falls_back():
    for lang in LANGS:
        assert T.C.TAG[lang]["open_soon"] and T.C.TAG[lang]["care_soon"]
    assert T.C.serve_language("hi") == "en"
