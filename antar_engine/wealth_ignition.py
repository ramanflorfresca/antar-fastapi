"""
antar_engine/wealth_ignition.py
===============================
Forward wealth-ignition forecast — the two-system converged wealth window.

This is the forward projection the engine was missing. `chapter_arc` and the
nodal-return rarity signal describe the wealth theme in the PRESENT; this module
projects the dated windows AHEAD by intersecting two independent timing systems:

  1. Jaimini (Sri Lagna × K.N. Rao Chara antardaśā) — WHERE prosperity
     accumulates and WHEN a sub-period energises it (sri_lagna + jaimini).
  2. Vimśottari (planetary MD/AD) — whether a wealth-favourable planetary
     period is running over that same window.

A window where BOTH agree is a converged wealth window — the same "two systems
agreeing beats one system scoring higher" principle the cycle engine is built
on. Conviction is capped at "medium" (never "high") per the forward-engine
discipline: forward accuracy cannot be measured directly.

Voice: this module's output feeds the LLM context (planet/dasha detail allowed,
like arc/rarity context blocks) — it is NOT a bare user chip.
"""
from __future__ import annotations

import datetime as _dt
from typing import Dict, List, Optional

from antar_engine import vimsottari
from antar_engine.jaimini import (
    compute_jaimini_dashas, get_current_dasha, compute_jaimini_antardashas,
)
from antar_engine.sri_lagna import sri_lagna, sri_lagna_activation_windows

# Standard sign lords (Rahu/Ketu are never rasi lords here).
_SIGN_LORD = ["Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
              "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"]
_JAIMINI_LORD_PLANETS = ("Mars", "Venus", "Mercury", "Moon", "Sun",
                         "Jupiter", "Saturn", "Rahu")
_DHANA_KARAKAS = {"Jupiter", "Venus"}       # universal wealth significators


def _lagna_idx(chart_data: dict) -> Optional[int]:
    lg = (chart_data or {}).get("lagna") or {}
    si = lg.get("sign_index")
    return si % 12 if isinstance(si, int) else None


def _planet_sign_map(chart_data: dict) -> Dict[str, int]:
    out = {}
    for p, d in ((chart_data or {}).get("planets") or {}).items():
        si = d.get("sign_index") if isinstance(d, dict) else None
        if isinstance(si, int):
            out[p] = si % 12
    return out


def _house_from_lagna(sign_idx: int, lagna_idx: int) -> int:
    return ((sign_idx - lagna_idx) % 12) + 1


def _wealth_planet_set(chart_data: dict, lagna_idx: int,
                       sl_lord: str) -> set:
    """Planets that carry this chart's wealth: 2nd/11th lords & occupants,
    plus the Sri Lagna lord."""
    psm = _planet_sign_map(chart_data)
    wealth = set()
    if sl_lord:
        wealth.add(sl_lord)
    # 2nd and 11th sign lords (from lagna)
    for h in (2, 11):
        sign = (lagna_idx + (h - 1)) % 12
        wealth.add(_SIGN_LORD[sign])
    # 2nd / 11th occupants
    for p, si in psm.items():
        if _house_from_lagna(si, lagna_idx) in (2, 11):
            wealth.add(p)
    return wealth


def _lord_is_wealth_favourable(lord: str, chart_data: dict, lagna_idx: int,
                               wealth_set: set) -> tuple:
    """(bool, reason). A Vimśottari period lord is wealth-favourable when it is
    a dhana karaka, part of the wealth set, occupies the 2nd/11th, or sits with
    a wealth planet."""
    if not lord:
        return (False, "")
    psm = _planet_sign_map(chart_data)
    si = psm.get(lord)
    # Most specific reasons first.
    if si is not None and _house_from_lagna(si, lagna_idx) in (2, 11):
        h = _house_from_lagna(si, lagna_idx)
        return (True, f"{lord} occupies the {h}th house of wealth/gains")
    for h in (2, 11):
        if _SIGN_LORD[(lagna_idx + (h - 1)) % 12] == lord:
            return (True, f"{lord} rules the {h}th house of wealth/gains")
    if lord in _DHANA_KARAKAS:
        return (True, f"{lord} is a natural wealth significator")
    if lord in wealth_set:
        return (True, f"{lord} is the Sri Lagna lord")
    if si is not None:  # sits with a wealth planet
        for wp in wealth_set:
            wsi = psm.get(wp)
            if wsi is not None and wsi == si and wp != lord:
                h = _house_from_lagna(si, lagna_idx)
                return (True, f"{lord} sits with {wp}, a wealth planet, in the {h}th")
    return (False, "")


def _vimsottari_at(vims: dict, when: _dt.datetime) -> tuple:
    """(md, ad) Vimśottari periods active at `when` (tz-aware)."""
    mds = (vims or {}).get("mahadashas") or []
    ads = (vims or {}).get("antardashas") or []
    md = next((m for m in mds
               if m["start_datetime"] <= when < m["end_datetime"]), None)
    ad = None
    if md:
        ad = next((a for a in ads
                   if a.get("parent_lord") == md["lord"]
                   and a["start_datetime"] <= when < a["end_datetime"]), None)
    return (md, ad)


def _as_dt(d) -> _dt.datetime:
    if isinstance(d, _dt.datetime):
        return d if d.tzinfo else d.replace(tzinfo=_dt.timezone.utc)
    if isinstance(d, _dt.date):
        return _dt.datetime(d.year, d.month, d.day, tzinfo=_dt.timezone.utc)
    return _dt.datetime.strptime(str(d)[:10], "%Y-%m-%d").replace(
        tzinfo=_dt.timezone.utc)


