"""
antar_engine/topic_engine.py
────────────────────────────
Topic picker + topic read for the /ask home screen.

  rank_topics(ctx, today, language)          -> [{key,label,status,tag,rank}]
  read_topic(ctx, topic, scale, today, lang) -> {claim, best_window, watch_window, …}

Pure and deterministic: no LLM, no IO, never raises past the public functions
(rank_topics falls back to all-"steady" in fixed order). main.py does the DB
loading and hands in a `TopicContext`.

HONESTY RULES (owner, from project memory — do not loosen)
  • Rank by REAL activation (forecast-surfacing / daily-vote-grounding): a topic
    is "active" only when the running chapter is tied to it AND/OR dated
    movement lands on it. A neutral topic stays "steady"/"quiet"; it is never
    padded into a window.
  • SIGNAL INDEPENDENCE (signal-independence-in-scoring). Seven topics share
    houses (Family/Peace share the 4th, Love/Business the 7th) and every topic
    shares the one running chapter. Three guards keep a single sky event from
    inflating several topics or one topic several times:
      1. A dated movement is credited to the topic that owns its house
         (primary beats secondary-core beats supporting; a tie splits it).
      2. The chapter contributes ONCE per topic — the strongest single link
         (house-lord/occupant > key planet > supporting lord), never summed.
      3. The second timeline (chara) only CONFIRMS a chapter hit; it is a
         confidence dial, not a second independent bet. Alone it is a whisper.
    Motion sub-events of one passage are collapsed by house_activation's
    _dedup_transit_signals before counting.
  • "Watch" exists only when real: a risk reading needs a dated, demanding
    movement inside the window. Structural lean alone never makes a Watch.
  • Money / Business speak timing and approach only; Health speaks rhythm only
    (see topic_copy). The chart does not predict wealth level or venture success.
  • No window is ever dated before `today`.
"""
from __future__ import annotations

import copy
import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from antar_engine import topic_copy as C
from antar_engine.house_activation import (
    _BENEFICS, _DUSTHANAS, _MALEFICS, _dedup_transit_signals, _house_lord,
    _lagna_index, _occupants, _vim_active_planets,
)

logger = logging.getLogger(__name__)

TOPIC_KEYS = C.TOPIC_KEYS
SCALES = C.SCALES

# Core houses are the topic's own; support houses colour it. Mirrors
# places_concern.CONCERN_MAP (pinned by a test) so Places and Ask agree.
TOPIC_SPEC: Dict[str, Dict[str, Any]] = {
    "money":    {"core": [2, 11], "support": [5, 9],  "karakas": ["Jupiter", "Venus", "Mercury"]},
    "career":   {"core": [10, 6], "support": [1],     "karakas": ["Sun", "Saturn", "Mercury"]},
    "love":     {"core": [7],     "support": [5, 11], "karakas": ["Venus", "Mars", "Moon"]},
    "health":   {"core": [1, 6],  "support": [],      "karakas": ["Sun", "Mars", "Saturn"]},
    "business": {"core": [7, 10], "support": [11, 3], "karakas": ["Mercury", "Mars", "Jupiter"]},
    "peace":    {"core": [4, 12], "support": [],      "karakas": ["Moon", "Jupiter", "Ketu"]},
    "family":   {"core": [4],     "support": [9, 7],  "karakas": ["Moon", "Sun", "Jupiter"]},
}

ACTIVE_MIN = 3.5     # score at which a topic / bucket counts as really lit
STEADY_MIN = 1.5     # below this a topic is "quiet"
# A picker where most tiles say "active now" tells the user nothing, so "active"
# is also RELATIVE to the chart: of the topics that are really lit, only those
# within REL_FRAC of the strongest stay active, at most ACTIVE_CAP of them. A
# genuinely strong signal (STRONG_MIN) is never demoted by the cap or the cut.
ACTIVE_CAP = 3
REL_FRAC = 0.75
STRONG_MIN = 5.5
LOOKAHEAD_DAYS = 150
NOW_HORIZON_DAYS = 30
SEASON_SCAN_CAP_DAYS = 730


# ── context ──────────────────────────────────────────────────────────────────
@dataclass
class TopicContext:
    chart_id: str
    chart_data: dict
    dashas: dict                      # {system: [rows]} as main.get_dashas_for_chart
    birth_date: str = ""              # ISO
    jaimini_data: Optional[dict] = None
    birth_time_accuracy: Optional[str] = None   # exact|approximate|unknown|None
    _events_cache: Dict[Any, list] = field(default_factory=dict, repr=False)
    degraded: bool = field(default=False, repr=False)   # a transit feed / scale read failed: result is partial

    @property
    def lagna_sign(self) -> str:
        return str(((self.chart_data or {}).get("lagna") or {}).get("sign") or "").strip().title()

    @property
    def time_quality(self) -> str:
        a = (self.birth_time_accuracy or "").lower()
        return a if a in ("exact", "approximate", "unknown") else "exact"

    def events(self, start: date, end: date, fast: bool) -> list:
        """Transit events in [start,end], memoised per context (one ephemeris pass)."""
        key = (start, end, fast)
        if key not in self._events_cache:
            for attempt in (1, 2):
                try:
                    from antar_engine.transit_events import compute_transit_events_in_range
                    self._events_cache[key] = compute_transit_events_in_range(
                        self.chart_data, start, end, include_fast=fast) or []
                    break
                except Exception as e:  # swisseph missing → dasha-only, never an error
                    if attempt == 2:
                        logger.warning("[topics] transit feed skipped chart=%s %s..%s fast=%s: %s",
                                       str(self.chart_id)[:8], start, end, fast, e)
                        self.degraded = True
                        self._events_cache[key] = []
        return self._events_cache[key]


# ── independence: who owns a house's movement ────────────────────────────────
def _house_claim_share() -> Dict[Tuple[str, int], float]:
    """(topic, house) -> share of a movement on that house credited to the topic.
    The topic whose PRIMARY (first core) house it is owns it; else a topic with
    it as a secondary core house; else supporting topics. Only genuine ties split
    evenly (Family/Peace on the 4th, Love/Business on the 7th get 0.5 each), so
    one event can never add a full point to two topics."""
    def level(spec, h):
        if h == spec["core"][0]:
            return 0
        if h in spec["core"]:
            return 1
        return 2 if h in spec["support"] else None

    share: Dict[Tuple[str, int], float] = {}
    for h in range(1, 13):
        lv = {k: level(sp, h) for k, sp in TOPIC_SPEC.items()}
        lv = {k: v for k, v in lv.items() if v is not None}
        if not lv:
            continue
        best = min(lv.values())
        owners = [k for k, v in lv.items() if v == best]
        for k in owners:
            share[(k, h)] = 1.0 / len(owners)
    return share


