"""
Phase Analyzer — Surface B: Life Arc
=====================================
Computes the current life phase for a chart:
- Current Vimsottari MD/AD/PD with end dates
- Current Jaimini Chara dasha
- Sade Sati status (entering, peak, setting, dormant)
- Transit overlay — where slow planets are relative to natal
- One-paragraph life phase summary (LLM call)

Author: Antar Engine · April 2026
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Any

from antar_engine import vimsottari, transits, utils, constants


def _now_utc() -> datetime:
    """Timezone-aware UTC now — matches vimsottari's tz-aware datetimes."""
    return datetime.now(timezone.utc)


# ─── Vimsottari: Current MD / AD / PD ───────────────────────────────────────

def _find_current_period(periods: list, now: datetime) -> Optional[dict]:
    """Find the period that contains `now`."""
    for p in periods:
        if p["start_datetime"] <= now < p["end_datetime"]:
            return p
    return None


def _compute_pratyantardashas(ad: dict) -> list:
    """
    Compute the 9 Pratyantardashas (PDs) within an Antardasha.
    Same Vimsottari proportional subdivision logic.
    """
    seq = constants.VIMSOTTARI_SEQUENCE
    years_map = constants.VIMSOTTARI_YEARS
    ad_lord = ad["lord"]
    start_idx = seq.index(ad_lord)
    total_seconds = (ad["end_datetime"] - ad["start_datetime"]).total_seconds()

    pds = []
    current_start = ad["start_datetime"]
    for i in range(9):
        lord = seq[(start_idx + i) % 9]
        lord_years = years_map[lord]
        # PD duration = (lord_years / 120) * AD_duration
        pd_fraction = lord_years / 120.0
        pd_seconds = total_seconds * (pd_fraction * ad["duration_years"]) / ad["duration_years"] if ad["duration_years"] > 0 else 0
        # Simpler: same proportional logic as AD within MD
        pd_seconds = total_seconds * (lord_years / 120.0)
        pd_end = current_start + timedelta(seconds=pd_seconds)
        pds.append({
            "lord": lord,
            "start_datetime": current_start,
            "end_datetime": pd_end,
            "parent_lord": ad_lord,
        })
        current_start = pd_end
    return pds


def _compute_sookshma_dashas(pd: dict) -> list:
    """
    Compute the 9 Sookshma Dashas (SDs) within a Pratyantardasha.
    Same Vimsottari proportional subdivision logic, one level below PD.
    SD duration = (lord_years / 120) * PD_duration.
    Typically shifts every 2-3 days.
    """
    from antar_engine import constants
    from datetime import timedelta

    seq = constants.VIMSOTTARI_SEQUENCE
    years_map = constants.VIMSOTTARI_YEARS
    pd_lord = pd["lord"]
    start_idx = seq.index(pd_lord)
    total_seconds = (pd["end_datetime"] - pd["start_datetime"]).total_seconds()

    sds = []
    current_start = pd["start_datetime"]
    for i in range(9):
        lord = seq[(start_idx + i) % 9]
        lord_years = years_map[lord]
        sd_seconds = total_seconds * (lord_years / 120.0)
        sd_end = current_start + timedelta(seconds=sd_seconds)
        sds.append({
            "lord": lord,
            "start_datetime": current_start,
            "end_datetime": sd_end,
            "parent_pd_lord": pd_lord,
        })
        current_start = sd_end
    return sds


