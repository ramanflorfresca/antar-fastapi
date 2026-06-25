"""
antar_engine/layered_phrasing.py
────────────────────────────────
LLM phrasing for the layered-fidelity domain fields on This Month / This Year.

DOCTRINE
  Python computes WHAT is true per domain: {domain, conviction, polarity, window,
  seed}. The model only PHRASES it into hook/substance/depth. It may NOT add a
  noun, date or event not in the computed input — enforced by the prompt AND by
  the validators in layered_fields (run on every returned field).

  The Claude client is INJECTED (``claude_call`` async callable: prompt -> text)
  so this module stays free of the global client and is unit-testable with a stub.
  If the call fails or returns junk, a deterministic fallback builds valid fields
  from the seeds — the endpoint must NEVER break or wait on the model to succeed.

  Cycle does NOT use this module (its phase prose already exists — see
  layered_fields.build_phase_fields).
"""

from __future__ import annotations

import json
import re
from typing import Any, Awaitable, Callable, Dict, List, Optional

from antar_engine.layered_fields import (
    CANONICAL_DOMAINS,
    ALT_MONTH,
    ALT_YEAR,
    CONV_HIGH,
    CONV_MED,
    CONV_LOW,
    CONV_NONE,
    route_domain,
    conviction_for_domain,
    assemble_domain_field,
    has_week_date,
)

# The five, in display order. (Spiritual is excluded by doctrine — Practice only.)
FIVE: tuple = CANONICAL_DOMAINS

# Jargon-free labels for fallback copy.
_DOMAIN_LABEL = {
    "career": "work",
    "money": "money",
    "relationships": "relationships",
    "health": "wellbeing",
    "family": "home and family",
}

_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


# ─────────────────────────────────────────────────────────────────────────────
# Window formatting
# ─────────────────────────────────────────────────────────────────────────────
def iso_to_loose(iso: Optional[str]) -> Optional[str]:
    """'2026-06-28' -> 'around Jun 28' (a real, sourced week-level anchor)."""
    if not iso:
        return None
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(iso))
    if not m:
        return None
    mo = int(m.group(2))
    day = int(m.group(3))
    if not (1 <= mo <= 12):
        return None
    return f"around {_MONTHS[mo - 1]} {day}"


