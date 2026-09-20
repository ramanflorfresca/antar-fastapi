"""
antar_engine/cycle_narrator.py
Turn the deterministic cycle bundle into a warm reading — inventing nothing.
2026-07-23

The paddhati bundle (cycle_paddhati.cycle_reading) is a set of already-composed
English sentences grounded in the chart: the mahadasha handover, the verdict, the
timing, the houses lit, the chara moving-lagna rotation, the transit notes, the
cross-system agreement. Every claim in it is deterministic and checkable.

This module hands those sentences to the LLM to weave into prose a person will
actually read. The one rule that matters is the NO-INVENTION GATE: the narrator
may rephrase, order, warm up and connect the given facts, and may add nothing —
no planet, house, sign, date, dasha or event that is not already in the bundle.
This is the same contract the daily card runs under, and it exists because the
credible part of this reading is the specifics, and a model left to improvise
fills the gaps with horoscope.

The bundle is passed as an explicit fact list, not as free narrative, precisely
so the model has nothing to embroider. If a fact is not in the list, it does not
belong in the reading.
"""

from typing import Dict, List, Optional, Callable, Awaitable


def _facts_from_bundle(bundle: dict) -> List[str]:
    """Flatten the cycle bundle into the ordered fact list the narrator may use.

    Order is deliberate: the handover (if any) is the headline, then whether the
    period delivers, then where its weight sits, then the Jaimini and transit
    detail. Nothing here is generated — every string comes straight off the
    deterministic reading.
    """
    facts: List[str] = []
    if bundle.get("handover"):
        facts.append("HEADLINE — " + bundle["handover"])
    if bundle.get("verdict"):
        facts.append("WHETHER IT DELIVERS — " + bundle["verdict"])
    if bundle.get("timing"):
        facts.append("RIGHT NOW — " + bundle["timing"])

    houses = bundle.get("primary_houses") or []
    meaning = bundle.get("primary_house_meaning") or ""
    if houses and meaning:
        facts.append(f"WHERE THE WEIGHT SITS — the period concentrates on "
                     f"{meaning} (house{'s' if len(houses) > 1 else ''} "
                     f"{', '.join(str(h) for h in houses)}).")

    for f in (bundle.get("chara_rotation") or [])[:4]:
        facts.append("JAIMINI MOVING LAGNA — " + f)
    for n in ((bundle.get("transit") or {}).get("notes") or []):
        facts.append("TRANSIT NOW — " + n)
    for a in (bundle.get("agreement") or []):
        facts.append("CROSS-CHECK — " + a)
    return facts


_CYCLE_SYSTEM = """You are Antar, writing the short "current cycle" reading a person sees when they open the app. Your job: make a busy person instantly understand what this chapter of their life is about — in plain, everyday words, with nothing to decode.

## LIVE DATA
You are given a numbered list of FACTS about this person's current period, already computed from their chart. They are the only truths you may use.

ABSOLUTE RULES:
- Invent NOTHING beyond the facts — no event, date, or claim the facts don't support. No "the universe", no mysticism, no filler.
- PLAIN LANGUAGE ONLY. NEVER name a planet (no Jupiter, Saturn, Rahu, Ketu, Mars, Mercury, Venus, Sun, Moon), never say "house"/"houses", "chart", "system", "method", "calculation", "convergence", "alignment", "transit", "energy", or any Sanskrit. The facts may use those words — you MUST translate them into ordinary life language and never repeat them.
  - A house or its meaning → the real-life area it stands for (money you share with others, your own work and voice, home and family, career and reputation, health, and so on).
  - "Two systems/methods agree" or any cross-check → say simply "this is a clear, reliable signal right now" in ONE short clause. Do NOT describe methods, arithmetic, or that two things agree.
- Be CONCRETE about their actual life — money, work, home, family, health, relationships — never abstract images like "territory", "rooms", "center of gravity", or "zones".

WHAT TO WRITE, in this order:
1. ONE sentence naming the single biggest theme of this chapter, in plain life terms.
2. ONE or TWO sentences: what is opening or supported, and what feels harder — name the real areas of life plainly.
3. ONE sentence: the one practical thing to lean into, or to hold steady on, right now.

FORMAT: 3 short paragraphs or 4-6 short sentences, ~90-130 words. Warm, direct, second person ("you"). No headers, no bullets, no preamble. Start with the biggest theme."""


async def narrate_cycle(
    bundle: dict,
    name: str,
    claude_caller: Callable[..., Awaitable[tuple]],
    language: str = "en",
) -> str:
    """Compose the cycle bundle into user-facing prose via the LLM.

    claude_caller is injected (the same call_llm_claude the life-arc uses) so this
    stays free of a circular import on main. Returns the prose, or a plain
    deterministic fallback if the bundle is empty or the model is unavailable.
    """
    if not bundle or not bundle.get("available"):
        return ""
    facts = _facts_from_bundle(bundle)
    if not facts:
        return ""

    numbered = "\n".join(f"{i+1}. {f}" for i, f in enumerate(facts))
    first = (name or "").split()[0] if name else ""
    lang_line = ("" if language == "en"
                 else f"\nWrite the reading in this language code: {language}.")
    prompt = (f"FACTS about {first or 'this person'}'s current period:\n{numbered}\n"
              f"{lang_line}\n"
              f"Write their current-cycle reading now, following every rule. "
              f"Address them as \"you\". Use only the facts above.")
    try:
        text, _ = await claude_caller(prompt, None, _CYCLE_SYSTEM)
        return (text or "").strip()
    except Exception:
        # Deterministic fallback — still grounded, just unpolished.
        return " ".join(f.split("— ", 1)[-1] for f in facts[:4])
