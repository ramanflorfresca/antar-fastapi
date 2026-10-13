"""Windows feed: one cross-topic list of dated windows, built from the topic engine.

No second window algorithm: every window comes from `topic_engine.windows_for` (the same
scan, bucketing, run-merging and never-in-the-past clamp the topic reads use) at the month,
season and year scales. This module only merges the overlapping runs of one topic and kind,
cuts them to the horizon, and words them with the existing topic copy. Deterministic, no LLM.
Describes timing only; never promises an outcome.

Two layers so a repeat call is cheap: `raw_windows` (dates only, language-free, the part that
costs an ephemeris pass) and `assemble` (words, ordering, caps). Never raises."""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

from antar_engine import topic_copy as C
from antar_engine import topic_engine as T

logger = logging.getLogger(__name__)

DEFAULT_HORIZON_MONTHS = 30
MAX_HORIZON_MONTHS = 36
NEXT_MAX = 12
NEXT_PER_TOPIC = 2
CARE_MAX = 6
FEED_SCALES = ("month", "season", "year")
KINDS = ("open", "care")


def clamp_horizon(months) -> int:
    try:
        m = int(months)
    except (TypeError, ValueError):
        return DEFAULT_HORIZON_MONTHS
    return max(1, min(MAX_HORIZON_MONTHS, m))


def _merge(runs: List[Tuple[date, date]]) -> List[Tuple[date, date]]:
    """Union of overlapping / back-to-back runs, ordered by start."""
    out: List[Tuple[date, date]] = []
    for s, e in sorted(runs):
        if out and (s - out[-1][1]).days <= 1:
            out[-1] = (out[-1][0], max(out[-1][1], e))
        else:
            out.append((s, e))
    return out


def _merge_driver(a: dict, b: dict) -> dict:
    """The driver of two merged runs: the stronger run's chapter link / timeline agreement,
    the widest span of dated movement. n_signals is a max, not a sum: month, season and year
    scans can see the same movement."""
    base = dict(a if a.get("score", 0) >= b.get("score", 0) else b)
    firsts = [x["first_date"] for x in (a, b) if x.get("first_date")]
    lasts = [x["last_date"] for x in (a, b) if x.get("last_date")]
    base["first_date"] = min(firsts) if firsts else ""
    base["last_date"] = max(lasts) if lasts else ""
    base["n_signals"] = max(a.get("n_signals", 0), b.get("n_signals", 0))
    base["chara_confirm"] = bool(base.get("chara_confirm"))
    return base


def _merge_with(runs: List[Tuple[date, date]], drivers: Dict[str, dict]):
    """_merge + carry each run's driver (keyed by start ISO) onto the merged run."""
    out: List[Tuple[date, date]] = []
    out_drv: Dict[str, dict] = {}
    for s, e in sorted(runs):
        d = drivers.get(s.isoformat())
        if out and (s - out[-1][1]).days <= 1:
            ps = out[-1][0]
            out[-1] = (ps, max(out[-1][1], e))
            if d is not None:
                out_drv[ps.isoformat()] = (_merge_driver(out_drv[ps.isoformat()], d)
                                           if ps.isoformat() in out_drv else d)
        else:
            out.append((s, e))
            if d is not None:
                out_drv[s.isoformat()] = d
    return out, out_drv


def raw_windows(ctx: T.TopicContext, today: date) -> Dict[str, Optional[dict]]:
    """{topic: {"open": [(s, e)], "care": [(s, e)]} | None}, merged across scales, out to the
    longest horizon. None marks a topic whose scan failed (so it is never called "quiet")."""
    out: Dict[str, Optional[dict]] = {}
    for key in T.TOPIC_KEYS:
        try:
            runs = {k: [] for k in KINDS}
            drv = {k: {} for k in KINDS}
            for scale in FEED_SCALES:
                w = T.windows_for(ctx, key, scale, today)
                for k in KINDS:
                    for r in w.get(k, []):
                        c = T.clamp_window(r["start"], r["end"], today)
                        if c:
                            runs[k].append(c)
                            if r.get("driver"):
                                prev = drv[k].get(c[0].isoformat())
                                drv[k][c[0].isoformat()] = (_merge_driver(prev, r["driver"])
                                                            if prev else r["driver"])
            merged = {k: _merge_with(v, drv[k]) for k, v in runs.items()}
            out[key] = {k: merged[k][0] for k in KINDS}
            out[key]["drivers"] = {k: merged[k][1] for k in KINDS}
        except Exception:
            logger.exception("[windows-feed] %s scan failed -> skipped", key)
            out[key] = None
    return out


