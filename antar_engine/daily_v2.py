"""
antar_engine/daily_v2.py — new /predict/daily contract assembler
=================================================================

Produces the JSON shape the Daily brief specifies, layered on top of the
existing endpoint output (additive, not breaking). Frontend reads the
new fields; legacy clients keep working until Lovable migrates.

Contract (brief, verbatim):
  {
    "date":            "YYYY-MM-DD",
    "day_label":       "MON · JUN 8",
    "verdict_headline": "...",
    "strength":         0..100,
    "strength_note":    "...",
    "windows": [
      {"type":"best", "start":"HH:MM","end":"HH:MM","text":"..."},
      {"type":"avoid","start":"HH:MM","end":"HH:MM","text":"..."}
    ],
    "domains": [
      {"key":"mind",  "name":"Mind",  "state":"favorable|caution|steady","line":"..."},
      {"key":"body",  "name":"Body",  ...},
      {"key":"work",  "name":"Work",  ...},
      {"key":"money", "name":"Money", ...},
      {"key":"people","name":"People",...}
    ]
  }

By construction:
  * `domains` is always exactly five — one slot per domain — last-write-
    wins inside the composer. Impossible to emit two of the same.
  * `windows` come from the existing hora_engine at the user's location.
  * `strength` is the score_day(today) score (0..100).
  * No remedy is included — brief: "Today has no remedy".
  * Sanskrit/planet/house leaks scrubbed by apply_user_facing_strips.
"""
from __future__ import annotations

from datetime import date as _date, datetime as _dt, timedelta as _td, timezone as _tz
from typing import Any, Dict, List, Optional


_DOMAIN_LABELS = {
    "mind":   "Mind",
    "body":   "Body",
    "work":   "Work",
    "money":  "Money",
    "people": "People",
}
_DOMAIN_ORDER = ("mind", "body", "work", "money", "people")

# Per-domain plain-language line per state. The composer overrides these
# with chart-specific lines when score_day produced a strong bias on that
# domain (i.e. when there's actually something to say beyond the state).
_STATE_LINES = {
    "favorable": {
        "mind":   "Your head runs clear today — write, decide, work the hard thinking.",
        "body":   "Body holds up well today — a good day for movement and routine care.",
        "work":   "Work rewards visible effort today — push the thing that matters.",
        "money":  "Money matters carry tailwind today — chase what you're owed, send invoices.",
        "people": "People respond warmly today — make the ask, mend the rift, reach out.",
    },
    "caution": {
        "mind":   "Judgment is foggier than usual today — avoid choices that need a sharp head.",
        "body":   "Don't overexert physically today — your reserves are lower than they feel.",
        "work":   "Don't force big work commitments today — execution yes, decisions later.",
        "money":  "Hold off on new spending or speculative money moves today — timing isn't with you.",
        "people": "Go easy in tense conversations today — postpone confrontation if you can.",
    },
    "steady": {
        "mind":   "Mental texture is steady today — focused, ordinary work moves things.",
        "body":   "Body is steady today — keep the habit, don't push past warning signs.",
        "work":   "Work is steady today — protect blocks of focus time, ship small things.",
        "money":  "Money is quiet today — no big moves needed; tend the cushion.",
        "people": "Relationships are calm today — short, warm touches are enough.",
    },
}


def _strength_note(score: int, states: Dict[str, str]) -> str:
    """[dv2-polish 2026-06-08] Human subtitle — no raw counts, no clinical
    labels ('favorable' / 'need care'). A friend's day-mood phrase."""
    cau = sum(1 for v in states.values() if v == "caution")
    if score >= 75:
        if cau == 0:
            return "A strong day across the board"
        if cau == 1:
            return "Strong day — one area to protect"
        return "Strong day — a couple of areas to protect"
    if score >= 60:
        if cau == 0:
            return "A supportive day — lean in"
        if cau == 1:
            return "A supportive day — one area to protect"
        return "A supportive day — a couple of areas to protect"
    if score >= 45:
        if cau == 0:
            return "A steady, ordinary day"
        if cau == 1:
            return "Mixed day — one area needs care"
        return "Mixed day — a few areas need care"
    if score >= 30:
        return "Lower-energy day — protect the basics"
    return "Protect-mode day — keep things light"


