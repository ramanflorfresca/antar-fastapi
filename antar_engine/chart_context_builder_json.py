"""
antar_engine/chart_context_builder_json.py
==========================================
Phase 3: JSON context builder for the /predict endpoint.

Replaces build_complete_context() prose blob with a structured dict split into:

  chart_static   — stable per chart (cacheable with KV prompt caching)
  live           — per-request dynamic data (transits, hora, question)

ARCHITECTURE:
  build_chart_context_json(chart_id, question, concern, language, supabase)
    -> {"chart_static": {...}, "live": {...}}

chart_static contains:
  natal          — lagna + planets from chart_data (normalized)
  divisional_charts — d1/d9/d10/d12 (canonical lowercase, sign names + indices)
  dashas         — vimsottari current MD/AD/PD from dasha_periods table
  lal_kitab      — sleeping planets + house rules from lal_kitab_data column
  jaimini        — karakas + predictions from jaimini_data column
  varshphal      — current year's house destinations (stable for 365 days)
  dkp_context    — desha (place/culture) + kala (age as int) + patra (role/industry)
  natal_signature — archetype name + key signals
  yogas          — active yogas list

live contains:
  current_transits  — planet positions today (computed per-request)
  current_hora      — Kala Hora power window right now
  today_iso         — "2026-04-14" (date only, no time)
  question          — user's question
  concern           — domain (career/finance/health/relationships/general)
  language          — "es" or "en"

USAGE in main.py /predict route:
  from antar_engine.chart_context_builder_json import build_chart_context_json
  ctx = await build_chart_context_json(
      chart_id=request.chart_id,
      question=request.question,
      concern=concern,
      language=language,
      supabase=supabase,
  )
  # chart_static → cached system prompt block
  # live         → dynamic user message block

Place at: ~/antarai/antar_engine/chart_context_builder_json.py
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from antar_engine.chart_schema import normalize_chart_data, get_divisional


# ---------------------------------------------------------------------------
# 1. Dasha fetcher — reads from dasha_periods table
# ---------------------------------------------------------------------------

def _fetch_dashas(chart_id: str, supabase) -> Dict[str, Any]:
    """
    Fetch current dasha periods from dasha_periods table.
    Table uses: planet_or_sign (not lord_or_sign), system field ("jaimini"/"vimsottari").
    Returns structured dict per system for JSON context (no prose).
    """
    try:
        result = supabase.table("dasha_periods") \
            .select("*") \
            .eq("chart_id", chart_id) \
            .order("sequence") \
            .limit(500) \
            .execute()
        rows = result.data or []
    except Exception as e:
        print(f"[json_ctx] dasha fetch failed: {e}")
        return {}

    today = date.today().isoformat()
    out: Dict[str, Any] = {}

    # Group by system
    by_system: Dict[str, list] = {}
    for row in rows:
        sys_name = row.get("system", "vimsottari")
        by_system.setdefault(sys_name, []).append(row)

    for sys_name, sys_rows in by_system.items():
        current_md = None
        current_ad = None
        current_pd = None
        upcoming_md = []

        # level field stores int OR "MD"/"AD"/"PD" string
        def _level_int(row):
            lv = row.get("level")
            tp = row.get("type", "")
            if isinstance(lv, int):
                return lv
            if isinstance(tp, str):
                return {"MD": 1, "AD": 2, "PD": 3}.get(tp.upper(), 1)
            return 1

        for row in sys_rows:
            start = str(row.get("start_date", ""))[:10]
            end   = str(row.get("end_date", ""))[:10]
            if not start or not end:
                continue
            planet = row.get("planet_or_sign", "")
            lv = _level_int(row)

            if start <= today <= end:
                if lv == 1 and current_md is None:
                    current_md = {"planet": planet, "start": start, "end": end}
                elif lv == 2 and current_ad is None:
                    current_ad = {"planet": planet, "start": start, "end": end}
                elif lv == 3 and current_pd is None:
                    current_pd = {"planet": planet, "start": start, "end": end}

        # Upcoming MDs — use >= so same-day transitions (end==start) are included
        if current_md:
            for row in sys_rows:
                if _level_int(row) == 1:
                    start = str(row.get("start_date", ""))[:10]
                    # >= catches same-day handoff (e.g. Mars ends Aug 13, Rahu starts Aug 13)
                    # but skip the current MD itself
                    if start >= current_md["end"] and start != current_md["start"]:
                        upcoming_md.append({
                            "planet": row.get("planet_or_sign", ""),
                            "start": start,
                            "end": str(row.get("end_date", ""))[:10],
                        })
                        if len(upcoming_md) >= 3:
                            break

        out[sys_name] = {
            "current_md": current_md,
            "current_ad": current_ad,
            "current_pd": current_pd,
            "upcoming_md": upcoming_md,
        }

    return out


# ---------------------------------------------------------------------------
# 2. LK data extractor — from lal_kitab_data column
# ---------------------------------------------------------------------------

def _extract_lk_static(lk_data: Any) -> Dict[str, Any]:
    """
    Extract prediction-relevant LK fields from lal_kitab_data column.

    Real structure (confirmed Apr 14 2026):
    {
      "age": int,
      "advanced": {
        "sleeping_planets": [...],
        "rin": {...},
        "remedies": [...],
        ...
      },
      "placements": {...},
      "natal_planets": {...},
      "lagna_sign": str,
      "is_special_cycle": bool,
      "cycle_significance": str,
    }
    """
    if not isinstance(lk_data, dict):
        return {}

    out: Dict[str, Any] = {}

    # Advanced block (sleeping planets, rin, remedies)
    advanced = lk_data.get("advanced") or {}
    if isinstance(advanced, dict):
        for key in ("sleeping_planets", "dormant_planets", "lk_sleeping_planets"):
            if key in advanced:
                out["sleeping_planets"] = advanced[key]
                break
        for key in ("rin", "rin_planets", "debt_planets"):
            if key in advanced:
                out["rin"] = advanced[key]
                break
        for key in ("remedies", "lk_remedies"):
            if key in advanced:
                out["remedies"] = advanced[key]
                break
        for key in ("planet_strengths", "strengths"):
            if key in advanced:
                out["planet_strengths"] = advanced[key]
                break

    # Also check top-level for these keys (some chart versions store here)
    if "sleeping_planets" not in out:
        for key in ("sleeping_planets", "dormant_planets"):
            if key in lk_data:
                out["sleeping_planets"] = lk_data[key]
                break

    # Placements (house-by-house LK rules)
    if "placements" in lk_data:
        out["placements"] = lk_data["placements"]

    # Cycle info
    for key in ("is_special_cycle", "cycle_significance"):
        if key in lk_data:
            out[key] = lk_data[key]

    # Lagna sign
    if "lagna_sign" in lk_data:
        out["lagna_sign"] = lk_data["lagna_sign"]

    return out


# ---------------------------------------------------------------------------
# 3. Jaimini data extractor — from jaimini_data column
# ---------------------------------------------------------------------------

def _extract_jaimini_static(jaimini_data: Any) -> Dict[str, Any]:
    """
    Extract prediction-relevant Jaimini fields.
    Drops computed_at and prompt_block (prose, not needed in JSON path).
    """
    if not isinstance(jaimini_data, dict):
        return {}

    out: Dict[str, Any] = {}

    for key in ("karakas", "chara_karakas"):
        if key in jaimini_data:
            out["karakas"] = jaimini_data[key]
            break

    for key in ("arudha_lagna", "AL"):
        if key in jaimini_data:
            out["arudha_lagna"] = jaimini_data[key]
            break

    for key in ("upapada_lagna", "UL"):
        if key in jaimini_data:
            out["upapada_lagna"] = jaimini_data[key]
            break

    for key in ("karakamsa", "KL"):
        if key in jaimini_data:
            out["karakamsa"] = jaimini_data[key]
            break

    # Predictions with both EN and ES descriptions
    for key in ("predictions", "jaimini_predictions"):
        if key in jaimini_data:
            preds = jaimini_data[key]
            if isinstance(preds, list):
                # Keep only active predictions, strip verbose fields
                out["predictions"] = [
                    {k: v for k, v in p.items()
                     if k in ("id", "type", "description", "description_es",
                               "active", "confidence", "window", "domain")}
                    for p in preds if isinstance(p, dict)
                ][:20]  # cap at 20
            break

    # Chara dasha current period
    for key in ("chara_dasha", "current_chara_dasha"):
        if key in jaimini_data:
            out["chara_dasha"] = jaimini_data[key]
            break

    return out


# ---------------------------------------------------------------------------
# 4. Varshphal builder — annual chart (stable for 365 days)
# ---------------------------------------------------------------------------

def _build_varshphal(chart_data: Dict[str, Any], birth_date: str) -> Dict[str, Any]:
    """
    Build Varshphal (annual chart) context for current running year.
    Uses existing varshaphal_table.py if available.
    Returns running year as integer — no day/time drift.
    """
    try:
        from antar_engine.varshaphal_table import get_varshaphal_for_year
        today = date.today()
        # Running year = age + 1 (year that started on last birthday)
        birth = datetime.fromisoformat(str(birth_date)[:10]).date()
        age = today.year - birth.year - (
            1 if (today.month, today.day) < (birth.month, birth.day) else 0
        )
        running_year = age + 1  # integer only — no drift

        varsh = get_varshaphal_for_year(chart_data, running_year)
        if varsh:
            return {
                "running_year": running_year,
                "houses": varsh,
            }
    except ImportError:
        pass
    except Exception as e:
        print(f"[json_ctx] varshphal failed (non-fatal): {e}")

    return {}


# ---------------------------------------------------------------------------
# 5. DKP context builder — from chart_record fields
# ---------------------------------------------------------------------------

def _build_dkp_context(chart_record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build DKP (Desha-Kala-Patra) context from chart record.
    Age stored as integer years only — no days/hours/microseconds (no drift).
    """
    birth_date = chart_record.get("birth_date", "")
    today = date.today()

    # Age as integer only
    age = None
    if birth_date:
        try:
            birth = datetime.fromisoformat(str(birth_date)[:10]).date()
            age = today.year - birth.year - (
                1 if (today.month, today.day) < (birth.month, birth.day) else 0
            )
        except Exception:
            pass

    # Life stage
    life_stage = "unknown"
    if age is not None:
        if age < 25:
            life_stage = "early_career"
        elif age < 35:
            life_stage = "establishment"
        elif age < 50:
            life_stage = "peak"
        elif age < 65:
            life_stage = "consolidation"
        else:
            life_stage = "wisdom"

    desha = {
        "current_country": chart_record.get("current_country") or chart_record.get("country_code", ""),
        "birth_country": chart_record.get("birth_country") or chart_record.get("country_code", ""),
        "lived_abroad": chart_record.get("lived_abroad", False),
    }

    kala = {
        "age": age,                    # integer, no drift
        "life_stage": life_stage,
        "birth_year": datetime.fromisoformat(str(birth_date)[:10]).year if birth_date else None,
    }

    patra = {
        "career_stage": chart_record.get("career_stage", ""),
        "marital_status": chart_record.get("marital_status", ""),
        "children_status": chart_record.get("children_status", ""),
        "financial_status": chart_record.get("financial_status", ""),
        "health_status": chart_record.get("health_status", ""),
        "gender": chart_record.get("gender", ""),
        "signup_intent": chart_record.get("signup_intent", ""),
    }

    return {"desha": desha, "kala": kala, "patra": patra}


