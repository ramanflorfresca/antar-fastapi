"""
antar_engine/chapter_arc.py

Life Chapter Arc Engine
──────────────────────────────────────────────────────────────────────
WHAT THIS DOES:
  Generates a deeply personal narrative arc for the user's current
  life chapter — past, present, and approaching transition.

  This is the thing that makes people cry.
  This is what makes them send it to their friends.
  This is what builds lifetime subscribers.

  NOT: "You are in a Jupiter Mahadasha."
  YES: "You are 3 years into a 16-year expansion chapter.
        The first three years were about clearing the old — dissolving
        relationships, structures, and identities that didn't fit
        who you were becoming. That clearing is done.
        You are now in the building phase. What you create in
        the next 4 years will be the defining work of this lifetime.
        In 13 years, a Clarifying Pressure chapter begins —
        it will ask you to account for everything you've built.
        Build something you'll be proud to stand behind."

  That is the difference between data and wisdom.

HOW IT WORKS:
  1. Identifies the current MD phase (opening/building/peak/closing)
  2. Reads the Dasha-Kala-Patra intersection:
     - Dasha = WHAT is happening (the energy)
     - Kala = WHEN (where we are in the chapter arc)
     - Patra = WHO it's happening to (life stage, circumstances)
  3. Generates a 3-paragraph narrative:
     Para 1: What the chapter has been building (past)
     Para 2: What is being asked of them right now (present)
     Para 3: What to complete + what the next chapter demands (future)
  4. Includes the "chapter theme" — a one-line poetic summary

USAGE:
    from antar_engine.chapter_arc import build_chapter_arc

    arc = build_chapter_arc(
        chart_data=chart_data,
        dashas=dashas,
        patra=patra,           # from patra.py
    )
    # Returns ChapterArc dict with narrative + metadata
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional


# ── Energy language ───────────────────────────────────────────────────────────

DASHA_ENERGY = {
    "Sun":     "Identity & Purpose",
    "Moon":    "Emotional Depth",
    "Mars":    "Action & Courage",
    "Mercury": "Intellect & Communication",
    "Jupiter": "Expansive Growth",
    "Venus":   "Heart & Beauty",
    "Saturn":  "Clarifying Pressure",
    "Rahu":    "Hungry Becoming",
    "Ketu":    "Releasing & Liberation",
}

# What each chapter phase means by planet
CHAPTER_PHASES = {

    "Sun": {
        "opening": {
            "past":    "The chapter opened with a call toward your own authority — a sense that something needed to change about how you were showing up in the world.",
            "present": "You are in the early phase of stepping into your own identity. Old patterns of deferring, hiding, or waiting for permission are being replaced by a growing sense of your own authority.",
            "gift":    "Clarity about who you really are is emerging.",
        },
        "building": {
            "past":    "The early phase of this chapter brought shifts in identity — old roles fell away and new ones began forming.",
            "present": "You are in the building phase of your identity work. The clarity about who you are is solidifying. Your relationship with visibility, authority, and purpose is being forged right now.",
            "gift":    "Your authentic self is becoming undeniable.",
        },
        "peak": {
            "past":    "Years of identity work and clarity have brought you to this point.",
            "present": "You are at the peak of your Identity chapter. Your sense of self, purpose, and authority is at its strongest. This is when your life's most important moves can be made with maximum clarity.",
            "gift":    "Full expression of who you are is now possible.",
        },
        "closing": {
            "past":    "This Identity chapter has done its work — you know who you are at a level that wasn't available before.",
            "present": "The chapter is completing. You are being asked to consolidate what you've learned about yourself before the next chapter begins.",
            "gift":    "Integration of a new, more authentic identity.",
        },
    },

    "Moon": {
        "opening": {
            "past":    "The chapter opened with a deepening of your emotional world — a heightened sensitivity to what you truly feel beneath the surface.",
            "present": "You are in the opening phase of an Emotional Depth chapter. Your inner world is becoming more available to you — dreams are more vivid, old feelings are surfacing, and your relationship with home and family is shifting.",
            "gift":    "Your emotional intelligence is awakening.",
        },
        "building": {
            "past":    "The opening of this chapter brought emotional depth and inner stirring that may have felt disorienting at first.",
            "present": "You are in the building phase of your Emotional Depth chapter. The emotional groundwork of your life is being laid. What you build in your inner life right now will be the foundation you stand on for years.",
            "gift":    "Deep emotional security and inner richness.",
        },
        "peak": {
            "past":    "Years of emotional deepening have brought extraordinary inner richness.",
            "present": "You are at the peak of your Emotional Depth chapter. Your intuition, emotional intelligence, and connection to home and family are at their fullest. This is one of the most nourishing periods of your life.",
            "gift":    "Profound inner security and emotional wisdom.",
        },
        "closing": {
            "past":    "This deep emotional chapter has given you an inner world of extraordinary richness.",
            "present": "The chapter is completing. You are integrating the emotional wisdom gained and preparing to carry this depth into a new chapter.",
            "gift":    "A permanently enriched inner life.",
        },
    },

    "Mars": {
        "opening": {
            "past":    "The chapter opened with an activation of your energy and courage — a feeling that something needed to be acted on, built, or defended.",
            "present": "You are in the opening phase of an Action chapter. Your energy is rising, your tolerance for passivity is falling, and your instinct for bold action is sharpening.",
            "gift":    "Renewed courage and physical vitality.",
        },
        "building": {
            "past":    "The opening of this chapter ignited your capacity for bold action.",
            "present": "You are in the building phase of your Action & Courage chapter. This is when you build real things — not plans, not intentions, but actual structures. Your energy is high and your capacity to work hard is exceptional.",
            "gift":    "Tangible, lasting results from courageous action.",
        },
        "peak": {
            "past":    "Years of building and acting have produced real results.",
            "present": "You are at the peak of your Action chapter. Your capacity to take decisive, effective action is at its highest point. What you do now will be remembered.",
            "gift":    "The ability to accomplish what previously seemed impossible.",
        },
        "closing": {
            "past":    "This chapter produced real, tangible achievements through courage and effort.",
            "present": "The chapter is completing. You are integrating the confidence and results built through bold action.",
            "gift":    "Permanent increase in your capacity for courage and decisive action.",
        },
    },

    "Mercury": {
        "opening": {
            "past":    "The chapter opened with a quickening of your mind — new ideas, new connections, new ways of seeing things.",
            "present": "You are in the opening phase of an Intellect chapter. Your curiosity is sharp, your communication is energized, and business and educational opportunities are beginning to appear.",
            "gift":    "Mental clarity and the beginning of new intellectual paths.",
        },
        "building": {
            "past":    "The opening phase sharpened your mind and opened new intellectual avenues.",
            "present": "You are in the building phase of your Intellect & Communication chapter. Business, education, and the power of your ideas are the central themes. This is when intellectual work produces lasting results.",
            "gift":    "Mastery in communication and intellectual leadership.",
        },
        "peak": {
            "past":    "Years of intellectual work have produced real mastery.",
            "present": "You are at the peak of your Intellect chapter. Your mind is at its sharpest, your communication is most effective, and your business acumen is strongest. This is when intellectual ventures should be launched or scaled.",
            "gift":    "Full expression of your mental gifts.",
        },
        "closing": {
            "past":    "This chapter produced intellectual clarity and communicative power.",
            "present": "The chapter is completing. You are integrating the intellectual mastery developed and preparing for a new cycle.",
            "gift":    "Permanent sharpening of your mind and communication.",
        },
    },

    "Jupiter": {
        "opening": {
            "past":    "The chapter opened with an expansion of your world — new possibilities, new relationships, and a sense that something larger was beginning.",
            "present": "You are in the opening phase of an Expansive Growth chapter. Doors are beginning to open. The seeds of this period's blessings are being planted right now.",
            "gift":    "Access to a new world of possibility.",
        },
        "building": {
            "past":    "The opening phase expanded your world and introduced the opportunities of this chapter.",
            "present": "You are in the building phase of your greatest expansion period. This is when Jupiter's blessings fully materialize — marriage, wealth, wisdom, recognition, and spiritual growth are all available. Build boldly.",
            "gift":    "The real flowering of abundance and wisdom.",
        },
        "peak": {
            "past":    "Years of expansion have produced extraordinary abundance.",
            "present": "You are at the absolute peak of your Expansion chapter. Everything Jupiter represents — wealth, wisdom, relationships, recognition — is most fully available right now. Act with intention.",
            "gift":    "The fullest expression of abundance in this lifetime.",
        },
        "closing": {
            "past":    "This extraordinary chapter has given you abundance, wisdom, and expanded possibility.",
            "present": "The chapter is completing. You are consolidating the blessings received and preparing to carry this abundance into the next cycle.",
            "gift":    "A permanently elevated life built on Jupiter's foundation.",
        },
    },

    "Venus": {
        "opening": {
            "past":    "The chapter opened with a softening — a movement toward love, beauty, and the refinement of your life.",
            "present": "You are in the opening phase of a Heart chapter. Love, creativity, and the desire for beauty are awakening. Your relationships and creative life are beginning to bloom.",
            "gift":    "The opening of your heart and creative life.",
        },
        "building": {
            "past":    "The opening phase awakened your heart and creative instincts.",
            "present": "You are in the building phase of your Heart & Beauty chapter. This is when relationships deepen, creative work flourishes, and the refinement of your life accelerates. Love is a teacher right now.",
            "gift":    "Deep love, creative mastery, and a refined life.",
        },
        "peak": {
            "past":    "Years of love and creative work have produced extraordinary beauty.",
            "present": "You are at the peak of your Heart chapter. Your capacity for love, creativity, and the enjoyment of beauty is at its highest. This is one of life's most gracious periods.",
            "gift":    "The fullest expression of love and creative beauty.",
        },
        "closing": {
            "past":    "This chapter of love and beauty has enriched your life in ways that won't fade.",
            "present": "The chapter is completing. You are integrating the love and beauty cultivated and carrying it forward.",
            "gift":    "A heart permanently opened and a life permanently refined.",
        },
    },

    "Saturn": {
        "opening": {
            "past":    "The chapter opened with a pressure — a sense that what was convenient or comfortable was being replaced by what was real and necessary.",
            "present": "You are in the opening phase of a Clarifying Pressure chapter. Saturn is beginning to ask: what here is real? What in your life is built on solid ground and what is built on wishful thinking?",
            "gift":    "The beginning of a profound clarification of your life.",
        },
        "building": {
            "past":    "The opening phase began the clarification — things that weren't real began to surface.",
            "present": "You are in the building phase of your Clarifying Pressure chapter. This is when Saturn's gifts — discipline, integrity, real work — produce lasting results. What you build with honest effort right now will outlast everything.",
            "gift":    "The construction of something that will last a lifetime.",
        },
        "peak": {
            "past":    "Years of real work and honest building have produced something of genuine value.",
            "present": "You are at the peak of your Clarifying Pressure chapter. The work of Saturn is most concentrated now. What is not real cannot survive here. What is genuine will be revealed with extraordinary clarity.",
            "gift":    "Total clarity about what is real in your life.",
        },
        "closing": {
            "past":    "This chapter stripped away what wasn't real and revealed what was. That gift is permanent.",
            "present": "The chapter is completing. You are integrating the hard-earned wisdom of Saturn's work and preparing to carry a clarified, more authentic life forward.",
            "gift":    "Permanent integrity and the freedom that comes from it.",
        },
    },

    "Rahu": {
        "opening": {
            "past":    "The chapter opened with a hunger — an unusual ambition for something new, something that the previous version of you would not have reached for.",
            "present": "You are in the opening phase of a Hungry Becoming chapter. Rahu's disruptive energy is beginning to rewrite your ambitions, your social world, and your sense of what is possible.",
            "gift":    "Access to completely new possibilities.",
        },
        "building": {
            "past":    "The opening phase disrupted old patterns and introduced entirely new possibilities.",
            "present": "You are in the building phase of your Hungry Becoming chapter. Material rise, unconventional success, and foreign or technological connections are all in play. Move boldly, but stay honest with yourself about what you're chasing.",
            "gift":    "Rapid transformation and unconventional success.",
        },
        "peak": {
            "past":    "Years of unconventional ambition have produced rapid transformation.",
            "present": "You are at the peak of your Rahu chapter. The material and social rise that Rahu promises is most fully available now. Your world looks almost nothing like it did at the start of this chapter.",
            "gift":    "Arrival at a completely new version of your life.",
        },
        "closing": {
            "past":    "This chapter of hungry becoming has transformed your world beyond recognition.",
            "present": "The chapter is completing. Rahu's illusions are beginning to clear, revealing what was truly worth the ambition and what was not.",
            "gift":    "Wisdom about what truly matters, earned through transformation.",
        },
    },

    "Ketu": {
        "opening": {
            "past":    "The chapter opened with a releasing — things that once mattered began to feel less important, and a pull toward something more essential began.",
            "present": "You are in the opening phase of a Releasing chapter. Ketu is beginning to dissolve what is no longer needed. What falls away is making room for something truer.",
            "gift":    "The beginning of a profound liberation.",
        },
        "building": {
            "past":    "The opening phase began the releasing — things fell away that made more room than you expected.",
            "present": "You are in the building phase of your Releasing chapter. This is when spiritual clarity and detachment from what doesn't matter reaches its greatest depth. What you are releasing is giving you back to yourself.",
            "gift":    "Profound spiritual clarity and inner freedom.",
        },
        "peak": {
            "past":    "Years of releasing have produced an extraordinary lightness and spiritual clarity.",
            "present": "You are at the peak of your Releasing chapter. The spiritual wisdom, detachment, and liberation that Ketu offers are most fully available now. This is one of the most spiritually significant periods of your life.",
            "gift":    "Liberation from what has held you back for years.",
        },
        "closing": {
            "past":    "This chapter of releasing has freed you from burdens you didn't fully know you were carrying.",
            "present": "The chapter is completing. What needed releasing has been released. You are preparing to carry a lighter, freer self into the next cycle.",
            "gift":    "Permanent spiritual maturity and inner freedom.",
        },
    },
}

# What the next chapter demands, as preparation advice
NEXT_CHAPTER_PREP = {
    "Sun":     "Build your confidence and clarity about your identity before then.",
    "Moon":    "Develop your emotional intelligence and inner security.",
    "Mars":    "Build your physical strength and capacity for decisive action.",
    "Mercury": "Sharpen your mind and communication skills.",
    "Jupiter": "Expand your thinking and prepare to receive abundance.",
    "Venus":   "Open your heart and cultivate beauty in your life.",
    "Saturn":  "Get honest about what in your life is real and what is not.",
    "Rahu":    "Be open to completely new possibilities arriving.",
    "Ketu":    "Begin the inner work of releasing what no longer serves your soul.",
}

SIGN_LORDS = {
    "Aries":"Mars","Taurus":"Venus","Gemini":"Mercury","Cancer":"Moon",
    "Leo":"Sun","Virgo":"Mercury","Libra":"Venus","Scorpio":"Mars",
    "Sagittarius":"Jupiter","Capricorn":"Saturn","Aquarius":"Saturn","Pisces":"Jupiter"
}


def _parse_dt(s: str) -> datetime:
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:10], fmt[:10])
        except:
            continue
    return datetime.utcnow()

def _lord(sign: str) -> str:
    return SIGN_LORDS.get(sign, sign)

def _current_period(periods: list, now: datetime) -> Optional[dict]:
    for p in periods:
        if _parse_dt(p["start"]) <= now <= _parse_dt(p["end"]):
            return p
    return periods[0] if periods else None

def _get_phase(elapsed_months: int, total_months: int) -> str:
    pct = elapsed_months / max(total_months, 1)
    if pct < 0.20:
        return "opening"
    elif pct < 0.60:
        return "building"
    elif pct < 0.80:
        return "peak"
    else:
        return "closing"


def build_chapter_arc(
    chart_data: dict,
    dashas: dict,
    patra: object = None,
) -> dict:
    """
    Main entry point. Builds a full chapter arc narrative.

    Returns:
        {
            "chapter_theme":      str,   # One-line poetic summary
            "current_energy":     str,   # e.g. "Expansive Growth"
            "phase":              str,   # opening/building/peak/closing
            "phase_label":        str,   # Human-readable phase
            "elapsed_months":     int,
            "remaining_months":   int,
            "total_months":       int,
            "past_narrative":     str,   # What the chapter has been building
            "present_narrative":  str,   # What is being asked right now
            "future_narrative":   str,   # What to complete + next chapter
            "invitation":         str,   # The core invitation of this moment
            "next_chapter_energy":str,   # What comes next
            "next_chapter_start": str,   # When (formatted date)
            "patra_note":         str,   # How life stage intersects
        }
    """
    now = datetime.utcnow()
    vim = dashas.get("vimsottari", [])

    current_md = _current_period(vim, now)
    if not current_md:
        return _empty_arc()

    planet = current_md["lord_or_sign"]
    md_start = _parse_dt(current_md["start"])
    md_end   = _parse_dt(current_md["end"])

    total_months   = max(1, int((md_end - md_start).days / 30))
    elapsed_months = max(0, int((now - md_start).days / 30))
    remaining_months = max(0, int((md_end - now).days / 30))

    phase = _get_phase(elapsed_months, total_months)
    phase_labels = {
        "opening": "The Opening Phase",
        "building": "The Building Phase",
        "peak":    "The Peak Phase",
        "closing": "The Completion Phase",
    }

    # Get phase narratives for this planet
    planet_phases = CHAPTER_PHASES.get(planet, CHAPTER_PHASES["Saturn"])
    phase_data    = planet_phases.get(phase, planet_phases["building"])

    current_energy = DASHA_ENERGY.get(planet, planet)

    # Find next chapter
    next_md = None
    for p in vim:
        if _parse_dt(p["start"]) > now:
            next_md = p
            break

    next_planet = next_md["lord_or_sign"] if next_md else "Sun"
    next_energy = DASHA_ENERGY.get(next_planet, next_planet)
    next_start  = next_md["start"] if next_md else ""
    next_start_formatted = ""
    if next_start:
        try:
            next_start_formatted = _parse_dt(next_start).strftime("%B %Y")
        except:
            next_start_formatted = next_start[:7]

    # Patra intersection (life stage note)
    patra_note = ""
    if patra:
        try:
            life_stage = getattr(patra, "life_stage_name", "") or ""
            career_stage = getattr(patra, "career_stage", "") or ""
            if life_stage:
                stage_context = {
                    "Young Adult": "You are in the years of formation — what you build now is foundational.",
                    "Prime Years": "You are in your prime — this chapter's work carries maximum leverage.",
                    "Wisdom Years": "You are in the years of legacy — this chapter asks what you will leave behind.",
                    "Elder": "You are in the years of completion and wisdom — this chapter's gift is profound integration.",
                }
                patra_note = stage_context.get(life_stage, f"As someone in {life_stage}, this chapter has particular relevance.")
        except:
            pass

    # Build future narrative
    prep_advice = NEXT_CHAPTER_PREP.get(next_planet, "Prepare consciously for what is coming.")
    future_narrative = (
        f"In approximately {remaining_months} months, a {next_energy} chapter begins "
        f"({next_start_formatted}). "
        f"What you complete before this chapter closes, you carry forward transformed. "
        f"What you leave unfinished, the next chapter will have to deal with on different terms. "
        f"{prep_advice}"
    )

    # Chapter theme — the one-line poetic summary
    chapter_themes = {
        ("Sun",     "opening"):  "The soul is stepping out of the shadow and into its own light.",
        ("Sun",     "building"): "An identity is being forged that cannot be taken away.",
        ("Sun",     "peak"):     "The full sun of who you are is at its zenith.",
        ("Sun",     "closing"):  "The harvest of hard-won identity is complete.",
        ("Moon",    "opening"):  "The inner world is becoming the teacher.",
        ("Moon",    "building"): "Emotional roots are being planted that will hold for a lifetime.",
        ("Moon",    "peak"):     "The deepest feeling is the clearest truth.",
        ("Moon",    "closing"):  "A river of feeling is becoming a deep, still lake.",
        ("Mars",    "opening"):  "The warrior in you is waking up.",
        ("Mars",    "building"): "Courage is being built through use.",
        ("Mars",    "peak"):     "The fire of will is at its brightest.",
        ("Mars",    "closing"):  "The battle is ending. The victor is ready for peace.",
        ("Mercury", "opening"):  "The mind is sharpening like a new blade.",
        ("Mercury", "building"): "Intellect is becoming the primary tool.",
        ("Mercury", "peak"):     "The mind at its most precise and powerful.",
        ("Mercury", "closing"):  "The library is full. The teaching begins.",
        ("Jupiter", "opening"):  "The sky is getting larger.",
        ("Jupiter", "building"): "Abundance is being constructed, brick by brick.",
        ("Jupiter", "peak"):     "The harvest of expansion is here.",
        ("Jupiter", "closing"):  "What was received must now be given forward.",
        ("Venus",   "opening"):  "The heart is learning how to love.",
        ("Venus",   "building"): "Beauty is becoming a way of living.",
        ("Venus",   "peak"):     "Love in its fullest expression.",
        ("Venus",   "closing"):  "What was beautiful remains in the heart forever.",
        ("Saturn",  "opening"):  "The sculptor has arrived. The work begins.",
        ("Saturn",  "building"): "What is real is being separated from what is not.",
        ("Saturn",  "peak"):     "Truth without ornamentation.",
        ("Saturn",  "closing"):  "The fire has burned. What remains is gold.",
        ("Rahu",    "opening"):  "Something new and unprecedented is beginning.",
        ("Rahu",    "building"): "The old world is dissolving into the new.",
        ("Rahu",    "peak"):     "Transformation at maximum velocity.",
        ("Rahu",    "closing"):  "The dream and the reality are meeting.",
        ("Ketu",    "opening"):  "Something essential is being uncovered beneath the layers.",
        ("Ketu",    "building"): "The soul is lightening its load.",
        ("Ketu",    "peak"):     "Liberation in the truest sense.",
        ("Ketu",    "closing"):  "The last thing to be released is the releasing itself.",
    }

    chapter_theme = chapter_themes.get((planet, phase), f"A {current_energy} chapter is unfolding.")

    return {
        "chapter_theme":        chapter_theme,
        "current_energy":       current_energy,
        "phase":                phase,
        "phase_label":          phase_labels.get(phase, "Active Phase"),
        "elapsed_months":       elapsed_months,
        "remaining_months":     remaining_months,
        "total_months":         total_months,
        "elapsed_pct":          round(elapsed_months / total_months * 100),
        "past_narrative":       phase_data["past"],
        "present_narrative":    phase_data["present"],
        "gift":                 phase_data["gift"],
        "future_narrative":     future_narrative,
        "invitation":           f"The gift available in this phase: {phase_data['gift']}",
        "next_chapter_energy":  next_energy,
        "next_chapter_start":   next_start_formatted,
        "next_chapter_months":  remaining_months,
        "patra_note":           patra_note,
        "planet":               planet,
    }


def _empty_arc() -> dict:
    return {
        "chapter_theme":     "Your chapter is being calculated.",
        "current_energy":    "Unknown",
        "phase":             "building",
        "phase_label":       "Active Phase",
        "elapsed_months":    0,
        "remaining_months":  0,
        "total_months":      0,
        "elapsed_pct":       0,
        "past_narrative":    "",
        "present_narrative": "",
        "gift":              "",
        "future_narrative":  "",
        "invitation":        "",
        "next_chapter_energy": "",
        "next_chapter_start":  "",
        "next_chapter_months": 0,
        "patra_note":        "",
        "planet":            "",
    }


def chapter_arc_to_context_block(arc: dict) -> str:
    """
    Convert chapter arc to LLM context block for prompt_builder.py.
    """
    if not arc or not arc.get("current_energy"):
        return ""

    lines = [
        "═══ LIFE CHAPTER ARC (use this as the narrative foundation) ═══",
        f"Current Chapter: {arc['current_energy']} — {arc['phase_label']}",
        f"Chapter Theme: {arc['chapter_theme']}",
        f"Progress: {arc['elapsed_months']} months elapsed / {arc['remaining_months']} months remaining",
        f"",
        f"PAST (what this chapter has been building):",
        arc['past_narrative'],
        f"",
        f"PRESENT (what is being asked right now):",
        arc['present_narrative'],
        f"",
        f"FUTURE (what to complete + what's coming):",
        arc['future_narrative'],
        f"",
        f"THE GIFT OF THIS PHASE: {arc['gift']}",
    ]

    if arc.get("patra_note"):
        lines.append(f"LIFE STAGE NOTE: {arc['patra_note']}")

    lines.append("═══ END CHAPTER ARC ═══")
    return "\n".join(lines)