_CLAIM = _house_claim_share()


def _topic_houses(key: str) -> List[int]:
    s = TOPIC_SPEC[key]
    return list(s["core"]) + list(s["support"])


# ── assessment (one topic, one date, one event set) ──────────────────────────
def _links(ctx: TopicContext, key: str) -> Tuple[set, set]:
    spec = TOPIC_SPEC[key]
    ls, occ = ctx.lagna_sign, _occupants(ctx.chart_data)
    core, sup = set(), set()
    for h in spec["core"]:
        l = _house_lord(ls, h) if ls else None
        if l:
            core.add(l)
        core.update(occ.get(h, []))
    for h in spec["support"]:
        l = _house_lord(ls, h) if ls else None
        if l:
            sup.add(l)
        sup.update(occ.get(h, []))
    return core, sup


def _chara_weight(ctx: TopicContext, key: str, on: date) -> float:
    if ctx.time_quality == "unknown" or not ctx.jaimini_data:
        return 0.0
    try:
        from antar_engine.chara_dasha import chara_activation
        r = chara_activation(ctx.chart_data, ctx.jaimini_data, ctx.dashas,
                             _lagna_index(ctx.chart_data), on.isoformat())
        if not r.get("available"):
            return 0.0
        hs = r.get("houses") or {}
        return max([float(hs.get(h, 0.0)) for h in _topic_houses(key)] or [0.0])
    except Exception:
        return 0.0


def assess(ctx: TopicContext, key: str, on: date, events: list) -> dict:
    """Score one topic on `on`, with `events` as the dated movement in play."""
    spec = TOPIC_SPEC[key]
    vim = _vim_active_planets(ctx.dashas, on.isoformat())
    core_l, sup_l = _links(ctx, key)
    kar = set(spec["karakas"])

    # (2) the chapter counts once: strongest single link
    if vim & core_l:
        dasha_pts, dasha_kind = 3.0, "core"
    elif vim & kar:
        dasha_pts, dasha_kind = 1.5, "theme"
    elif vim & sup_l:
        dasha_pts, dasha_kind = 1.0, "theme"
    else:
        dasha_pts, dasha_kind = 0.0, ""

    # (3) second timeline confirms, never stands alone
    cw = _chara_weight(ctx, key, on)
    if dasha_pts > 0:
        chara_pts = min(1.0, cw * 1.2) if cw >= 0.35 else 0.0
    else:
        chara_pts = 0.5 if cw >= 0.6 else 0.0
    chara_confirm = dasha_pts > 0 and chara_pts > 0

    # (1) dated movement, credited by house ownership, motion sub-events collapsed
    houses = set(_topic_houses(key))
    mine = [e for e in (events or []) if isinstance(e.get("natal_house"), int)
            and e["natal_house"] in houses]
    sigs = _dedup_transit_signals(mine)
    credit = 0.0
    tone = 0.0
    n_ben = n_mal = 0
    dates: List[str] = []
    for e in sigs:
        share = _CLAIM.get((key, e["natal_house"]), 0.0)
        if share <= 0:
            continue
        credit += share
        w = 1.2 if e.get("event_type") == "aspect" else 1.0   # direction is not split by ownership
        pl = str(e.get("planet") or "").title()
        if pl in _BENEFICS:
            tone += w
            n_ben += 1
        elif pl in _MALEFICS:
            tone -= w
            n_mal += 1
        if e.get("date"):
            dates.append(str(e["date"])[:10])
    transit_pts = min(3.0, 0.75 * credit)

    md_malefic = bool(vim & _MALEFICS) and not (vim & _BENEFICS)
    if md_malefic:
        tone -= 0.3
    dus = sum(1 for h in spec["core"] if h in _DUSTHANAS) / max(1, len(spec["core"]))
    if dus >= 0.5 and md_malefic:
        tone -= 0.4

    score = round(dasha_pts + chara_pts + transit_pts, 2)
    convergence = dasha_kind == "core" and chara_confirm

    # polarity: a RISK needs a dated demanding movement; an OPPORTUNITY needs
    # either a dated supportive one or two agreeing timelines. Otherwise neutral.
    if tone < -0.4 and n_mal >= 1:
        polarity = "risk"
    elif (tone > 0.4 and n_ben >= 1) or (convergence and not md_malefic and tone >= -0.4):
        polarity = "opportunity"
    else:
        polarity = "neutral"

    mode = "care" if polarity == "risk" else "open" if polarity == "opportunity" else "steady"
    return {
        "key": key, "score": score, "dasha_pts": dasha_pts, "dasha_kind": dasha_kind,
        "chara_confirm": chara_confirm, "chara_pts": round(chara_pts, 2),
        "n_signals": len(dates), "n_benefic": n_ben, "n_malefic": n_mal,
        "tone": round(tone, 2), "polarity": polarity, "mode": mode,
        "convergence": convergence, "md_malefic": md_malefic,
        "first_date": min(dates) if dates else "", "last_date": max(dates) if dates else "",
        "lit": score >= ACTIVE_MIN and polarity != "neutral",
    }


# ── ranking ──────────────────────────────────────────────────────────────────
def _now_assessments(ctx: TopicContext, today: date) -> Dict[str, dict]:
    ev = ctx.events(today, today + timedelta(days=NOW_HORIZON_DAYS - 1), False)
    return {k: assess(ctx, k, today, ev) for k in TOPIC_KEYS}


def _bucket_ranges(start: date, end: date, days: int) -> List[Tuple[date, date]]:
    out, s = [], start
    while s <= end:
        e = min(end, s + timedelta(days=days - 1))
        out.append((s, e))
        s = e + timedelta(days=1)
    return out


def _assess_bucket(ctx, key, b: Tuple[date, date], events: list) -> dict:
    s, e = b
    inside = [x for x in events if s.isoformat() <= str(x.get("date") or "")[:10] <= e.isoformat()]
    mid = s + (e - s) // 2
    return assess(ctx, key, mid, inside)


