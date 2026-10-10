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
        assert set(out[0]) == {"key", "label", "status", "tag", "tag_kind", "tone", "rank", "window_start", "window_end", "headline", "verdict", "ends_today"}
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


KINDS = ("open_now", "opens", "care_now", "care_from", "quiet")


def _tag_class(lang, tag, kind=None):
    """care | open | calm — the family of a served tag, from its tag_kind."""
    return {"open_now": "open", "opens": "open", "care_now": "care", "care_from": "care"}.get(kind, "calm")


_DATES3 = [TODAY, date(2027, 1, 15), date(2027, 6, 2)]


@pytest.mark.parametrize("lang", ["en", "es", "pt", "hinglish"])
def test_tag_never_contradicts_tone_and_tone_is_the_best_fit_read(ctxs, lang):
    """4 charts x 7 topics x 3 dates: one plain kind per tile, and tone is the best-fit read's."""
    for ctx in ctxs:
        for d in _DATES3:
            for r in T.rank_topics(ctx, d, lang):
                assert r["tag_kind"] in KINDS, (ctx.chart_id, d, r)
                if r["tone"] == "steady":
                    assert r["tag_kind"] == "quiet" or r["status"] == "active", (ctx.chart_id, d, r)
                if lang == "en":
                    full = T.read_topic(ctx, r["key"], T.best_fit_scale(ctx, r["key"], d), d, "en")
                    assert r["tone"] == full["tone"], (ctx.chart_id, d, r["key"])


def test_the_maya_money_case_active_open_never_says_needs_care():
    """Regression: status active + tone open used to carry 'needs care now'."""
    ctx = _synth("Jupiter", [_ev("2026-10-12", "Jupiter", 2)])
    for r in T.rank_topics(ctx, TODAY, "en"):
        assert not (r["tone"] == "open" and r["tag_kind"] in ("care_now", "care_from")), r
        assert not (r["tone"] == "care" and r["tag"] == "Open now"), r


def test_tags_follow_tone_for_each_status(monkeypatch):
    now = {k: {"score": 0.0, "lit": False, "mode": "steady"} for k in T.TOPIC_KEYS}
    now["money"] = {"score": 5.0, "lit": True, "mode": "care"}   # old logic: care tag
    now["love"] = {"score": 4.5, "lit": True, "mode": "open"}    # old logic: active tag
    monkeypatch.setattr(T, "_now_assessments", lambda c, t: now)
    monkeypatch.setattr(T, "_next_opening", lambda c, k, t: None)
    tones = {"money": "open", "love": "care"}
    monkeypatch.setattr(T, "_tile_read", lambda c, k, t: (tones.get(k, "steady"), None))
    rows = {r["key"]: r for r in T.rank_topics(_synth(), TODAY, "en")}
    assert rows["money"]["tag"] == "Open now" and rows["money"]["tone"] == "open"
    assert rows["love"]["tag"] == "Care now" and rows["love"]["tone"] == "care"


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
    assert out["career"]["status"] == "active" and out["career"]["tag"] == "Open now, until Oct 13"
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
    assert r["period"]["label"] == "Your year · birthday to birthday"
    assert r["period"]["chip"] == "10/15/25 – 10/15/26"
    r2 = T.read_topic(ctx, "money", "year", date(2026, 10, 15), "en", with_best_fit=False)
    assert (r2["period"]["start"], r2["period"]["end"]) == ("2026-10-15", "2027-10-14")


def test_season_is_the_current_sub_period_with_its_end_date():
    ctx = _synth("Saturn")
    r = T.read_topic(ctx, "career", "season", TODAY, "en", with_best_fit=False)
    assert r["period"]["end"] == "2027-03-10" and not r["period"]["approximate"]
    # 5 months out -> a plain length, no end date, never the word "season"
    assert r["period"]["span_label"] == "The next 5 months"
    assert r["period"]["label"] == "Your current life chapter · to Mar 2027"
    assert r["period"]["span"] == {"months": 5, "bucket": "months"}
    assert r["claim"].startswith("Over the next 5 months, ")


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
        assert r["label"] == "Career" and r["claim"].startswith("Over the next 30 days")


