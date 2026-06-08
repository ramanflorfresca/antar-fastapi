"""
antar_engine/domain_anchor.py
─────────────────────────────
WS2 + WS3 of the "kill the generic read" sprint.

THE CORE FIX (per cowork brief):
  Before the narrator builds /predict's answer, decide whether the asked
  life area has a DOMAIN-MATCHED signal in any of the already-computed
  layers. If yes → narrate as today (proven good for property et al.).
  If no → the prompt MUST take an honest path (flat read or cross-domain
  redirect) and MUST NOT manufacture generic pressure dressed in
  domain vocabulary.

Specificity tracks domain-matched signal availability, not narrator
quality. Live diagnostic confirmed: speculation question got the property
rarity signal (correct), narrator correctly ignored it as off-topic, and
then fell back to a generic template. That fallback IS the bug.

This module:
  1. Computes `has_domain_anchor(concern, ...)` against rarity_signals,
     precision_windows, the layered predictions dict, and the live
     transit map.
  2. Surfaces a `redirect_candidate` — a strong, non-fungible signal for
     a DIFFERENT area — so the narrator can say:
        "Speculation is flat for you today. What is actually live is
         property, and it is a rare window."
  3. Builds the strict instruction block the prompt uses when no anchor
     exists. The block BANS manufactured pressure and names the two
     allowed framings (flat / redirect).
  4. Runs a post-generation guard that detects manufactured-pressure
     language in the no-anchor case and reports it so main.py can
     either re-prompt or fall through to the honest template.

This is the *only* place the no-anchor decision is made. main.py wires
it in once, near the existing rarity_signals / precision_windows block.
"""

from __future__ import annotations
from typing import Any, Dict, Iterable, List, Optional, Tuple

from antar_engine.life_area_map import area_houses, area_karakas, get_life_area


# ─────────────────────────────────────────────────────────────────────
# Anchor detection
# ─────────────────────────────────────────────────────────────────────

# Houses (1..12) → rough domain themes. Used to score whether a
# rarity_signal that names planets (e.g. ["Saturn","Mars"]) plausibly
# touches the asked area — we map the planets through karakas, AND we
# inspect the signal's title/message text for the area's keywords.
_AREA_KEYWORDS: Dict[str, List[str]] = {
    "speculation":    ["speculation", "speculative", "gamble", "lottery", "stock", "trade", "trading", "bet", "crypto"],
    "property":       ["property", "real estate", "home", "house", "land", "apartment", "flat", "rent"],
    "career":         ["career", "job", "work", "profession", "promotion", "boss", "office"],
    "finance":        ["finance", "money", "income", "revenue", "cashflow", "cash flow", "funding", "capital"],
    "wealth":         ["wealth", "rich", "wealthy", "abundance", "fortune", "net worth"],
    "loss":           ["loss", "drain", "debt", "bankrupt", "ruined"],
    "marriage":       ["marriage", "spouse", "husband", "wife", "married"],
    "love":           ["love", "romance", "dating", "boyfriend", "girlfriend", "partner"],
    "reconciliation": ["reconcile", "reunite", "back together"],
    "divorce":        ["divorce", "separation", "split", "breakup"],
    "health":         ["health", "body", "illness", "energy", "fatigue", "healing"],
    "foreign":        ["foreign", "abroad", "overseas", "relocat", "visa"],
    "spiritual":      ["spiritual", "purpose", "dharma", "meaning", "soul"],
    "family":         ["family", "home", "mother", "father"],
    "children":       ["child", "children", "son", "daughter", "baby", "pregnan"],
    "general":        ["life", "direction", "purpose"],
}


def _normalised_concern(concern: Optional[str]) -> str:
    if not concern:
        return "general"
    return str(concern).strip().lower() or "general"


def _planets_overlap(signal_planets: Iterable[Any], karakas: Iterable[str]) -> bool:
    if not signal_planets or not karakas:
        return False
    norm_karakas = {str(k).strip().lower() for k in karakas if k}
    for p in signal_planets:
        if not p:
            continue
        if str(p).strip().lower() in norm_karakas:
            return True
    return False


