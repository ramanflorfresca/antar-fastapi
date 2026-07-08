"""
today_highlight.py — "highlight, not horoscope" selection engine for the Today card.

GOAL (Slice 1: layers A + C; layer B / patra prior lands in Slice 2):
  The ENGINE deterministically picks the 1–2 life-domains that actually dominate
  today and commits to a direction (clearly positive OR clearly adverse, or an
  honest "quiet day"). It never offers a five-domain buffet, and it never lets an
  LLM choose the domain. The committed headline + highlight text are built here
  from the jargon-free template banks so the output is fully deterministic and
  testable; a later slice can hand the chosen domains to Claude for richer prose.

LAYERS (a weighting that converges — NOT a fallback ladder):
  A — Moon at arrival (attention): the house the current Moon transits FROM THE
      LAGNA flags which life-area is "live" today. Soft tilt.
  C — Chart reality (the deterministic confirm/veto): the Lal-Kitab daily
      diagnostic's per-domain amplify/avoid (already chart-personalized) plus the
      day score / friction flag give the real per-domain signal + direction.
  (B — patra prior + behaviour: added in Slice 2; this module accepts an optional
      `patra_tilt` dict now so the wiring is forward-compatible.)

OUTPUT (engine -> endpoint): chosen domain(s), direction, strength, a committed
headline, a 3–4 line highlight, the hora windows tied to the highlight, and an
internal `_debug` blob that MUST NOT be rendered.

ZERO jargon leaves this module: no planet names, houses, nakshatras, dashas, or
Sanskrit in any field except `_debug`.
"""

from __future__ import annotations
from typing import Optional

from antar_engine import highlight_templates as T
from antar_engine import life_areas as _LA

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

# Canonical (frontend-locked) domains this engine commits to.
SELECTABLE = ("money", "work", "relationships", "body", "mind")

# Whole-sign house (counted from the lagna) -> (primary domain, polarity_bias).
# polarity_bias: +1 benefic house, -1 dusthana (6/8/12), 0 neutral. Used only as
# a tilt on Layer A — the truth of direction still comes from Layer C.
HOUSE_DOMAIN = {
    1:  ("body", 0),
    2:  ("money", +1),
    3:  ("work", +1),
    4:  ("relationships", +1),
    5:  ("mind", +1),
    6:  ("body", -1),
    7:  ("relationships", 0),
    8:  ("money", -1),
    9:  ("work", +1),
    10: ("work", +1),
    11: ("money", +1),
    12: ("mind", -1),
}

# Committed headline phrasings (jargon-free). {d} = plain domain phrase.
_DOMAIN_PHRASE = {
    "money":         "money",
    "work":          "work",
    "relationships": "the people around you",
    "body":          "your energy and health",
    "mind":          "clear thinking",
}
_HEADLINE_DOMAIN = {  # short form for the headline line
    "money":         "money",
    "work":          "work",
    "relationships": "relationships",
    "body":          "your body",
    "mind":          "your head",
}

# Plain "do X in the good window / avoid Y in the bad window" verbs per domain.
_BEST_FOR = {
    "money":         "the money move you've been putting off — send the invoice, make the ask, close the number",
    "work":          "the work that needs to be seen — ship it, present it, push the decision",
    "relationships": "the conversation that matters — make the call, mend the rift, say the thing",
    "body":          "anything physical — movement, a check-up, the appointment you've delayed",
    "mind":          "the thinking work — plan, write, decide what's been sitting unresolved",
}
_AVOID_WHAT = {
    "money":         "committing money or signing anything financial",
    "work":          "locking in big commitments or forcing a decision",
    "relationships": "hard conversations or confrontation",
    "body":          "overexerting or pushing through fatigue",
    "mind":          "choices that need a sharp, calm head",
}


def _moon_house_from_lagna(moon_sign: str, lagna_idx: int) -> Optional[int]:
    """Whole-sign house (1–12) the current Moon occupies counted from the lagna."""
    if moon_sign not in SIGNS:
        return None
    return (SIGNS.index(moon_sign) - lagna_idx) % 12 + 1


def _norm_domains(values) -> list:
    """LK fine domains -> locked palette, filtered to SELECTABLE."""
    out = []
    for v in (values or []):
        d = T.lk_micro_to_domain(v)
        # LK maps some micro-domains to meta buckets (watch/opportunity); fold
        # those back onto a selectable domain so they can be highlighted.
        if d == "opportunity":
            d = "work"
        if d == "watch":
            continue
        if d in SELECTABLE and d not in out:
            out.append(d)
    return out


