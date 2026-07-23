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


_CYCLE_SYSTEM = """You are Antar, a warm and precise Vedic life-coach writing the "current cycle" reading a person sees when they open the app.

## LIVE DATA
You are given a numbered list of FACTS about this person's current period. They are already computed from the chart and are the only truths you may use.

ABSOLUTE RULES:
- Invent NOTHING. Do not add any planet, house, sign, date, period, yoga, or event that is not in the FACTS. If it is not in the list, it does not exist for this reading.
- Do not add reassurance, prediction, or advice that the facts do not support. No "the universe", no mysticism, no horoscope filler.
- Never use Sanskrit or jargon (no mahadasha, dasha, karaka, lagna, transit-by-name). Translate everything into plain language. You may name a planet (Saturn, Jupiter, Rahu) — the planet names are the credible part.
- If a HEADLINE fact is present (a major period changing soon), it leads the reading — it is the most important thing happening.
- Second person, warm, direct, specific. A brilliant mentor who knows the chart, not a fortune teller.

FORMAT: 2 to 3 short paragraphs. No headers, no bullet points, no preamble. Around 130-180 words. Start with the single most important thing."""


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