def _text_mentions_area(text: str, concern: str) -> bool:
    if not text:
        return False
    t = str(text).lower()
    for kw in _AREA_KEYWORDS.get(concern, []):
        if kw in t:
            return True
    return False


def _scan_precision_windows(
    precision_windows: List[Dict[str, Any]],
    concern: str,
) -> Optional[Dict[str, Any]]:
    """find_precision_windows runs scoped to `concern` already, so a
    window with score >= 6 is by definition a domain-matched anchor."""
    for w in precision_windows or []:
        try:
            score = float(w.get("score", 0))
        except (TypeError, ValueError):
            score = 0.0
        if score >= 6.0:
            return {
                "source": "precision_window",
                "detail": w.get("date_range") or w.get("window_label") or "precision window",
                "score": score,
            }
    return None


def _scan_rarity_signals(
    rarity_signals: List[Dict[str, Any]],
    concern: str,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Return (anchor, redirect_candidate).

    - anchor: a rarity signal that maps to the asked concern (via karaka
      planet overlap OR keyword match in title/message).
    - redirect_candidate: the strongest (rarity_score >= 7) signal that
      does NOT map to the asked concern — surfaced so a no-anchor answer
      can pivot to it honestly.
    """
    karakas = area_karakas(concern)
    anchor: Optional[Dict[str, Any]] = None
    redirect: Optional[Dict[str, Any]] = None

    for sig in rarity_signals or []:
        text_blob = " ".join(
            str(sig.get(k, "")) for k in ("title", "message", "what_to_do", "type")
        )
        planet_match = _planets_overlap(sig.get("planets", []), karakas)
        text_match = _text_mentions_area(text_blob, concern)

        if planet_match or text_match:
            if anchor is None or float(sig.get("rarity_score", 0)) > float(anchor.get("score", 0)):
                anchor = {
                    "source": "rarity_signal",
                    "detail": sig.get("title") or sig.get("type") or "rare signal",
                    "score": float(sig.get("rarity_score", 0)),
                    "matched_via": "planets" if planet_match else "keywords",
                }
            continue

        # Not a match for the asked concern — but maybe a strong
        # cross-domain candidate worth surfacing as a redirect.
        try:
            r_score = float(sig.get("rarity_score", 0))
        except (TypeError, ValueError):
            r_score = 0.0
        if r_score >= 7.0:
            if redirect is None or r_score > float(redirect.get("score", 0)):
                redirect = {
                    "source": "rarity_signal",
                    "detail": sig.get("title") or sig.get("type") or "rare signal",
                    "score": r_score,
                    "message": sig.get("message", ""),
                    "rarity_label": sig.get("rarity", ""),
                    "planets": sig.get("planets", []),
                    "what_to_do": sig.get("what_to_do", ""),
                    # Best-effort guess at which area this redirect belongs to —
                    # used only for the prompt's framing line.
                    "guessed_area": _guess_area_from_text(
                        " ".join(str(sig.get(k, "")) for k in ("title", "message", "type"))
                    ),
                }
    return anchor, redirect


def _guess_area_from_text(text: str) -> Optional[str]:
    if not text:
        return None
    t = text.lower()
    for area, kws in _AREA_KEYWORDS.items():
        if area == "general":
            continue
        for kw in kws:
            if kw in t:
                return area
    return None


def _scan_predictions(
    predictions: Dict[str, Any],
    concern: str,
) -> Optional[Dict[str, Any]]:
    """Walks layered predictions for a hit on the asked area's houses or
    karakas. Tolerant to multiple shapes (each layer entry might be a
    str, dict with 'planet'/'house', or nested dict)."""
    if not predictions:
        return None
    houses = set(area_houses(concern))
    karakas = {k.lower() for k in area_karakas(concern)}

    for layer_key in ("layer_1", "layer_2", "layer_3", "layer_4"):
        entries = predictions.get(layer_key) or []
        for entry in entries:
            blob = ""
            houses_in_entry: List[int] = []
            planets_in_entry: List[str] = []
            if isinstance(entry, dict):
                # common shapes
                for hk in ("house", "transit_house", "natal_house"):
                    v = entry.get(hk)
                    if isinstance(v, int):
                        houses_in_entry.append(v)
                hl = entry.get("houses") or entry.get("activated_houses")
                if isinstance(hl, list):
                    for h in hl:
                        if isinstance(h, int):
                            houses_in_entry.append(h)
                for pk in ("planet", "planets", "karaka"):
                    v = entry.get(pk)
                    if isinstance(v, str):
                        planets_in_entry.append(v)
                    elif isinstance(v, list):
                        planets_in_entry.extend(str(x) for x in v if x)
                blob = " ".join(
                    str(entry.get(k, "")) for k in ("title", "prediction", "message", "rule_id")
                )
            else:
                blob = str(entry)

            if any(h in houses for h in houses_in_entry):
                return {
                    "source": layer_key,
                    "detail": f"house {[h for h in houses_in_entry if h in houses][0]}",
                    "score": 1.0,
                }
            if any(p.lower() in karakas for p in planets_in_entry):
                return {
                    "source": layer_key,
                    "detail": f"karaka {next(p for p in planets_in_entry if p.lower() in karakas)}",
                    "score": 1.0,
                }
            if blob and _text_mentions_area(blob, concern):
                return {
                    "source": layer_key,
                    "detail": "text match",
                    "score": 0.5,
                }
    return None


def _scan_transits(
    current_transits: Any,
    chart_data: Optional[Dict[str, Any]],
    concern: str,
) -> Optional[Dict[str, Any]]:
    """Karaka transit hitting any of the area's houses from lagna counts
    as a domain-matched anchor (matches what precision_windows scores at
    Dimension 2)."""
    if not current_transits or not chart_data:
        return None

    SIGNS = [
        "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
        "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces",
    ]
    def sidx(name: str) -> Optional[int]:
        try:
            return SIGNS.index(name)
        except (ValueError, TypeError):
            return None

    try:
        lagna_sign = (chart_data.get("lagna") or {}).get("sign", "")
    except AttributeError:
        return None
    lagna_idx = sidx(lagna_sign)
    if lagna_idx is None:
        return None

    karakas = {k for k in area_karakas(concern)}
    houses = set(area_houses(concern))

    # current_transits can be {planet: {sign:...}} dict or list of dicts.
    iter_pairs: List[Tuple[str, str]] = []
    if isinstance(current_transits, dict):
        for p, v in current_transits.items():
            if isinstance(v, dict):
                s = v.get("sign") or v.get("current_sign") or v.get("transit_sign") or ""
            else:
                s = str(v) if v else ""
            iter_pairs.append((str(p), s))
    elif isinstance(current_transits, list):
        for t in current_transits:
            if isinstance(t, dict):
                iter_pairs.append((
                    str(t.get("planet", t.get("name", ""))),
                    str(t.get("current_sign", t.get("sign", t.get("transit_sign", "")))),
                ))

    for planet, sign in iter_pairs:
        if planet not in karakas:
            continue
        s_idx = sidx(sign)
        if s_idx is None:
            continue
        house = ((s_idx - lagna_idx) % 12) + 1
        if house in houses:
            return {
                "source": "transit",
                "detail": f"{planet} in house {house}",
                "score": 1.0,
            }
    return None


def has_domain_anchor(
    concern: str,
    rarity_signals: Optional[List[Dict[str, Any]]] = None,
    precision_windows: Optional[List[Dict[str, Any]]] = None,
    predictions: Optional[Dict[str, Any]] = None,
    current_transits: Any = None,
    chart_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Decide whether the asked area has a domain-matched signal.

    Returns a dict with:
      - has_anchor        : bool
      - matched_via       : str or None  (which source caught it)
      - anchor            : dict or None (the matching signal summary)
      - redirect_candidate: dict or None (a strong cross-domain signal)
      - concern           : normalised concern
    """
    concern_n = _normalised_concern(concern)

    # 1. precision_windows is scoped to concern by construction —
    #    a score >= 6 is the cheapest, strongest anchor signal.
    anchor = _scan_precision_windows(precision_windows or [], concern_n)
    matched_via = "precision_window" if anchor else None

    # 2. rarity_signals (and redirect_candidate as a side effect).
    r_anchor, redirect = _scan_rarity_signals(rarity_signals or [], concern_n)
    if anchor is None and r_anchor:
        anchor = r_anchor
        matched_via = "rarity_signal"

    # 3. layered predictions.
    if anchor is None:
        p_anchor = _scan_predictions(predictions or {}, concern_n)
        if p_anchor:
            anchor = p_anchor
            matched_via = p_anchor["source"]

    # 4. live transits of karaka planets to area houses.
    if anchor is None:
        t_anchor = _scan_transits(current_transits, chart_data, concern_n)
        if t_anchor:
            anchor = t_anchor
            matched_via = "transit"

    return {
        "has_anchor": anchor is not None,
        "matched_via": matched_via,
        "anchor": anchor,
        "redirect_candidate": redirect,
        "concern": concern_n,
    }


# ─────────────────────────────────────────────────────────────────────
# Prompt-side instruction (WS2 + WS3 narration contract)
# ─────────────────────────────────────────────────────────────────────

def build_no_anchor_instruction(
    concern: str,
    redirect_candidate: Optional[Dict[str, Any]] = None,
) -> str:
    """The strict instruction block injected into the system prompt when
    no domain-matched signal exists. Bans manufactured pressure and
    names the two allowed framings."""
    concern_n = _normalised_concern(concern)

    lines: List[str] = [
        "",
        "═══ DOMAIN ANCHOR GATE — NO SIGNAL ═══",
        f"DETECTED: the asked life area ({concern_n}) has NO chart- or",
        "  day-specific anchor right now. No rarity signal, precision",
        "  window, dated dasha/transit hit, yoga, or personal-mirror",
        f"  layer is pointing at {concern_n} for this user today.",
        "",
        "HARD RULES — DO NOT VIOLATE:",
        f"  1. NEVER manufacture pressure about {concern_n}. Do not invent",
        f"     urgency, friction, opportunity, or a generic-but-true",
        "     timing story dressed in the area's vocabulary. That reads",
        "     as a horoscope — and we just decided not to ship horoscopes.",
        "  2. NEVER use templated lines like 'wait until ___ to decide',",
        "     '... is risky today', or 'the pressure lifts' unless a",
        "     CONCRETE date or condition is bound to the same sentence.",
        "  3. NEVER end the answer with a refinement / fishing question.",
        "     Answer completely, end on the move, stop.",
        "",
        "ALLOWED FRAMINGS — pick ONE:",
    ]

    if redirect_candidate:
        guessed = redirect_candidate.get("guessed_area") or "another life area"
        rarity = redirect_candidate.get("rarity_label") or "rare"
        title = redirect_candidate.get("detail") or "a rare signal"
        msg = (redirect_candidate.get("message") or "")[:280]
        lines += [
            "  (a) CROSS-DOMAIN REDIRECT — preferred when stronger:",
            f"      {concern_n.title()} itself is flat for you right now.",
            f"      What IS live is {guessed} — {title} ({rarity}).",
            f"      Anchor that pivot in the actual rarity signal:",
            f"        \"{msg}\"",
            "      Tell the user that's the higher-value answer today,",
            "      and give them the move on that, not on the asked area.",
            "",
            "  (b) HONEST FLAT READ — if (a) doesn't fit:",
            f"      Nothing unusual is active for {concern_n} for you",
            "      today; this is a neutral window. Say so plainly.",
            "      Give YOUR MOVE based on baseline practice, not on",
            "      manufactured timing.",
        ]
    else:
        lines += [
            "  (a) HONEST FLAT READ:",
            f"      Nothing unusual is active for {concern_n} for you",
            "      today; this is a neutral window. Say so plainly,",
            "      directly, in the user's language. Give YOUR MOVE",
            "      based on baseline practice — not on manufactured",
            "      timing.",
        ]

    lines += [
        "",
        "Keep YOUR MOVE. Keep DOMAIN_VOCABULARY (use domain nouns —",
        "  runway, leverage, positioning — not vague energetic terms).",
        "  This rule is the SHAPE of the answer, not its vocabulary.",
        "═══ END DOMAIN ANCHOR GATE ═══",
        "",
    ]
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────
# WS3 post-generation guard
# ─────────────────────────────────────────────────────────────────────

# Manufactured-pressure phrases the no-anchor path must NOT emit.
# Each pattern is checked case-insensitively. The list is conservative
# — only catch language that asserts day-specific urgency without an
# anchor.
_MANUFACTURED_PRESSURE = [
    "is risky today",
    "is risky right now",
    "pressure lifts",
    "the pressure to act",
    "this window won't stay open",
    "this window will not stay open",
    "act before this window closes",
    "before the window closes",
    "urgency is building",
    "the timing is rare and deliberate",
    "wait until to ",
    "wait until when ",
    "wait until ___",
    "wait until --",
]


def detect_manufactured_pressure(text: str) -> List[str]:
    """Return list of forbidden snippets present in `text`. Empty list
    means clean."""
    if not text:
        return []
    t = text.lower()
    return [p for p in _MANUFACTURED_PRESSURE if p in t]


def has_anchor_violation(plain_summary: str, signal_line: str) -> bool:
    """True if the no-anchor path nonetheless emitted manufactured
    pressure. main.py uses this to decide whether to re-prompt or fall
    through to the honest template."""
    blobs = " ".join(s for s in (plain_summary or "", signal_line or "") if s)
    return bool(detect_manufactured_pressure(blobs))


# ─────────────────────────────────────────────────────────────────────
# Fallback honest-flat / redirect templates (used only if a re-prompt
# also fails — never overwrite a clean Claude answer).
# ─────────────────────────────────────────────────────────────────────

def build_honest_flat_fallback(concern: str, language: str = "en") -> Dict[str, str]:
    """Last-resort plain text the narration contract allows."""
    concern_n = _normalised_concern(concern)
    if (language or "en").lower().startswith("es"):
        signal_line = f"{concern_n.title()} está neutral hoy — nada especial está activo."
        plain_summary = (
            f"Hoy no hay una señal específica en tu carta para {concern_n}. "
            "No es una ventana excepcional ni una de fricción — es neutral. "
            "Actúa con tu base habitual; no fuerces nada porque la fecha lo pida."
        )
    else:
        signal_line = f"{concern_n.title()} is flat for you today — no specific signal."
        plain_summary = (
            f"Today is a neutral window for {concern_n}. Nothing unusual is "
            "active in your chart for this area right now — neither a rare "
            "opening nor a real friction. Act from your baseline; do not "
            "force a move because the date demands one."
        )
    return {"signal_line": signal_line, "plain_summary": plain_summary}


def build_redirect_fallback(
    concern: str,
    redirect_candidate: Dict[str, Any],
    language: str = "en",
) -> Dict[str, str]:
    """Honest cross-domain redirect when the redirect_candidate is strong."""
    concern_n = _normalised_concern(concern)
    guessed = (redirect_candidate or {}).get("guessed_area") or "another life area"
    msg = ((redirect_candidate or {}).get("message") or "").strip()
    rarity = ((redirect_candidate or {}).get("rarity_label") or "rare").strip()

    if (language or "en").lower().startswith("es"):
        signal_line = f"{concern_n.title()} está neutral — lo que sí está activo es {guessed}."
        plain_summary = (
            f"Hoy {concern_n} no tiene una señal específica en tu carta. "
            f"Lo que sí está vivo es {guessed} — una ventana {rarity}. "
            f"{msg[:280]}"
        ).strip()
    else:
        signal_line = f"{concern_n.title()} is flat — what's actually live is {guessed}."
        plain_summary = (
            f"{concern_n.title()} itself has no chart-specific signal for you "
            f"today. What IS live is {guessed} — a {rarity} window. "
            f"{msg[:280]}"
        ).strip()
    return {"signal_line": signal_line, "plain_summary": plain_summary}