def _day_label(d: _date) -> str:
    """'MON · JUN 8' format — uppercase 3-letter weekday + month."""
    wk = d.strftime("%a").upper()
    mo = d.strftime("%b").upper()
    return f"{wk} · {mo} {d.day}"


# [dv2-polish 2026-06-08] Domain-keyed plain phrases. No 'X energy'
# anywhere; each phrase reads as a sentence fragment a friend would say.
_DOMAIN_PUSH_PHRASE = {
    "mind":   "your head is sharp — write, decide, work the hard thinking",
    "body":   "your body is willing — move, train, stay outside",
    "work":   "the work moves today — push the visible thing",
    "money":  "money matters carry tailwind — chase what you're owed",
    "people": "people respond warmly — make the ask, reach out",
}
_DOMAIN_GUARD_PHRASE = {
    "mind":   "your head's a little foggy — don't make sharp calls",
    "body":   "your body's tired — pull back, don't push through",
    "work":   "work runs heavier — execute, defer the big decisions",
    "money":  "money runs tight — hold off on new spending",
    "people": "relationships are tender — listen more, react less",
}


def _verdict_headline(score: int, states: Dict[str, str]) -> str:
    """[dv2-polish 2026-06-08] Plain-language headline. No 'X energy'
    calque pattern. Uses domain-keyed phrase banks instead of f-string
    interpolation on the bare slot name."""
    strong = [d for d in _DOMAIN_ORDER if states.get(d) == "favorable"]
    soft   = [d for d in _DOMAIN_ORDER if states.get(d) == "caution"]
    if score >= 70 and strong:
        push = _DOMAIN_PUSH_PHRASE.get(strong[0], "push the thing that matters")
        if not soft:
            return f"A high-energy day — {push}."
        guard = _DOMAIN_GUARD_PHRASE.get(soft[0], "protect the rest")
        return f"Strong day — {push}; {guard}."
    if score >= 55 and strong:
        push = _DOMAIN_PUSH_PHRASE.get(strong[0], "lean into the steady work")
        if soft:
            guard = _DOMAIN_GUARD_PHRASE.get(soft[0], "go easy elsewhere")
            return f"Use the lift — {push}; {guard}."
        return f"A supportive day — {push}."
    if score >= 40 and soft:
        guard = _DOMAIN_GUARD_PHRASE.get(soft[0], "protect what's tender")
        push  = (_DOMAIN_PUSH_PHRASE.get(strong[0]) if strong
                 else "lean on small wins")
        return f"Mixed day — {guard}; {push}."
    if soft:
        guard = _DOMAIN_GUARD_PHRASE.get(soft[0], "protect the basics")
        return f"Low-key day — {guard}, don't force decisions."
    return "A steady day — small, consistent moves outpace big bets."


def _format_time_hhmm(iso_or_local, tz_offset_hours: float = 0.0) -> str:
    """Best-effort HH:MM extractor.

    Accepts:
      ISO datetime ('2026-06-08T11:42:00Z' / '...+00:00')
      'HH:MM' or 'HH:MM AM' / 'HH:MM PM'
      'H:MM AM' / 'H:MM PM' (one-digit hour, from hora_engine output)
    Always returns 24-hour 'HH:MM' or '' on parse failure.
    """
    if not iso_or_local:
        return ""
    s = str(iso_or_local).strip()
    if not s:
        return ""
    s_upper = s.upper()
    is_pm = "PM" in s_upper
    is_am = "AM" in s_upper
    body = s_upper.replace("AM", "").replace("PM", "").strip()
    if "T" in body and ":" in body:
        try:
            dt = _dt.fromisoformat(body.replace("Z", "+00:00"))
            dt_local = dt + _td(hours=tz_offset_hours) if dt.tzinfo is None else dt
            return dt_local.strftime("%H:%M")
        except Exception:
            pass
    if ":" in body:
        try:
            parts = body.split(":")
            hh = int(parts[0])
            mm = int(parts[1][:2])
            if is_pm and hh < 12:
                hh += 12
            elif is_am and hh == 12:
                hh = 0
            return f"{hh:02d}:{mm:02d}"
        except Exception:
            return ""
    return ""