def _month_end(d: date) -> date:
    """Last day of d's month. The feed's horizon snaps here so a window that runs into it ends on a calendar boundary and does
    not move by a day every day (it was today + N months, so the last window's end date slid daily)."""
    nxt = date(d.year + (d.month == 12), 1 if d.month == 12 else d.month + 1, 1)
    return nxt - timedelta(days=1)


def _cut(wins: List[Tuple[date, date]], horizon_end: date) -> List[Tuple[date, date]]:
    return [(s, min(e, horizon_end)) for s, e in wins if s <= horizon_end]


def _sentence(text: str) -> str:
    t = (text or "").strip()
    return (t[:1].upper() + t[1:] + ("" if t.endswith(".") else ".")) if t else t


def _fmt(d: date, lang: str, today: date) -> str:
    return C.day_label(d, lang) if d.year == today.year else C.day_label_y(d, lang)


def _why(key: str, kind: str, s: date, e: date, today: date, lang: str,
         driver: Optional[dict], time_quality: str) -> Tuple[dict, Optional[dict]]:
    """({"line", "bullets"}, {"level", "note"} | None) from the window's driver. The line is the
    chapter clause plus the dated clause when something is dated; a window carried by the chapter
    alone says only that (the confidence chip carries the rest)."""
    if not driver:
        return {"line": "", "bullets": []}, None
    d = dict(driver, mode=kind)
    bullets = T.why_bullets(time_quality, key, d, lang, s, e, today, then=s > today)
    none_dated = C.pick(C.WHY_BULLET, lang)["none_dated"]
    bullets = [b for b in bullets if b != none_dated]   # a window card is not "not a dated window"
    agree = C.pick(C.WHY_BULLET, lang)["agree"]
    line = " ".join(b for b in bullets[:3] if b != agree and b not in (
        C.pick(C.WHY_BULLET, lang)["approx_time"], C.pick(C.WHY_BULLET, lang)["no_time"]))
    level = driver.get("confidence") or "low"
    if time_quality == "unknown":
        level = "low"
    note = C.pick(C.CONFIDENCE_NOTE, lang).get(level, "")
    return {"line": line, "bullets": bullets}, {"level": level, "note": note}


def _entry(key: str, kind: str, s: date, e: date, today: date, lang: str,
           driver: Optional[dict] = None, time_quality: str = "") -> dict:
    phase = T.window_phase(s, e, today)
    when = _fmt(s, lang, today)
    if phase == "now":
        headline = _sentence(C.pick(C.CORE, lang)[key][kind])
        move = C.pick(C.MOVE, lang)[key][kind]
    else:   # not open yet: name the day it opens and make the move a prepare step
        headline = _sentence(C.pick(C.CORE_AHEAD, lang)[key][kind].format(date=when))
        move = C.pick(C.MOVE_AHEAD, lang)[key][kind].format(date=when)
    rng = (f"{_fmt(s, lang, today)} – {_fmt(e, lang, today)}" if s != e else _fmt(s, lang, today))
    why, conf = _why(key, kind, s, e, today, lang, driver, time_quality)
    return {"topic": key, "label": C.LABEL[lang][key], "kind": kind,
            "start": s.isoformat(), "end": e.isoformat(), "label_range": rng,
            "headline": headline, "move": move, "window_phase": phase,
            "days_left": (e - today).days, "opens_in_days": max(0, (s - today).days),
            "why": why, "confidence": conf}


