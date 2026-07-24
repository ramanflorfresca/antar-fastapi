"""
antar_engine/wealth_ignition.py
===============================
Forward wealth-ignition forecast — the two-system converged wealth window.

This is the forward projection the engine was missing. `chapter_arc` and the
nodal-return rarity signal describe the wealth theme in the PRESENT; this module
projects dated windows AHEAD by intersecting two independent timing systems that
are ALREADY computed and stored in `dasha_periods` for every chart:

  1. Jaimini Chara (system='jaimini') — the moving rāśi MD + antardaśā. WHERE
     prosperity accumulates (Sri Lagna) and WHEN a sub-period energises it.
  2. Vimśottari (system='vimshottari') — whether a wealth-favourable planetary
     period is running over that same window.

A window where BOTH agree is a converged wealth window — the same "two systems
agreeing beats one system scoring higher" principle the cycle engine is built
on. Conviction is capped at "medium" (never "high") per the forward-engine
discipline: forward accuracy cannot be measured directly.

The Chara antardaśās are READ from the stored production rows (written by
jaimini_engine.generate_dasha_rows at onboarding / backfill_chara_dasha.py) —
this module does NOT recompute them, so it inherits the engine's authoritative
Chara method for every chart. Callers pass the `get_dashas_for_chart()` result.

Voice: output feeds the LLM context (planet/dasha detail allowed, like the
arc/rarity context blocks) — it is NOT a bare user chip.
"""
from __future__ import annotations

import datetime as _dt
from typing import Dict, List, Optional

from antar_engine.sri_lagna import sri_lagna, sri_lagna_activation_windows, SIGNS

# Standard sign lords (Rahu/Ketu are never rāśi lords here).
_SIGN_LORD = ["Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
              "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"]
_SIGN_IDX = {name: i for i, name in enumerate(SIGNS)}
_DHANA_KARAKAS = {"Jupiter", "Venus"}       # universal wealth significators
_MD_LEVELS = {"mahadasha", "md", "1", "1.0"}
_AD_LEVELS = {"antardasha", "ad", "2", "2.0"}


# ── stored-row helpers ──────────────────────────────────────────────────────

def _level(r: dict) -> str:
    return str(r.get("level") or r.get("type") or "").strip().lower()


def _sign_of(r: dict) -> str:
    return str(r.get("planet_or_sign") or r.get("lord_or_sign") or "").strip()


def _pd(s) -> Optional[_dt.date]:
    if isinstance(s, _dt.datetime):
        return s.date()
    if isinstance(s, _dt.date):
        return s
    try:
        return _dt.datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def _pdt(s) -> Optional[_dt.datetime]:
    d = _pd(s)
    return _dt.datetime(d.year, d.month, d.day, tzinfo=_dt.timezone.utc) if d else None


def _dashas_key(dashas: dict, *names) -> list:
    for n in names:
        rows = (dashas or {}).get(n)
        if rows:
            return rows
    return []


def _chara_windows_from_rows(jaimini_rows: list,
                             now_date: _dt.date) -> List[dict]:
    """Current Chara MD's antardaśā windows, from stored jaimini rows."""
    mds = [r for r in jaimini_rows if _level(r) in _MD_LEVELS]
    cur = next((r for r in mds
                if _pd(r.get("start_date") or r.get("start")) is not None
                and _pd(r["start_date"]) <= now_date <= _pd(r["end_date"])), None)
    if not cur:
        return []
    s, e = _pd(cur["start_date"]), _pd(cur["end_date"])
    ads = [r for r in jaimini_rows if _level(r) in _AD_LEVELS
           and _pd(r.get("start_date")) and s <= _pd(r["start_date"]) <= e]
    out = []
    for r in sorted(ads, key=lambda x: str(x.get("start_date"))):
        sign = _sign_of(r)
        si = _SIGN_IDX.get(sign)
        if si is None:
            continue
        out.append({"sign": sign, "sign_index": si,
                    "start_date": _pd(r["start_date"]),
                    "end_date": _pd(r["end_date"])})
    return out


def _vims_from_rows(vim_rows: list) -> dict:
    """Normalise stored vimśottari rows to {mahadashas, antardashas} with
    tz-aware datetimes, matching vimsottari.calculate_vimsottari_from_chart."""
    mds, ads = [], []
    for r in vim_rows:
        rec = {"lord": _sign_of(r),
               "start_datetime": _pdt(r.get("start_date") or r.get("start")),
               "end_datetime": _pdt(r.get("end_date") or r.get("end")),
               "parent_lord": r.get("parent_lord", "")}
        if not rec["start_datetime"] or not rec["end_datetime"]:
            continue
        lv = _level(r)
        if lv in _MD_LEVELS:
            mds.append(rec)
        elif lv in _AD_LEVELS:
            ads.append(rec)
    return {"mahadashas": mds, "antardashas": ads}


# ── chart / favourability helpers ───────────────────────────────────────────

def _lagna_idx(chart_data: dict) -> Optional[int]:
    si = ((chart_data or {}).get("lagna") or {}).get("sign_index")
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


def _wealth_planet_set(chart_data: dict, lagna_idx: int, sl_lord: str) -> set:
    psm = _planet_sign_map(chart_data)
    wealth = set()
    if sl_lord:
        wealth.add(sl_lord)
    for h in (2, 11):
        wealth.add(_SIGN_LORD[(lagna_idx + (h - 1)) % 12])
    for p, si in psm.items():
        if _house_from_lagna(si, lagna_idx) in (2, 11):
            wealth.add(p)
    return wealth