def _split_range_string(value, tz_offset_hours: float = 0.0):
    """[dv2-polish 2026-06-08] Split 'HH:MM AM – HH:MM PM' into
    ('HH:MM','HH:MM'). Accepts en-dash, em-dash, hyphen, or ' to '.
    Returns (None, None) on failure."""
    if not isinstance(value, str) or not value.strip():
        return None, None
    s = value.strip()
    for sep in (" \u2013 ", " \u2014 ", " - ", " to ", "\u2013", "\u2014", "-"):
        if sep in s:
            left, _, right = s.partition(sep)
            l = _format_time_hhmm(left.strip(), tz_offset_hours)
            r = _format_time_hhmm(right.strip(), tz_offset_hours)
            if l and r:
                return l, r
    return None, None


def _residence_tz_offset(chart_record: dict):
    """UTC offset of where the user LIVES NOW, DST-correct for today.

    Derived from the persisted `current_timezone` IANA id rather than stored as
    a number, because an offset is not a stable property of a place — it moves
    twice a year. `tz_offset_hours` on the chart is the BIRTH offset and is only
    a fallback: it is the wrong clock for anyone who has moved.
    """
    try:
        from antar_engine.tz_utils import iana_offset_hours
        off = iana_offset_hours(chart_record.get("current_timezone"))
        if off is not None:
            return float(off)
    except Exception:
        pass
    try:
        return float(chart_record.get("tz_offset_hours") or 0.0)
    except Exception:
        return 0.0


def _coerce_window_pair(value, tz_offset_hours: float = 0.0):
    """[dv2-polish 2026-06-08] Accept either a dict ({start,end} or
    {start_local,end_local}) OR a flat range string and return a uniform
    (start_hhmm, end_hhmm) tuple. (None, None) if unparseable."""
    if isinstance(value, dict):
        s = value.get("start") or value.get("start_local") or value.get("begin")
        e = value.get("end")   or value.get("end_local")   or value.get("finish")
        return (_format_time_hhmm(s, tz_offset_hours) or None,
                _format_time_hhmm(e, tz_offset_hours) or None)
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        return (_format_time_hhmm(value[0], tz_offset_hours) or None,
                _format_time_hhmm(value[1], tz_offset_hours) or None)
    if isinstance(value, str):
        return _split_range_string(value, tz_offset_hours)
    return None, None


def _build_windows_from_hora(hora_block: Dict[str, Any], tz_offset_hours: float = 0.0
                             ) -> List[Dict[str, Any]]:
    """[dv2-polish 2026-06-08] Pick best + avoid windows from the
    legacy /daily fields. abhijit / rahu_kalam may arrive as dicts OR
    as flat range strings ('11:42 AM – 12:30 PM') — both supported.
    Returns whatever it could parse; caller adds direct-hora fallback
    when this returns < 2 entries."""
    out: List[Dict[str, Any]] = []
    if not isinstance(hora_block, dict):
        return out

    # BEST: prefer abhijit, fall back to a current peak hora.
    best_value = (hora_block.get("abhijit")
                  or hora_block.get("abhijit_muhurta")
                  or hora_block.get("best_time"))
    bs, be = _coerce_window_pair(best_value, tz_offset_hours)
    if not (bs and be):
        cur = hora_block.get("current_hora") or {}
        if isinstance(cur, dict) and cur:
            bs, be = _coerce_window_pair(cur, tz_offset_hours)
    if bs and be:
        out.append({
            "type":  "best",
            "start": bs, "end": be,
            "text":  "Decide, pitch, ask — anything that matters.",
        })

    # AVOID: prefer rahu_kalam; honour avoid_time as a secondary.
    av_value = (hora_block.get("rahu_kalam")
                or hora_block.get("avoid_time")
                or hora_block.get("avoid_window"))
    avs, ave = _coerce_window_pair(av_value, tz_offset_hours)
    if avs and ave:
        out.append({
            "type":  "avoid",
            "start": avs, "end": ave,
            "text":  "Don't force decisions or hard talks here.",
        })

    return out