def _overall_direction(score, day_quality_for_user):
    """Coarse day direction from the deterministic score + LK day quality.
    Returns (bias_float, decisive_bool). bias: + favourable, - adverse."""
    bias = 0.0
    decisive = False
    try:
        s = int(score)
        if s >= 7:
            bias += 1.0; decisive = True
        elif s <= 3:
            bias -= 1.0; decisive = True
        elif s >= 6:
            bias += 0.4
        elif s <= 4:
            bias -= 0.4
    except Exception:
        pass
    q = (day_quality_for_user or "").strip().lower()
    if q in ("excellent", "very good", "good", "favorable", "favourable"):
        bias += 0.6; decisive = decisive or q in ("excellent", "very good")
    elif q in ("adverse", "difficult", "challenging", "poor", "bad", "caution"):
        bias -= 0.6; decisive = decisive or q in ("adverse", "difficult", "poor", "bad")
    return bias, decisive


def _build_evidence(debug: dict, chosen: list, lead_dir: str) -> dict:
    """Stable, admin/dev-visible audit trail. Every daily read is
    explainable as votes -> net -> chosen -> direction. NOT a user-
    facing field; the endpoint keeps it in the payload for inspection
    but never renders it. Schema is stable across the coarse-domain and
    (later) house-anchored life-area taxonomies — only the values get
    finer."""
    return {
        "votes": list(debug.get("votes") or []),
        "net": dict(debug.get("net") or {}),
        "mag": dict(debug.get("mag") or {}),
        "chosen": list(chosen or []),
        "lead_dir": lead_dir,
        "dasha_tone": debug.get("dasha_tone", ""),
    }