# ─────────────────────────────────────────────────────────────────────────────
# Compute per-domain inputs from each surface's existing data
# ─────────────────────────────────────────────────────────────────────────────
def compute_month_inputs(
    deepdive: Dict[str, Any],
    debug: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Build MONTH-altitude inputs from priority_actions + _debug_reasoning.

    Window = the ISO best/caution day already computed in score_day_* (founder
    pick), rendered loose ('around Jun 28'). Conviction = base 1, +1 if the domain
    is a transit-hot domain, +1 if LK-amplified; caution/avoid flips polarity.
    """
    debug = debug or deepdive.get("_debug_reasoning") or {}
    hot = {route_domain(d) for d in (debug.get("transit_hot_domains") or [])}
    lk = debug.get("lk_month") or {}
    amplified = {route_domain(d) for d in (lk.get("amplified") or [])}
    caution = {route_domain(d) for d in (lk.get("caution") or [])}

    best_win = iso_to_loose(debug.get("score_day_best"))
    caution_win = iso_to_loose(debug.get("score_day_caution"))

    # seed copy: the existing priority_actions action per (normalised) domain
    seeds: Dict[str, str] = {}
    for pa in (deepdive.get("priority_actions") or []):
        dom = route_domain(pa.get("domain"))
        if dom and dom not in seeds and pa.get("action"):
            seeds[dom] = str(pa["action"])

    inputs: List[Dict[str, Any]] = []
    for dom in FIVE:
        is_hot = dom in hot
        is_amp = dom in amplified
        is_caut = dom in caution
        conv = CONV_LOW + (1 if is_hot else 0) + (1 if is_amp else 0)
        conv = min(conv, CONV_HIGH)
        if is_caut:
            polarity = "caution"
            window = caution_win
        elif is_hot or is_amp:
            polarity = "positive"
            window = best_win
        else:
            polarity = "steady"
            window = None
            conv = min(conv, CONV_LOW)  # quiet domain reads directional
        inputs.append({
            "domain": dom,
            "conviction": conv,
            "polarity": polarity,
            "window": window,
            "seed": seeds.get(dom, ""),
            "altitude": ALT_MONTH,
        })
    return inputs


def compute_year_inputs(year_view: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build YEAR-altitude inputs from year.areas[] (arc-level, NO week dates).

    Conviction falls back to the area's strength bars (founder Decision 1: bars are
    the fallback when no precision spine is present on this surface). Polarity from
    bars + the care flag. Seed = area note.
    """
    areas = year_view.get("areas") or []
    by_dom: Dict[str, Dict[str, Any]] = {}
    for a in areas:
        dom = route_domain(a.get("name"))
        if not dom:
            continue
        bars = a.get("bars")
        care = bool(a.get("care"))
        prev = by_dom.get(dom)
        # keep the strongest-signal area if two map to the same domain
        if prev is None or (isinstance(bars, int) and bars > prev.get("_bars", -1)):
            by_dom[dom] = {"_bars": bars if isinstance(bars, int) else None,
                           "care": care, "note": a.get("note") or ""}

    inputs: List[Dict[str, Any]] = []
    for dom in FIVE:
        row = by_dom.get(dom)
        bars = row.get("_bars") if row else None
        care = row.get("care") if row else False
        note = row.get("note") if row else ""
        conv = conviction_for_domain(bars=bars)
        if care:
            polarity = "caution"
        elif isinstance(bars, int) and bars >= 2:
            polarity = "positive"
        elif isinstance(bars, int) and bars == 0:
            polarity = "pressure"
        else:
            polarity = "steady"
        inputs.append({
            "domain": dom,
            "conviction": conv,
            "polarity": polarity,
            "window": None,            # YEAR altitude: never a week window
            "seed": note,
            "altitude": ALT_YEAR,
        })
    return inputs


def monthly_handoff_text(language: str = "en") -> str:
    """Static closing nudge for the Year surface."""
    return "For dated moves, check This Month."


# ─────────────────────────────────────────────────────────────────────────────
# Prompt
# ─────────────────────────────────────────────────────────────────────────────
_DOTS = {0: "0 (no signal — directional only)",
         1: "1 (low — directional only, no specific event)",
         2: "2 (medium — name the domain, SOFTEN: 'may', 'tends to', NO hard event)",
         3: "3 (high — you MAY name the concrete event + its window)"}


def build_prompt(inputs: List[Dict[str, Any]], altitude: str, language: str) -> str:
    alt_rule = (
        "MONTH altitude: the hook is a DATED move. If a window is given, weave it in "
        "verbatim. Be concrete about the near-term action."
        if altitude == ALT_MONTH else
        "YEAR altitude: the hook is the ARC of the domain across the whole year. "
        "ABSOLUTELY NO week-level dates, no day numbers, no 'this week'. Months/seasons "
        "are fine only as broad strokes."
    )
    lang_rule = ("Write in English." if language == "en"
                 else f"Write the entire response in {language}.")

    blocks = []
    for i in inputs:
        win = i.get("window") or "no dated window — do NOT invent one"
        seed = i.get("seed") or "(no prior note — keep it a calm directional read)"
        blocks.append(
            f'- domain "{i["domain"]}": conviction {_DOTS.get(i["conviction"], i["conviction"])}; '
            f'tone={i["polarity"]}; window={win}; '
            f'source_note="{seed}"'
        )
    body = "\n".join(blocks)

    return f"""You phrase pre-computed life-guidance into reader-facing copy for a
life-navigation app. You are a STYLIST, not a forecaster. Every fact — the domain,
the timing window, how certain it is — is already decided below. You only choose words.

HARD RULES
- Do NOT introduce any date, month, day-number or event that is not in the input.
  If a domain has "no dated window", your copy for it must contain NO date at all.
- Conviction governs boldness. A 2-dot domain may NOT say "will happen" / "lands this
  week" / "guaranteed". Use "may", "tends to", "is favoured". Only a 3-dot domain may
  name a concrete event.
- {alt_rule}
- No astrology words, no planet names, no house numbers, no "energy". Plain life nouns.
- {lang_rule}

For EACH domain below, write three tiers:
  hook       — ONE vivid line (the headline the reader sees first)
  substance  — 2-3 sentences, always visible
  depth      — one fuller paragraph (tap to expand)

INPUT (already computed — phrase, never originate):
{body}

Return ONLY a JSON object keyed by domain, each value an object with keys
"hook","substance","depth". No prose outside the JSON."""


def parse_response(text: str) -> Dict[str, Dict[str, str]]:
    """Robustly pull the JSON object out of the model reply."""
    if not text:
        return {}
    s = text.strip()
    # strip code fences
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s, flags=re.IGNORECASE).strip()
    try:
        obj = json.loads(s)
    except Exception:
        m = re.search(r"\{.*\}", s, re.DOTALL)
        if not m:
            return {}
        try:
            obj = json.loads(m.group(0))
        except Exception:
            return {}
    if not isinstance(obj, dict):
        return {}
    out: Dict[str, Dict[str, str]] = {}
    for k, v in obj.items():
        if isinstance(v, dict):
            out[route_domain(k) or str(k)] = {
                "hook": str(v.get("hook") or ""),
                "substance": str(v.get("substance") or ""),
                "depth": str(v.get("depth") or ""),
            }
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Deterministic fallback (used when the model fails OR a field fails validation)
# ─────────────────────────────────────────────────────────────────────────────
def _fallback_copy(inp: Dict[str, Any]) -> Dict[str, str]:
    dom = inp["domain"]
    label = _DOMAIN_LABEL.get(dom, dom)
    seed = (inp.get("seed") or "").strip()
    win = inp.get("window")
    conv = inp.get("conviction", 0)
    if inp["altitude"] == ALT_MONTH:
        if conv >= CONV_HIGH and win:
            hook = f"A clear opening in {label} — {win}."
        elif inp["polarity"] == "caution" and win:
            hook = f"Go gently with {label} {win}."
        elif conv >= CONV_MED:
            hook = f"{label.capitalize()} may move this month — stay ready."
        else:
            hook = f"{label.capitalize()} stays steady this month."
    else:  # YEAR — never a week date
        if conv >= CONV_HIGH:
            hook = f"{label.capitalize()} is where the year concentrates — position early."
        elif conv >= CONV_MED:
            hook = f"{label.capitalize()} tends to build across the year."
        else:
            hook = f"{label.capitalize()} stays steady through the year."
    substance = seed or hook
    depth = seed or substance
    return {"hook": hook, "substance": substance, "depth": depth}