def _next_opening(ctx: TopicContext, key: str, today: date) -> Optional[Tuple[date, str]]:
    """First dated window (after today) that turns this topic really lit."""
    end = today + timedelta(days=LOOKAHEAD_DAYS)
    ev = ctx.events(today, end, False)
    for b in _bucket_ranges(today + timedelta(days=1), end, 15):
        a = _assess_bucket(ctx, key, b, ev)
        if a["lit"]:
            return b[0], a["mode"]
    return None


def fallback_topics(language: str = "en") -> List[dict]:
    lang = C.serve_language(language)
    return [{"key": k, "label": C.LABEL[lang][k], "status": "steady",
             "tag": C.TAG[lang]["quiet"], "tag_kind": "quiet", "tone": "steady", "rank": i + 1,
             "window_start": None, "window_end": None}
            for i, k in enumerate(TOPIC_KEYS)]


def active_set(now: Dict[str, dict]) -> set:
    """Which really-lit topics stay "active": relative to the chart's strongest,
    capped, ties broken by fixed topic order. The rest fall to steady."""
    lit = sorted((k for k in TOPIC_KEYS if now[k]["lit"]),
                 key=lambda k: (-now[k]["score"], TOPIC_KEYS.index(k)))
    if not lit:
        return set()
    top = now[lit[0]]["score"]
    keep = set()
    for i, k in enumerate(lit):
        sc = now[k]["score"]
        if sc >= STRONG_MIN or (i < ACTIVE_CAP and sc >= REL_FRAC * top):
            keep.add(k)
    return keep


NEAR_DAYS = 2   # a window starting this soon is "now-ish", never "opens {month}"
FAR_MONTHS = 12          # a window starting later than this is "far": its tag names the date
LABEL_YEAR_MONTHS = 11   # a period ending later than this carries its year in the label
TAG_DAY_DAYS = 45        # a window start further out than this is named by month: the scan is bucketed
                         # from today, so a day-exact date there would slide a day every day


def _is_far(start: Optional[date], today: date) -> bool:
    return bool(start) and start > C.add_months(today, FAR_MONTHS)


TAG_UNTIL_DAYS = 30      # "Open now" names its end only when it is this close


def _tag_date(d: date, lang: str, today: date, far_key: str, near_key: str) -> Tuple[str, str]:
    """(copy key, value): a day ("Oct 30") within TAG_DAY_DAYS, a month + year beyond."""
    if d > today + timedelta(days=TAG_DAY_DAYS):
        return far_key, C.month_year_short(d, lang)
    return near_key, C.day_label(d, lang)


def _pick_tile_window(tone: str, read: Optional[dict], today: date,
                      opening: Optional[Tuple[date, str]] = None) -> Optional[Tuple[str, date, date]]:
    """The one (mode, start, end) window a tile talks about: running today wins, else soonest ahead."""
    wins = []                                   # (mode, start, end)
    for mode, field in (("open", "best_window"), ("care", "watch_window")):
        w = (read or {}).get(field)
        if w:
            wins.append((mode, date.fromisoformat(w["start"]), date.fromisoformat(w["end"])))
    if not wins and opening and read is None:   # no read to agree with: the engine's own next opening
        wins.append((opening[1], opening[0], opening[0]))
    live = [w for w in wins if w[1] <= today <= w[2]]
    ahead = [w for w in wins if w[1] > today]
    return (sorted(live, key=lambda w: w[0] != tone) or sorted(ahead, key=lambda w: (w[1], w[0] != tone)) or [None])[0]


def _tile_tag(lang: str, tone: str, read: Optional[dict], today: date,
              active: bool = False, opening: Optional[Tuple[date, str]] = None) -> Tuple[str, str]:
    """(tag, tag_kind): exactly one of open_now | opens | care_now | care_from | quiet.

    The windows come from the read the tile opens. A window running today wins;
    otherwise the one that starts soonest (the tone's own on a tie). Never two phrases."""
    t = C.TAG[lang]
    pick = _pick_tile_window(tone, read, today, opening)
    if pick is None:
        if active:                              # lit today but the read carries no dated window
            kind = "care_now" if tone == "care" else "open_now"
            return t[kind], kind
        return t["quiet"], "quiet"
    mode, s0, e0 = pick
    if s0 <= today:
        if mode == "open":
            if (e0 - today).days <= TAG_UNTIL_DAYS:
                return t["open_now_until"].format(d=C.day_label(e0, lang)), "open_now"
            return t["open_now"], "open_now"
        return t["care_now_until"].format(d=C.day_label(e0, lang)), "care_now"
    kind = "opens" if mode == "open" else "care_from"
    key, val = _tag_date(s0, lang, today, kind + "_far", kind)
    return t[key].format(d=val, my=val), kind


def _tile_window(tone: str, read: Optional[dict]) -> Optional[Tuple[date, date]]:
    """(start, end) of the window the tile's tone names, from the read it opens."""
    if not read or tone not in ("open", "care"):
        return None
    w = read.get("best_window" if tone == "open" else "watch_window")
    if not w:
        return None
    return date.fromisoformat(w["start"]), date.fromisoformat(w["end"])


def _near_score(ctx: TopicContext, key: str, today: date, now_score: float) -> float:
    try:
        a = assess(ctx, key, today, ctx.events(today - timedelta(days=1), today + timedelta(days=NEAR_DAYS), True))
        return max(now_score, a["score"])
    except Exception:
        return now_score