def _direct_hora_windows(chart_record: Dict[str, Any], target_date,
                          location_override = None,
                          ) -> List[Dict[str, Any]]:
    """[dv2-reqloc 2026-06-08] Compute best + avoid windows directly
    from the hora_engine + panchanga. When location_override is given,
    use those coords/tz literally (skip chart_record entirely) so the
    REQUEST's location drives the computation — not the chart's.
    Without override: current_country -> birth coords -> Delhi default,
    matching the chart-bound fallback chain."""
    out: List[Dict[str, Any]] = []
    try:
        from antar_engine.hora_engine import get_hora_schedule, get_next_power_hora
        from antar_engine.daily_panchanga import calculate_panchanga
        # [dv2-reqloc 2026-06-08] explicit override wins (request-bound
        # location); otherwise current_country/birth via chart_record.
        if isinstance(location_override, dict) and (
                location_override.get("lat") is not None
                and location_override.get("lng") is not None):
            lat = location_override.get("lat")
            lng = location_override.get("lng")
            tz_offset = location_override.get("tz_offset") or 0
        else:
            lat = (chart_record.get("current_latitude")
                   or chart_record.get("latitude") or 28.6)
            lng = (chart_record.get("current_longitude")
                   or chart_record.get("longitude") or 77.2)
            # Residence tz first. tz_offset_hours is the BIRTH offset, which is
            # the wrong clock for someone who has moved — it is only a fallback.
            tz_offset = _residence_tz_offset(chart_record)
        try:
            # NOT int(round(...)). Rounding to whole hours put every Indian user
            # on +6 instead of +5:30 and every Nepali user on +6 instead of
            # +5:45, shifting sunrise — and therefore the Vedic day boundary,
            # rahu kalam, abhijit and every clock window shown on the card — by
            # half an hour for the single largest group of users in the product.
            tz_offset = float(tz_offset)
        except Exception:
            tz_offset = 0.0
        # Best: prefer panchanga's abhijit (universally auspicious midday window).
        pan = calculate_panchanga(lat=float(lat), lng=float(lng),
                                  tz_offset=tz_offset, target_date=target_date) or {}
        ab = pan.get("abhijit") or pan.get("abhijit_muhurta")
        abs_s, abs_e = _coerce_window_pair(ab, 0.0)
        if abs_s and abs_e:
            out.append({
                "type":  "best",
                "start": abs_s, "end": abs_e,
                "text":  "Decide, pitch, ask — anything that matters.",
            })
        # Avoid: rahu_kalam from panchanga.
        rk = pan.get("rahu_kalam") or pan.get("avoid_time")
        rks_s, rks_e = _coerce_window_pair(rk, 0.0)
        if rks_s and rks_e:
            out.append({
                "type":  "avoid",
                "start": rks_s, "end": rks_e,
                "text":  "Don't force decisions or hard talks here.",
            })
        # Last resort: derive best from the next favorable hora.
        if not any(w.get("type") == "best" for w in out):
            sched = get_hora_schedule(float(lat), float(lng),
                                      tz_offset=tz_offset) or {}
            cur = sched.get("current_hora") or {}
            up  = sched.get("upcoming_horas") or []
            cand = up[0] if up else cur
            if isinstance(cand, dict) and cand.get("start_local"):
                out.append({
                    "type":  "best",
                    "start": _format_time_hhmm(cand.get("start_local")),
                    "end":   _format_time_hhmm(cand.get("end_local")),
                    "text":  "Use this window for anything that actually matters.",
                })
    except Exception as _hor_e:
        print(f"[daily_v2] direct hora fallback failed: {_hor_e}")
    return out