def get_current_vimsottari(chart_data: dict, birth_jd: float, now: datetime = None) -> dict:
    """
    Returns current MD, AD, PD with end dates.
    """
    now = now or _now_utc()
    result = vimsottari.calculate_vimsottari_from_chart(chart_data, birth_jd)
    mds = result["mahadashas"]
    ads = result["antardashas"]

    current_md = _find_current_period(mds, now)
    if not current_md:
        return {"error": "No active Vimsottari period found for current date"}

    # Find current AD
    md_ads = [a for a in ads if a.get("parent_lord") == current_md["lord"]
              and a["start_datetime"] >= current_md["start_datetime"]
              and a["end_datetime"] <= current_md["end_datetime"] + timedelta(seconds=1)]
    current_ad = _find_current_period(md_ads, now)

    # Compute PD within current AD
    current_pd = None
    pd_end_date = None
    if current_ad:
        pds = _compute_pratyantardashas(current_ad)
        current_pd = _find_current_period(pds, now)
        if current_pd:
            pd_end_date = current_pd["end_datetime"].strftime("%Y-%m-%d")

    # Compute SD within current PD — shifts every 2-3 days, critical for daily
    current_sd = None
    sd_end_date = None
    if current_pd:
        sds = _compute_sookshma_dashas(current_pd)
        current_sd = _find_current_period(sds, now)
        if current_sd:
            sd_end_date = current_sd["end_datetime"].strftime("%Y-%m-%d")

    return {
        "md": current_md["lord"] if current_md else None,
        "md_lord_condition": _assess_lord_condition(current_md["lord"], chart_data) if current_md else None,
        "ad": current_ad["lord"] if current_ad else None,
        "pd": current_pd["lord"] if current_pd else None,
        "sd": current_sd["lord"] if current_sd else None,
        "sd_end_date": sd_end_date,
        "md_end_date": current_md["end_datetime"].strftime("%Y-%m-%d") if current_md else None,
        "ad_end_date": current_ad["end_datetime"].strftime("%Y-%m-%d") if current_ad else None,
        "pd_end_date": pd_end_date,
    }


def _assess_lord_condition(lord: str, chart_data: dict) -> str:
    """Simple dignity assessment for a planet."""
    planets = chart_data.get("planets", {})
    planet_data = planets.get(lord, {})
    if not planet_data:
        return "unknown"
    sign_idx = planet_data.get("sign_index", -1)
    sign_name = planet_data.get("sign", "")

    # Check exaltation
    exaltation_signs = {
        "Sun": 0, "Moon": 1, "Mars": 9, "Mercury": 5,
        "Jupiter": 3, "Venus": 11, "Saturn": 6, "Rahu": 1, "Ketu": 7
    }
    debilitation_signs = {
        "Sun": 6, "Moon": 7, "Mars": 3, "Mercury": 11,
        "Jupiter": 9, "Venus": 5, "Saturn": 0, "Rahu": 7, "Ketu": 1
    }
    own_signs = {
        "Sun": [4], "Moon": [3], "Mars": [0, 7], "Mercury": [2, 5],
        "Jupiter": [8, 11], "Venus": [1, 6], "Saturn": [9, 10],
        "Rahu": [10], "Ketu": [7]
    }

    if sign_idx == exaltation_signs.get(lord, -99):
        return "exalted"
    if sign_idx == debilitation_signs.get(lord, -99):
        return "debilitated"
    if sign_idx in own_signs.get(lord, []):
        return "own sign"
    return f"in {sign_name}"


# ─── Jaimini Chara Dasha ────────────────────────────────────────────────────

def get_current_jaimini(chart_data: dict, birth_date_str: str, now: datetime = None) -> dict:
    """
    Returns current Jaimini Chara MD with end date.
    """
    now = now or _now_utc()
    try:
        from antar_engine.jaimini_engine import (
            compute_chara_dasha, get_current_dasha, Planet, SIGN_NAMES
        )

        lagna = chart_data.get("lagna", {})
        lagna_sign = lagna.get("sign_index", 0)
        planets_raw = chart_data.get("planets", {})

        # Convert to Planet objects
        planets = {}
        for name, pdata in planets_raw.items():
            if not isinstance(pdata, dict):
                continue
            planets[name] = Planet(
                name=name,
                sign=pdata.get("sign_index", 0),
                degree=pdata.get("longitude", 0.0),
                degree_in_sign=pdata.get("degree", 0.0),
                retrograde=pdata.get("retrograde", False),
                nakshatra=pdata.get("nakshatra", ""),
            )

        # Parse birth date
        bd_parts = birth_date_str[:10].split("-")
        birth_dt = datetime(int(bd_parts[0]), int(bd_parts[1]), int(bd_parts[2]))

        all_mds = compute_chara_dasha(lagna_sign, planets, birth_dt, num_cycles=3)
        # Jaimini uses naive datetimes — strip tz for comparison
        now_naive = now.replace(tzinfo=None) if now.tzinfo else now
        current_md, current_ad = get_current_dasha(all_mds, now_naive)

        if current_md:
            return {
                "md": current_md.sign_name,
                "md_start_date": current_md.start_date.strftime("%Y-%m-%d"),
                "md_end_date": current_md.end_date.strftime("%Y-%m-%d"),
            }
    except Exception as e:
        print(f"[life_arc.phase_analyzer] Jaimini error (non-fatal): {e}")

    return {"md": None, "md_end_date": None}