# ---------------------------------------------------------------------------
# 6. Natal summary — compact form of chart_data for JSON
# ---------------------------------------------------------------------------

def _build_natal_summary(chart_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build compact natal summary from normalized chart_data.
    Includes lagna + planets with only prediction-relevant fields.
    """
    cd = normalize_chart_data(chart_data)

    lagna = cd.get("lagna", {})
    planets_raw = cd.get("planets", {})

    # Compact planet list — only fields Claude needs for interpretation
    planets_compact: Dict[str, Any] = {}
    for pname, pdata in planets_raw.items():
        if not isinstance(pdata, dict):
            continue
        planets_compact[pname] = {
            k: v for k, v in pdata.items()
            if k in ("sign", "sign_index", "house", "degree",
                     "nakshatra", "nakshatra_lord", "retrograde",
                     "longitude")
        }

    # Key divisional charts — only d1, d9, d10, d12
    div = cd.get("divisional_charts", {})
    key_divs: Dict[str, Any] = {}
    for key in ("d1", "d9", "d10", "d12", "d2", "d7"):
        if key in div:
            chart = div[key]
            key_divs[key] = {
                "lagna": chart.get("lagna"),
                "lagna_index": chart.get("lagna_index"),
                "lagna_lord": chart.get("lagna_lord"),
                "meaning": chart.get("meaning"),
                "planets": {
                    p: {k: v for k, v in pd.items()
                        if k in ("sign", "sign_index", "house", "sign_lord")}
                    for p, pd in chart.get("planets", {}).items()
                    if isinstance(pd, dict)
                },
            }

    return {
        "lagna": lagna,
        "planets": planets_compact,
        "divisional_charts": key_divs,
        "atmakaraka": cd.get("atmakaraka", ""),
        "yogas": cd.get("yogas", [])[:15],  # cap at 15
        "house_lords": cd.get("house_lords", {}),
    }


# ---------------------------------------------------------------------------
# 7. Live data builder — per-request, NOT cached
# ---------------------------------------------------------------------------

def _build_live(
    chart_data: Dict[str, Any],
    question: str,
    concern: str,
    language: str,
    chart_record: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build the live (per-request) context block.
    Contains only data that changes per call.
    today_iso is DATE ONLY (no time) — prevents drift within same day.
    """
    today_iso = date.today().isoformat()  # "2026-04-14" — no time, no drift

    # Current transits
    current_transits: Dict[str, Any] = {}
    try:
        from antar_engine import transits as transits_engine
        raw = transits_engine.calculate_transits(chart_data, target_date=None, ayanamsa_mode=1)
        if isinstance(raw, list):
            current_transits = {
                t["planet"]: {
                    k: v for k, v in t.items()
                    if k in ("sign", "house", "nakshatra", "degree", "retrograde")
                }
                for t in raw if isinstance(t, dict) and "planet" in t
            }
        elif isinstance(raw, dict):
            current_transits = raw
    except Exception as e:
        print(f"[json_ctx] transits failed (non-fatal): {e}")

    # Current Kala Hora
    current_hora: Dict[str, Any] = {}
    try:
        from antar_engine.hora_engine import get_hora_schedule
        _lat = float((chart_record or {}).get("latitude", 28.6))
        _lng = float((chart_record or {}).get("longitude", 77.2))
        # get_hora_schedule returns list of hora windows; find the current one
        schedule = get_hora_schedule(_lat, _lng)
        if schedule and isinstance(schedule, list):
            now_str = datetime.now(timezone.utc).isoformat()
            for h in schedule:
                h_start = h.get("start", "")
                h_end   = h.get("end", "")
                if h_start and h_end and h_start <= now_str <= h_end:
                    current_hora = {
                        "planet": h.get("ruler", h.get("planet", "")),
                        "quality": h.get("quality", ""),
                        "good_for": h.get("good_for", h.get("activities", "")),
                        "is_power": h.get("is_power_hora", False),
                    }
                    break
            if not current_hora and schedule:
                # fallback: first upcoming hora
                h = schedule[0]
                current_hora = {
                    "planet": h.get("ruler", h.get("planet", "")),
                    "quality": h.get("quality", ""),
                }
    except Exception as e:
        print(f"[json_ctx] hora failed (non-fatal): {e}")

    return {
        "today_iso": today_iso,
        "question": question,
        "concern": concern,
        "language": language,
        "current_transits": current_transits,
        "current_hora": current_hora,
    }


# ---------------------------------------------------------------------------
# 8. Main entry point
# ---------------------------------------------------------------------------

async def build_chart_context_json(
    chart_id: str,
    question: str,
    concern: str,
    language: str,
    supabase,
) -> Dict[str, Any]:
    """
    Build the full JSON context for /predict.

    Returns:
        {
            "chart_static": {...},   # stable per chart — goes in cached system prompt
            "live": {...},           # per-request — goes in user message
        }

    chart_static is deterministic when serialized with json.dumps(sort_keys=True).
    No timestamps, no datetime.now(), no float rounding drift.
    """

    # ── Fetch chart record (single SELECT *) ─────────────────────
    try:
        result = supabase.table("charts").select("*").eq("id", chart_id).single().execute()
        chart_record = result.data
    except Exception as e:
        print(f"[json_ctx] chart fetch failed: {e}")
        return {"chart_static": {}, "live": _build_live({}, question, concern, language, None)}

    if not chart_record:
        return {"chart_static": {}, "live": _build_live({}, question, concern, language, None)}

    chart_data = chart_record.get("chart_data") or {}
    lal_kitab_data = chart_record.get("lal_kitab_data") or {}
    jaimini_data = chart_record.get("jaimini_data") or {}

    # ── Build chart_static ────────────────────────────────────────
    natal = _build_natal_summary(chart_data)

    dashas = _fetch_dashas(chart_id, supabase)

    lk_static = _extract_lk_static(lal_kitab_data)

    jaimini_static = _extract_jaimini_static(jaimini_data)

    birth_date = chart_record.get("birth_date", "")
    varshphal = _build_varshphal(chart_data, birth_date)

    dkp_context = _build_dkp_context(chart_record)

    # Natal signature + archetype (from separate columns)
    natal_signature = chart_record.get("planet_signatures") or {}
    archetype = chart_record.get("character_archetype") or {}

    chart_static = {
        "natal": natal,
        "dashas": dashas,
        "lal_kitab": lk_static,
        "jaimini": jaimini_static,
        "varshphal": varshphal,
        "dkp_context": dkp_context,
        "natal_signature": natal_signature,
        "archetype": archetype,
    }

    # ── Build live ────────────────────────────────────────────────
    live = _build_live(chart_data, question, concern, language, chart_record)

    return {
        "chart_static": chart_static,
        "live": live,
    }


# ---------------------------------------------------------------------------
# 9. Serialization helpers for the prompt builder
# ---------------------------------------------------------------------------

def chart_static_to_json(ctx: Dict[str, Any]) -> str:
    """
    Serialize chart_static to deterministic JSON string.
    sort_keys=True ensures byte-identical output for KV cache.
    separators=(',', ':') removes whitespace for smaller payload.
    """
    return json.dumps(ctx.get("chart_static", {}), sort_keys=True, separators=(",", ":"), default=str)


def live_to_json(ctx: Dict[str, Any]) -> str:
    """Serialize live block to JSON string."""
    return json.dumps(ctx.get("live", {}), sort_keys=True, separators=(",", ":"), default=str)


def estimate_token_count(s: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    return len(s) // 4


# ---------------------------------------------------------------------------
# 10. Quick smoke test (run: python -m antar_engine.chart_context_builder_json)
# ---------------------------------------------------------------------------

def _smoke_test() -> None:
    """
    Smoke test with fake data — verifies structure and serialization,
    not actual Supabase data.
    """
    print("Running chart_context_builder_json smoke test...\n")

    # Fake chart_data matching real production shape
    fake_chart_data = {
        "lagna": {"sign": "Capricorn", "degree": 24.69, "sign_index": 9},
        "planets": {
            "Sun": {"sign": "Scorpio", "house": 11, "degree": 10.1, "sign_index": 7, "nakshatra": "Anuradha"},
            "Moon": {"sign": "Pisces", "house": 3, "degree": 5.2, "sign_index": 11, "nakshatra": "Uttara Bhadrapada"},
            "Rahu": {"sign": "Aries", "house": 4, "degree": 18.3, "sign_index": 0, "nakshatra": "Bharani"},
            "Ketu": {"sign": "Libra", "house": 10, "degree": 18.3, "sign_index": 6, "nakshatra": "Swati"},
            "Saturn": {"sign": "Capricorn", "house": 1, "degree": 12.5, "sign_index": 9, "nakshatra": "Shravana"},
        },
        "divisional_charts": {
            "d9": {"lagna": "Leo", "meaning": "Navamsa", "lagna_lord": "Sun",
                   "planets": {"Sun": {"sign": "Libra", "house": 3, "sign_lord": "Venus"}}},
            "d10": {"lagna": "Virgo", "meaning": "Dasamsa", "lagna_lord": "Mercury",
                    "planets": {"Saturn": {"sign": "Capricorn", "house": 5, "sign_lord": "Saturn"}}},
        },
        "yogas": [{"name": "Shasha Yoga", "planets": ["Saturn"], "active": True}],
        "atmakaraka": "Saturn",
        "house_lords": {1: {"lord": "Saturn"}, 10: {"lord": "Venus"}},
    }

    natal = _build_natal_summary(fake_chart_data)
    assert "lagna" in natal
    assert "planets" in natal
    assert natal["lagna"]["sign"] == "Capricorn"
    assert natal["lagna"]["sign_index"] == 9
    assert "Sun" in natal["planets"]
    assert "d9" in natal["divisional_charts"]
    assert natal["divisional_charts"]["d9"]["lagna_index"] == 4  # Leo
    print("✅ natal summary correct")

    lk_test = _extract_lk_static({
        "sleeping_planets": ["Mercury", "Venus"],
        "rin": {"Jupiter": True},
        "computed_at": "2026-04-14T12:00:00",  # should be excluded
    })
    assert "sleeping_planets" in lk_test
    assert "computed_at" not in lk_test
    print("✅ LK extractor strips computed_at")

    dkp_test = _build_dkp_context({
        "birth_date": "1988-01-15",
        "current_country": "CO",
        "birth_country": "IN",
        "career_stage": "founder",
        "gender": "male",
    })
    assert isinstance(dkp_test["kala"]["age"], int)
    assert dkp_test["desha"]["current_country"] == "CO"
    print(f"✅ DKP context — age={dkp_test['kala']['age']} (int), stage={dkp_test['kala']['life_stage']}")

    # Serialization determinism
    ctx1 = {"chart_static": {"natal": natal, "dkp_context": dkp_test}, "live": {}}
    ctx2 = {"chart_static": {"natal": natal, "dkp_context": dkp_test}, "live": {}}
    s1 = chart_static_to_json(ctx1)
    s2 = chart_static_to_json(ctx2)
    assert s1 == s2, "FAIL: serialization not deterministic"
    print(f"✅ Deterministic serialization — {len(s1)} chars, ~{estimate_token_count(s1)} tokens")

    # Verify no datetime.now() or timestamps in static
    assert "now()" not in s1
    assert "computed_at" not in s1
    print("✅ No drift sources in serialized output")

    print("\n✅ All smoke tests passed.")


if __name__ == "__main__":
    _smoke_test()