def rank_topics(ctx: TopicContext, today: date, language: str = "en") -> List[dict]:
    """[{key,label,status,tag,tone,rank}], most active first. Never raises.

    Status, tag and tone all come from the read the tile opens (best_fit_scale):
    a window running today (or starting within NEAR_DAYS) is never "upcoming",
    and "window opens {mon}" names the month of that read's own window."""
    lang = C.serve_language(language)
    try:
        now = _now_assessments(ctx, today)
        keep = active_set(now)
        tiles = {k: _tile_read(ctx, k, today) for k in TOPIC_KEYS}
        # unlit tiles whose own read has a window running today / about to start
        near = {}
        for k in TOPIC_KEYS:
            tone, read = tiles[k]
            win = _tile_window(tone, read)
            if k not in keep and not now[k]["lit"] and win and win[0] <= today + timedelta(days=NEAR_DAYS):
                near[k] = (win, _near_score(ctx, k, today, now[k]["score"]))
        # a window running TODAY may join "active" under the same cap and relative cut
        promoted = set()
        top = max([now[k]["score"] for k in keep] + [v[1] for v in near.values()] or [0.0])
        for k in sorted(near, key=lambda k: (-near[k][1], TOPIC_KEYS.index(k))):
            win, sc = near[k]
            if win[0] <= today and len(keep) + len(promoted) < ACTIVE_CAP and (
                    sc >= STRONG_MIN or sc >= REL_FRAC * top):
                promoted.add(k)
        rows = []
        for i, k in enumerate(TOPIC_KEYS):
            a = now[k]
            tone, read = tiles[k]
            if k in keep or k in promoted:
                status = "active"
                tag, kind = _tile_tag(lang, tone, read, today, active=True)
                order = (0, -(near[k][1] if k in promoted else a["score"]), i)
            elif a["lit"]:
                # really lit, but not among the chart's strongest: steady, not "now"
                status = "steady"
                tag, kind = _tile_tag(lang, tone, read, today)
                order = (2, -a["score"], i)
            elif k in near:
                # its own read is already inside a window: near-term words, never "opens {month}"
                status = "steady"
                tag, kind = _tile_tag(lang, tone, read, today)
                order = (2, -near[k][1], i)
            else:
                win = _tile_window(tone, read)
                opening = _next_opening(ctx, k, today)
                # "upcoming" needs a real opening ahead AND, when the tile's read is known,
                # a window in THAT read: the month comes from it, so tag and read agree
                if opening and (win or read is None):
                    d, mode = (win[0], tone) if win else opening
                    status = "upcoming"
                    tag, kind = _tile_tag(lang, tone, read, today, opening=(d, mode))
                    order = (1, d.toordinal(), -a["score"], i)
                elif a["score"] >= STEADY_MIN:
                    status = "steady"
                    tag, kind = _tile_tag(lang, tone, read, today)
                    order = (2, -a["score"], i)
                else:
                    status = "quiet"
                    tag, kind = _tile_tag(lang, tone, read, today)
                    order = (3, -a["score"], i)
            pw = _pick_tile_window(tone, read, today) if kind != "quiet" else None
            rows.append((order, {"key": k, "label": C.LABEL[lang][k], "status": status, "tag": tag,
                                 "tag_kind": kind, "tone": tone,
                                 "window_start": pw[1].isoformat() if pw else None,
                                 "window_end": pw[2].isoformat() if pw else None}))
        rows.sort(key=lambda r: r[0])
        return [dict(r[1], rank=n + 1) for n, r in enumerate(rows)]
    except Exception:
        logger.exception("[topics] ranking failed → steady fallback")
        return fallback_topics(lang)


# ── windows ──────────────────────────────────────────────────────────────────
def clamp_window(start: date, end: date, today: date) -> Optional[Tuple[date, date]]:
    """No window or deadline may ever be dated before today."""
    if end < today:
        return None
    return max(start, today), end


def _runs(results: List[Tuple[Tuple[date, date], dict]], mode: str) -> List[dict]:
    runs, cur = [], None
    for (s, e), a in results:
        ok = a["lit"] and a["mode"] == mode
        if ok and cur and (s - cur["end"]).days <= 1:
            cur["end"] = e
            cur["score"] += a["score"]
            cur["assessments"].append(a)
        elif ok:
            cur = {"start": s, "end": e, "score": a["score"], "assessments": [a]}
            runs.append(cur)
        else:
            cur = None
    return runs


def _best_run(runs: List[dict]) -> Optional[dict]:
    return max(runs, key=lambda r: (r["score"], -r["start"].toordinal())) if runs else None


MIN_LEAD_DAYS = 7   # a window already running that has fewer days left than this is not the headline of a long read


def _merge_runs(runs: List[dict]) -> List[dict]:
    """Union of overlapping / back-to-back runs (same rule as windows_feed._merge), keeping scores."""
    out: List[dict] = []
    for r in sorted(runs, key=lambda x: (x["start"], x["end"])):
        if out and (r["start"] - out[-1]["end"]).days <= 1:
            cur = out[-1]
            cur["end"] = max(cur["end"], r["end"])
            cur["score"] += r["score"]
            cur["assessments"] = cur["assessments"] + r["assessments"]
        else:
            out.append(dict(r, assessments=list(r["assessments"])))
    return out


def _agree_with_feed(ctx: TopicContext, key: str, today: date, per: dict, scale: str,
                     opens: list, cares: list) -> Tuple[list, list]:
    """A long read lists the SAME windows the Windows feed does: the feed unions the month, season and
    year scans, so the long read folds in the scales it did not scan itself (clipped to its own period)."""
    for sc in ("month", "season", "year"):
        if sc == scale:
            continue
        try:
            p2 = _period(ctx, sc, today, "en")
            res = _scan(ctx, key, sc, p2, today)
            o2, c2 = _runs(res, "open"), _runs(res, "care")
            if sc == "month":
                _fold_in_today(ctx, key, today, o2, c2)
            opens, cares = opens + o2, cares + c2
        except Exception:
            logger.exception("[topic-read] %s scan for %s skipped", sc, key)
    out = []
    for lst in (opens, cares):
        clipped = []
        for r in lst:
            if r["start"] > per["end"]:
                continue
            clipped.append(dict(r, end=min(r["end"], per["end"])))
        out.append(_merge_runs(clipped))
    return out[0], out[1]


def _lead_run(runs: List[dict], today: date) -> Optional[dict]:
    """The window a long read leads with: the one running now (if it has days left), else the soonest
    to start; None when all that exists is a window about to end. A later, stronger window is mentioned
    separately."""
    live = [r for r in runs if r["start"] <= today <= r["end"] and (r["end"] - today).days >= MIN_LEAD_DAYS - 1]
    if live:
        return min(live, key=lambda r: r["start"])
    upcoming = [r for r in runs if r["start"] > today]
    if upcoming:
        return min(upcoming, key=lambda r: r["start"])
    return None   # only a window about to end: not a headline for a long read


def _peak(r: dict) -> float:
    return max((a["score"] for a in r["assessments"]), default=0.0)