# ─── Sade Sati Detection ────────────────────────────────────────────────────

def detect_sade_sati(chart_data: dict, now: datetime = None) -> dict:
    """
    Detect Sade Sati status: Saturn transiting 12H, 1H, or 2H from natal Moon.
    Returns status string and months remaining.
    """
    now = now or _now_utc()
    natal_moon = chart_data.get("planets", {}).get("Moon", {})
    moon_sign_idx = natal_moon.get("sign_index", 0)

    # Get Saturn's current transit position
    jd_now = utils.julian_day(now)
    positions = transits.get_current_positions(jd_now)
    saturn_pos = positions.get("Saturn", {})
    saturn_sign_idx = saturn_pos.get("sign_index", -1)

    # House from Moon (1-indexed)
    house_from_moon = (saturn_sign_idx - moon_sign_idx + 12) % 12 + 1

    if house_from_moon == 12:
        status = "entering phase"
    elif house_from_moon == 1:
        status = "peak phase"
    elif house_from_moon == 2:
        status = "setting phase"
    else:
        return {
            "active": False,
            "status": "dormant",
            "saturn_house_from_moon": house_from_moon,
            "months_remaining": 0,
        }

    # Estimate months remaining based on Saturn's average transit (~2.5 years per sign)
    saturn_degree = saturn_pos.get("degree", 15.0)
    if house_from_moon == 12:
        # Entering: needs to transit rest of 12H + full 1H + full 2H
        remaining_degrees = (30 - saturn_degree) + 30 + 30
    elif house_from_moon == 1:
        # Peak: needs to transit rest of 1H + full 2H
        remaining_degrees = (30 - saturn_degree) + 30
    else:
        # Setting: needs to transit rest of 2H
        remaining_degrees = 30 - saturn_degree

    # Saturn moves ~12 degrees per year
    months_remaining = int(remaining_degrees / 12 * 12)

    return {
        "active": True,
        "status": status,
        "saturn_house_from_moon": house_from_moon,
        "months_remaining": months_remaining,
    }


# ─── Transit Overlay ────────────────────────────────────────────────────────

def get_transit_overlay(chart_data: dict, now: datetime = None) -> dict:
    """
    Get slow-planet transit positions relative to natal Moon for context.
    """
    now = now or _now_utc()
    natal_moon = chart_data.get("planets", {}).get("Moon", {})
    moon_sign_idx = natal_moon.get("sign_index", 0)
    natal_lagna_idx = chart_data.get("lagna", {}).get("sign_index", 0)

    jd_now = utils.julian_day(now)
    positions = transits.get_current_positions(jd_now)

    saturn_sign = positions.get("Saturn", {}).get("sign_index", 0)
    jupiter_sign = positions.get("Jupiter", {}).get("sign_index", 0)
    rahu_sign = positions.get("Rahu", {}).get("sign_index", 0)

    sade_sati = detect_sade_sati(chart_data, now)

    return {
        "sade_sati_status": f"{sade_sati['status']}, {sade_sati['months_remaining']} months remaining" if sade_sati["active"] else "dormant",
        "saturn_house_from_moon": (saturn_sign - moon_sign_idx + 12) % 12 + 1,
        "jupiter_house_from_moon": (jupiter_sign - moon_sign_idx + 12) % 12 + 1,
        "rahu_house_from_lagna": (rahu_sign - natal_lagna_idx + 12) % 12 + 1,
        "saturn_house_from_lagna": (saturn_sign - natal_lagna_idx + 12) % 12 + 1,
        "jupiter_house_from_lagna": (jupiter_sign - natal_lagna_idx + 12) % 12 + 1,
    }