def _lord_is_wealth_favourable(lord: str, chart_data: dict, lagna_idx: int,
                               wealth_set: set) -> tuple:
    if not lord:
        return (False, "")
    psm = _planet_sign_map(chart_data)
    si = psm.get(lord)
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
    if si is not None:
        for wp in wealth_set:
            wsi = psm.get(wp)
            if wsi is not None and wsi == si and wp != lord:
                h = _house_from_lagna(si, lagna_idx)
                return (True, f"{lord} sits with {wp}, a wealth planet, in the {h}th")
    return (False, "")


def _vimsottari_at(vims: dict, when: _dt.datetime) -> tuple:
    """(md, ad) Vimśottari periods active at `when`. AD matched by date within
    the active MD (parent_lord used only as a tie-break when present)."""
    mds = (vims or {}).get("mahadashas") or []
    ads = (vims or {}).get("antardashas") or []
    md = next((m for m in mds
               if m["start_datetime"] <= when < m["end_datetime"]), None)
    ad = None
    if md:
        cands = [a for a in ads if a["start_datetime"] <= when < a["end_datetime"]]
        ad = next((a for a in cands if a.get("parent_lord") == md["lord"]),
                  cands[0] if cands else None)
    return (md, ad)


def build_wealth_ignition(chart_data: dict, dashas: Optional[dict] = None,
                          birth_jd: Optional[float] = None,
                          birth_date_str: str = "",
                          now: Optional[_dt.datetime] = None,
                          horizon_years: int = 5,
                          language: str = "en") -> dict:
    """Forward wealth-ignition windows (stored Jaimini Chara × Vimśottari).

    `dashas` is the get_dashas_for_chart() result (needs the 'jaimini' and
    'vimshottari' systems). Returns {available, sri_lagna, windows, primary} or
    {available: False}. Never raises — a forecasting bug must not tank /predict.
    """
    empty = {"available": False}
    try:
        lagna_idx = _lagna_idx(chart_data)
        if lagna_idx is None:
            return empty
        sl = sri_lagna(chart_data)
        if not sl.get("available"):
            return empty

        now = now or _dt.datetime.now(_dt.timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=_dt.timezone.utc)
        horizon = now + _dt.timedelta(days=365 * horizon_years)

        # 1. Jaimini Chara antardaśās — READ from stored production rows.
        jrows = _dashas_key(dashas or {}, "jaimini", "chara")
        chara_windows = _chara_windows_from_rows(jrows, now.date())
        if not chara_windows:
            # No authoritative Chara rows for this chart → no forecast (rather
            # than recompute with a non-production method).
            return empty
        sl_windows = sri_lagna_activation_windows(
            chart_data, chara_windows, as_of=now.date())
        if not sl_windows:
            return empty

        # 2. Vimśottari — stored rows preferred; birth_jd fallback.
        vrows = _dashas_key(dashas or {}, "vimshottari", "vimsottari")
        if vrows:
            vims = _vims_from_rows(vrows)
        elif birth_jd:
            try:
                from antar_engine import vimsottari
                vims = vimsottari.calculate_vimsottari_from_chart(chart_data, birth_jd)
            except Exception:
                vims = {}
        else:
            vims = {}

        wealth_set = _wealth_planet_set(chart_data, lagna_idx, sl.get("lord"))

        windows: List[dict] = []
        for w in sl_windows:
            start = _pdt(w["start_date"])
            end = _pdt(w["end_date"])
            if start is None or start > horizon:
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
                tier = "peak"
            elif strength >= 0.7 and converged:
                tier = "strong"
            elif converged:
                tier = "supported"
            else:
                tier = "chara_only"
            conviction = "medium" if converged else "low"  # never high

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
                "start":         start.date().isoformat(),
                "end":           end.date().isoformat(),
                "sign":          w["sign"],
                "activation":    w["activation"],
                "strength":      strength,
                "tier":          tier,
                "conviction":    conviction,
                "vimsottari_md": md_lord,
                "vimsottari_ad": ad_lord,
                "md_favourable": md_fav,
                "ad_favourable": ad_fav,
                "reasons":       reasons,
            })

        if not windows:
            return empty

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
    """Serialize the forecast for the LLM prompt. Empty when unavailable."""
    if not wi or not wi.get("available"):
        return ""
    sl = wi.get("sri_lagna") or {}
    p = wi.get("primary") or {}
    lines = [
        "FORWARD WEALTH-IGNITION (Jaimini Chara × Vimśottari, forward projection):",
        f"- Sri Lagna (wealth reference): {sl.get('degree')}° {sl.get('sign')}, "
        f"lord {sl.get('lord')}, {sl.get('house_from_lagna')}th from ascendant.",
    ]
    if p:
        lines.append(
            f"- PRIMARY window: {p['start']} → {p['end']} "
            f"({p['tier']}, conviction {p['conviction']}). {' '.join(p['reasons'])}")
    for w in [w for w in (wi.get("windows") or []) if w is not p][:3]:
        lines.append(
            f"- {w['start']} → {w['end']}: {w['sign']} {w['activation']} "
            f"({w['tier']}, {w['conviction']}).")
    lines.append(
        "Frame the PRIMARY window as the forward wealth-ignition to prepare for, "
        "not a present event. Do not overstate — conviction is capped at medium.")
    return "\n".join(lines)