def _fold_in_today(ctx: TopicContext, key: str, today: date, opens: list, cares: list) -> None:
    """The 30-day read starts today: a window that is lit today is part of it. The weekly buckets can
    miss it (a lit day inside a quiet week), which let the month say 'nothing sharp' next to a
    Right-now read that is open. Extend an adjoining run back to today, or add today as its own."""
    try:
        a = assess(ctx, key, today, ctx.events(today - timedelta(days=1), today + timedelta(days=2), True))
    except Exception:
        return
    if not (a.get("lit") and a.get("mode") in ("open", "care")):
        return
    lst = opens if a["mode"] == "open" else cares
    if any(r["start"] <= today <= r["end"] for r in lst):
        return
    near = next((r for r in lst if 0 < (r["start"] - today).days <= 7), None)
    if near:
        near["start"] = today
        near["assessments"].append(a)
        near["score"] += a["score"]
    else:
        lst.append({"start": today, "end": today, "score": a["score"], "assessments": [a]})


def _span_out(per: dict) -> Optional[dict]:
    return dict(per["span"]) if per.get("span") else None


def _lead(lang: str, scale: str, per: Optional[dict]) -> str:
    if scale == "chapter":
        return C.pick(C.CHAPTER_LEAD, lang)
    if scale == "season" and per and per.get("span"):
        return C.season_text(C.SPAN_LEAD_SEASON, lang, per["span"])
    return C.pick(C.SPAN_LEAD, lang)[scale]


def _period(ctx: TopicContext, scale: str, today: date, lang: str) -> dict:
    """The dated frame for a scale (always >= today at its start for windows)."""
    approx = False
    if scale == "today":
        s = e = today
    elif scale == "month":
        s, e = today, today + timedelta(days=29)
    elif scale == "season":
        s, e = None, None
        for r in (ctx.dashas or {}).get("vimsottari", []) or []:
            lv = str(r.get("level") or "").lower()
            rs, re_ = str(r.get("start_date") or r.get("start") or "")[:10], str(r.get("end_date") or r.get("end") or "")[:10]
            if lv.startswith("antar") and rs <= today.isoformat() <= re_:
                s, e = date.fromisoformat(rs), date.fromisoformat(re_)
                break
        if e is None or e < today:
            s, e, approx = today, today + timedelta(days=180), True
    else:  # year = the solar-return year
        try:
            from antar_engine.jyotish_periods import year_period
            ys, ye, _ = year_period(ctx.birth_date, today)
            s, e = date.fromisoformat(ys), date.fromisoformat(ye)
        except Exception:
            s, e, approx = today, today + timedelta(days=364), True
    if scale == "chapter":   # the whole current major period; the stretch label is the secondary line
        s, e, approx = None, None, False
        for r in (ctx.dashas or {}).get("vimsottari", []) or []:
            lv = str(r.get("level") or "").lower()
            rs, re_ = str(r.get("start_date") or r.get("start") or "")[:10], str(r.get("end_date") or r.get("end") or "")[:10]
            if lv.startswith("maha") and rs <= today.isoformat() <= re_:
                s, e = date.fromisoformat(rs), date.fromisoformat(re_)
                break
        if e is None or e < today:
            s, e, approx = today, today + timedelta(days=365), True
        return {"start": s, "end": e, "approximate": approx, "span": None,
                "label": C.pick(C.CHAPTER_LABEL_WHOLE, lang).format(end=C.month_year_short(e, lang)),
                "chip": C.pick(C.CHIP, lang)["chapter"], "rung": "chapter"}
    pl = C.PERIOD_LABEL[lang][scale]
    span = None
    if scale == "season":
        span = C.span_info(today, e)
        far = e > C.add_months(today, LABEL_YEAR_MONTHS)
        span_label = C.season_text(C.SPAN_TEXT, lang, span)
        if far:   # long stretch: the end date is secondary info
            span_label = C.pick(C.SPAN_END, lang).format(span=span_label, end=C.month_year_short(e, lang))
        return {"start": s, "end": e, "approximate": approx, "span": span, "span_label": span_label,
                "label": C.pick(C.CHAPTER_LABEL, lang).format(end=C.month_year_short(e, lang)),
                "chip": C.pick(C.CHIP, lang)["season"], "rung": "stretch"}
    if scale == "year":
        bday = e + timedelta(days=1)   # the year runs birthday to the day before the next one
        return {"start": s, "end": e, "approximate": approx, "label": pl, "span": None,
                "chip": C.year_chip(s, bday, lang), "rung": "year"}
    label = pl
    return {"start": s, "end": e, "approximate": approx, "label": label, "span": span,
            "chip": C.pick(C.CHIP, lang)[scale], "rung": C.RUNG_BY_SCALE[scale]}


def _period_extra(per: dict) -> dict:
    out = {"chip": per.get("chip"), "rung": per.get("rung")}
    if per.get("span_label"):
        out["span_label"] = per["span_label"]
    return out


def _rung_order(ctx: TopicContext, today: date, lang: str) -> list:
    ends = {}
    for sc in ("year", "season"):
        try:
            ends[sc] = _period(ctx, sc, today, lang)["end"]
        except Exception:
            ends[sc] = None
    return C.rung_order(ends["year"], ends["season"])


def _scan(ctx: TopicContext, key: str, scale: str, per: dict, today: date) -> List[Tuple[Tuple[date, date], dict]]:
    ws, we = max(per["start"], today), per["end"]
    if scale == "today":
        ev = ctx.events(today - timedelta(days=1), today + timedelta(days=2), True)
        return [((today, today), assess(ctx, key, today, ev))]
    if scale == "month":
        ev = ctx.events(ws, we, False)
        step = 7
    else:
        we_scan = min(we, today + timedelta(days=SEASON_SCAN_CAP_DAYS))
        ev = ctx.events(ws, we_scan, False)
        we, step = we_scan, 30
    return [(b, _assess_bucket(ctx, key, b, ev)) for b in _bucket_ranges(ws, we, step)]


# ── reasoning ────────────────────────────────────────────────────────────────
def _confidence(ctx: TopicContext, a: dict) -> str:
    families = (a["dasha_kind"] == "core") + bool(a["chara_confirm"]) + (a["n_signals"] >= 1)
    level = "high" if families >= 3 else "medium" if families == 2 else "low"
    tq = ctx.time_quality
    if tq == "unknown":
        return "low"
    if tq == "approximate" and level == "high":
        return "medium"
    return level


