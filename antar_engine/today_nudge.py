"""
today_nudge.py — engine-derived day-scale behavioral nudge for the Today card.

Today redesign v2 (Part 3): the daily card carries NO remedy — a remedy
(mantra/gemstone/daan/vrat) operates on the dasha/varshphal timescale and
takes ~21–43 days (a mandala) to act; it is meaningless per-day. Real
remedies live in the Practice tab. Day-scale = TODAY'S MOVE (hora timing)
+ this NUDGE: one light behavioral do/avoid derived from the SAME dominant
signal as the highlight. It tilts the day; it does not "fix" anything.

Rules (founder brief, 2026-06-04):
  * Engine-derived from the day's dominant signal — matches the highlight
    (an adverse-money day nudges "hold off on the purchase", never a
    random "be vegetarian").
  * Culturally concrete (DKP desha): when the nudge involves giving, name
    the real place for the user's culture — mandir/gurudwara, iglesia/
    comedor popular, church — not abstract "perform daan".
  * Framed as a nudge ("tilt the day"), never a prescription or remedy.
  * One nudge, one line. Optional — omitted on a flat quiet day.

Deterministic, zero LLM, zero jargon. English source text; the translation
middleware localizes at response time.
"""

from __future__ import annotations
from typing import Optional

# ── DKP desha: the real giving place per culture ─────────────────────────────
# Keyed by ISO-2 country code (charts.current_country). Full-name aliases
# normalised below. Defaults stay generic but still name real places.
_COUNTRY_ALIAS = {
    "INDIA": "IN", "MEXICO": "MX", "COLOMBIA": "CO", "PERU": "PE",
    "BRAZIL": "BR", "BRASIL": "BR", "ARGENTINA": "AR", "CHILE": "CL",
    "SPAIN": "ES", "USA": "US", "UNITED STATES": "US",
    "UNITED KINGDOM": "GB", "UK": "GB", "CANADA": "CA", "AUSTRALIA": "AU",
    "NEPAL": "NP", "ECUADOR": "EC", "GUATEMALA": "GT", "BOLIVIA": "BO",
    "VENEZUELA": "VE", "URUGUAY": "UY", "PARAGUAY": "PY",
}

_GIVING_PLACE_BY_COUNTRY = {
    # South Asia — mandir / gurudwara
    "IN": "mandir or gurudwara",
    "NP": "mandir",
    "LK": "temple",
    # Latin America — English source ("church"); @translate_response renders
    # "iglesia"/"igreja" on the es path, so en stays clean and es is unchanged.
    "MX": "church", "CO": "church", "EC": "church", "GT": "church",
    "BO": "church", "VE": "church", "UY": "church", "PY": "church",
    "HN": "church", "SV": "church", "NI": "church", "CR": "church",
    "PA": "church", "DO": "church", "CU": "church", "CL": "church",
    "PE": "church or soup kitchen",
    "AR": "church or soup kitchen",
    "BR": "church",
    "ES": "church",
    # Anglosphere
    "US": "church or community kitchen",
    "GB": "church or food bank",
    "CA": "church or food bank",
    "AU": "church or food bank",
}
_GIVING_PLACE_DEFAULT = "church, temple, or community kitchen near you"

# ── Nudge banks — keyed by the engine's lead highlight domain ────────────────
# Adverse day: hold-the-line nudges in the SAME domain the highlight flags.
_ADVERSE_NUDGE = {
    "money":         "Hold off on any big purchase or transfer today — let money sit still.",
    "work":          "Don't lock in new commitments today — keep what you agree to reversible.",
    "relationships": "Go easy in conversations today — let the small frictions pass without comment.",
    "body":          "Keep meals simple and light today, and skip the drink if you can.",
    "mind":          "Go easy on travel and noise today — fewer inputs, clearer head.",
}

# Positive / benefic day: a small act of giving, anchored to the real place.
_POSITIVE_NUDGE = {
    "money":         "Some of today's flow isn't yours to keep — drop a small donation at the {place}.",
    "work":          "Share the credit on what lands today — and leave a small donation at the {place} on your way.",
    "relationships": "Give a little without being asked today — start with a small donation at the {place}.",
    "body":          "Spend an hour of today's energy on someone who needs it — or drop a small donation at the {place}.",
    "mind":          "Put the clarity to generous use — a small donation at the {place} keeps the day flowing your way.",
}


def _giving_place(current_country: str) -> str:
    up = (current_country or "").strip().upper()
    code = up if len(up) == 2 else _COUNTRY_ALIAS.get(up, up[:2])
    return _GIVING_PLACE_BY_COUNTRY.get(code, _GIVING_PLACE_DEFAULT)


def derive_todays_nudge(
    direction: str,
    domains: list,
    current_country: str = "",
    lk_daily: Optional[dict] = None,
) -> Optional[str]:
    """One-line, day-scale behavioral nudge tied to the chosen highlight.

    Returns None on a quiet day (omit the field — no manufactured advice)
    or when no domain was chosen. Never returns a remedy.
    """
    if direction not in ("positive", "adverse") or not domains:
        return None
    lead = domains[0]
    if direction == "adverse":
        return _ADVERSE_NUDGE.get(lead)
    tmpl = _POSITIVE_NUDGE.get(lead)
    if not tmpl:
        return None
    return tmpl.format(place=_giving_place(current_country))
