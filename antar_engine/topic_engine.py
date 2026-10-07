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
            try:
                from antar_engine.transit_events import compute_transit_events_in_range
                self._events_cache[key] = compute_transit_events_in_range(
                    self.chart_data, start, end, include_fast=fast) or []
            except Exception as e:  # swisseph missing → dasha-only, never an error
                logger.warning("[topics] transit feed skipped: %s", e)
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
             "tag": C.TAG[lang]["steady"], "tone": "steady", "rank": i + 1}
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


def _calm_tag(lang: str, tone: str, quiet: bool = False) -> str:
    """Tag for a tile that is not "active now": the wording follows the read's tone."""
    t = C.TAG[lang]
    return t["steady_open"] if tone == "open" else t["steady_care"] if tone == "care" \
        else t["quiet" if quiet else "steady"]


NEAR_DAYS = 2   # a window starting this soon is "now-ish", never "opens {month}"


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
                tag = C.TAG[lang]["care" if tone == "care" else "active"]
                order = (0, -(near[k][1] if k in promoted else a["score"]), i)
            elif a["lit"]:
                # really lit, but not among the chart's strongest: steady, not "now"
                status, tag = "steady", _calm_tag(lang, tone)
                order = (2, -a["score"], i)
            elif k in near:
                # its own read is already inside a window: near-term words, never "opens {month}"
                status = "steady"
                tag = C.TAG[lang]["care_soon" if tone == "care" else "open_soon"]
                order = (2, -near[k][1], i)
            else:
                win = _tile_window(tone, read)
                opening = _next_opening(ctx, k, today)
                # "upcoming" needs a real opening ahead AND, when the tile's read is known,
                # a window in THAT read: the month comes from it, so tag and read agree
                if opening and (win or read is None):
                    d, mode = (win[0], tone) if win else opening
                    status = "upcoming"
                    tag = C.TAG[lang]["care_from" if mode == "care" else "open"].format(
                        mon=C.month_name(d, lang))
                    order = (1, d.toordinal(), -a["score"], i)
                elif a["score"] >= STEADY_MIN:
                    status, tag = "steady", _calm_tag(lang, tone)
                    order = (2, -a["score"], i)
                else:
                    status, tag = "quiet", _calm_tag(lang, tone, quiet=True)
                    order = (3, -a["score"], i)
            rows.append((order, {"key": k, "label": C.LABEL[lang][k], "status": status, "tag": tag,
                                 "tone": tone}))
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
    pl = C.PERIOD_LABEL[lang][scale]
    label = pl.format(end=C.day_label(e, lang),
                      start=C.day_label_y(s, lang)) if scale != "year" else pl.format(
        end=C.day_label_y(e, lang), start=C.day_label_y(s, lang))
    return {"start": s, "end": e, "approximate": approx, "label": label}


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
    based: List[dict] = []
    if a["dasha_kind"]:
        based.append({"label": bo["chapter"], "view": "chapter"})
    view = {"today": "today", "month": "month", "season": "chapter", "year": "year"}[scale]
    if a["n_signals"] and view != "chapter":
        based.append({"label": bo[view], "view": view})
    if not based:
        based.append({"label": bo[view if view != "chapter" else "chapter"], "view": view})
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
def _window_obj(ctx, key, run, scale, lang, kind, whole_label: bool = False) -> dict:
    s, e = run["start"], run["end"]
    a = max(run["assessments"], key=lambda x: x["score"])
    a = dict(a, n_signals=sum(x["n_signals"] for x in run["assessments"]))
    label = (C.pick(C.WINDOW_LABEL, lang)["whole"].format(span=C.pick(C.WHOLE_SPAN, lang)[scale])
             if whole_label else C.range_label(s, e, lang))
    return {"start": s.isoformat(), "end": e.isoformat(), "label": label,
            "reasoning": _reasoning(ctx, key, a, scale, lang, s, e)}