def _reasoning(ctx: TopicContext, key: str, a: dict, scale: str, lang: str,
               w_start: Optional[date] = None, w_end: Optional[date] = None) -> dict:
    B, area = C.pick(C.WHY_BULLET, lang), C.pick(C.AREA, lang)[key]
    bullets: List[str] = []
    if a["dasha_kind"] == "core":
        bullets.append(B["chapter_core"].format(area=area))
    elif a["dasha_kind"] == "theme":
        bullets.append(B["chapter_theme"].format(area=area))
    if a["chara_confirm"]:
        bullets.append(B["agree"])
    if a["n_signals"] and w_start and w_end:
        sfx = "_day" if w_start == w_end else ""   # one day reads "on Oct 7", never "between Oct 7 and Oct 7"
        tmpl = B[("signals_care" if a["mode"] == "care" else "signals_open") + sfx]
        bullets.append(tmpl.format(n=a["n_signals"], area=area,
                                   start=C.day_label(w_start, lang), end=C.day_label(w_end, lang)))
    elif not a["n_signals"]:
        bullets.append(B["none_dated"])
    if ctx.time_quality == "approximate":
        bullets.append(B["approx_time"])
    elif ctx.time_quality == "unknown":
        bullets.append(B["no_time"])
    bo = C.pick(C.BASED_ON, lang)
    # one chip per family that counted toward _confidence, so chips == the confidence's reasons
    based: List[dict] = []
    if a["dasha_kind"] == "core":
        based.append({"label": bo["chapter"], "view": "chapter"})
    if a["chara_confirm"]:
        based.append({"label": bo["second"], "view": "second"})
    if a["n_signals"] >= 1:
        view = {"today": "today", "month": "month", "season": "dated", "year": "year"}[scale]
        based.append({"label": bo["dated"], "view": view})
    if not based:
        based.append({"label": bo["chapter"], "view": "chapter"})
    level = _confidence(ctx, a)
    return {"bullets": bullets, "based_on": based,
            "confidence": {"level": level, "note": C.pick(C.CONFIDENCE_NOTE, lang)[level]}}


# ── remedy ───────────────────────────────────────────────────────────────────
def _chart_gem(ctx: TopicContext) -> Optional[dict]:
    try:
        from antar_engine.practice_engine import select_chart_gemstone
        return select_chart_gemstone((ctx.chart_data or {}).get("planets") or {},
                                     (ctx.chart_data or {}).get("lagna"))
    except Exception:
        return None


def remedy_planet(ctx: TopicContext, key: str, today: date, gem: Optional[dict] = None) -> str:
    """The ONE planet a topic's remedy speaks for: the running chapter ∩ the topic's
    key planets. When the chart's own stone planet is among those, it wins, so the
    mantra and the stone can agree; with no overlap, the topic's first key planet."""
    vim = _vim_active_planets(ctx.dashas, today.isoformat())
    kar = TOPIC_SPEC[key]["karakas"]
    hits = [p for p in kar if p in vim]
    if gem and gem.get("_planet") in hits:
        return gem["_planet"]
    return hits[0] if hits else kar[0]


def build_remedy(ctx: TopicContext, key: str, today: date, lang: str) -> dict:
    """{summary, steps[]} — free steps first, a stone only as an optional last
    step, never a price. The mantra and the stone are for the SAME planet: the
    chart-level stone engine cannot be pointed at an arbitrary planet (a planet
    that works against the lagna is never offered as a stone), so when its planet
    is not the remedy planet the stone step is dropped rather than mismatched."""
    steps = [{"kind": "practice", "optional": False, "text": t}
             for t in C.pick(C.FREE_STEPS, lang)[key]]
    gem = _chart_gem(ctx)
    try:
        planet = remedy_planet(ctx, key, today, gem)
    except Exception:
        planet = None
    if planet:
        try:
            from antar_engine.practice_library import get_planet_content
            name = ((get_planet_content(planet, "en") or {}).get("mantra") or {}).get("name")
            if name:
                steps.append({"kind": "mantra", "optional": True,
                              "text": C.pick(C.MANTRA_STEP, lang).format(name=name)})
        except Exception:
            pass
        if gem and gem.get("stone") and gem.get("_planet") == planet:
            steps.append({"kind": "stone", "optional": True,
                          "text": C.pick(C.STONE_STEP, lang).format(stone=gem["stone"])})
    return {"summary": C.pick(C.REMEDY_SUMMARY, lang), "steps": steps}


# ── the read ─────────────────────────────────────────────────────────────────
def chara_dependent(a: dict) -> bool:
    """[audit 2026-10-08] True when this read leans on the second (Jaimini chara) timeline for being 'lit' at all: without its
    points the score would fall under the activity bar, or an 'opportunity' rests on dasha-core + chara convergence with no
    dated signal. Measured over all real charts: 56% of lit topics were lit only because of chara, and every 'high' confidence
    depended on it. Recorded with each claim so the check-backs can say whether those reads hold as often as the rest. It
    changes NO score, tone or wording."""
    try:
        if not a.get("lit"):
            return False
        return bool((a["score"] - a.get("chara_pts", 0.0)) < ACTIVE_MIN or (a.get("convergence") and not a.get("n_signals")))
    except Exception:
        return False


STRONGER_RATIO = 1.15   # a later window leads the second sentence only if its peak beats the lead by this much
SOON_DAYS = 14   # a window starting within this many days is "soon"


def window_phase(start: date, end: date, today: date) -> str:
    """now = running today; soon = opens within SOON_DAYS; later = opens further out."""
    if start <= today <= end:
        return "now"
    return "soon" if (start - today).days <= SOON_DAYS else "later"


def _window_obj(ctx, key, run, scale, lang, kind, whole_label: bool = False, today: Optional[date] = None,
                span: Optional[dict] = None) -> dict:
    s, e = run["start"], run["end"]
    a = max(run["assessments"], key=lambda x: x["score"])
    a = dict(a, n_signals=sum(x["n_signals"] for x in run["assessments"]))
    whole = (C.season_text(C.WHOLE_SEASON, lang, span) if scale == "season" and span
             else C.pick(C.WHOLE_SPAN, lang)[scale])
    label = (C.pick(C.WINDOW_LABEL, lang)["whole"].format(span=whole)
             if whole_label else C.range_label(s, e, lang))
    return {"start": s.isoformat(), "end": e.isoformat(), "label": label,
            "window_phase": window_phase(s, e, today) if today else None,
            "reasoning": _reasoning(ctx, key, a, scale, lang, s, e),
            "evidence": {"chara_dependent": chara_dependent(a), "dated_signals": a.get("n_signals", 0)}}


