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

# [faith-neutral P3 2026-07-12] Country != religion. The old map named a specific
# house of worship per country (US -> "church"), which is wrong for anyone of a
# minority faith — e.g. a Sikh in the US being told "church". Lead with a SECULAR
# giving place (universally appropriate charity) and offer "a place of worship"
# generically for those who want the devotional option. English source; the es
# path is LLM-translated by @translate_response.
_GIVING_PLACE_BY_COUNTRY = {
    # South Asia
    "IN": "community kitchen or a place of worship",
    "NP": "community kitchen or a place of worship",
    "LK": "community kitchen or a place of worship",
    # Latin America (soup kitchen / comedor)
    "MX": "soup kitchen or a place of worship", "CO": "soup kitchen or a place of worship",
    "EC": "soup kitchen or a place of worship", "GT": "soup kitchen or a place of worship",
    "BO": "soup kitchen or a place of worship", "VE": "soup kitchen or a place of worship",
    "UY": "soup kitchen or a place of worship", "PY": "soup kitchen or a place of worship",
    "HN": "soup kitchen or a place of worship", "SV": "soup kitchen or a place of worship",
    "NI": "soup kitchen or a place of worship", "CR": "soup kitchen or a place of worship",
    "PA": "soup kitchen or a place of worship", "DO": "soup kitchen or a place of worship",
    "CU": "soup kitchen or a place of worship", "CL": "soup kitchen or a place of worship",
    "PE": "soup kitchen or a place of worship", "AR": "soup kitchen or a place of worship",
    "BR": "soup kitchen or a place of worship", "ES": "soup kitchen or a place of worship",
    # Anglosphere
    "US": "community kitchen or a place of worship",
    "GB": "food bank or a place of worship",
    "CA": "food bank or a place of worship",
    "AU": "food bank or a place of worship",
}
_GIVING_PLACE_DEFAULT = "community kitchen or a place of worship near you"

# ── Nudge banks — keyed by the engine's lead highlight domain ────────────────
# Adverse day: hold-the-line nudges in the SAME domain the highlight flags.
_ADVERSE_NUDGE = {
    "money":         "Hold off on any big purchase or transfer today — let money sit still.",
    "work":          "Don't lock in new commitments today — keep what you agree to reversible.",
    "relationships": "Go easy in conversations today — let the small frictions pass without comment.",
    "body":          "Keep meals simple and light today, and skip the drink if you can.",
    "mind":          "Go easy on travel and noise today — fewer inputs, clearer head.",
}

# Caution lead: the day LIGHTS UP this domain but under real risk (a high-
# reward / high-risk theme — a venture, a journey, a speculative or joint-money
# bet under a demanding chapter). The headline says "take it, but keep a stop",
# so the nudge must speak the SAME lean-in-with-a-cap voice — not the pure
# "avoid it" adverse line, which reads as the card contradicting itself.
_CAUTION_NUDGE = {
    "money":         "Take the money move today if you want it — but keep it small and reversible, and set a hard stop before you commit.",
    "work":          "Push the work forward today, but don't over-promise — take on less than you're tempted to and keep an exit.",
    "relationships": "Lean into the connection today, but don't force the hard conversation — leave yourself room to step back.",
    "body":          "Use the energy today, but don't redline it — keep something in reserve for tomorrow.",
    "mind":          "Take the trip or the risk today if it calls you — but cap the downside and keep one clear exit.",
}

# Positive / benefic day: a small act of giving, anchored to the real place.
_POSITIVE_NUDGE = {
    "money":         "Some of today's flow isn't yours to keep — drop a small donation at the {place}.",
    "work":          "Share the credit on what lands today — and leave a small donation at the {place} on your way.",
    "relationships": "Give a little without being asked today — start with a small donation at the {place}.",
    "body":          "Spend an hour of today's energy on someone who needs it — or drop a small donation at the {place}.",
    "mind":          "Put the clarity to generous use — a small donation at the {place} keeps the day flowing your way.",
}

# [no-income 2026-09-23] When money is strained or income is absent, a
# "drop a small donation" nudge is tone-deaf — it assumes surplus the person
# doesn't have (owner flagged: a user with money strain / NO income was told to
# donate). Non-monetary generosity: give TIME and help, never money.
_POSITIVE_NUDGE_NONMONEY = {
    "money":         "Money's tight today, so don't give it away — but a little of your time for someone who needs it still pays you back.",
    "work":          "Share the credit on what lands today, and lift someone with your time — no money needed.",
    "relationships": "Give a little without being asked today — your attention and a helping hand, not your wallet.",
    "body":          "Spend an hour of today's energy on someone who needs it.",
    "mind":          "Put the clarity to generous use — offer someone your time or a hand today.",
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
    can_give_money: bool = True,
) -> Optional[str]:
    """One-line, day-scale behavioral nudge tied to the chosen highlight.

    Returns None on a quiet day (omit the field — no manufactured advice)
    or when no domain was chosen. Never returns a remedy.

    can_give_money=False (money strained / no income) → the positive "giving"
    nudge switches to NON-MONETARY generosity (time/help), never "donate money".
    """
    if direction not in ("positive", "adverse", "caution") or not domains:
        return None
    lead = domains[0]
    _pos = _POSITIVE_NUDGE if can_give_money else _POSITIVE_NUDGE_NONMONEY
    if direction == "adverse":
        return _ADVERSE_NUDGE.get(lead)
    if direction == "caution":
        # lean-in-with-a-cap; fall back to the giving nudge if the domain
        # has no caution line so the field is never left contradicting.
        _fb = _pos.get(lead, "")
        return _CAUTION_NUDGE.get(lead) or (
            (_fb.format(place=_giving_place(current_country)) if "{place}" in _fb else _fb)
            or None)
    tmpl = _pos.get(lead)
    if not tmpl:
        return None
    return tmpl.format(place=_giving_place(current_country)) if "{place}" in tmpl else tmpl