def build_wealth_ignition(chart_data: dict, birth_jd: float,
                          birth_date_str: str = "",
                          now: Optional[_dt.datetime] = None,
                          horizon_years: int = 5,
                          language: str = "en") -> dict:
    """Forward wealth-ignition windows (Jaimini × Vimśottari converged).

    Returns {available, sri_lagna, windows:[...], primary:{...}} or
    {available: False}. Never raises — a forecasting bug must not tank /predict.
    """
    empty = {"available": False}
    try:
        lagna_idx = _lagna_idx(chart_data)
        if lagna_idx is None:
            return empty
        try:
            bdate = _dt.datetime.strptime(str(birth_date_str)[:10], "%Y-%m-%d").date()
        except Exception:
            return empty

        sl = sri_lagna(chart_data)
        if not sl.get("available"):
            return empty

        now = now or _dt.datetime.now(_dt.timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=_dt.timezone.utc)
        horizon = now + _dt.timedelta(days=365 * horizon_years)

        # 1. Chara MD → antardaśās (Jaimini side)
        psm = _planet_sign_map(chart_data)
        mds = compute_jaimini_dashas(lagna_idx, psm, bdate)
        cur_md = get_current_dasha(mds, now.date())
        if not cur_md:
            return empty
        ads = compute_jaimini_antardashas(cur_md, lagna_idx)
        sl_windows = sri_lagna_activation_windows(chart_data, ads, as_of=now.date())

        # 2. Vimśottari timeline (planetary side)
        try:
            vims = vimsottari.calculate_vimsottari_from_chart(chart_data, birth_jd)
        except Exception:
            vims = {}

        wealth_set = _wealth_planet_set(chart_data, lagna_idx, sl.get("lord"))

        windows: List[dict] = []
        for w in sl_windows:
            start = _as_dt(w["start_date"])
            end = _as_dt(w["end_date"])
            if start > horizon:
                continue
            mid = start + (end - start) / 2
            md, ad = _vimsottari_at(vims, mid)
            md_lord = (md or {}).get("lord")
            ad_lord = (ad or {}).get("lord")
            md_fav, md_reason = _lord_is_wealth_favourable(
                md_lord, chart_data, lagna_idx, wealth_set)
            ad_fav, ad_reason = _lord_is_wealth_favourable(
                ad_lord, chart_data, lagna_idx, wealth_set)

            strength = float(w.get("strength") or 0.0)
            converged = (md_fav or ad_fav)
            if strength >= 1.0 and converged:
                tier = "peak"           # Sri Lagna ignition + favourable planet
            elif strength >= 0.7 and converged:
                tier = "strong"         # dhana/gains window + favourable planet
            elif converged:
                tier = "supported"
            else:
                tier = "chara_only"     # Jaimini flags it, planet period neutral
            # conviction discipline: two systems -> medium, else low. Never high.
            conviction = "medium" if converged else "low"

            reasons = [
                f"Chara {w['sign']} sub-period activates the Sri Lagna "
                f"({w['activation']}, {w['house_from_sri_lagna']}th from it)"
            ]
            if md_fav:
                reasons.append(f"Vimśottari {md_lord} major-period supports it — {md_reason}")
            if ad_fav and ad_lord != md_lord:
                reasons.append(f"Vimśottari {ad_lord} sub-period supports it — {ad_reason}")
            if not converged:
                reasons.append(
                    f"Vimśottari period ({md_lord}/{ad_lord}) is neutral for wealth — "
                    f"Jaimini flag only")

            windows.append({
                "start":        start.date().isoformat(),
                "end":          end.date().isoformat(),
                "sign":         w["sign"],
                "activation":   w["activation"],
                "strength":     strength,
                "tier":         tier,
                "conviction":   conviction,
                "vimsottari_md": md_lord,
                "vimsottari_ad": ad_lord,
                "md_favourable": md_fav,
                "ad_favourable": ad_fav,
                "reasons":      reasons,
            })

        if not windows:
            return {"available": False}

        # Primary = soonest ignition PEAK; else soonest strong; else soonest.
        primary = (next((w for w in windows if w["tier"] == "peak"), None)
                   or next((w for w in windows if w["tier"] == "strong"), None)
                   or windows[0])

        return {
            "available": True,
            "sri_lagna": {
                "sign":  sl["sign"],
                "degree": sl["degree"],
                "lord":  sl["lord"],
                "house_from_lagna": sl["house_from_lagna"],
            },
            "windows": windows,
            "primary": primary,
        }
    except Exception as _e:
        print(f"[wealth_ignition] non-blocking failure: {type(_e).__name__}: {_e}")
        return empty


def wealth_ignition_to_context_block(wi: dict) -> str:
    """Serialize the forecast for the LLM prompt (planet/dasha detail allowed,
    like the arc/rarity context blocks). Empty string when unavailable."""
    if not wi or not wi.get("available"):
        return ""
    sl = wi.get("sri_lagna") or {}
    p = wi.get("primary") or {}
    lines = [
        "FORWARD WEALTH-IGNITION (Jaimini × Vimśottari, forward projection):",
        f"- Sri Lagna (wealth reference): {sl.get('degree')}° {sl.get('sign')}, "
        f"lord {sl.get('lord')}, {sl.get('house_from_lagna')}th from ascendant.",
    ]
    if p:
        lines.append(
            f"- PRIMARY window: {p['start']} → {p['end']} "
            f"({p['tier']}, conviction {p['conviction']}). {' '.join(p['reasons'])}")
    others = [w for w in (wi.get("windows") or []) if w is not p][:3]
    for w in others:
        lines.append(
            f"- {w['start']} → {w['end']}: {w['sign']} {w['activation']} "
            f"({w['tier']}, {w['conviction']}).")
    lines.append(
        "Frame the PRIMARY window as the forward wealth-ignition to prepare for, "
        "not a present event. Do not overstate — conviction is capped at medium.")
    return "\n".join(lines)