def read_topic(ctx: TopicContext, key: str, scale: str, today: date, language: str = "en",
                with_best_fit: bool = True) -> dict:
    """One topic at one time scale. Final strings and dates; never raises for a
    valid key/scale (degrades to an honest steady read, no windows)."""
    try:
        return _read_topic(ctx, key, scale, today, language, with_best_fit)
    except Exception:
        logger.exception("[topic-read] engine failed → steady fallback")
        lang = C.serve_language(language)
        per_fb = None
        try:
            per = per_fb = _period(ctx, scale, today, lang)
            period = {"start": per["start"].isoformat(), "end": per["end"].isoformat(),
                      "label": per["label"], "approximate": True, "span": _span_out(per),
                      **_period_extra(per)}
        except Exception:
            period = {"start": today.isoformat(), "end": today.isoformat(),
                      "label": C.PERIOD_LABEL[lang]["today"], "approximate": True,
                      "chip": C.pick(C.CHIP, lang)["today"], "rung": "now"}
        note = C.pick(C.CONFIDENCE_NOTE, lang)["low"]
        try:
            remedy = build_remedy(ctx, key, today, lang)
        except Exception:
            remedy = {"summary": C.pick(C.REMEDY_SUMMARY, lang), "steps": []}
        return {"chart_id": ctx.chart_id, "topic": key, "label": C.LABEL[lang][key],
                "scale": scale, "language": lang, "as_of": today.isoformat(), "period": period,
                "tone": "steady",
                "claim": C.pick(C.LEAD_JOIN, lang).format(
                    lead=_lead(lang, scale, per_fb),
                    core=C.pick(C.STEADY_CORE, lang).format(area=C.pick(C.AREA, lang)[key])),
                "best_window": None, "watch_window": None,
                "why": C.pick(C.WHY_BULLET, lang)["none_dated"],
                "your_move": C.pick(C.MOVE, lang)[key]["steady"], "confidence_note": note,
                "reasoning": {"bullets": [C.pick(C.WHY_BULLET, lang)["none_dated"]],
                              "based_on": [{"label": C.pick(C.BASED_ON, lang)["chapter"], "view": "chapter"}],
                              "confidence": {"level": "low", "note": note}},
                "remedy": remedy, "best_fit_scale": "season", "window_phase": None}


def _read_topic(ctx: TopicContext, key: str, scale: str, today: date, language: str,
                with_best_fit: bool) -> dict:
    lang = C.serve_language(language)
    per = _period(ctx, scale, today, lang)
    view_scale, scale = scale, ("season" if scale == "chapter" else scale)   # the chapter scans like the long stretch
    area = C.pick(C.AREA, lang)[key]
    best = watch = strongest = None
    mode = "steady"
    a_main = assess(ctx, key, today, [])
    try:
        results = _scan(ctx, key, scale, per, today)
        opens, cares = _runs(results, "open"), _runs(results, "care")
        if scale == "month":
            _fold_in_today(ctx, key, today, opens, cares)
        long_scale = scale in ("season", "year")
        if long_scale:
            opens, cares = _agree_with_feed(ctx, key, today, per, scale, opens, cares)
        # a window may only start today or later, and only if it has not ended
        for lst in (opens, cares):
            for r in list(lst):
                c = clamp_window(r["start"], r["end"], today)
                if c is None:
                    lst.remove(r)
                else:
                    r["start"], r["end"] = c
        if scale == "month":   # a single day is not the headline of a 30-day read (the Windows feed still lists it)
            opens = [r for r in opens if r["start"] != r["end"]]
            cares = [r for r in cares if r["start"] != r["end"]]
        pick_run = (lambda rs: _lead_run(rs, today)) if long_scale else _best_run
        br, wr = pick_run(opens), pick_run(cares)
        whole = lambda r: (r["start"], r["end"]) == (max(per["start"], today), per["end"]) and scale != "today"
        if br:
            best = _window_obj(ctx, key, br, scale, lang, "best", whole_label=whole(br), today=today, span=per.get("span"))
        a_main = max((a for _, a in results), key=lambda x: x["score"]) if results else a_main
        if wr:
            watch = _window_obj(ctx, key, wr, scale, lang, "watch", whole_label=whole(wr), today=today, span=per.get("span"))
            if not br:
                a_main = max(wr["assessments"], key=lambda x: x["score"])
        care_first = bool(long_scale and br and wr and wr["start"] < br["start"])   # a long read leads with whichever window comes first
        if br and not care_first:
            a_main = max(br["assessments"], key=lambda x: x["score"])
        mode = "open" if best and not care_first else "care" if watch else "steady"
        if long_scale:   # a later, clearly stronger window rides along as a second sentence
            lead_r, lead_kind = (br, "open") if mode == "open" else (wr, "care") if mode == "care" else (None, None)
            pool = opens if lead_kind == "open" else cares
            top = _best_run(pool) if lead_r else None
            if top and top is not lead_r and top["start"] > lead_r["end"] and _peak(top) >= _peak(lead_r) * STRONGER_RATIO:
                strongest = _window_obj(ctx, key, top, scale, lang, lead_kind, today=today, span=per.get("span"))
    except Exception:
        logger.exception("[topic-read] scan failed → steady read")
        best = watch = strongest = None
        mode = "steady"

    lead = _lead(lang, view_scale, per)
    core = (C.pick(C.CORE, lang)[key][mode] if mode in ("open", "care")
            else C.pick(C.STEADY_CORE, lang).format(area=area))
    primary = best if mode == "open" else watch if mode == "care" else None
    phase = primary["window_phase"] if primary else None
    your_move = C.pick(C.MOVE, lang)[key][mode]
    if phase in ("soon", "later"):
        # the window is still ahead: name when it opens and make the move a prepare step
        when = date.fromisoformat(primary["start"])
        dlab = C.day_label(when, lang) if when.year == today.year else C.day_label_y(when, lang)
        core = C.pick(C.CORE_AHEAD, lang)[key][mode].format(date=dlab)
        your_move = C.pick(C.MOVE_AHEAD, lang)[key][mode].format(date=dlab)
    claim = C.pick(C.LEAD_JOIN, lang).format(lead=lead, core=core)
    if strongest and mode in ("open", "care"):
        claim = f"{claim.rstrip()} " + C.pick(C.STRONGEST_TAIL, lang)[mode].format(
            start=C.day_label_y(date.fromisoformat(strongest["start"]), lang),
            end=C.day_label_y(date.fromisoformat(strongest["end"]), lang))
    # the top-level reasoning is the PRIMARY window's own (the one `tone` names);
    # the other window keeps its own distinct reasoning
    if primary:
        reasoning = copy.deepcopy(primary["reasoning"])
    else:
        reasoning = _reasoning(ctx, key, dict(a_main, mode=mode), scale, lang, None, None)
    why = " ".join(reasoning["bullets"][:2])
    out = {
        "chart_id": ctx.chart_id, "topic": key, "label": C.LABEL[lang][key],
        "scale": view_scale, "language": lang, "as_of": today.isoformat(),
        "rung_order": _rung_order(ctx, today, lang),
        "period": {"start": per["start"].isoformat(), "end": per["end"].isoformat(),
                   "label": per["label"], "approximate": per["approximate"], "span": _span_out(per),
                   **_period_extra(per)},
        "tone": mode,
        "claim": claim,
        "best_window": best,
        "watch_window": watch,
        "strongest_window": strongest,
        "why": why,
        "window_phase": phase,
        "your_move": your_move,
        "confidence_note": reasoning["confidence"]["note"],
        "reasoning": reasoning,
        "remedy": build_remedy(ctx, key, today, lang),
    }
    if view_scale == "chapter":   # the stretch label stays as the secondary line inside the chapter rung
        try:
            out["period"]["stretch_label"] = _period(ctx, "season", today, lang)["span_label"]
        except Exception:
            pass
    if with_best_fit:
        out["best_fit_scale"] = best_fit_scale(ctx, key, today)
    return out


