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
    route_domain_strict,
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

# Sentiment read of a priority-action seed → polarity. Clean signal: the action
# text itself ("favours bold moves" = positive; "energy drops, delay costs" =
# caution). This replaces the noisy lk_month/transit vocab for polarity.
_CAUTION_WORDS = (
    "drop", "delay", "cost", "avoid", "careful", "gently", "gentle", "postpone",
    "scatter", "tangle", "caution", "risk", "slow", "hold off", "protect",
    "drain", "conflict", "strain", "difficult", "watch", "guard", "rest",
    "overcommit", "stretched", "tension", "friction",
)
_POSITIVE_WORDS = (
    "favour", "favor", "bold", "opening", "opportunit", "gain", "sharp",
    "strong", "advance", "push", "launch", "pursue", "momentum", "win",
    "breakthrough", "ask for", "step up", "seize", "expand", "thrive",
)


def _seed_polarity(text: str) -> str:
    """positive | caution | steady, read from the action text."""
    t = (text or "").lower()
    if not t.strip():
        return "steady"
    caut = sum(1 for w in _CAUTION_WORDS if w in t)
    pos = sum(1 for w in _POSITIVE_WORDS if w in t)
    if caut > pos:
        return "caution"
    if pos > 0:
        return "positive"
    return "positive"  # an action with no caution cue = an opportunity to act