def _big_picture(ctx: T.TopicContext, today: date, lang: str) -> dict:
    stretch = chapter = None
    try:
        per = T._period(ctx, "season", today, lang)
        sp = per["span"]
        stretch = {"label": C.season_text(C.SPAN_TEXT, lang, sp), "start": per["start"].isoformat(),
                   "end": per["end"].isoformat(), "span": dict(sp),
                   "chip": per["chip"], "rung": per["rung"]}
    except Exception:
        logger.exception("[windows-feed] stretch skipped")
    try:
        for r in (ctx.dashas or {}).get("vimsottari", []) or []:
            if not str(r.get("level") or "").lower().startswith("maha"):
                continue
            rs = str(r.get("start_date") or r.get("start") or "")[:10]
            re_ = str(r.get("end_date") or r.get("end") or "")[:10]
            if rs <= today.isoformat() <= re_:
                chapter = {"label": C.pick(C.WINDOWS_CHAPTER, lang).format(
                    end=C.month_year_short(date.fromisoformat(re_), lang)), "start": rs, "end": re_,
                    "rung": "chapter"}
                break
    except Exception:
        logger.exception("[windows-feed] chapter skipped")
    return {"stretch": stretch, "chapter": chapter, "rung_order": T._rung_order(ctx, today, lang)}


def assemble(ctx: T.TopicContext, raw: Dict[str, Optional[dict]], today: date, language: str = "en",
             horizon_months: int = DEFAULT_HORIZON_MONTHS) -> dict:
    lang = C.serve_language(language)
    hm = clamp_horizon(horizon_months)
    horizon_end = _month_end(C.add_months(today, hm))
    now, upcoming, tracks, quiet = [], [], [], []
    for key in T.TOPIC_KEYS:
        r = raw.get(key)
        if r is None:
            continue
        wins = {k: _cut(r.get(k, []), horizon_end) for k in KINDS}
        flat = sorted(((s, e, k) for k in KINDS for s, e in wins[k]))
        drivers = r.get("drivers") or {}
        if not flat:
            quiet.append(key)
            continue
        tracks.append({"topic": key, "label": C.LABEL[lang][key],
                       "windows": [{"kind": k, "start": s.isoformat(), "end": e.isoformat()} for s, e, k in flat]})
        for s, e, k in flat:
            drv = (drivers.get(k) or {}).get(s.isoformat())
            (now if s <= today else upcoming).append(
                _entry(key, k, s, e, today, lang, drv, ctx.time_quality))
    now.sort(key=lambda w: (w["end"], T.TOPIC_KEYS.index(w["topic"]), w["kind"]))
    upcoming.sort(key=lambda w: (w["start"], T.TOPIC_KEYS.index(w["topic"]), w["kind"]))
    nxt, per_topic = [], {}
    for w in upcoming:
        if per_topic.get(w["topic"], 0) >= NEXT_PER_TOPIC or len(nxt) >= NEXT_MAX:
            continue
        per_topic[w["topic"]] = per_topic.get(w["topic"], 0) + 1
        nxt.append(w)
    care = [w for w in upcoming if w["kind"] == "care"][:CARE_MAX]
    now_out = [{k: v for k, v in w.items() if k not in ("opens_in_days", "label_range", "window_phase")}
               for w in now]
    return {"chart_id": ctx.chart_id, "as_of": today.isoformat(), "language": lang,
            "horizon_end": horizon_end.isoformat(),
            "now": now_out, "next": nxt, "care": care, "tracks": tracks,
            "big_picture": _big_picture(ctx, today, lang), "quiet_topics": quiet}


def empty_feed(chart_id: str, today: date, language: str, horizon_months: int) -> dict:
    lang = C.serve_language(language)
    return {"chart_id": chart_id, "as_of": today.isoformat(), "language": lang,
            "horizon_end": _month_end(C.add_months(today, clamp_horizon(horizon_months))).isoformat(),
            "now": [], "next": [], "care": [], "tracks": [],
            "big_picture": {"stretch": None, "chapter": None}, "quiet_topics": []}


def raw_to_json(raw) -> dict:
    return {k: (None if v is None else dict(
                {kd: [[s.isoformat(), e.isoformat()] for s, e in v[kd]] for kd in KINDS},
                drivers=v.get("drivers") or {kd: {} for kd in KINDS}))
            for k, v in raw.items()}


def raw_from_json(d) -> Dict[str, Optional[dict]]:
    return {k: (None if v is None else dict(
                {kd: [(date.fromisoformat(s), date.fromisoformat(e)) for s, e in v[kd]] for kd in KINDS},
                drivers=v.get("drivers") or {kd: {} for kd in KINDS})) for k, v in d.items()}