def windows_for(ctx: TopicContext, key: str, scale: str, today: date) -> dict:
    """[circle] EVERY dated open / care run for one topic at one scale - the same scan,
    bucketing, run-merging and never-in-the-past clamp `read_topic` uses, but returning all
    the runs instead of only the strongest. The Circle pair page intersects two charts'
    runs, so it needs more than each chart's single best window. No new astrology: this
    only exposes what `_read_topic` already computes. Never raises (degrades to no runs).

    -> {"period_end": date, "approximate": bool,
        "open": [{"start": date, "end": date, "confidence": "high|medium|low"}],
        "care": [...same...]}"""
    out = {"period_end": today, "approximate": True, "open": [], "care": []}
    try:
        per = _period(ctx, scale, today, "en")
        out["period_end"], out["approximate"] = per["end"], per["approximate"]
        results = _scan(ctx, key, scale, per, today)
        by_mode = {"open": _runs(results, "open"), "care": _runs(results, "care")}
        if scale == "month":
            _fold_in_today(ctx, key, today, by_mode["open"], by_mode["care"])
        elif scale in ("season", "year"):
            by_mode["open"], by_mode["care"] = _agree_with_feed(ctx, key, today, per, scale,
                                                                 by_mode["open"], by_mode["care"])
        for mode, name in (("open", "open"), ("care", "care")):
            for r in by_mode[mode]:
                c = clamp_window(r["start"], r["end"], today)
                if c is None:
                    continue
                a = max(r["assessments"], key=lambda x: x["score"])
                out[name].append({"start": c[0], "end": c[1], "confidence": _confidence(ctx, a)})
    except Exception:
        logger.exception("[topic-windows] scan failed -> no runs")
        out["open"], out["care"] = [], []
    return out


def _best_fit(ctx: TopicContext, key: str, today: date) -> Tuple[str, Optional[dict]]:
    """(scale, that scale's read): the nearest scale with a real dated window, preferring
    one that starts within 12 months over a far one. With none anywhere, an honest steady season read."""
    season = far = None
    for scale in ("today", "month", "season", "year"):
        try:
            r = read_topic(ctx, key, scale, today, "en", with_best_fit=False)
        except Exception:
            ctx.degraded = True
            continue
        if scale == "season":
            season = r
        if r["best_window"] or r["watch_window"]:
            w = r["best_window"] if r["tone"] == "open" else r["watch_window"]
            if _is_far(date.fromisoformat(w["start"]), today):
                far = far or (scale, r)   # keep looking for a nearer window on a later scale
                continue
            return scale, r
    # only far windows: the nearest scale that shows one; the tile tag carries the timing
    return far or ("season", season)


def best_fit_scale(ctx: TopicContext, key: str, today: date) -> str:
    """The scale the UI should open on: the nearest one with a real dated window."""
    return _best_fit(ctx, key, today)[0]


def _tile_read(ctx: TopicContext, key: str, today: date) -> Tuple[str, Optional[dict]]:
    """(tone, read) of topic-read(scale=best_fit_scale) — the one place a tile's
    colour and wording come from. read is None on the steady fallback."""
    try:
        scale, r = _best_fit(ctx, key, today)
        if r is None:
            r = read_topic(ctx, key, scale, today, "en", with_best_fit=False)
        return r["tone"], r
    except Exception:
        return "steady", None


def topic_tone(ctx: TopicContext, key: str, today: date) -> str:
    """open|care|steady — exactly topic-read(scale=best_fit_scale).tone, so a tile
    and the read it opens can never disagree."""
    return _tile_read(ctx, key, today)[0]


# ── small TTL cache (per process) ────────────────────────────────────────────
_CACHE: Dict[Any, Tuple[float, Any]] = {}
_LOCK = threading.Lock()
_MAX = 2000


def cache_get(key):
    with _LOCK:
        hit = _CACHE.get(key)
        if hit and hit[0] > time.time():
            return json.loads(hit[1])
    return None


def cache_put(key, value, ttl: int):
    with _LOCK:
        if len(_CACHE) >= _MAX:
            _CACHE.clear()
        _CACHE[key] = (time.time() + ttl, json.dumps(value))


def cache_clear():
    with _LOCK:
        _CACHE.clear()