# ─── Life Phase Summary (Claude call) ───────────────────────────────────────

async def generate_phase_summary(
    vimsottari_phase: dict,
    jaimini_phase: dict,
    transit_overlay: dict,
    sade_sati: dict,
    archetype_name: str,
    language: str = "en",
    claude_caller=None,
) -> str:
    """
    Generate the Current Cycle narration: {"headline": str, "body": str}.
    Inputs are translated to life-nouns BEFORE the prompt; output is gated
    by narration_validator (violation -> dated life-noun fallback).
    claude_caller should be the call_llm_claude function from main.py.
    """
    if not claude_caller:
        return _fallback_phase_pair(vimsottari_phase, sade_sati)

    # noun layer (2026-06-07): the chapter's slow transits point at literal
    # life-areas — Jupiter's house = where support/growth lands, Saturn's =
    # where it's tested. Translate to concrete nouns so the summary names real
    # life (your work, home, partner, finances) not abstract "energy".
    _noun_hint = ""
    try:
        from antar_engine.house_significations import select_nouns
        from antar_engine.life_context import active_life as _al
        _life = _al()  # gate boss/child/spouse nouns on the reader's known facts
        _jh = transit_overlay.get("jupiter_house_from_moon")
        _sh = transit_overlay.get("saturn_house_from_moon")
        _grow = select_nouns(_jh, "positive", None, 3, life=_life) if isinstance(_jh, int) else []
        _test = select_nouns(_sh, "adverse", None, 3, life=_life) if isinstance(_sh, int) else []
        _bits = []
        if _grow:
            _bits.append("supported/growing: " + ", ".join(_grow))
        if _test:
            _bits.append("tested/asking effort: " + ", ".join(_test))
        if _bits:
            _noun_hint = ("\n- Concrete life-areas this chapter touches (name a "
                          "few of these naturally, no jargon) — " + "; ".join(_bits))
    except Exception:
        _noun_hint = ""

    # ── Translate BEFORE generation (energy-voice retirement 2026-06-10) ──
    # The prompt receives ONLY life-language. No planet names, no house
    # numbers, no sign names, no archetype label, no Sanskrit. Claude can't
    # leak what it never sees; the validator below catches the rest.
    from antar_engine.life_arc.voice.energy_vocabulary import (
        get_life_phrase as _lp, get_life_nouns as _ln,
    )
    _dig_map = {"exalted": "strong", "own sign": "steady",
                "debilitated": "strained"}
    _md_cond = _dig_map.get(str(vimsottari_phase.get("md_lord_condition") or ""), "mixed")
    _md_phrase = _lp(vimsottari_phase.get("md") or "")
    _ad_phrase = _lp(vimsottari_phase.get("ad") or "")
    _pd_phrase = _lp(vimsottari_phase.get("pd") or "")
    _md_nouns = ", ".join(_ln(vimsottari_phase.get("md") or "", 3)) or _md_phrase
    _ad_nouns = ", ".join(_ln(vimsottari_phase.get("ad") or "", 3)) or _ad_phrase
    _md_end = vimsottari_phase.get("md_end_date") or ""
    _ad_end = vimsottari_phase.get("ad_end_date") or ""
    _pd_end = vimsottari_phase.get("pd_end_date") or ""
    _sade_on = bool((sade_sati or {}).get("active"))

    prompt = f"""You are writing the Current Cycle read for Antar (a life-navigation app).

PERIOD FACTS — already translated into life-language. Use ONLY these nouns. Never mention astrology, planets, signs, houses, or any system name.
- Long phase: centered on {_md_phrase} ({_md_cond} footing); life-areas: {_md_nouns}; runs until {_md_end}.
- Current stretch inside it: centered on {_ad_phrase}; life-areas: {_ad_nouns}; runs until {_ad_end}.
- The immediate weeks: colored by {_pd_phrase}; until {_pd_end}.
- Consolidation pressure (slow, testing stretch): {"active — slower outside, deeper inside" if _sade_on else "not active"}.{_noun_hint}

WRITE TWO FIELDS, exactly in this format:
HEADLINE: one sentence, max 18 words, verdict-first — the dominant life-area, what to do about it, and the nearest date.
BODY: 3-5 short sentences. Do NOT repeat or rephrase the headline as the first sentence — start somewhere new. Name 2-3 concrete life-areas from the lists above. Say what shifts around {_ad_end or "the next turn"} and what changes after. End with ONE specific action.

RULES (NON-NEGOTIABLE):
1. Plain English a smart, busy person gets instantly. Sound like a sharp human coach texting them.
2. NEVER use: the word "energy", planet names, the word "house", Sanskrit, "sub-chapter", "micro-phase", "chapter lord", "rhythm", "layering", "MD", "AD", "PD", or any archetype label.
3. Every sentence starts with a capital letter. One idea per sentence, under ~18 words.
4. Refer to time with dates ("through April 2028", "until late 2030") — never coined period names.
5. Concrete life-nouns over categories: "your savings", "the people who report to you" — not "material matters".
6. Language: {language}"""

    # [prompt-registry 2026-06-10] admin-editable body + immutable header.
    from antar_engine.prompt_registry import get_system_prefix
    system = get_system_prefix("cycle_phase")

    try:
        text, _ = await claude_caller(prompt, system_override=system)
        # Parse the two fields.
        import re as _pf_re
        _m = _pf_re.search(r"HEADLINE:\s*(.+?)\s*BODY:\s*(.+)", text or "",
                           _pf_re.DOTALL | _pf_re.IGNORECASE)
        def _strip_md(_s):
            # Markdown wrappers Claude sometimes adds around field values
            # ("** Focus on ... **"). Format cleanup, not prose substitution.
            _s = (_s or "").strip()
            _s = _pf_re.sub(r"^[*#_\s]+|[*_\s]+$", "", _s)
            return _s.strip()
        if _m:
            headline = _strip_md(" ".join(_m.group(1).split()))
            body = _strip_md(_m.group(2))
        else:
            headline, body = "", _strip_md(text)

        # [readability 2026-06-10] simplify the body only (the headline is
        # already a single short sentence).
        try:
            from antar_engine.readability import maybe_simplify as _rb_maybe
            _rb = await _rb_maybe(body, language=language, surface="cycle.phase_summary")
            body = _rb["text"]
        except Exception as _rb_e:
            print(f"[life_arc.phase_analyzer] readability non-fatal: {_rb_e}")

        # Deterministic de-dupe: body must not open with the headline.
        if headline and body.lower().startswith(headline.lower()[:40]):
            _sents = _pf_re.split(r"(?<=[.!?])\s+", body, maxsplit=1)
            body = _sents[1].strip() if len(_sents) > 1 else body

        # ── VALIDATOR, not stripper (Class B) ─────────────────────────────
        # Any banned token in either field -> deterministic dated fallback.
        # Never silently rewrite generated prose.
        from antar_engine.narration_validator import validate_narration as _vn
        _extra = [archetype_name] if archetype_name else []
        _viol = _vn(headline or body, extra_banned=_extra, language=language) \
            + _vn(body, extra_banned=_extra, language=language)
        if _viol:
            print(f"[life_arc.phase_analyzer] narration REJECTED by validator: {_viol[:4]}")
            return _fallback_phase_pair(vimsottari_phase, sade_sati)
        # Format miss (Claude skipped the HEADLINE marker): keep the clean
        # body, take the deterministic headline — never slice the body.
        if not headline:
            headline = _fallback_phase_pair(vimsottari_phase, sade_sati)["headline"]
        return {"headline": headline, "body": body}
    except Exception as e:
        print(f"[life_arc.phase_analyzer] Summary LLM error: {e}")
        return _fallback_phase_pair(vimsottari_phase, sade_sati)