def _build_one(inp: Dict[str, Any], phrased: Dict[str, Dict[str, str]],
               language: str) -> Optional[Dict[str, Any]]:
    copy = phrased.get(inp["domain"]) or {}
    if not copy.get("hook"):
        copy = _fallback_copy(inp)
    windows = [inp["window"]] if inp.get("window") else []
    field = assemble_domain_field(
        domain=inp["domain"],
        polarity=inp["polarity"],
        conviction=inp["conviction"],
        altitude=inp["altitude"],
        hook=copy.get("hook", ""),
        substance=copy.get("substance", ""),
        depth=copy.get("depth", ""),
        language=language,
        sourced_windows=windows,
    )
    if field is None:
        return None
    if not field.get("_valid"):
        # the model broke a rule — rebuild from the safe deterministic template
        fb = _fallback_copy(inp)
        field = assemble_domain_field(
            domain=inp["domain"], polarity=inp["polarity"],
            conviction=inp["conviction"], altitude=inp["altitude"],
            hook=fb["hook"], substance=fb["substance"], depth=fb["depth"],
            language=language, sourced_windows=windows,
        )
        if field is not None:
            field["_fallback"] = True
    return field


async def phrase_domains(
    inputs: List[Dict[str, Any]],
    altitude: str,
    language: str,
    claude_call: Optional[Callable[[str], Awaitable[str]]],
) -> List[Dict[str, Any]]:
    """Orchestrate: prompt -> model -> parse -> assemble+validate per domain.

    Returns the domains[] list (always the five, minus any practice-routed). Never
    raises; on any failure each field falls back to deterministic copy.
    """
    phrased: Dict[str, Dict[str, str]] = {}
    if claude_call is not None:
        try:
            text = await claude_call(build_prompt(inputs, altitude, language))
            phrased = parse_response(text)
        except Exception as e:  # noqa: BLE001
            print(f"[layered_phrasing] model call failed, using fallback: {e}")
            phrased = {}

    out: List[Dict[str, Any]] = []
    for inp in inputs:
        field = _build_one(inp, phrased, language)
        if field is not None:
            out.append(field)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Self-test (sandbox: python antar_engine/layered_phrasing.py)