def _scrub_text(language: str, text: str, field_type: str = "plain") -> str:
    if not isinstance(text, str) or not text:
        return text
    try:
        from antar_engine.output_strips import apply_user_facing_strips
        return apply_user_facing_strips(text, language=(language or "en"),
                                        field_type=field_type)
    except Exception:
        return text


def _domains_v2(states: Dict[str, str], bias: Dict[str, float],
                language: str) -> List[Dict[str, Any]]:
    """Always exactly five slots, in canonical order. last-write-wins is
    enforced by the dict-of-states being closed to the five keys."""
    out: List[Dict[str, Any]] = []
    for key in _DOMAIN_ORDER:
        state = states.get(key, "steady")
        line  = (_STATE_LINES.get(state, _STATE_LINES["steady"]).get(key) or
                 _STATE_LINES["steady"][key])
        out.append({
            "key":   key,
            "name":  _DOMAIN_LABELS[key],
            "state": state,
            "line":  _scrub_text(language, line, "plain"),
        })
    return out


def compose_daily_contract(chart_id: str,
                           chart_record: Dict[str, Any],
                           legacy_response: Dict[str, Any],
                           language: str = "en",
                           target_date: Optional[_date] = None,
                           location_override: Optional[Dict[str, Any]] = None,
                           ) -> Dict[str, Any]:
    """
    Build the new daily contract on top of the existing endpoint output.

    Returns ONLY the new fields — caller merges into the legacy response.
    No remedy field is added. All text fields run through the central scrub.
    """
    language = (language or "en").split("-")[0].lower()
    if language not in ("en", "es", "pt"):
        language = "en"

    # Date the contract is anchored to.
    d = target_date or _date.today()
    if isinstance(d, _dt):
        d = d.date()

    chart_data = chart_record.get("chart_data") or {}
    if isinstance(chart_data, str):
        try:
            import json as _j
            chart_data = _j.loads(chart_data)
        except Exception:
            chart_data = {}

    # [dv2-reqloc 2026-06-08] If the request supplied a location
    # override ({lat,lng,tz}), use it for ALL location-dependent steps
    # below — sunrise/sunset, hora segments, score_day panchanga.
    # The chart-bound legacy abhijit/rahu_kalam are SKIPPED in this
    # path because they were computed at chart-record coords, not the
    # request location (the reason NJ and Mumbai were returning byte-
    # identical windows for the same chart).
    _req_loc = location_override if (
        isinstance(location_override, dict)
        and location_override.get("lat") is not None
        and location_override.get("lng") is not None
    ) else None
    # [lk-real-fix3 2026-06-08] Resolve CURRENT location with the same
    # priority chain every location-aware endpoint uses:
    #   1) caller-supplied current_latitude/current_longitude
    #   2) current_country -> country capital (when current != birth)
    #   3) birth latitude/longitude
    #   4) Delhi default (last resort — never empty)
    # We don't import main._resolve_moment_coords here (avoids circular
    # import) — inline the same priority chain. The chart_record fields
    # mirror what the helper sees.
    lat = lng = None
    _cur_lat = chart_record.get("current_latitude")
    _cur_lng = chart_record.get("current_longitude")
    if _cur_lat is not None and _cur_lng is not None:
        try:
            lat, lng = float(_cur_lat), float(_cur_lng)
        except (TypeError, ValueError):
            pass
    if lat is None or lng is None:
        _cc = (chart_record.get("current_country") or "").strip().upper()
        _bcc = (chart_record.get("birth_country")
                or chart_record.get("country_code") or "").strip().upper()
        if _cc and _cc != _bcc:
            try:
                from antar_engine.day_chart_engine import COUNTRY_COORDS as _CC
                if _cc in _CC:
                    lat, lng = _CC[_cc]
            except Exception:
                pass
    if lat is None or lng is None:
        try:
            lat = float(chart_record.get("latitude") or 28.6139)
            lng = float(chart_record.get("longitude") or 77.2090)
        except (TypeError, ValueError):
            lat, lng = 28.6139, 77.2090
    tz_offset_hours = 0.0
    try:
        tz_offset_hours = float(chart_record.get("tz_offset_hours") or 0.0)
    except Exception:
        tz_offset_hours = 0.0
    # [dv2-reqloc 2026-06-08] override wins for the location dict that
    # score_day will consume — panchanga + hora must reflect the user's
    # ACTUAL location, not the chart's stored coords.
    if _req_loc is not None:
        try:
            lat = float(_req_loc.get("lat"))
            lng = float(_req_loc.get("lng"))
        except (TypeError, ValueError):
            pass
        try:
            tz_offset_hours = float(_req_loc.get("tz_offset") or tz_offset_hours)
        except (TypeError, ValueError):
            pass
    location = {"lat": lat, "lng": lng, "tz_offset": tz_offset_hours}

    # ── score_day → strength + per-domain states ──
    try:
        from antar_engine.score_day import score_day
        sd = score_day(chart_data, d, location)
    except Exception:
        sd = {"score": 50, "domain_states": {k: "steady" for k in _DOMAIN_ORDER},
              "domain_bias": {k: 0.0 for k in _DOMAIN_ORDER}}

    states = {k: (sd.get("domain_states") or {}).get(k, "steady")
              for k in _DOMAIN_ORDER}
    bias   = {k: (sd.get("domain_bias")   or {}).get(k, 0.0)
              for k in _DOMAIN_ORDER}
    score  = int(sd.get("score") or 50)

    # [dv2-reqloc 2026-06-08] windows[] resolution order:
    #   1. REQUEST location override -> compute directly via
    #      _direct_hora_windows (panchanga at the override coords).
    #      Legacy chart-bound abhijit/rahu_kalam are SKIPPED here.
    #   2. No override -> try legacy parse (chart-bound), then fall
    #      back to _direct_hora_windows on the chart_record location.
    windows: List[Dict[str, Any]] = []
    if _req_loc is not None:
        try:
            windows = _direct_hora_windows(chart_record, d,
                                            location_override=_req_loc)
        except Exception as _reqfbe:
            print(f"[daily_v2] request-location windows failed: {_reqfbe}")
    else:
        _legacy_pan = (legacy_response.get("panchanga") or {}) if isinstance(legacy_response.get("panchanga"), dict) else {}
        windows = _build_windows_from_hora({
            "abhijit":    legacy_response.get("abhijit")    or _legacy_pan.get("abhijit"),
            "rahu_kalam": legacy_response.get("rahu_kalam") or _legacy_pan.get("rahu_kalam"),
            "best_time":  _legacy_pan.get("best_time"),
            "avoid_time": _legacy_pan.get("avoid_time"),
            "current_hora": (legacy_response.get("hora") or {}).get("current_hora")
                              if isinstance(legacy_response.get("hora"), dict) else None,
        }, tz_offset_hours=tz_offset_hours)
        _have_types = {w.get("type") for w in windows}
        if ("best" not in _have_types) or ("avoid" not in _have_types):
            try:
                _fb = _direct_hora_windows(chart_record, d)
                for _fw in _fb:
                    if _fw.get("type") not in _have_types:
                        windows.append(_fw)
                        _have_types.add(_fw.get("type"))
            except Exception as _fbe:
                print(f"[daily_v2] window fallback skipped: {_fbe}")

    # ── verdict_headline ──
    verdict = _verdict_headline(score, states)
    verdict = _scrub_text(language, verdict, "plain")

    contract: Dict[str, Any] = {
        "date":             d.isoformat(),
        "day_label":        _day_label(d),
        "verdict_headline": verdict,
        "strength":         score,
        "strength_note":    _scrub_text(language, _strength_note(score, states), "plain"),
        "windows":          windows,
        "domains":          _domains_v2(states, bias, language),
    }
    # Legacy `strength` may already be a string ("high"/"mid"/"low"); the
    # caller preserves it under "strength_label" and overwrites the
    # top-level "strength" with our int. This is a breaking change
    # consumers asked for — see the brief.
    return contract


__all__ = ["compose_daily_contract"]