def _fallback_phase_pair(vimsottari_phase: dict, sade_sati: dict) -> dict:
    """Deterministic dated life-noun fallback — used when Claude is
    unavailable OR the validator rejects generated prose. Zero astrology
    vocabulary, zero "energy" wording, always dated, always actionable."""
    from antar_engine.life_arc.voice.energy_vocabulary import (
        get_life_phrase as _fb_lp, get_life_nouns as _fb_ln,
    )
    md_phrase = _fb_lp(vimsottari_phase.get("md") or "")
    ad_phrase = _fb_lp(vimsottari_phase.get("ad") or "")
    ad_nouns = _fb_ln(vimsottari_phase.get("ad") or "", 2)
    md_end = vimsottari_phase.get("md_end_date") or ""
    ad_end = vimsottari_phase.get("ad_end_date") or ""
    sade_on = bool((sade_sati or {}).get("active"))

    headline = f"A long stretch built on {md_phrase}"
    if md_end:
        headline += f" runs until {md_end}"
    headline += f" — focus on {ad_phrase} now."

    body_bits = []
    if ad_end:
        body_bits.append(
            f"The current stretch centers on {ad_phrase} and runs until {ad_end}."
        )
    else:
        body_bits.append(f"The current stretch centers on {ad_phrase}.")
    if sade_on:
        body_bits.append(
            "It is a consolidation period — slower on the outside, deeper on the inside."
        )
    if ad_nouns:
        body_bits.append(
            f"Expect the real movement around {ad_nouns[0]}"
            + (f" and {ad_nouns[1]}" if len(ad_nouns) > 1 else "")
            + "."
        )
    if ad_end:
        body_bits.append(f"The tone changes after {ad_end}.")
    body_bits.append(
        f"Pick one concrete step on {ad_phrase} this week and finish it."
    )
    return {"headline": headline, "body": " ".join(body_bits)}