def read_topic(ctx: TopicContext, key: str, scale: str, today: date, language: str = "en",
                with_best_fit: bool = True) -> dict:
    """One topic at one time scale. Final strings and dates; never raises for a
    valid key/scale (degrades to an honest steady read, no windows)."""
    try:
        return _read_topic(ctx, key, scale, today, language, with_best_fit)
    except Exception:
        logger.exception("[topic-read] engine failed → steady fallback")
        lang = C.serve_language(language)
        try:
            per = _period(ctx, scale, today, lang)
            period = {"start": per["start"].isoformat(), "end": per["end"].isoformat(),
                      "label": per["label"], "approximate": True}
        except Exception:
            period = {"start": today.isoformat(), "end": today.isoformat(),
                      "label": C.PERIOD_LABEL[lang]["today"], "approximate": True}
        note = C.pick(C.CONFIDENCE_NOTE, lang)["low"]
        try:
            remedy = build_remedy(ctx, key, today, lang)
        except Exception:
            remedy = {"summary": C.pick(C.REMEDY_SUMMARY, lang), "steps": []}
        return {"chart_id": ctx.chart_id, "topic": key, "label": C.LABEL[lang][key],
                "scale": scale, "language": lang, "as_of": today.isoformat(), "period": period,
                "tone": "steady",
                "claim": C.pick(C.LEAD_JOIN, lang).format(
                    lead=C.pick(C.SPAN_LEAD, lang)[scale],
                    core=C.pick(C.STEADY_CORE, lang).format(area=C.pick(C.AREA, lang)[key])),
                "best_window": None, "watch_window": None,
                "why": C.pick(C.WHY_BULLET, lang)["none_dated"],
                "your_move": C.pick(C.MOVE, lang)[key]["steady"], "confidence_note": note,
                "reasoning": {"bullets": [C.pick(C.WHY_BULLET, lang)["none_dated"]],
                              "based_on": [{"label": C.pick(C.BASED_ON, lang)["chapter"], "view": "chapter"}],
                              "confidence": {"level": "low", "note": note}},
                "remedy": remedy, "best_fit_scale": "season"}


def _read_topic(ctx: TopicContext, key: str, scale: str, today: date, language: str,
                with_best_fit: bool) -> dict:
    lang = C.serve_language(language)
    per = _period(ctx, scale, today, lang)
    area = C.pick(C.AREA, lang)[key]
    best = watch = None
    mode = "steady"
    a_main = assess(ctx, key, today, [])
    try:
        results = _scan(ctx, key, scale, per, today)
        opens, cares = _runs(results, "open"), _runs(results, "care")
        # a window may only start today or later, and only if it has not ended
        for lst in (opens, cares):
            for r in list(lst):
                c = clamp_window(r["start"], r["end"], today)
                if c is None:
                    lst.remove(r)
                else:
                    r["start"], r["end"] = c
        br, wr = _best_run(opens), _best_run(cares)
        whole = lambda r: (r["start"], r["end"]) == (max(per["start"], today), per["end"]) and scale != "today"
        if br:
            best = _window_obj(ctx, key, br, scale, lang, "best", whole_label=whole(br))
        a_main = max((a for _, a in results), key=lambda x: x["score"]) if results else a_main
        if wr:
            watch = _window_obj(ctx, key, wr, scale, lang, "watch", whole_label=whole(wr))
            if not br:
                a_main = max(wr["assessments"], key=lambda x: x["score"])
        if br:
            a_main = max(br["assessments"], key=lambda x: x["score"])
        mode = "open" if best else "care" if watch else "steady"
    except Exception:
        logger.exception("[topic-read] scan failed → steady read")
        best = watch = None
        mode = "steady"

    lead = C.pick(C.SPAN_LEAD, lang)[scale]
    core = (C.pick(C.CORE, lang)[key][mode] if mode in ("open", "care")
            else C.pick(C.STEADY_CORE, lang).format(area=area))
    claim = C.pick(C.LEAD_JOIN, lang).format(lead=lead, core=core)
    # the top-level reasoning is the PRIMARY window's own (the one `tone` names);
    # the other window keeps its own distinct reasoning
    primary = best if mode == "open" else watch if mode == "care" else None
    if primary:
        reasoning = copy.deepcopy(primary["reasoning"])
    else:
        reasoning = _reasoning(ctx, key, dict(a_main, mode=mode), scale, lang, None, None)
    why = " ".join(reasoning["bullets"][:2])
    out = {
        "chart_id": ctx.chart_id, "topic": key, "label": C.LABEL[lang][key],
        "scale": scale, "language": lang, "as_of": today.isoformat(),
        "period": {"start": per["start"].isoformat(), "end": per["end"].isoformat(),
                   "label": per["label"], "approximate": per["approximate"]},
        "tone": mode,
        "claim": claim,
        "best_window": best,
        "watch_window": watch,
        "why": why,
        "your_move": C.pick(C.MOVE, lang)[key][mode],
        "confidence_note": reasoning["confidence"]["note"],
        "reasoning": reasoning,
        "remedy": build_remedy(ctx, key, today, lang),
    }
    if with_best_fit:
        out["best_fit_scale"] = best_fit_scale(ctx, key, today)
    return out


def _best_fit(ctx: TopicContext, key: str, today: date) -> Tuple[str, Optional[dict]]:
    """(scale, that scale's read): the nearest scale with a real dated window.
    With none anywhere, an honest steady season read."""
    season = None
    for scale in ("today", "month", "season", "year"):
        try:
            r = read_topic(ctx, key, scale, today, "en", with_best_fit=False)
        except Exception:
            continue
        if scale == "season":
            season = r
        if r["best_window"] or r["watch_window"]:
            return scale, r
    return "season", season


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