# ─────────────────────────────────────────────────────────────────────────────
def _selftest() -> int:
    import asyncio

    failures: List[str] = []

    def check(name: str, cond: bool) -> None:
        if not cond:
            failures.append(name)

    # iso window
    check("iso loose", iso_to_loose("2026-06-28") == "around Jun 28")
    check("iso bad→None", iso_to_loose("nope") is None)

    # month inputs
    deepdive = {
        "priority_actions": [
            {"domain": "career", "action": "Line up the role conversation."},
            {"domain": "wealth", "action": "Review the cash runway."},
            {"domain": "spiritual", "action": "Sit quietly each morning."},  # → practice
        ],
        "_debug_reasoning": {
            "transit_hot_domains": ["career"],
            "lk_month": {"amplified": ["career"], "caution": ["health"]},
            "score_day_best": "2026-06-28",
            "score_day_caution": "2026-07-03",
        },
    }
    mi = compute_month_inputs(deepdive)
    check("month has 5", len(mi) == 5)
    check("month domains == FIVE", [x["domain"] for x in mi] == list(FIVE))
    career = next(x for x in mi if x["domain"] == "career")
    check("career hot+amp→conv3", career["conviction"] == 3)
    check("career window=best", career["window"] == "around Jun 28")
    health = next(x for x in mi if x["domain"] == "health")
    check("health caution polarity", health["polarity"] == "caution")
    check("health window=caution", health["window"] == "around Jul 3")
    check("money seed carried", next(x for x in mi if x["domain"] == "money")["seed"] == "Review the cash runway.")

    # year inputs
    year_view = {"areas": [
        {"name": "Career", "bars": 3, "care": False, "note": "Strong — favourable."},
        {"name": "Identity", "bars": 1, "care": False, "note": "Steady."},
        {"name": "Wellbeing", "bars": 0, "care": True, "note": "Under pressure."},
    ]}
    yi = compute_year_inputs(year_view)
    check("year has 5", len(yi) == 5)
    yc = next(x for x in yi if x["domain"] == "career")
    check("year career bars3→conv3", yc["conviction"] == 3)
    check("year career no window", yc["window"] is None)
    yh = next(x for x in yi if x["domain"] == "health")
    check("year health care→caution", yh["polarity"] == "caution")

    # prompt mentions altitude rule
    p = build_prompt(mi, ALT_MONTH, "en")
    check("month prompt dated", "DATED move" in p)
    py = build_prompt(yi, ALT_YEAR, "en")
    check("year prompt no-week", "NO week-level dates" in py)

    # parse response
    parsed = parse_response('```json\n{"career": {"hook":"h","substance":"s","depth":"d"}}\n```')
    check("parse fenced json", parsed.get("career", {}).get("hook") == "h")

    # phrase with a GOOD stub model
    async def good_call(prompt: str) -> str:
        # year stub must avoid week dates; month may include the given window
        obj = {}
        for dom in FIVE:
            obj[dom] = {"hook": f"{dom} reads calm and clear",
                        "substance": f"{dom} substance line.",
                        "depth": f"{dom} depth paragraph."}
        return json.dumps(obj)

    out_y = asyncio.run(phrase_domains(yi, ALT_YEAR, "en", good_call))
    check("year out 5", len(out_y) == 5)
    check("year out all valid", all(f["_valid"] for f in out_y))
    check("year out no week date", all(not has_week_date(f["hook"]) for f in out_y))
    check("year out has core keys", all(
        all(k in f for k in ("domain", "status_label", "status_color", "conviction",
                             "hook", "substance", "depth")) for f in out_y))

    # phrase with a BAD stub: model injects a week date into a YEAR hook → must
    # fall back to deterministic (no week date), field still valid
    async def bad_call(prompt: str) -> str:
        obj = {d: {"hook": "the deal will close Jul 25", "substance": "x", "depth": "y"}
               for d in FIVE}
        return json.dumps(obj)

    out_bad = asyncio.run(phrase_domains(yi, ALT_YEAR, "en", bad_call))
    check("bad→all valid via fallback", all(f["_valid"] for f in out_bad))
    check("bad→no week date leaked", all(not has_week_date(f["hook"]) for f in out_bad))
    check("bad→fallback flagged", all(f.get("_fallback") for f in out_bad))

    # model entirely down (None) → deterministic fallback, still five valid
    out_none = asyncio.run(phrase_domains(mi, ALT_MONTH, "en", None))
    check("none→5 valid", len(out_none) == 5 and all(f["_valid"] for f in out_none))
    # month high-conviction career must carry its sourced window
    oc = next(f for f in out_none if f["domain"] == "career")
    check("none month career has window", has_week_date(oc["hook"]))

    if failures:
        print(f"SELFTEST FAIL ({len(failures)}): " + "; ".join(failures))
        return 1
    print("SELFTEST PASS — all layered_phrasing checks green")
    return 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