def _fallback_phase_summary(vimsottari_phase: dict, sade_sati: dict) -> str:
    """Back-compat wrapper — body text only."""
    return _fallback_phase_pair(vimsottari_phase, sade_sati)["body"]


# ─── Main Entry Point ───────────────────────────────────────────────────────

async def analyze_current_phase(
    chart_data: dict,
    birth_jd: float,
    birth_date_str: str,
    archetype_name: str = "",
    language: str = "en",
    claude_caller=None,
    now: datetime = None,
) -> dict:
    """
    Full current phase analysis. Returns the current_phase block
    for the life-arc response.
    """
    now = now or _now_utc()

    # 1. Vimsottari
    vim = get_current_vimsottari(chart_data, birth_jd, now)

    # 2. Jaimini
    jaim = get_current_jaimini(chart_data, birth_date_str, now)

    # 3. Transit overlay (includes Sade Sati)
    overlay = get_transit_overlay(chart_data, now)
    sade_sati = detect_sade_sati(chart_data, now)

    # 4. Life phase summary
    _pair = await generate_phase_summary(
        vim, jaim, overlay, sade_sati,
        archetype_name, language, claude_caller
    )
    if isinstance(_pair, dict):
        _headline = (_pair.get("headline") or "").strip()
        _body = (_pair.get("body") or "").strip()
    else:  # defensive — old str contract
        _headline, _body = "", str(_pair or "").strip()

    return {
        "vimsottari": vim,
        "jaimini_chara": jaim,
        "transit_overlay": overlay,
        "life_phase_summary": _body,
        "headline": _headline,
    }