def select_today_highlight(
    *,
    signal0: dict,
    lk_daily: dict,
    natal_chart: dict,
    panchanga: dict,
    patra_tilt: Optional[dict] = None,
    dasha: Optional[dict] = None,
) -> dict:
    """Pick 1–2 dominant domains + direction + committed headline/highlight + hora.

    All inputs are already computed elsewhere in the daily pipeline; this is pure
    selection + narration, no astronomy.
    """
    signal0 = signal0 or {}
    lk_daily = lk_daily or {}
    natal_chart = natal_chart or {}
    panchanga = panchanga or {}
    patra_tilt = patra_tilt or {}          # Slice 2 fills this; soft, never overrides.
    dasha = dasha or {}                     # Source D: running MD/AD lord + tone.

    # ── lagna index (reuse the same whole-sign convention as ask_consultation) ──
    lagna = natal_chart.get("lagna", {})
    lagna_idx = 0
    if isinstance(lagna, dict):
        si = lagna.get("sign_index")
        if isinstance(si, int) and 0 <= si <= 11:
            lagna_idx = si
        elif lagna.get("sign") in SIGNS:
            lagna_idx = SIGNS.index(lagna["sign"])
    elif isinstance(lagna, str) and lagna in SIGNS:
        lagna_idx = SIGNS.index(lagna)

    moon_sign = signal0.get("moon_sign") or signal0.get("today_moon_sign") or ""
    score = signal0.get("score", 5)

    # Per-life-area running tallies: positive vs adverse evidence.
    pos = {a: 0.0 for a in _LA.AREAS}
    neg = {a: 0.0 for a in _LA.AREAS}
    debug = {"votes": [], "lagna_idx": lagna_idx, "moon_sign": moon_sign, "score": score}

    # ── Layer C — Lal-Kitab per-domain amplify/avoid (chart-personalised truth) ──
    # This is the most specific signal we have — it must outrank the generic
    # Moon-attention tilt (layer A), so it carries the heaviest single weight.
    _amp_seen = []
    for _micro in (lk_daily.get("domains_amplified_today") or []):
        a = _LA.lk_micro_to_area(_micro)
        if a and a not in _amp_seen:
            _amp_seen.append(a)
            pos[a] += 3.5
            debug["votes"].append(f"C:lk_amplify:{a}:+3.5")
    _avd_seen = []
    for _micro in (lk_daily.get("domains_to_avoid_today") or []):
        a = _LA.lk_micro_to_area(_micro)
        if a and a not in _avd_seen:
            _avd_seen.append(a)
            neg[a] += 3.5
            debug["votes"].append(f"C:lk_avoid:{a}:-3.5")

    # ── Layer C — overall day direction (score + LK day quality) ────────────────
    day_bias, day_decisive = _overall_direction(score, lk_daily.get("day_quality_for_user"))
    debug["day_bias"] = round(day_bias, 2)
    debug["day_decisive"] = day_decisive

    # ── Layer A — Moon house from lagna tilts the "live" domain ────────────────
    # When the day's overall direction is DECISIVE, the attention domain is itself
    # a committed highlight even without an LK per-domain vote (LK is often
    # unavailable in prod — chart JSONB stored as a string / empty). On a genuinely
    # flat day the tilt stays small, so the honest "quiet day" still wins.
    house = _moon_house_from_lagna(moon_sign, lagna_idx)
    if house:
        a_area = _LA.HOUSE_TO_AREA.get(house, "work")
        a_pol = _LA.AREA_POLARITY.get(a_area, 0)
        a_weight = 1.6 + (1.6 if day_decisive else 0.0)
        # polarity follows the day's overall direction, nudged by whether the
        # transited house is a benefic house or a dusthana.
        lean = day_bias + (0.4 * a_pol)
        if lean >= 0:
            pos[a_area] += a_weight
        else:
            neg[a_area] += a_weight
        debug["votes"].append(
            f"A:moon_house{house}:{a_area}:{'+' if lean>=0 else '-'}{a_weight}")

    # ── Layer B placeholder — soft patra tilt (Slice 2 supplies it) ────────────
    for d, w in (patra_tilt.items() if isinstance(patra_tilt, dict) else []):
        a = d if d in _LA.AREAS else _LA.area_from_coarse(d)
        if a in pos:
            _wt = min(float(w), 1.0)            # capped soft tilt, never an override
            pos[a] += _wt
            debug["votes"].append(f"B:patra:{a}:+{_wt}")

    # ── Source D — dasha lord (the running chapter's through-line) ─────────────
    # The MD/AD lord votes on the life-areas it rules + occupies, at a MODEST
    # weight: faint alone (below the selection bar), decisive only when it
    # CONVERGES with the Moon/LK on the same area — the "this is my whole
    # chapter" reinforcement. Its tone tag rides along for the narrator whether
    # or not the area is chosen. Direction follows the day's overall lean.
    _lagna_sign = SIGNS[lagna_idx] if 0 <= lagna_idx <= 11 else ""
    try:
        from antar_engine.lk_trigger import _natal_planets as _dh_np
        _dasha_np = _dh_np(natal_chart)
    except Exception:
        _dasha_np = {}
    for _lvl, _dw in (("md", 1.5), ("ad", 0.8)):
        _lord = (dasha.get(f"{_lvl}_lord") or dasha.get(_lvl) or "").strip().title()
        if not _lord:
            continue
        if not debug.get("dasha_tone"):
            _tone = _LA.dasha_tone(_lord)
            if _tone:
                debug["dasha_tone"] = _tone
                debug["dasha_lord_level"] = _lvl
        for _area, _h in _LA.dasha_votes(_lagna_sign, _dasha_np, _lord):
            if day_bias >= 0:
                pos[_area] += _dw
                debug["votes"].append(f"D:dasha_{_lvl}h{_h}:{_area}:+{_dw}")
            else:
                neg[_area] += _dw
                debug["votes"].append(f"D:dasha_{_lvl}h{_h}:{_area}:-{_dw}")

    # ── Resolve: net weight + direction per domain ─────────────────────────────
    net = {a: pos[a] - neg[a] for a in _LA.AREAS}
    mag = {a: pos[a] + neg[a] for a in _LA.AREAS}     # how much evidence at all
    ranked = sorted(_LA.AREAS, key=lambda a: (mag[a], abs(net[a])), reverse=True)
    debug["net"] = {a: round(net[a], 2) for a in _LA.AREAS if mag[a] > 0}
    debug["mag"] = {a: round(mag[a], 2) for a in _LA.AREAS if mag[a] > 0}

    # Decisiveness bar: the top domain needs real evidence AND a clear polarity.
    # The 2nd domain bar is HIGHER so the generic attention tilt doesn't get
    # paired onto every decisive day — two domains only when both are strongly
    # evidenced (e.g. two explicit chart signals).
    # [Fix D] Coverage: a decisive-lead bar keeps a genuinely flat day
    # honest (still the quiet-day template), then sweep in EVERY other area
    # carrying real evidence — Yogi's whole-life breadth, but only across
    # computed votes. Strongest-first, capped so it stays readable.
    LEAD_MAG = 3.0
    FLOOR_MAG = 1.5
    FLOOR_NET = 0.5
    MAX_AREAS = 5
    top = ranked[0]
    chosen = []
    if mag[top] >= LEAD_MAG and abs(net[top]) >= 1.0:
        chosen.append(top)
        for _a in ranked[1:]:
            if len(chosen) >= MAX_AREAS:
                break
            if mag[_a] >= FLOOR_MAG and abs(net[_a]) >= FLOOR_NET:
                chosen.append(_a)

    # ── Hora windows (already-computed panchanga; jargon-free clock strings) ────
    best_window = panchanga.get("abhijit_muhurta") or panchanga.get("abhijit") or panchanga.get("best_time") or ""
    avoid_window = panchanga.get("rahu_kalam") or panchanga.get("avoid_time") or ""

    if not chosen:
        # Honest quiet day — no manufactured drama, no five-domain hedge.
        debug["chosen"] = []
        debug["lead_dir"] = "quiet"
        hora = {
            "best_window": best_window,
            "best_for": "the one thing that actually matters today — keep it simple",
            "avoid_window": avoid_window,
            "avoid_what": "starting anything big or making it more complicated than it is",
        }
        return {
            "headline": "A quiet day — hold steady and consolidate.",
            "highlight": ("Nothing is pulling hard in any one direction today. "
                          "That's not a flat day — it's a good one to tidy loose ends, "
                          "rest, and keep momentum without forcing anything new."),
            "highlight_domains": [],
            "highlight_areas": [],
            "direction": "quiet",
            "strength": "low",
            "hora": hora,
            "todays_move": hora,
            "evidence": _build_evidence(debug, [], "quiet"),
            "_debug_reasoning": debug,
        }

    # Direction of the lead (fine) area decides the committed tone; the
    # deterministic headline/hora fall back to the coarse collapse so the
    # frontend-locked palette and downstream theme maps keep working.
    lead = chosen[0]
    lead_dir = "positive" if net[lead] >= 0 else "adverse"
    strength = "high" if mag[lead] >= 5.0 else "medium"
    chosen_coarse = _LA.collapse(chosen)
    lead_c = chosen_coarse[0]

    # ── Committed headline ──────────────────────────────────────────────────
    if len(chosen_coarse) == 2:
        d2 = chosen[1]
        d2c = chosen_coarse[1]
        d2_dir = "positive" if net[d2] >= 0 else "adverse"
        if lead_dir == d2_dir == "positive":
            headline = f"A strong day for {_HEADLINE_DOMAIN[lead_c]} and {_HEADLINE_DOMAIN[d2c]}."
        elif lead_dir == d2_dir == "adverse":
            headline = f"Go carefully with {_HEADLINE_DOMAIN[lead_c]} and {_HEADLINE_DOMAIN[d2c]} today."
        elif lead_dir == "positive":
            headline = f"Strong on {_HEADLINE_DOMAIN[lead_c]}, but tread lightly with {_HEADLINE_DOMAIN[d2c]}."
        else:
            headline = f"Tread lightly with {_HEADLINE_DOMAIN[lead_c]}, but {_HEADLINE_DOMAIN[d2c]} is working for you."
    else:
        if lead_dir == "positive":
            headline = f"Today is a strong day for {_HEADLINE_DOMAIN[lead_c]}."
        else:
            headline = f"Go carefully with {_HEADLINE_DOMAIN[lead_c]} today."

    # ── 3–4 line highlight, built only from chosen domains (jargon-free banks) ──
    lines = []
    _line_seen = set()
    for d in chosen:
        c = _LA.coarse_of(d)
        if c in _line_seen:
            continue
        _line_seen.add(c)
        if (net[d] >= 0):
            lines.append(T.AMPLIFIED_BY_DOMAIN.get(c, T.AMPLIFIED_BY_DOMAIN["opportunity"]))
        else:
            lines.append(T.AVOID_BY_DOMAIN.get(c, T.AVOID_BY_DOMAIN["work"]))
    highlight = " ".join(lines)

    # ── Hora tied to the lead domain ──────────────────────────────────────────
    if lead_dir == "positive":
        best_for = _BEST_FOR.get(lead_c, "what matters most today")
        avoid_what = _AVOID_WHAT.get(lead_c, "forcing anything that can wait")
    else:
        # adverse lead: the good window is for low-stakes progress; the bad window
        # is precisely where this domain is most fragile.
        best_for = "low-stakes progress and prep — keep the big moves for a better day"
        avoid_what = _AVOID_WHAT.get(lead_c, "forcing the issue")

    hora = {
        "best_window": best_window,
        "best_for": best_for,
        "avoid_window": avoid_window,
        "avoid_what": avoid_what,
    }

    debug["chosen"] = chosen
    debug["chosen_coarse"] = chosen_coarse
    debug["lead_dir"] = lead_dir
    return {
        "headline": headline,
        "highlight": highlight,
        "highlight_domains": chosen_coarse,
        "highlight_areas": chosen,
        "direction": lead_dir,
        "strength": strength,
        "hora": hora,
        "todays_move": hora,
        "evidence": _build_evidence(debug, chosen, lead_dir),
        "_debug_reasoning": debug,
    }