def _week_label(week_text: Optional[str]) -> Optional[str]:
    """Trim 'Week of June 22 — bold career moves pay off' → 'Week of June 22'."""
    if not week_text:
        return None
    head = re.split(r"\s+[—–-]\s+", str(week_text), 1)[0].strip()
    return head or None


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
    """Build MONTH-altitude inputs. SPINE = priority_actions (clean, dated,
    domain-tagged). Polarity is read from the action TEXT (not the noisy
    lk_month/transit vocab). Window is WEEK-level: best_week for positive,
    caution_week for caution (month-shape, not a single-day pinpoint).

    The 'sourced' list carries EVERY real computed date-string for a domain so
    the no-hallucination validator passes genuine dates (priority_actions dates,
    best_week / caution_week, score_day_*) and only fails invented ones.
    """
    debug = debug or deepdive.get("_debug_reasoning") or {}
    # strict map: drop noisy labels instead of bucketing them into career
    hot = {d for d in (route_domain_strict(x) for x in
                       (debug.get("transit_hot_domains") or [])) if d}

    best_week = _week_label(deepdive.get("best_week"))
    caution_week = _week_label(deepdive.get("caution_week"))
    best_loose = iso_to_loose(debug.get("score_day_best"))
    caution_loose = iso_to_loose(debug.get("score_day_caution"))

    # seed copy: the existing priority_actions action per (normalised) domain
    seeds: Dict[str, str] = {}
    for pa in (deepdive.get("priority_actions") or []):
        dom = route_domain(pa.get("domain"))
        if dom and dom not in seeds and pa.get("action"):
            seeds[dom] = str(pa["action"])

    # everything date-bearing is "sourced" — shared across domains.
    # [blocker2-harden] include EVERY priority_actions action string (all
    # domains), not just each domain's own seed, so a real computed date
    # echoed into another domain's copy still validates. A date present
    # anywhere in the computed input is SOURCED and must PASS.
    _all_action_texts = [str(pa.get("action")) for pa in (deepdive.get("priority_actions") or [])
                         if pa.get("action")]
    base_sourced = [s for s in (best_week, caution_week, best_loose, caution_loose,
                                deepdive.get("best_week"), deepdive.get("caution_week"),
                                *_all_action_texts)
                    if s]

    inputs: List[Dict[str, Any]] = []
    for dom in FIVE:
        seed = seeds.get(dom, "")
        has_action = bool(seed)
        is_hot = dom in hot
        if has_action:
            polarity = _seed_polarity(seed)
        else:
            polarity = "steady"
        conv = CONV_LOW + (1 if has_action else 0) + (1 if is_hot else 0)
        conv = min(conv, CONV_HIGH)
        if polarity == "caution":
            window = caution_week or caution_loose
        elif polarity == "positive" and has_action:
            window = best_week or best_loose
        else:
            polarity = "steady"
            window = None
            conv = min(conv, CONV_LOW)  # quiet domain reads directional
        sourced = list(base_sourced)
        if seed:
            sourced.append(seed)  # the action text's own dates are sourced
        if window:
            sourced.append(window)
        inputs.append({
            "domain": dom,
            "conviction": conv,
            "polarity": polarity,
            "window": window,
            "seed": seed,
            "sourced": sourced,
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
            "sourced": [],             # arc-level: no dates to source
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
        "MONTH altitude: the hook describes the MONTH'S SHAPE and points to the named "
        "WEEK window for that domain (e.g. 'the week of June 22'), not a single-day "
        "pinpoint. Keep the week wording you are given. Sentiment MUST match the tone: "
        "a 'positive' domain's week is an opening/opportunity; a 'caution' domain's week "
        "is one to move gently or protect — NEVER describe a caution week as an 'opening'."
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
    Label = label[:1].upper() + label[1:]
    seed = (inp.get("seed") or "").strip()
    win = inp.get("window")
    polarity = inp.get("polarity", "steady")
    if inp["altitude"] == ALT_MONTH:
        # Sentiment MUST match polarity — never call a caution week an "opening".
        if polarity == "caution" and win:
            hook = f"Go gently with {label} — {win} is the stretch that needs care."
        elif polarity == "caution":
            hook = f"Ease off in {label} this month; protect your energy."
        elif polarity == "positive" and win:
            hook = f"{Label} opens up this month — {win} is the one to use."
        elif polarity == "positive":
            hook = f"{Label} is favoured this month — stay ready to act."
        else:
            hook = f"{Label} stays steady this month."
    else:  # YEAR — never a week date
        if polarity == "caution":
            hook = f"{Label} asks for care across the year — pace yourself."
        elif inp.get("conviction", 0) >= CONV_HIGH:
            hook = f"{Label} is where the year concentrates — position early."
        elif inp.get("conviction", 0) >= CONV_MED:
            hook = f"{Label} tends to build across the year."
        else:
            hook = f"{Label} stays steady through the year."
    substance = seed or hook
    # give depth a distinct second beat even in fallback (avoid substance==depth)
    if seed:
        depth = f"{seed} Treat it as the month's shape, not a fixed appointment."
    else:
        depth = f"{hook} Let it stay a gentle direction rather than a hard plan."
    return {"hook": hook, "substance": substance, "depth": depth}


def build_fallback_domains(inputs: List[Dict[str, Any]], language: str) -> List[Dict[str, Any]]:
    """Deterministic domains[] — NO model call. Served immediately on the cold
    path (Option A); the phrased version is computed in the background and cached.
    """
    out: List[Dict[str, Any]] = []
    for inp in inputs:
        field = _build_one(inp, {}, language)
        if field is not None:
            field["_cold"] = True
            out.append(field)
    return out


def _build_one(inp: Dict[str, Any], phrased: Dict[str, Dict[str, str]],
               language: str) -> Optional[Dict[str, Any]]:
    copy = phrased.get(inp["domain"]) or {}
    if not copy.get("hook"):
        copy = _fallback_copy(inp)
    windows = list(inp.get("sourced") or ([inp["window"]] if inp.get("window") else []))
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

    # month inputs — mirrors the real de0c6265 payload (clean priority_actions
    # spine + noisy lk_month vocab that must be IGNORED for polarity)
    deepdive = {
        "best_week": "Week of June 22 — bold career moves pay off",
        "caution_week": "Week of June 15 — communication tangles and energy scatters",
        "priority_actions": [
            {"domain": "career", "action": "Ask your boss for the promotion during the week of June 8 — timing favors bold moves at work."},
            {"domain": "health", "action": "Book a check-up for that recurring complaint before June 22 — your energy drops after that and the delay costs you."},
            {"domain": "learning", "action": "Finish one creative project by June 15 while your focus is sharp."},  # → career (already seeded)
            {"domain": "spiritual", "action": "Sit quietly each morning."},  # → practice (dropped)
        ],
        "_debug_reasoning": {
            "transit_hot_domains": ["health", "learning", "career"],
            "lk_month": {"amplified": ["emotion", "action", "trade"],
                         "caution": ["comfort", "initiative", "luxury"]},
            "score_day_best": "2026-06-25",
            "score_day_caution": "2026-06-17",
        },
    }
    mi = compute_month_inputs(deepdive)
    check("month has 5", len(mi) == 5)
    check("month domains == FIVE", [x["domain"] for x in mi] == list(FIVE))
    career = next(x for x in mi if x["domain"] == "career")
    check("career positive (not caution)", career["polarity"] == "positive")
    check("career action+hot→conv3", career["conviction"] == 3)
    check("career window=best week", career["window"] == "Week of June 22")
    health = next(x for x in mi if x["domain"] == "health")
    check("health caution from 'drops/delay/costs'", health["polarity"] == "caution")
    check("health window=caution week", health["window"] == "Week of June 15")
    money = next(x for x in mi if x["domain"] == "money")
    check("money no action→steady/no window", money["polarity"] == "steady" and money["window"] is None)
    # noisy lk_month labels must NOT pollute (career stayed positive, not caution)
    check("lk noise ignored", career["polarity"] != "caution")

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
    check("month prompt month-shape", "MONTH'S SHAPE" in p and "caution week as an 'opening'" in p)
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
    # month high-conviction career must carry its sourced week window
    oc = next(f for f in out_none if f["domain"] == "career")
    check("none month career has window", has_week_date(oc["hook"]))
    # FALLBACK INVERSION FIX: caution domain must NOT read "opens up"
    oh = next(f for f in out_none if f["domain"] == "health")
    check("caution fallback not 'opens up'", "opens up" not in oh["hook"].lower())
    check("caution fallback says gently/ease", any(w in oh["hook"].lower() for w in ("gently", "ease", "care")))
    # fallback substance != depth (real layering even on the cold path)
    check("fallback substance!=depth", all(f["substance"] != f["depth"] for f in out_none if f.get("substance")))

    # BLOCKER 2: a REAL seeded date (from priority_actions) must PASS — the model
    # echoes "June 8" / "before June 22"; these are sourced, so NO fallback.
    async def month_call(prompt: str) -> str:
        obj = {
            "career": {"hook": "Work opens up — the week of June 22 is the one to use.",
                       "substance": "Ask for the promotion in the week of June 8 while timing favours bold moves.",
                       "depth": "The opening is real but brief; prepare your case before the week of June 8 so you can move with conviction when it lands."},
            "health": {"hook": "Go gently with wellbeing — the week of June 15 needs care.",
                       "substance": "Book the check-up before June 22, because your energy dips afterward.",
                       "depth": "Treat the first half of the month as the window to act on health; after June 22 the same task costs more effort."},
        }
        for d in FIVE:
            obj.setdefault(d, {"hook": f"{d} stays steady this month.",
                               "substance": f"{d} steady.", "depth": f"{d} steady, longer."})
        return json.dumps(obj)

    out_m = asyncio.run(phrase_domains(mi, ALT_MONTH, "en", month_call))
    mc = next(f for f in out_m if f["domain"] == "career")
    mh = next(f for f in out_m if f["domain"] == "health")
    check("BLOCKER2 career real date PASS (no fallback)", mc.get("_valid") and not mc.get("_fallback"))
    check("BLOCKER2 health real date PASS (no fallback)", mh.get("_valid") and not mh.get("_fallback"))
    check("BLOCKER2 career substance!=depth", mc["substance"] != mc["depth"])
    check("career hook sentiment positive", "opens up" in mc["hook"].lower())
    check("health hook sentiment caution", "gently" in mh["hook"].lower())

    # build_fallback_domains: deterministic, no model, all five, flagged cold
    cold = build_fallback_domains(mi, "en")
    check("cold 5", len(cold) == 5)
    check("cold all valid", all(f["_valid"] for f in cold))
    check("cold flagged", all(f.get("_cold") for f in cold))

    if failures:
        print(f"SELFTEST FAIL ({len(failures)}): " + "; ".join(failures))
        return 1
    print("SELFTEST PASS — all layered_phrasing checks green")
    return 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
