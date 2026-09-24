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
    # [verdict-leads 2026-09-23] The VERDICT is the chapter's headline and MUST lead
    # the reading. It is listed FIRST and flagged as the lead; the handover and the
    # activated-area fact are explicitly SECONDARY so the narrator can't open on a
    # life-area the verdict didn't name (a "wealth-building chapter" whose body
    # opened entirely on home/mother read as two unrelated chapters).
    if bundle.get("verdict"):
        facts.append("THE CHAPTER — LEAD THE READING WITH THIS, it is the headline: "
                     + bundle["verdict"])
    if bundle.get("handover"):
        facts.append("(context) transition — " + bundle["handover"])
    if bundle.get("timing"):
        facts.append("RIGHT NOW — " + bundle["timing"])

    houses = bundle.get("primary_houses") or []
    meaning = bundle.get("primary_house_meaning") or ""
    if houses and meaning:
        facts.append(f"NEAR-TERM FOCUS (SECONDARY — where life is loud right now; weave "
                     f"in AFTER the headline and connect it to the chapter, NEVER open "
                     f"the reading with this): {meaning} (house"
                     f"{'s' if len(houses) > 1 else ''} "
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
  - "Two systems/methods agree" or any cross-check → do NOT announce it. Never write "this is a clear, reliable signal", "the signal is strong", or any sentence about a signal, reading, or things lining up. Agreement just means you STATE the theme as a plain fact, confidently — not that you comment on the reading.
- Be CONCRETE about their actual life — money, work, home, family, health, relationships — never abstract images like "territory", "rooms", "center of gravity", or "zones".

PICK ONE THING. The facts list several activated life areas. Do NOT name them all — a paragraph that touches money AND career AND siblings AND health AND partnership at once is generic and true for no one. Choose the SINGLE strongest theme (the top-ranked / heaviest-weighted fact) and build the read around it. You may name AT MOST ONE more area — the one that most opens it up OR the one that's hardest. Never more than TWO life areas in the whole reading. Ignore the rest.

ANCHOR ON THE VERDICT. The "WHETHER IT DELIVERS" fact is the chapter's headline judgment — it names the chapter's real direction (e.g. a wealth / career / name-and-standing chapter opening, or a demanding chapter to hold steady through). That direction IS your dominant theme: lead with it and commit. If it names a clear direction, do NOT dilute it into "pulled in two directions", "two currents side by side", or "no single clean theme" — a split framing on top of a clear verdict reads as hedging and buries the point. State the direction plainly; you may note ONE real tension within it, but the verdict leads.

CHAPTER vs RIGHT-NOW — do not let one undercut the other. The verdict describes the whole CHAPTER (often many years). A "RIGHT NOW" or timing fact that says things are "steady", "holding", "not breaking open yet" describes only the CURRENT stretch, which may be early in a long chapter. When the verdict names a BIG opening (wealth / name / career rising), you must NEVER call the CHAPTER itself "steady", "not a breakthrough", "quiet", or "not a big moment" — that flatly contradicts the verdict and reads as the app not believing its own call. Instead, frame any near-term steadiness as the BUILD-UP / groundwork phase OF that big chapter ("the big chapter is here; right now is the build-up — lay the groundwork"). The chapter's size comes from the verdict; "steady" only ever qualifies the current moment, never the chapter.

VERDICT vs "WHERE THE WEIGHT SITS" — when they name DIFFERENT life-areas, the verdict still leads. The verdict names the CHAPTER's theme (e.g. "a wealth-building chapter"). The "WHERE THE WEIGHT SITS" / activated-area fact may name a DIFFERENT area that's loud RIGHT NOW (e.g. home, family, a parent, property). Do NOT open with that activated area as if it were the chapter's theme — that makes the headline (wealth) and the body (home/parent) read as two unrelated chapters. Instead: FIRST sentence states the verdict's theme; THEN connect the activated area to it as where that theme is playing out or being tested right now ("this is a wealth-building chapter — and right now the money question is showing up through a home or property move"). If the two genuinely don't connect, still name the verdict's theme first and give the activated area only ONE line as the current focus — never let the body drift entirely onto an area the verdict didn't name.

WHAT TO WRITE, in this order:
1. First sentence = the chapter's direction from the VERDICT, in plain life terms — what this chapter opens or asks of them. Commit to it. Direct, specific, no hedging, no build-up.
2. ONE sentence on how it's playing out — what's opening (or the one real tension within it) in that same area (plus at most one secondary area).
3. ONE sentence: the single most useful thing to DO about it right now — concrete.

FORMAT: 3-4 short sentences, ~60-90 words — tight, not a wall of text. Warm, direct, second person ("you"). No headers, no bullets, no preamble, no meta-commentary. Lead with the one thing that matters most and stay on it."""


async def narrate_cycle(
    bundle: dict,
    name: str,
    claude_caller: Callable[..., Awaitable[tuple]],
    language: str = "en",
    lead: str = "",
) -> str:
    """Compose the cycle bundle into user-facing prose via the LLM.

    claude_caller is injected (the same call_llm_claude the life-arc uses) so this
    stays free of a circular import on main. Returns the prose, or a plain
    deterministic fallback if the bundle is empty or the model is unavailable.

    [deterministic-lead 2026-09-24] When `lead` is given (a deterministic opening
    sentence matched to the verdict's tempo), the LLM writes ONLY the elaboration
    (2 sentences that continue it) and we PREPEND the lead verbatim. This is the
    reliable fix for the model defaulting to a 'holding chapter / stay steady'
    opener that contradicted a strong verdict — the opening is no longer the LLM's
    to choose.
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
    _lead = (lead or "").strip()
    if _lead:
        prompt = (
            f"FACTS about {first or 'this person'}'s current period:\n{numbered}\n"
            f"{lang_line}\n"
            f"The reading's OPENING sentence is already written for you (do NOT "
            f"repeat it, do NOT contradict its direction or tempo):\n\"{_lead}\"\n"
            f"Write ONLY the 2 sentences that CONTINUE from it: (a) how it's "
            f"playing out — the one real tension or what's opening, in the same "
            f"direction as the opening; (b) the single most useful thing to DO now, "
            f"concrete. ~40-60 words total. Address them as \"you\". Plain language, "
            f"no headers/preamble/meta. Use only the facts above.")
    else:
        prompt = (f"FACTS about {first or 'this person'}'s current period:\n{numbered}\n"
                  f"{lang_line}\n"
                  f"Write their current-cycle reading now, following every rule. "
                  f"Address them as \"you\". Use only the facts above.")
    try:
        text, _ = await claude_caller(prompt, None, _CYCLE_SYSTEM)
        body = (text or "").strip()
        if _lead:
            # Guarantee the deterministic opening; drop an accidental echo.
            if body.lower().startswith(_lead.lower()[:24]):
                return body  # model already opened with (a paraphrase of) the lead
            return f"{_lead} {body}".strip() if body else _lead
        return body
    except Exception:
        # Deterministic fallback — still grounded, just unpolished.
        _elab = " ".join(f.split("— ", 1)[-1] for f in facts[:3])
        return (f"{_lead} {_elab}".strip() if _lead else _elab)