def test_each_language_is_actually_translated():
    ctx = _synth("Saturn", [_ev("2026-10-20", "Jupiter", 10)])
    claims = {l: T.read_topic(ctx, "career", "month", TODAY, l)["claim"] for l in LANGS}
    assert len(set(claims.values())) == 4
    assert claims["es"].startswith("Durante los próximos 30 días") and claims["pt"].startswith("Nos próximos 30 dias")
    assert claims["hinglish"].startswith("Agle 30 din mein")


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
    assert out[0]["label"] == "Carreira" and out[0]["tag"] == "Aberto agora, até 13 out"


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
        assert rs["based_on"] and all(b["view"] in ("today", "month", "year", "chapter", "second", "dated") and b["label"]
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
    assert all(set(r) == {"key", "label", "status", "tag", "tag_kind", "tone", "rank", "window_start", "window_end", "headline", "verdict", "ends_today"} for r in a)


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
    assert money["status"] == "active" and money["tag"].startswith("Open now") and money["tag_kind"] == "open_now" and money["tone"] == "open"


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
    assert row["status"] == "upcoming" and row["tag"] == "Opens Jan 2027"   # not Nov, the unrelated opening; month-level beyond 45 days


def test_a_read_without_a_window_is_never_upcoming(monkeypatch):
    _stub(monkeypatch, {"money": ("steady", {"best_window": None, "watch_window": None})},
          opening=(date(2026, 11, 20), "open"))
    row = {r["key"]: r for r in T.rank_topics(_synth(), TODAY, "en")}["money"]
    assert row["status"] != "upcoming"


def test_window_within_two_days_gets_near_term_words_then_a_month_after(monkeypatch):
    mk = lambda s: {"health": ("care", {"best_window": None, "watch_window": {"start": s, "end": "2026-10-20"}})}
    _stub(monkeypatch, mk("2026-10-09"), opening=(date(2027, 1, 5), "care"))
    row = {r["key"]: r for r in T.rank_topics(_synth(), TODAY, "en")}["health"]
    assert (row["status"], row["tag"], row["tone"]) == ("steady", "Care from Oct 9", "care")
    _stub(monkeypatch, mk("2026-10-10"), opening=(date(2027, 1, 5), "care"))
    row = {r["key"]: r for r in T.rank_topics(_synth(), TODAY, "en")}["health"]
    assert (row["status"], row["tag"]) == ("upcoming", "Care from Oct 10")


def test_promoted_running_windows_obey_the_active_cap_and_relative_cut(monkeypatch):
    w = {"start": TODAY.isoformat(), "end": TODAY.isoformat()}
    _stub(monkeypatch, {k: ("open", {"best_window": w, "watch_window": None}) for k in T.TOPIC_KEYS})
    monkeypatch.setattr(T, "_near_score", lambda c, k, t, s: {"money": 6.0, "career": 5.0, "love": 4.6,
                                                              "health": 4.4, "business": 3.6}.get(k, 3.5))
    rows = {r["key"]: r for r in T.rank_topics(_synth(), TODAY, "en")}
    active = [k for k, r in rows.items() if r["status"] == "active"]
    assert 1 <= len(active) <= T.ACTIVE_CAP and rows["money"]["status"] == "active"
    assert all(rows[k]["tag"] == "Open now, until Oct 7" and rows[k]["status"] == "steady"
               for k in rows if k not in active)
    order = [r["status"] for r in sorted(rows.values(), key=lambda r: r["rank"])]
    assert order == sorted(order, key=["active", "upcoming", "steady", "quiet"].index)


@pytest.mark.parametrize("lang", ["en", "es", "pt", "hinglish"])
def test_tile_status_tag_tone_and_read_agree(ctxs, lang):
    """4 charts x 7 topics x 3 dates x 4 languages. The window a tag names exists in
    topic-read at best_fit_scale: Open now = a window running today, Opens/Care from = start date."""
    for ctx in ctxs:
        for d in _DATES3:
            for r in T.rank_topics(ctx, d, lang):
                k = r["key"]
                fit = T.best_fit_scale(ctx, k, d)
                read = T.read_topic(ctx, k, fit, d, "en")
                where = (ctx.chart_id, str(d), k, r)
                assert read["best_fit_scale"] == fit and r["tone"] == read["tone"], where
                wins = {"open": read["best_window"], "care": read["watch_window"]}
                kind = r["tag_kind"]
                if kind == "open_now" and wins["open"]:
                    assert wins["open"]["start"] <= d.isoformat() <= wins["open"]["end"], where
                if kind == "opens":
                    w = wins["open"]
                    assert w and date.fromisoformat(w["start"]) > d, where
                    s0 = date.fromisoformat(w["start"])
                    key = "opens_far" if s0 > C.add_months(d, 11) else "opens"
                    assert r["tag"] == T.C.TAG[lang][key].format(d=C.day_label(s0, lang), my=C.month_year_short(s0, lang)), where
                if kind == "care_from":
                    w = wins["care"]
                    assert w and date.fromisoformat(w["start"]) > d, where
                if kind == "care_now" and wins["care"]:
                    assert wins["care"]["start"] <= d.isoformat() <= wins["care"]["end"], where
                if r["status"] == "upcoming":
                    assert kind in ("opens", "care_from"), where


def test_best_fit_scale_is_the_scale_that_shows_the_window():
    """Nothing today or this month, a window in the season: the default chip is the season."""
    ctx = _fast_ctx(_january(), [])
    assert T.best_fit_scale(ctx, "money", TODAY) == "season"
    read = T.read_topic(ctx, "money", "season", TODAY, "en")
    assert read["best_window"]["start"].startswith("2027-01") and read["best_fit_scale"] == "season"
    row = {r["key"]: r for r in T.rank_topics(ctx, TODAY, "en")}["money"]
    assert (row["status"], row["tag_kind"]) == ("upcoming", "opens") and row["tag"].startswith("Opens Jan")


def test_tag_copy_complete_in_every_language_and_hindi_falls_back():
    for lang in LANGS:
        assert set(C.TAG[lang]) == set(C.TAG["en"])
    assert T.C.serve_language("hi") == "en"


# ── far windows and far period labels (observed 2026-10-07, owner's chart) ───
def _season_ctx(end):
    ctx = _synth("Saturn")
    ctx.dashas["vimsottari"][1].update({"end_date": end, "end": end, "start_date": "2026-08-13", "start": "2026-08-13"})
    return ctx


_SEASON_FAR = {"en": "The next 2½ years · to Apr 2029", "es": "Los próximos 2½ años · hasta abr 2029",
               "pt": "Os próximos 2½ anos · até abr 2029", "hinglish": "Agle 2½ saal · Apr 2029 tak"}


@pytest.mark.parametrize("lang", LANGS)
def test_observed_season_label_carries_the_year_when_it_runs_to_2029(lang):
    r = T.read_topic(_season_ctx("2029-04-25"), "career", "season", TODAY, lang, with_best_fit=False)
    assert r["period"]["end"] == "2029-04-25" and r["period"]["span_label"] == _SEASON_FAR[lang]


def test_hindi_season_label_falls_back_to_english_with_the_year():
    r = T.read_topic(_season_ctx("2029-04-25"), "career", "season", TODAY, "hi", with_best_fit=False)
    assert r["period"]["span_label"] == "The next 2½ years · to Apr 2029"


@pytest.mark.parametrize("end,label", [
    ("2026-12-05", "The next year"),        # 11 months, same year: short
    ("2026-12-31", "The next year · to Dec 2026"),     # > 11 months out: year
    ("2027-01-05", "The next year · to Jan 2027"),     # 12 months
    ("2027-02-05", "The next year · to Feb 2027"),     # 13 months
])
def test_season_label_boundary_at_11_12_13_months(end, label):
    jan = date(2026, 1, 5)
    ctx = _season_ctx(end)
    ctx.dashas["vimsottari"][1]["start_date"] = ctx.dashas["vimsottari"][1]["start"] = "2025-12-01"
    assert T._period(ctx, "season", jan, "en")["span_label"] == label


def test_other_scale_labels_are_unchanged():
    ctx = _season_ctx("2029-04-25")
    assert T._period(ctx, "month", TODAY, "en")["label"] == "Next 30 days"
    assert T._period(ctx, "today", TODAY, "en")["label"] == "Today"
    assert T._period(ctx, "year", TODAY, "en")["label"].startswith("Your year · ")


def _score_stub(monkeypatch, reads, opening=None, score=3.0):
    now = {k: {"score": score, "lit": False, "mode": "steady"} for k in T.TOPIC_KEYS}
    monkeypatch.setattr(T, "_now_assessments", lambda c, t: now)
    monkeypatch.setattr(T, "_next_opening", lambda c, k, t: opening)
    monkeypatch.setattr(T, "_tile_read", lambda c, k, t: reads.get(k, ("steady", None)))


_FAR_TAGS = {
    "en": ("Opens Jun 2028", "Care from Jun 2028"),
    "es": ("Abre en jun 2028", "Con cuidado desde jun 2028"),
    "pt": ("Abre em jun 2028", "Com cuidado a partir de jun 2028"),
    "hinglish": ("Jun 2028 ko khulega", "Jun 2028 se savdhaani"),
}


@pytest.mark.parametrize("lang", LANGS)
def test_observed_business_far_window_tag_names_the_month_and_year(monkeypatch, lang):
    win = {"start": "2028-06-28", "end": "2028-08-26"}
    _score_stub(monkeypatch, {"business": ("open", {"best_window": win, "watch_window": None}),
                              "love": ("care", {"best_window": None, "watch_window": win})})
    rows = {r["key"]: r for r in T.rank_topics(_synth(), TODAY, lang)}
    assert (rows["business"]["status"], rows["business"]["tone"]) == ("steady", "open")
    assert rows["business"]["tag"] == _FAR_TAGS[lang][0]
    assert rows["love"]["tag"] == _FAR_TAGS[lang][1] and rows["love"]["tone"] == "care"


@pytest.mark.parametrize("days,far", [(30, False), (45, False), (46, True), (330, True), (400, True)])
def test_tag_names_a_day_only_within_45_days(monkeypatch, days, far):
    s = TODAY + timedelta(days=days)
    win = {"start": s.isoformat(), "end": (s + timedelta(days=40)).isoformat()}
    reads = {"business": ("open", {"best_window": win, "watch_window": None}),
             "health": ("care", {"best_window": None, "watch_window": win})}
    for opening in (None, (s, "open")):                   # steady/quiet path and upcoming path
        _score_stub(monkeypatch, reads, opening=opening)
        rows = {r["key"]: r for r in T.rank_topics(_synth(), TODAY, "en")}
        want = C.month_year_short(s, "en") if far else C.day_label(s, "en")
        assert rows["business"]["tag"] == f"Opens {want}"
        assert rows["health"]["tag"] == f"Care from {want}"


def test_tag_copy_has_no_jargon_and_no_old_words():
    old = re.compile(r"steady|go gently|take care|estable|estável|sthir|dhyaan", re.I)
    for lang in LANGS:
        for v in C.TAG[lang].values():
            assert not _JARGON.search(v) and not old.search(v), (lang, v)


def _fake_reads(monkeypatch, by_scale):
    def fake(ctx, key, scale, today, lang="en", with_best_fit=True):
        return by_scale.get(scale) or {"tone": "steady", "best_window": None, "watch_window": None}
    monkeypatch.setattr(T, "read_topic", fake)


def _open(start):
    return {"tone": "open", "best_window": {"start": start, "end": start}, "watch_window": None}


def test_best_fit_keeps_the_only_scale_that_shows_a_far_window(monkeypatch):
    _fake_reads(monkeypatch, {"season": _open("2028-06-28")})
    assert T.best_fit_scale(_synth(), "business", TODAY) == "season"


def test_best_fit_prefers_a_near_window_on_a_later_scale_over_a_far_one(monkeypatch):
    _fake_reads(monkeypatch, {"season": _open("2028-06-28"), "year": _open("2027-03-01")})
    assert T.best_fit_scale(_synth(), "business", TODAY) == "year"


def test_best_fit_nearest_scale_still_wins_when_its_window_is_near(monkeypatch):
    _fake_reads(monkeypatch, {"month": _open("2026-10-20"), "season": _open("2027-03-01")})
    assert T.best_fit_scale(_synth(), "business", TODAY) == "month"


# ── [circle] windows_for exposes EVERY run the read already finds - no new astrology ──
@pytest.mark.parametrize("scale", ["month", "season"])
def test_windows_for_contains_the_reads_best_and_watch_windows(ctxs, scale):
    for ctx in ctxs:
        for key in C.TOPIC_KEYS:
            w = T.windows_for(ctx, key, scale, TODAY)
            r = T.read_topic(ctx, key, scale, TODAY, "en", with_best_fit=False)
            for field, runs in (("best_window", w["open"]), ("watch_window", w["care"])):
                if r.get(field):
                    s, e = date.fromisoformat(r[field]["start"]), date.fromisoformat(r[field]["end"])
                    assert any(x["start"] == s and x["end"] == e for x in runs), (key, scale, field)
            for x in w["open"] + w["care"]:
                assert x["start"] >= TODAY and x["end"] >= x["start"] and x["confidence"] in ("high", "medium", "low")


def test_windows_for_never_raises_and_degrades_to_no_runs(monkeypatch):
    ctx = T.TopicContext("c", {}, {})
    monkeypatch.setattr(T, "_scan", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")))
    out = T.windows_for(ctx, "money", "month", TODAY)
    assert out["open"] == [] and out["care"] == []


# ── window phase: a window that has not opened yet must not read as "now" ───
def _later_ctx():
    return _synth("Saturn", [_ev("2026-12-01", "Jupiter", 10)])      # season window opens Nov 6


def _soon_ctx():
    return _synth("Saturn", [_ev("2026-10-20", "Jupiter", 10), _ev("2026-10-25", "Saturn", 10)])


def test_window_phase_boundaries():
    t = date(2026, 10, 8)
    assert T.window_phase(t, t, t) == "now"
    assert T.window_phase(t - timedelta(days=3), t + timedelta(days=3), t) == "now"
    assert T.window_phase(t + timedelta(days=14), t + timedelta(days=20), t) == "soon"
    assert T.window_phase(t + timedelta(days=15), t + timedelta(days=20), t) == "later"


def test_later_window_names_its_opening_date_and_prepares():
    r = T.read_topic(_later_ctx(), "career", "season", TODAY, "en")
    assert r["tone"] == "open" and r["window_phase"] == "later"
    assert r["best_window"]["window_phase"] == "later"
    assert r["claim"] == "Over the next 5 months, your best stretch for work starts Nov 6."
    assert r["your_move"] == ("Use the time before Nov 6 to get the one ask or application ready; "
                              "make it from Nov 6.")
    assert "inside the window" not in r["your_move"]


def test_soon_window_month_scale():
    r = T.read_topic(_soon_ctx(), "career", "month", TODAY, "en")
    assert r["tone"] == "open" and r["window_phase"] == "soon"
    assert r["claim"] == "Over the next 30 days, your best stretch for work starts Oct 14."
    assert r["your_move"].startswith("Use the time before Oct 14")


def test_long_read_leads_with_whichever_window_comes_first():
    r = T.read_topic(_soon_ctx(), "career", "season", TODAY, "en")   # care Oct 7 - Nov 5 (running), open Oct 14 - 20
    assert r["tone"] == "care" and r["window_phase"] == "now"
    assert r["watch_window"]["window_phase"] == "now" and r["best_window"]["start"] == "2026-10-14"
    assert r["claim"].startswith("Over the next 5 months, work asks for patience")
    # the 30-day read keeps its own rule (open wins when both exist)
    assert T.read_topic(_soon_ctx(), "career", "month", TODAY, "en")["tone"] == "open"


def test_steady_read_has_null_phase():
    r = T.read_topic(_synth(), "career", "month", TODAY, "en")
    assert r["tone"] == "steady" and r["window_phase"] is None


def test_today_scale_is_never_ahead():
    for ctx in (_soon_ctx(), _later_ctx()):
        for key in T.TOPIC_KEYS:
            r = T.read_topic(ctx, key, "today", TODAY, "en")
            assert r["window_phase"] in (None, "now"), (key, r["window_phase"])


def test_care_variant_for_a_window_that_has_not_opened():
    ctx = _synth("Saturn", [_ev("2026-12-01", "Saturn", 10), _ev("2026-12-05", "Saturn", 10)])
    r = T.read_topic(ctx, "career", "season", TODAY, "en")
    assert r["tone"] == "care" and r["window_phase"] == "later"
    assert r["watch_window"]["window_phase"] == "later"
    assert r["claim"] == "Over the next 5 months, work asks for care from Nov 6."
    assert r["your_move"].startswith("Until Nov 6, finish what is open")


def test_ahead_copy_complete_in_every_language_and_jargon_free():
    for table in (C.CORE_AHEAD, C.MOVE_AHEAD):
        for lang in LANGS:
            for key in T.TOPIC_KEYS:
                for mode in ("open", "care"):
                    s = table[lang][key][mode]
                    assert s and "{date}" in s and not _JARGON.search(s), (lang, key, mode)
    for lang in LANGS:
        assert C.BASED_ON[lang]["second"] and C.BASED_ON[lang]["dated"]


def test_ahead_reads_in_every_language_have_no_jargon(ctxs):
    for lang in LANGS:
        for ctx in (_later_ctx(), _soon_ctx()):
            for key in T.TOPIC_KEYS:
                for scale in ("month", "season", "year"):
                    r = T.read_topic(ctx, key, scale, TODAY, lang)
                    for s in _strings(r):
                        assert not _JARGON.search(s), (lang, key, scale, s)
                    if r["window_phase"] in ("soon", "later"):
                        assert r["claim"] and r["your_move"] and "{" not in r["claim"] + r["your_move"]


def test_based_on_chip_count_equals_confidence_families(ctxs):
    counts = {}
    synth = [_later_ctx(), _soon_ctx(), _synth("Saturn", [_ev("2026-10-20", "Jupiter", 10)])]
    for ctx in ctxs + synth:
        for key in T.TOPIC_KEYS:
            for scale in T.SCALES:
                r = T.read_topic(ctx, key, scale, TODAY, "en")
                for rs in [r["reasoning"]] + [w["reasoning"] for w in (r["best_window"], r["watch_window"]) if w]:
                    n = len(rs["based_on"])
                    assert 1 <= n <= 3
                    if ctx.time_quality in ("exact", None):   # no time-quality downgrade in play
                        counts.setdefault((scale, rs["confidence"]["level"]), set()).add(n)
    for (scale, lvl), ns in counts.items():
        if lvl == "high":
            assert ns == {3}, (scale, ns)
        if lvl == "medium":
            assert ns == {2}, (scale, ns)


def test_high_confidence_shows_three_chips_on_every_scale():
    ctx = _synth("Saturn")
    full = {"dasha_kind": "core", "chara_confirm": True, "n_signals": 2, "mode": "open"}
    for scale in T.SCALES:
        rs = T._reasoning(ctx, "career", full, scale, "en", TODAY, TODAY)
        assert rs["confidence"]["level"] == "high" and len(rs["based_on"]) == 3, scale
        assert [b["view"] for b in rs["based_on"]][:2] == ["chapter", "second"]
        assert all(b["label"] for b in rs["based_on"])
        two = T._reasoning(ctx, "career", dict(full, chara_confirm=False), scale, "en", TODAY, TODAY)
        assert two["confidence"]["level"] == "medium" and len(two["based_on"]) == 2
        one = T._reasoning(ctx, "career", dict(full, chara_confirm=False, n_signals=0), scale, "en", TODAY, TODAY)
        assert one["confidence"]["level"] == "low" and len(one["based_on"]) == 1


# ── the long-stretch scale is framed by its real length, never "season" ──────
_SPAN_CASES = [  # months out -> (bucket, en label, es, pt, hinglish)
    (3, "few", "The next few months", "Los próximos meses", "Os próximos meses", "Agle kuch mahine"),
    (6, "months", "The next 6 months", "Los próximos 6 meses", "Os próximos 6 meses", "Agle 6 mahine"),
    (12, "1y", "The next year · to Oct 2027", "El próximo año · hasta oct 2027",
     "O próximo ano · até out 2027", "Agla saal · Oct 2027 tak"),
    (18, "1.5y", "The next 1½ years · to Apr 2028", "Los próximos 1½ años · hasta abr 2028",
     "Os próximos 1½ anos · até abr 2028", "Agle 1½ saal · Apr 2028 tak"),
    (24, "2y", "The next 2 years · to Oct 2028", "Los próximos 2 años · hasta oct 2028",
     "Os próximos 2 anos · até out 2028", "Agle 2 saal · Oct 2028 tak"),
    (30, "2.5y", "The next 2½ years · to Apr 2029", "Los próximos 2½ años · hasta abr 2029",
     "Os próximos 2½ anos · até abr 2029", "Agle 2½ saal · Apr 2029 tak"),
    (36, "3y", "The next 3 years · to Oct 2029", "Los próximos 3 años · hasta oct 2029",
     "Os próximos 3 anos · até out 2029", "Agle 3 saal · Oct 2029 tak"),
]


def _span_ctx(months):
    end = C.add_months(TODAY, months).isoformat()
    ctx = _synth("Saturn")
    ctx.dashas["vimsottari"][1].update(start_date="2026-06-01", start="2026-06-01", end_date=end, end=end)
    return ctx


@pytest.mark.parametrize("case", _SPAN_CASES)
def test_season_label_follows_the_real_length(case):
    months, bucket, *labels = case
    for lang, want in zip(LANGS, labels):
        r = T.read_topic(_span_ctx(months), "money", "season", TODAY, lang, with_best_fit=False)
        got = r["period"]["span_label"]
        end = C.add_months(TODAY, months)
        want = want.replace("oct 20", C.month_year_short(end, lang)[:-4] + "20").replace("Oct 20", C.month_year_short(end, lang)[:-4] + "20")
        assert got == want, (lang, got)
        assert r["period"]["span"]["bucket"] == bucket
        assert "season" not in got.lower() and not _JARGON.search(got)
        assert r["period"]["end"] == C.add_months(TODAY, months).isoformat()


def test_season_lead_sentence_grammar():
    r = T.read_topic(_span_ctx(24), "money", "season", TODAY, "en", with_best_fit=False)
    assert r["claim"].startswith("Over the next 2 years, ") and "season" not in r["claim"].lower()
    r = T.read_topic(_span_ctx(24), "money", "season", TODAY, "es", with_best_fit=False)
    assert r["claim"].startswith("Durante los próximos 2 años, ")
    r = T.read_topic(_span_ctx(24), "money", "season", TODAY, "hinglish", with_best_fit=False)
    assert r["claim"].startswith("Agle 2 saal mein ")


def test_season_approximate_fallback_says_six_months():
    r = T.read_topic(_synth(), "career", "season", TODAY, "en", with_best_fit=False)
    assert r["period"]["approximate"] is True and r["period"]["span_label"] == "The next 6 months"
    assert r["period"]["span"] == {"months": 6, "bucket": "months"}
    assert r["period"]["end"] == (TODAY + timedelta(days=180)).isoformat()


def test_span_rounding_boundaries():
    assert C.span_info(TODAY, TODAY + timedelta(days=91))["bucket"] == "few"
    assert C.span_info(TODAY, TODAY + timedelta(days=125))["bucket"] == "months"
    assert C.span_info(TODAY, TODAY + timedelta(days=335))["bucket"] == "1y"
    assert C.span_info(TODAY, TODAY + timedelta(days=550))["bucket"] == "1.5y"
    assert C.span_info(TODAY, TODAY + timedelta(days=700))["bucket"] == "2y"
    assert C.span_info(TODAY, TODAY + timedelta(days=930))["bucket"] == "2.5y"
    assert C.span_info(TODAY, TODAY + timedelta(days=1100))["bucket"] == "3y"


@pytest.mark.parametrize("months,bucket", [
    (1, "few"), (3, "few"), (4, "months"), (10, "months"), (11, "1y"), (14, "1y"),
    (15, "1.5y"), (20, "1.5y"), (21, "2y"), (26, "2y"), (27, "2.5y"), (32, "2.5y"),
    (33, "3y"), (40, "3y")])
def test_span_bucket_month_boundaries(months, bucket):
    end = TODAY + timedelta(days=round(months * 30.44))
    assert C.span_info(TODAY, end) == {"months": months, "bucket": bucket}


def test_half_year_labels_exist_in_every_language():
    for tbl in (C.SPAN_TEXT, C.SPAN_LEAD_SEASON, C.WHOLE_SEASON):
        for lang in LANGS:
            assert "½" in tbl[lang]["1.5y"] and "½" in tbl[lang]["2.5y"]


# ── period.chip / period.rung (segmented control) ────────────────────────────
def _chip_ctx(birth="1990-10-15"):
    ctx = _synth("Saturn")
    ctx.birth_date = birth
    return ctx


_CHIPS = {"en": ("Right now", "Next 30 days", "Life chapter"), "es": ("Ahora", "Próximos 30 días", "Capítulo de vida"),
          "pt": ("Agora", "Próximos 30 dias", "Capítulo de vida"), "hinglish": ("Abhi", "Agle 30 din", "Life chapter")}


@pytest.mark.parametrize("lang", LANGS)
def test_chip_text_and_rung_per_scale(lang):
    ctx = _chip_ctx()
    now, m30, ch = _CHIPS[lang]
    got = {sc: T._period(ctx, sc, TODAY, lang) for sc in ("today", "month", "season", "year")}
    assert (got["today"]["chip"], got["today"]["rung"]) == (now, "now")
    assert (got["month"]["chip"], got["month"]["rung"]) == (m30, "30d")
    assert (got["season"]["chip"], got["season"]["rung"]) == (ch, "stretch")
    assert got["year"]["rung"] == "year"
    assert got["year"]["chip"] == ("10/15/25 – 10/15/26" if lang == "en" else "15/10/25 – 15/10/26")


@pytest.mark.parametrize("lang,exp", [("en", "9/8/26 – 9/8/27"), ("es", "8/9/26 – 8/9/27"),
                                      ("pt", "8/9/26 – 8/9/27"), ("hinglish", "8/9/26 – 8/9/27")])
def test_year_chip_is_the_numeric_birthday_range_in_locale_order(lang, exp):
    p = T._period(_chip_ctx("1990-09-08"), "year", TODAY, lang)
    assert p["chip"] == exp
    assert p["label"] == C.PERIOD_LABEL[lang]["year"]


def test_year_long_label_is_birthday_to_birthday():
    p = T._period(_chip_ctx(), "year", TODAY, "en")
    assert p["label"] == "Your year · birthday to birthday"
    assert (p["start"], p["end"]) == (date(2025, 10, 15), date(2026, 10, 14))


@pytest.mark.parametrize("lang", LANGS)
def test_chips_never_say_season_this_year_or_365(lang):
    for birth in ("1990-10-15", "1990-09-08"):
        for sc in ("today", "month", "season", "year"):
            p = T._period(_chip_ctx(birth), sc, TODAY, lang)
            for txt in (p["chip"], p["label"]):
                assert not re.search(r"season|this year|365|next year|este año|este ano|is saal", txt, re.I), txt


def test_period_numeric_fields_and_season_label_unchanged_by_chip():
    p = T._period(_chip_ctx(), "season", TODAY, "en")
    assert p["span_label"].startswith("The next ") and p["span"]["bucket"]
    assert p["label"] == "Your current life chapter · to Mar 2027"
    assert p["start"] == date(2026, 6, 1) and p["end"] == date(2027, 3, 10) and p["approximate"] is False
    assert T._period(_chip_ctx(), "month", TODAY, "en")["label"] == "Next 30 days"


def test_rung_order_sorts_year_and_stretch_by_end_date():
    assert C.rung_order(date(2026, 10, 14), date(2029, 4, 1)) == ["now", "30d", "year", "stretch", "chapter"]
    assert C.rung_order(date(2027, 9, 7), date(2027, 3, 10)) == ["now", "30d", "stretch", "year", "chapter"]
    assert C.rung_order(None, date(2027, 3, 10)) == ["now", "30d", "stretch", "chapter"]


def test_read_topic_period_carries_chip_rung_and_order():
    ctx = _chip_ctx()
    out = T.read_topic(ctx, "money", "year", TODAY, "en")
    assert out["period"]["chip"] == "10/15/25 – 10/15/26" and out["period"]["rung"] == "year"
    assert out["rung_order"][0] == "now" and out["rung_order"][-1] == "chapter"


def test_chip_copy_passes_jargon_guard():
    for tbl in (C.CHIP, C.PERIOD_LABEL, C.CHAPTER_LABEL, C.CHAPTER_LEAD, C.KEEP_SMALL):
        for lang in LANGS:
            vals = tbl[lang].values() if isinstance(tbl[lang], dict) else [tbl[lang]]
            for s in vals:
                assert not _JARGON.search(s), (lang, s)
    for lang in LANGS:
        assert set(C.CHIP[lang]) == {"today", "month", "season", "chapter"}


# ── one plain tag per tile: Open now / Opens / Care now / Care from / Quiet ───
_WIN = lambda a, b: {"start": a, "end": b}


def _tag(lang, tone, read, today=TODAY, **kw):
    return T._tile_tag(lang, tone, read, today, **kw)


_EXPECT = {
    "open_now": {"en": "Open now", "es": "Abierto ahora", "pt": "Aberto agora", "hinglish": "Abhi khula hai"},
    "open_now_until": {"en": "Open now, until Oct 30", "es": "Abierto ahora, hasta el 30 oct",
                       "pt": "Aberto agora, até 30 out", "hinglish": "Abhi khula hai, Oct 30 tak"},
    "opens": {"en": "Opens Nov 3", "es": "Abre el 3 nov", "pt": "Abre em 3 nov", "hinglish": "Nov 3 ko khulega"},
    "opens_far": {"en": "Opens Nov 2027", "es": "Abre en nov 2027", "pt": "Abre em nov 2027",
                  "hinglish": "Nov 2027 ko khulega"},
    "care_now": {"en": "Care now, until Oct 20", "es": "Con cuidado ahora, hasta el 20 oct",
                 "pt": "Com cuidado agora, até 20 out", "hinglish": "Abhi savdhaani, Oct 20 tak"},
    "care_from": {"en": "Care from Nov 3", "es": "Con cuidado desde 3 nov",
                  "pt": "Com cuidado a partir de 3 nov", "hinglish": "Nov 3 se savdhaani"},
    "quiet": {"en": "Quiet", "es": "Tranquilo", "pt": "Tranquilo", "hinglish": "Shaant"},
}


@pytest.mark.parametrize("lang", LANGS)
def test_each_tag_kind_in_every_language(lang):
    cases = {
        "open_now": ("open", {"best_window": _WIN("2026-10-01", "2027-02-01"), "watch_window": None}, "open_now"),
        "open_now_until": ("open", {"best_window": _WIN("2026-10-01", "2026-10-30"), "watch_window": None}, "open_now"),
        "opens": ("open", {"best_window": _WIN("2026-11-03", "2026-12-01"), "watch_window": None}, "opens"),
        "opens_far": ("open", {"best_window": _WIN("2027-11-03", "2027-12-01"), "watch_window": None}, "opens"),
        "care_now": ("care", {"best_window": None, "watch_window": _WIN("2026-10-01", "2026-10-20")}, "care_now"),
        "care_from": ("care", {"best_window": None, "watch_window": _WIN("2026-11-03", "2026-12-01")}, "care_from"),
        "quiet": ("steady", {"best_window": None, "watch_window": None}, "quiet"),
    }
    for name, (tone, read, kind) in cases.items():
        tag, k = _tag(lang, tone, read)
        assert (tag, k) == (_EXPECT[name][lang], kind), (lang, name, tag)


def test_tag_priority_current_then_sooner_never_two_phrases():
    both = lambda o, c: {"best_window": _WIN(*o), "watch_window": _WIN(*c)}
    # care running now beats an open window that starts later, even when the tone is open
    assert _tag("en", "open", both(("2026-11-03", "2026-12-01"), ("2026-10-01", "2026-10-20"))) == ("Care now, until Oct 20", "care_now")
    # open running now beats a care window later
    assert _tag("en", "care", both(("2026-10-01", "2027-03-01"), ("2026-11-03", "2026-12-01")))[1] == "open_now"
    # both ahead: the sooner one
    assert _tag("en", "open", both(("2026-12-03", "2027-01-01"), ("2026-11-03", "2026-12-01"))) == ("Care from Nov 3", "care_from")
    assert _tag("en", "care", both(("2026-11-03", "2026-12-01"), ("2026-12-03", "2027-01-01"))) == ("Opens Nov 3", "opens")
    for t in (_tag("en", "open", both(("2026-11-03", "2026-12-01"), ("2026-12-03", "2027-01-01")))[0],):
        assert t.count(",") == 0


def test_status_values_unchanged_and_kind_present_on_the_list(ctxs):
    for ctx in ctxs:
        for d in _DATES3:
            for r in T.rank_topics(ctx, d, "en"):
                assert r["status"] in ("active", "upcoming", "quiet", "steady")
                assert r["tag_kind"] in KINDS
                assert not re.search(r"steady|go gently|take care", r["tag"], re.I)
    assert {r["tag_kind"] for r in T.fallback_topics("en")} == {"quiet"}


def test_open_now_tile_opens_a_read_whose_window_is_running():
    ctx = _fast_ctx(_january(), _burst("2026-10-07"))
    money = {r["key"]: r for r in T.rank_topics(ctx, TODAY, "en")}["money"]
    read = T.read_topic(ctx, "money", T.best_fit_scale(ctx, "money", TODAY), TODAY, "en")
    assert money["tag_kind"] == "open_now" and read["best_window"]["start"] <= TODAY.isoformat() <= read["best_window"]["end"]


def test_opens_tile_names_the_start_of_the_reads_best_window():
    ctx = _fast_ctx(_january(), [])
    row = {r["key"]: r for r in T.rank_topics(ctx, TODAY, "en")}["money"]
    read = T.read_topic(ctx, "money", T.best_fit_scale(ctx, "money", TODAY), TODAY, "en")
    s0 = date.fromisoformat(read["best_window"]["start"])
    want = C.month_year_short(s0, "en") if s0 > TODAY + timedelta(days=T.TAG_DAY_DAYS) else C.day_label(s0, "en")
    assert row["tag_kind"] == "opens" and row["tag"] == f"Opens {want}"


def test_tile_rows_carry_the_window_their_tag_names():
    """window_start/window_end feed the FE timeline bar; they match the tagged window, null when quiet."""
    ctx = _fast_ctx(_january(), _burst("2026-10-07"))
    rows = {r["key"]: r for r in T.rank_topics(ctx, TODAY, "en")}
    money = rows["money"]
    assert money["tag_kind"] == "open_now" and money["window_start"] == "2026-10-07"
    assert money["window_end"] >= money["window_start"]
    for r in rows.values():
        if r["tag_kind"] == "quiet":
            assert r["window_start"] is None and r["window_end"] is None


def test_a_far_window_tag_does_not_slide_with_today(monkeypatch):
    """Windows beyond 45 days are named by month: the scan is bucketed from today, so a day-exact
    date there moved a day every day. The tag for the same real window is identical on adjacent days."""
    tags = set()
    for d in (0, 1, 2):
        today = TODAY + timedelta(days=d)
        s = date(2027, 8, 6)                     # the same real window start each day
        win = {"start": s.isoformat(), "end": (s + timedelta(days=40)).isoformat()}
        _stub(monkeypatch, {"career": ("care", {"best_window": None, "watch_window": win})}, opening=None)
        tags.add({r["key"]: r for r in T.rank_topics(_synth(), today, "en")}["career"]["tag"])
    assert tags == {"Care from Aug 2027"}


def _plain_ctx():
    """A real TopicContext (its own events()), unlike _synth which replaces events."""
    return T.TopicContext("plain", {"lagna": {"sign": "Aries", "sign_index": 0}, "planets": {}}, {"vimsottari": []})


def test_a_failed_transit_feed_marks_the_context_degraded(monkeypatch):
    import antar_engine.transit_events as TE
    monkeypatch.setattr(TE, "compute_transit_events_in_range", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    ctx = _plain_ctx()
    assert ctx.events(TODAY, TODAY + timedelta(days=30), True) == []
    assert ctx.degraded is True


def test_a_healthy_transit_feed_is_not_degraded(monkeypatch):
    import antar_engine.transit_events as TE
    monkeypatch.setattr(TE, "compute_transit_events_in_range", lambda *a, **k: [])
    ctx = _plain_ctx()
    ctx.events(TODAY, TODAY + timedelta(days=30), True)
    assert ctx.degraded is False


def test_a_transient_feed_failure_is_retried_once(monkeypatch):
    import antar_engine.transit_events as TE
    calls = {"n": 0}
    def flaky(*a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("transient")
        return ["ev"]
    monkeypatch.setattr(TE, "compute_transit_events_in_range", flaky)
    ctx = _plain_ctx()
    assert ctx.events(TODAY, TODAY + timedelta(days=30), True) == ["ev"] and ctx.degraded is False


def test_tile_rows_carry_a_plain_headline_verdict_and_ends_today():
    ctx = _fast_ctx(_january(), _burst("2026-10-07"))
    rows = {r["key"]: r for r in T.rank_topics(ctx, TODAY, "en")}
    money = rows["money"]
    assert money["tag_kind"] == "open_now"
    assert money["headline"].startswith("Money matters have better backing") and money["headline"].endswith(".")
    assert money["verdict"] == "Good time"
    for r in rows.values():
        assert r["headline"] and r["verdict"]
        if r["tag_kind"] == "quiet":
            assert r["headline"].startswith(("Nothing sharp is pulling", "Nothing pressing")) and r["verdict"] == "Quiet" and r["ends_today"] is False
        if r["tag_kind"] in ("care_now", "care_from"):
            assert r["verdict"].startswith("Be careful") and r["headline"].endswith(".") and r["headline"][0].isupper()


def test_ends_today_is_true_only_for_a_window_that_ends_on_today(monkeypatch):
    win = {"start": TODAY.isoformat(), "end": TODAY.isoformat()}
    _stub(monkeypatch, {"money": ("open", {"best_window": win, "watch_window": None})})
    row = {r["key"]: r for r in T.rank_topics(_synth(), TODAY, "en")}["money"]
    if row["tag_kind"] == "open_now":
        assert row["ends_today"] is True
    later = {"start": TODAY.isoformat(), "end": (TODAY + timedelta(days=20)).isoformat()}
    _stub(monkeypatch, {"money": ("open", {"best_window": later, "watch_window": None})})
    row = {r["key"]: r for r in T.rank_topics(_synth(), TODAY, "en")}["money"]
    assert row["ends_today"] is False


def test_care_headlines_are_distinct_per_topic():
    ctx = _fast_ctx(_january(), [])
    heads = [r["headline"] for r in T.rank_topics(ctx, TODAY, "en") if r["tag_kind"] in ("care_now", "care_from")]
    assert len(heads) == len(set(heads))


def test_headline_and_verdict_are_localised():
    for lang in ("es", "pt", "hinglish"):
        ctx = _fast_ctx(_january(), _burst("2026-10-07"))
        rows = {r["key"]: r for r in T.rank_topics(ctx, TODAY, lang)}
        assert not rows["money"]["headline"].startswith("Money matters") and rows["money"]["verdict"] != "Good time", lang
        assert rows["peace"]["headline"] and not rows["peace"]["headline"].startswith("Nothing sharp"), lang
