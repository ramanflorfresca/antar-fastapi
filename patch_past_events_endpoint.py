"""
patch_past_events_endpoint.py
==============================
Adds two endpoints to main.py:
  GET  /api/v1/chart/{chart_id}/past-events
  POST /api/v1/chart/{chart_id}/past-events/feedback

Uses landmark string search only. Idempotent.
"""

import shutil

TARGET = "main.py"
BAK    = TARGET + ".bak_past_events_endpoint"

shutil.copy2(TARGET, BAK)
print(f"[backup] {BAK}")

with open(TARGET, "r") as f:
    src = f.read()

# ── Guard: idempotency ───────────────────────────────────────────────────────
if '"/api/v1/chart/{chart_id}/past-events"' in src:
    print("[skip] past-events endpoint already present — nothing to do")
    exit(0)

# ── New endpoints block ──────────────────────────────────────────────────────
NEW_ENDPOINTS = '''

# ─────────────────────────────────────────────────────────────────────────────
# PAST-EVENTS: Signature verification screen
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/v1/chart/{chart_id}/past-events")
async def get_past_events(
    chart_id: str,
    min_confidence: int = 5,
    max_predictions: int = 5,
    authorization: Optional[str] = Header(None),
):
    """
    Returns high-confidence past-event predictions for the chart.
    Used by onboarding signature verification screen (Lovable).

    Query params:
      min_confidence : filter threshold 1-10 (default 5 = "moderate")
      max_predictions: cap on number returned (default 5)
    """
    try:
        from antar_engine.dasha_event_mapper import (
            map_all_events,
            find_event_window,
            EVENT_DISPLAY_LABELS,
            EVENT_DESCRIPTION,
        )

        # ── 1. Fetch chart row ────────────────────────────────────────────
        chart_res = supabase.table("charts").select(
            "chart_data,birth_date,first_name,name,lagna_sign"
        ).eq("id", chart_id).single().execute()

        if not chart_res.data:
            raise HTTPException(status_code=404, detail="Chart not found")

        cd          = chart_res.data.get("chart_data") or {}
        birth_date  = str(chart_res.data.get("birth_date", ""))
        birth_year  = int(birth_date[:4]) if birth_date and birth_date[:4].isdigit() else 1980
        lagna_raw   = cd.get("lagna") or {}
        lagna       = (lagna_raw.get("sign") if isinstance(lagna_raw, dict) else lagna_raw) \
                      or chart_res.data.get("lagna_sign") or "Capricorn"
        first_name  = chart_res.data.get("first_name") or chart_res.data.get("name") or ""
        today_str   = datetime.now().strftime("%Y-%m-%d")

        # ── 2. Fetch vimsottari antardashas ───────────────────────────────
        ads_res = supabase.table("dasha_periods") \
            .select("planet_or_sign,start_date,end_date,level,type,metadata") \
            .eq("chart_id", chart_id) \
            .eq("system", "vimsottari") \
            .order("start_date") \
            .execute()

        ads = [
            r for r in (ads_res.data or [])
            if r.get("level") == 2
            or str(r.get("type", "")).lower() in ("antardasha", "ad", "2")
        ]

        if not ads:
            # graceful: no dasha data yet
            return {
                "chart_id":             chart_id,
                "lagna":                lagna,
                "first_name":           first_name,
                "predictions":          [],
                "predictions_filtered": 0,
                "predictions_shown":    0,
                "fallback_message":     (
                    "Your dasha sequence hasn't been computed yet. "
                    "Visit your dashboard to generate your full blueprint."
                ),
            }

        # ── 3. Run all event windows ──────────────────────────────────────
        # map_all_events covers: serious_partnership_began, major_relocation,
        #   family_expansion_first, family_expansion_second, serious_partnership_ended
        raw_map = map_all_events(birth_year, lagna, ads)

        # Additional events not covered by map_all_events
        for extra_event in ("loss_of_mother", "major_acquisition"):
            if extra_event not in raw_map:
                raw_map[extra_event] = find_event_window(
                    extra_event, lagna, birth_year, ads
                )

        # ── 4. Score, filter, format ──────────────────────────────────────
        def _confidence_label(score: int) -> str:
            if score >= 8:
                return "high"
            if score >= 5:
                return "moderate"
            return "low"

        def _dasha_label(w: dict) -> str:
            md  = w.get("parent_md", "")
            ad  = w.get("planet", "")
            pd  = w.get("pd_lord", "")
            lbl = f"{md} MD + {ad} AD"
            if pd:
                lbl += f" + {pd} PD"
            return lbl

        def _human_window(start: str, end: str) -> str:
            try:
                s = datetime.fromisoformat(start)
                e = datetime.fromisoformat(end)
                if s.year == e.year:
                    return f"{s.strftime('%B')} to {e.strftime('%B %Y')}"
                return f"{s.strftime('%B %Y')} to {e.strftime('%B %Y')}"
            except Exception:
                return f"{start[:7]} to {end[:7]}"

        all_predictions = []
        for event_type, w in raw_map.items():
            if not w:
                continue
            win_end = w.get("window_end") or w.get("end") or ""
            # Keep only past events (window end before today)
            if win_end and win_end > today_str:
                continue
            score      = w.get("score", 5)
            confidence = min(score, 10)
            if confidence < min_confidence:
                continue
            win_start = w.get("window_start") or w.get("start") or ""
            all_predictions.append({
                "event_type":       event_type,
                "display_label":    EVENT_DISPLAY_LABELS.get(event_type, event_type),
                "description":      EVENT_DESCRIPTION.get(event_type, ""),
                "window": {
                    "start":          win_start,
                    "end":            win_end,
                    "precision":      w.get("precision", "AD"),
                    "human_readable": _human_window(win_start, win_end) if win_start and win_end else "",
                },
                "dasha":            _dasha_label(w),
                "confidence":       confidence,
                "confidence_label": _confidence_label(confidence),
                "explanation_short": w.get("reason", ""),
                "user_response":    None,
            })

        # Sort by confidence DESC
        all_predictions.sort(key=lambda x: -x["confidence"])
        shown             = all_predictions[:max_predictions]
        total_past        = len(all_predictions)
        filtered_out      = total_past - len(shown)

        # Fallback message for sparse charts
        fallback = None
        if len(shown) < 2:
            fallback = (
                "Your chart speaks in nuance, not headlines. Most charts have a "
                "few clear life events; yours threads its story through quieter "
                "patterns. Continue to your dashboard to explore your blueprint."
            )

        return {
            "chart_id":             chart_id,
            "lagna":                lagna,
            "first_name":           first_name,
            "predictions":          shown,
            "predictions_filtered": filtered_out,
            "predictions_shown":    len(shown),
            "fallback_message":     fallback,
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[past-events] Error for {chart_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to compute past events: {str(e)}")


@app.post("/api/v1/chart/{chart_id}/past-events/feedback")
async def submit_past_event_feedback(
    chart_id: str,
    feedback: dict,
    authorization: Optional[str] = Header(None),
):
    """
    Store user confirmation/correction of a past-event prediction.
    Payload: {"event_type": "...", "response": "yes|close|no", "actual_date": "YYYY-MM-DD" (optional)}

    Used to validate mapper accuracy and improve confidence calibration.
    Gracefully no-ops if the past_event_feedback table doesn't exist yet.
    """
    try:
        event_type  = feedback.get("event_type")
        response    = feedback.get("response")
        actual_date = feedback.get("actual_date")

        if response not in ("yes", "close", "no"):
            raise HTTPException(status_code=400, detail="response must be: yes, close, or no")

        try:
            supabase.table("past_event_feedback").insert({
                "chart_id":     chart_id,
                "event_type":   event_type,
                "response":     response,
                "actual_date":  actual_date,
                "submitted_at": datetime.now().isoformat(),
            }).execute()
        except Exception as db_err:
            # Table may not exist yet — log but don't block UX
            print(f"[past-events-feedback] DB insert skipped ({db_err})")

        return {"status": "recorded"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"[past-events-feedback] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

'''

# ── Insertion landmark: right before the /api/v1/chart/{chart_id} GET endpoint
# (which is the plain chart fetcher that follows the /signature endpoint)
LANDMARK = '@app.get("/api/v1/chart/{chart_id}", response_model=ChartResponse)\nasync def get_chart'

assert LANDMARK in src, f"Landmark not found in main.py — check manually:\n  {LANDMARK[:80]}"

src = src.replace(LANDMARK, NEW_ENDPOINTS + LANDMARK, 1)

with open(TARGET, "w") as f:
    f.write(src)

print(f"[done] Patched {TARGET} — past-events + feedback endpoints added")
print('Run syntax check: python -c "import ast; ast.parse(open(\'main.py\').read())"')
