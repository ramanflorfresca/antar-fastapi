"""
LK_CONDITIONS — Antar's curated Lal Kitab condition library.
40 conditions. Path B locked: planet names allowed as ACTORS per the
actor/scaffolding rule. House numbers and Sanskrit terms still scrubbed.

Source: Roop Chand Joshi Vols I-V with modern softening for culturally-bound
rules. All V1 + V2 revisions applied (see LK_CONDITIONS_REVISION_PASS.md and
LK_CONDITIONS_REVISION_PASS_V2.md).

Schema reference: ANTAR_LK_Conditions_Architecture.md

Emit path: every user-facing field passes through apply_user_facing_strips()
with source="curated_static". Underscore-prefixed keys (_source,
_softening_applied) are engine-internal and MUST be filtered out of frontend
payloads.
"""

LK_CONDITIONS = {
    # =========================================================================
    # SUPPORTIVE TRANSITS (9 rows: 1 sample + 8 from Batch A)
    # =========================================================================
    "jupiter_transit_natal_5": {
        "trigger": {
            "type": "transit", "planet": "Jupiter", "natal_house": 5,
            "natal_state_required": None, "dasha_match": None,
            "duration_min_days": 60,
        },
        "precedence": {"polarity": "positive", "slowness_rank": 7, "yoga_named": False},
        "headline_positive": "A season of creative grace.",
        "gist": "What you make, teach, or put into the world is supported now. Whatever you've been quietly working on — children, students, creative projects, intellectual work — wants to grow.",
        "use": "Move what you've been hesitant to share. Teach the thing you know. Submit, send, post, propose. Jupiter rewards visible faith in your own work — but it rewards prepared faith. Don't ship half-done; ship the thing you've actually polished.",
        "do": "Take one creative or expansive risk today. Send the proposal, publish the piece, sign up the student, start the course. If you have children, give them an unhurried hour. If you teach, prepare with care.",
        "dont": "Don't be lazy with detail just because the wind is favorable. Jupiter's blessing rewards rigor; sloppy work in this transit produces enthusiastic mistakes. Don't over-promise — the same expansive energy that opens you can over-extend you.",
        "areas_affected": [
            {"name": "Creativity", "care": False, "bars_override": 3},
            {"name": "Teaching & sharing", "care": False, "bars_override": 3},
            {"name": "Children", "care": False, "bars_override": 2},
        ],
        "remedy_planet": None, "remedy_variant": None,
        "duration_text": "This is the background music of the next several months — peaking when Jupiter is exactly mid-house. Use the whole window; don't wait for a single perfect day.",
        "_source": "Roop Chand Joshi, Vol II, Jupiter transit over 5th house. Cross-referenced K.N. Rao on Jupiter transits. Reading is standard across LK and Parashari traditions — no significant divergence.",
        "_softening_applied": "None. Original LK reading is universal — no caste, gender, or deity references in the canonical text.",
    },
    "sun_transit_natal_10": {
        "trigger": {
            "type": "transit", "planet": "Sun", "natal_house": 10,
            "natal_state_required": None, "dasha_match": None,
            "duration_min_days": 14,
        },
        "precedence": {"polarity": "positive", "slowness_rank": 3, "yoga_named": False},
        "headline_positive": "A month when your work is seen.",
        "gist": "The Sun is passing through your career sector. People in authority notice you more easily; visible work lands; what you say in meetings carries weight. This is a window to do the thing that requires being seen.",
        "use": "Ask for the meeting, the promotion, the byline, the introduction. Stand at the front of things you'd usually do quietly. If you've been waiting to share your work publicly, this is the window. Wear the colour you save for important days.",
        "do": "Take one specific visibility action this month — a presentation, a public post, a direct ask to someone senior. Show up early to meetings. Sit at the table, not the wall.",
        "dont": "Don't burn yourself trying to be visible everywhere — pick one or two arenas and shine there. Don't confuse arrogance with confidence; the Sun lights, it doesn't blare.",
        "areas_affected": [
            {"name": "Career", "care": False, "bars_override": 3},
            {"name": "Authority & recognition", "care": False, "bars_override": 3},
        ],
        "remedy_planet": None, "remedy_variant": None,
        "duration_text": "Roughly one month, peaking around mid-transit. The visibility window doesn't last; use it.",
        "_source": "Roop Chand Joshi Vol II, Sun transit through 10th house. Standard reading; no significant softening required.",
        "_softening_applied": "None.",
    },
    "moon_transit_natal_4": {
        "trigger": {
            "type": "transit", "planet": "Moon", "natal_house": 4,
            "natal_state_required": None, "dasha_match": None,
            "duration_min_days": 1,
        },
        "precedence": {"polarity": "positive", "slowness_rank": 1, "yoga_named": False},
        "headline_positive": "A day to come home.",
        "gist": "The Moon is passing through the deepest emotional part of your chart. You'll feel more grounded than the previous days — settled, slower, less reactive. The pull will be inward, toward home, family, the people who feel like roots.",
        "use": "Spend the day with people who feel like home, in places that feel like home. Cook something slow. Sit with a parent, a child, an old friend. Don't schedule the hard meeting today; schedule the conversation that's been waiting.",
        "do": "One unhurried hour with someone you love. One small care for the space you live in — a clean corner, fresh flowers, a meal made without rushing. Sleep early.",
        "dont": "Don't push hard or push fast today. Don't make decisions about leaving things — homes, jobs, relationships. The Moon over this part of your chart makes attachments feel large; come back to those decisions in 2 days.",
        "areas_affected": [
            {"name": "Home & family", "care": False, "bars_override": 3},
            {"name": "Emotional ground", "care": False, "bars_override": 3},
        ],
        "remedy_planet": None, "remedy_variant": None,
        "duration_text": "Roughly 2 days. The feeling is strongest the day the Moon enters this part of your chart.",
        "_source": "Roop Chand Joshi Vol I, Moon transit through 4th house (matri sthana). Standard.",
        "_softening_applied": "None.",
    },
    "mars_transit_natal_3": {
        "trigger": {
            "type": "transit", "planet": "Mars", "natal_house": 3,
            "natal_state_required": None, "dasha_match": None,
            "duration_min_days": 14,
        },
        "precedence": {"polarity": "positive", "slowness_rank": 4, "yoga_named": False},
        "headline_positive": "Energy for the work you've been postponing.",
        "gist": "Mars is moving through the part of your chart that rules effort, siblings, peers, short journeys, and the courage to take small risks. This is Mars's natural seat — when it transits there, you have more fuel than usual for hard, specific work.",
        "use": "Use the energy on the project you've been avoiding because it's tedious. Mars here likes specific tasks finished, not vague ambition. Reach out to a sibling, peer, or colleague you've been meaning to contact. Make the short trip you've been putting off.",
        "do": "List three concrete things you've been postponing. Finish at least one this week. Move your body daily, even briefly. Pick a small fight you've been ducking and have it cleanly.",
        "dont": "Don't pick fights with people who are not the actual problem. Don't drive aggressively — Mars here also rules accidents from rushing. Don't sign contracts with siblings or close peers without re-reading them carefully.",
        "areas_affected": [
            {"name": "Effort & projects", "care": False, "bars_override": 3},
            {"name": "Peers & siblings", "care": False, "bars_override": 2},
        ],
        "remedy_planet": None, "remedy_variant": None,
        "duration_text": "Roughly 6 weeks. Mid-transit is when initiative peaks; use it for the things you'd usually procrastinate on.",
        "_source": "Roop Chand Joshi Vol II, Mars transit through 3rd house. 3rd house is Mars's pakka ghar.",
        "_softening_applied": "None.",
    },
    "mercury_transit_natal_1": {
        "trigger": {
            "type": "transit", "planet": "Mercury", "natal_house": 1,
            "natal_state_required": None, "dasha_match": None,
            "duration_min_days": 7,
        },
        "precedence": {"polarity": "positive", "slowness_rank": 2, "yoga_named": False},
        "headline_positive": "Your mind is sharp this week.",
        "gist": "A clearing pass is moving over the part of your chart that holds your sense of self and how you present to the world. Thinking is clearer; the right words come easier; you can explain hard things to people who don't usually follow you.",
        "use": "Write the document, give the presentation, have the conversation you've been postponing because you didn't know how to phrase it. Send the emails you've been drafting. If you're learning something difficult, this is the window where it'll click.",
        "do": "Write something that matters — a proposal, a letter, a chapter, a clear explanation of a problem you've been turning over. Speak in meetings, not just listen. Make one phone call you've been meaning to make.",
        "dont": "Don't out-talk people. Mercury sharp also means Mercury sharp-tongued — you'll be cleverer than the room and the room won't like it. Don't sign contracts on the move; even with the clarity, read the small print twice.",
        "areas_affected": [
            {"name": "Communication", "care": False, "bars_override": 3},
            {"name": "Decisions & thinking", "care": False, "bars_override": 3},
        ],
        "remedy_planet": None, "remedy_variant": None,
        "duration_text": "Roughly 2-3 weeks. Mid-transit is the sharpest. After it passes, the clarity fades — capture what you can while the window is open.",
        "_source": "Roop Chand Joshi Vol II, Mercury transit over ascendant. Standard.",
        "_softening_applied": "None.",
    },
    "venus_transit_natal_7": {
        "trigger": {
            "type": "transit", "planet": "Venus", "natal_house": 7,
            "natal_state_required": None, "dasha_match": None,
            "duration_min_days": 14,
        },
        "precedence": {"polarity": "positive", "slowness_rank": 2, "yoga_named": False},
        "headline_positive": "A season of softness in your relationships.",
        "gist": "Venus is moving through your partnership sector — the part of the chart that holds spouse, primary partner, close business partner, the person you sit across from in life. Whatever has been tight there will loosen; whatever has been sweet will be sweeter.",
        "use": "Take the partner — romantic or business — somewhere you've been putting off. Have the conversation you've been avoiding, because Venus here makes hard things land softer. If you've been waiting for the right moment to deepen a partnership, this is it.",
        "do": "One specific act of care for your primary partner this month — a thing they've wanted you to notice, a meal, a small gift, a sustained hour of attention. If you're single, accept one social invitation you'd normally decline.",
        "dont": "Don't confuse temporary warmth with permanent change — Venus's grace is the lubricant, not the bond itself. Don't make extravagant promises in the warmth; the heat will pass and the promise will remain.",
        "areas_affected": [
            {"name": "Partnership", "care": False, "bars_override": 3},
            {"name": "Beauty & comfort", "care": False, "bars_override": 2},
        ],
        "remedy_planet": None, "remedy_variant": None,
        "duration_text": "Roughly 3-4 weeks. Use it for the conversation, the gesture, the deepening — Venus's warmth doesn't linger past the transit.",
        "_source": "Roop Chand Joshi Vol II, Venus transit over 7th house (Venus's pakka ghar). Standard.",
        "_softening_applied": "Original LK reading includes gender-specific marriage advice; replaced with relationship-neutral framing.",
    },
    "saturn_transit_natal_3": {
        "trigger": {
            "type": "transit", "planet": "Saturn", "natal_house": 3,
            "natal_state_required": None, "dasha_match": None,
            "duration_min_days": 90,
        },
        "precedence": {"polarity": "positive", "slowness_rank": 8, "yoga_named": False},
        "headline_positive": "A long phase of patient, undramatic building.",
        "gist": "Saturn is moving through the part of your chart that holds effort, peers, written work, short journeys, and small specific actions. This is one of Saturn's favorable transits. The work will feel slow but it'll compound. What you build now is built on stone.",
        "use": "Pick the long project — the book, the business, the credential, the body of work — and commit to a daily rhythm. Saturn here rewards consistency more than intensity. Half an hour a day for two years beats two days of frantic effort.",
        "do": "Establish one daily practice this month that you'll keep for the whole transit. Write, build, train, study, save. Tell no one for the first six months — Saturn loves quiet effort. Strengthen relationships with siblings and peers through small consistent acts.",
        "dont": "Don't expect quick visible rewards. The transit is real but slow — the harvest comes in year two or three, not month one. Don't break the rhythm to chase faster results; Saturn punishes the interruption more than the slowness.",
        "areas_affected": [
            {"name": "Long-term work", "care": False, "bars_override": 3},
            {"name": "Discipline & habit", "care": False, "bars_override": 3},
            {"name": "Peers & community", "care": False, "bars_override": 2},
        ],
        "remedy_planet": None, "remedy_variant": None,
        "duration_text": "Roughly 2.5 years. The first 6 months are foundation; the next year is build; the final year is consolidation. Don't quit in year one because nothing feels visible yet.",
        "_source": "Roop Chand Joshi Vol III, Saturn through 3rd (3-6-11 are Saturn's friendly houses). Strong LK consensus.",
        "_softening_applied": "None.",
    },
    "rahu_transit_natal_10": {
        "trigger": {
            "type": "transit", "planet": "Rahu", "natal_house": 10,
            "natal_state_required": None, "dasha_match": None,
            "duration_min_days": 90,
        },
        "precedence": {"polarity": "positive", "slowness_rank": 9, "yoga_named": False},
        "headline_positive": "An 18-month opening for unconventional ambition.",
        "gist": "Rahu is passing through your career sector. Rahu's nature is ambition, foreign elements, the unfamiliar, the rule-breaking move. When it sits here, your career wants to expand — but it wants to expand in a direction you haven't tried before. The standard path becomes uninteresting; an unusual path becomes possible.",
        "use": "Take the unconventional opportunity. The foreign client. The role nobody else wants but you can see how to make work. The pivot. The role you'd normally feel underqualified for — Rahu rewards reaching past your level. Build a public reputation in a niche, not a category.",
        "do": "Apply for the thing that scares you a little. Take the meeting in another country, another industry, another scale. Build something visible online — Rahu here loves digital ambition. Don't wait until you're ready.",
        "dont": "Don't confuse ambition for direction. Rahu hands you the energy, not the wisdom — you'll be hungry for outcomes without knowing if they're the right ones. Don't burn relationships in pursuit; the people you step over now will outlast Rahu's transit. Don't believe your own hype.",
        "areas_affected": [
            {"name": "Career", "care": False, "bars_override": 3},
            {"name": "Ambition", "care": False, "bars_override": 3},
            {"name": "Public reputation", "care": True, "bars_override": 2},
        ],
        "remedy_planet": None, "remedy_variant": None,
        "duration_text": "Roughly 18 months. The first half is the climb; the second half is when the consequences land. Use the climb wisely.",
        "_source": "Roop Chand Joshi Vol III, Rahu transit through 10th. Rahu is a benefic here by LK consensus.",
        "_softening_applied": "Original LK adds caste-specific advice on which professions favor different castes; removed.",
    },
    "ketu_transit_natal_9": {
        "trigger": {
            "type": "transit", "planet": "Ketu", "natal_house": 9,
            "natal_state_required": None, "dasha_match": None,
            "duration_min_days": 90,
        },
        "precedence": {"polarity": "positive", "slowness_rank": 9, "yoga_named": False},
        "headline_positive": "An 18-month inward turn toward meaning.",
        "gist": "Ketu is passing through the part of your chart that holds meaning, teachers, philosophy, long-distance travel, and the questions of why you're doing what you're doing. Ketu's gift is release; here, it releases certainty. You'll find old beliefs softening and new ones forming without forcing.",
        "use": "Read what you wouldn't normally read. Talk to teachers — real ones, not influencers. Travel inward if you can't travel outward. The questions you've been ignoring about purpose, ethics, or what your life is for will come back; let them speak. Don't argue them down.",
        "do": "Set aside 30 minutes a week of silent or contemplative time. Read one book outside your usual category. If a teacher, mentor, or wisdom-bearer crosses your path, follow up. Travel — even short distances — when the chance comes.",
        "dont": "Don't make permanent decisions based on temporary inward turns. Ketu here can produce a sudden urge to drop everything for a spiritual quest; wait six months before acting on any drop-everything impulse. Don't argue with your own emerging doubts; sit with them.",
        "areas_affected": [
            {"name": "Meaning & purpose", "care": False, "bars_override": 3},
            {"name": "Beliefs & teachers", "care": False, "bars_override": 3},
            {"name": "Travel", "care": False, "bars_override": 2},
        ],
        "remedy_planet": None, "remedy_variant": None,
        "duration_text": "Roughly 18 months. Don't expect resolution at the end — Ketu transits leave you with more open space, not more answers. The space is the gift.",
        "_source": "Roop Chand Joshi Vol III, Ketu transit through 9th (Ketu's pakka ghar). Standard LK and Parashari agreement.",
        "_softening_applied": "Original LK includes specific Hindu pilgrimage advice; softened to 'travel — even short distances'.",
    },
    # =========================================================================
    # FRICTION TRANSITS (9 rows, Batch A — house numbers scrubbed per item #2)
    # =========================================================================
    "sun_transit_natal_8": {
        "trigger": {
            "type": "transit", "planet": "Sun", "natal_house": 8,
            "natal_state_required": None, "dasha_match": None,
            "duration_min_days": 14,
        },
        "precedence": {"polarity": "negative", "slowness_rank": 3, "yoga_named": False},
        "headline_negative": "A month when your authority is quietly tested.",
        "gist": "The Sun is passing through the part of your chart that holds hidden things, transformation, others' resources, and what's owed. Your visibility and authority feel diminished; people don't respond to you the way they normally do; ego knocks happen quietly but they sting.",
        "cause": "That part of your chart compresses the Sun's natural light. What you usually rely on to be seen — confidence, presence, the way you walk into a room — works less well right now. This isn't because you've changed; the room is reading you differently for a month.",
        "do": "Do your work without performing it. Let outcomes do the speaking. Don't seek visible recognition this month — return to it after the Sun moves on. Resolve any financial dependence on others quietly. Honor your father or any elder authority figure with a specific act.",
        "dont": "Don't pick fights with authority figures — you'll lose this month even if you're right. Don't push for the visible role or promotion now; wait 4-6 weeks. Don't take ego hits personally; the room is being unfair, it's a season.",
        "areas_affected": [
            {"name": "Authority & recognition", "care": True, "bars_override": 0},
            {"name": "Father / elders", "care": True, "bars_override": 1},
            {"name": "Hidden matters", "care": True, "bars_override": 0},
        ],
        "remedy_planet": "Sun", "remedy_variant": "primary",
        "duration_text": "Roughly one month. The pressure releases when the Sun moves on.",
        "_source": "Roop Chand Joshi Vol II, Sun transit through 8th house. Standard LK reading.",
        "_softening_applied": "Original includes references to father's death; softened to 'father or any elder authority figure' as a relational concern, not a fatal one.",
    },
    "moon_transit_natal_12": {
        "trigger": {
            "type": "transit", "planet": "Moon", "natal_house": 12,
            "natal_state_required": None, "dasha_match": None,
            "duration_min_days": 1,
        },
        "precedence": {"polarity": "negative", "slowness_rank": 1, "yoga_named": False},
        "headline_negative": "Two days of low fuel and porous boundaries.",
        "gist": "The Moon is passing through the most hidden part of your chart — the place of release, isolation, sleep, hidden costs, things that drain. You'll feel more tired than the previous day warrants. Other people's emotions will come through your skin more easily than usual. You'll want to retreat.",
        "cause": "That part of your chart compresses the Moon's nurturing reach. What usually feeds you — connection, family contact, comfort food, attention — won't feed you as well right now. Your boundaries will be more porous; you'll absorb other people's weather.",
        "do": "Protect your sleep. Eat warm food. Take a longer-than-usual private walk. Limit your social hours; if you have a choice between a busy day and a quiet day, choose the quiet one. Drink more water than you think you need.",
        "dont": "Don't make decisions about leaving things — relationships, jobs, places — based on what you feel today. The drift will make everything feel like it should be released. Don't drink alcohol heavily; it accelerates the drain. Don't take on someone else's emotional crisis as your own.",
        "areas_affected": [
            {"name": "Energy & mood", "care": True, "bars_override": 0},
            {"name": "Sleep", "care": True, "bars_override": 0},
            {"name": "Boundaries", "care": True, "bars_override": 0},
        ],
        "remedy_planet": "Moon", "remedy_variant": "primary",
        "duration_text": "About 2 days. Don't expect to function at full capacity; expect to function at 70%.",
        "_source": "Roop Chand Joshi Vol I, Moon transit through 12th. The 12th is the Moon's house of dissolution.",
        "_softening_applied": "Original includes specific fears (drowning, hospitalization); softened to 'porous boundaries' and 'absorbing other people's weather'.",
    },
    "mars_transit_natal_8": {
        "trigger": {
            "type": "transit", "planet": "Mars", "natal_house": 8,
            "natal_state_required": None, "dasha_match": None,
            "duration_min_days": 14,
        },
        "precedence": {"polarity": "negative", "slowness_rank": 4, "yoga_named": False},
        "headline_negative": "Old anger surfacing through the wrong doors.",
        "gist": "Mars is moving through the part of your chart that holds hidden things, transformation, others' resources, and deep wounds. Mars here doesn't burn cleanly; it smolders. Anger that's been buried will come up at moments that don't seem to call for it. Sleep will be more restless. Small accidents become more likely.",
        "cause": "That part of your chart traps Mars's natural release. What would normally burn off through action gets pushed inward — into the body, into restless dreams, into snapping at people who didn't earn it. The fix is not to suppress Mars further; it's to give it a clean channel.",
        "do": "Move your body hard once a day — running, lifting, fighting a heavy bag, vigorous walking. Mars wants discharge. Address the financial entanglement you've been avoiding (the loan, the joint account, the unpaid invoice). Sleep with the window cracked — Mars here disturbs sleep, fresh air helps.",
        "dont": "Don't drive aggressively or operate sharp tools rushed. Don't argue financially with a partner or family member; this transit makes financial conflicts sharper than they need to be. Don't bury the anger further by drinking or numbing — it'll come out worse next time.",
        "areas_affected": [
            {"name": "Sleep & restlessness", "care": True, "bars_override": 0},
            {"name": "Hidden conflicts", "care": True, "bars_override": 0},
            {"name": "Health (inflammation, accidents)", "care": True, "bars_override": 1},
            {"name": "Shared finances", "care": True, "bars_override": 1},
        ],
        "remedy_planet": "Mars", "remedy_variant": "primary",
        "duration_text": "Roughly 6 weeks. Mid-transit is the most volatile — that's the time to discharge daily, not stockpile.",
        "_source": "Roop Chand Joshi Vol II, Mars transit through 8th. In LK transit reading the 8th is hostile to Mars's action nature.",
        "_softening_applied": "Original includes specific fears (violent death, surgery); softened to 'small accidents become more likely' as a precaution, not a prophecy.",
    },
    "mars_transit_natal_6_with_mars_sleeping": {
        "trigger": {
            "type": "transit", "planet": "Mars", "natal_house": 6,
            "natal_state_required": "sleeping", "dasha_match": None,
            "duration_min_days": 14,
        },
        "precedence": {"polarity": "negative", "slowness_rank": 4, "yoga_named": False},
        "headline_negative": "The fight you've been avoiding is asking to be had.",
        "gist": "There's a part of you that takes initiative — pushes, asks, claims, defends. That part has been quiet for a long time in your chart. Right now, conditions are stirring it awake, and it's stirring through friction.",
        "cause": "What you'd normally let slide will not slide this week. Small grievances will feel bigger; the patience you usually have for difficult people will be thinner; a low-grade conflict you've been managing without addressing will want to come to a head. This isn't a problem — it's the inactive part of you trying to wake up.",
        "do": "Choose ONE specific friction in your life this week and address it directly. Not all of them — just one. Have the conversation you've been avoiding. Send the email you've been drafting. Set the boundary you've been thinking about. Move your body hard once a day — Mars wants discharge.",
        "dont": "Don't pick the fight indiscriminately. Mars waking up unevenly is the dangerous part — you'll be tempted to vent at the wrong target. Don't drink heavily, don't drive aggressively, don't sign contracts under emotional pressure. Watch your speech — sharp words will land harder than you mean them to.",
        "areas_affected": [
            {"name": "Conflicts & boundaries", "care": True, "bars_override": 1},
            {"name": "Energy", "care": True, "bars_override": 1},
            {"name": "Health (inflammation, accidents)", "care": True, "bars_override": 0},
        ],
        "remedy_planet": "Mars", "remedy_variant": "awakening",
        "duration_text": "The Mars transit lasts about 6 weeks, but the awakening pressure is sharpest in the middle 2 weeks. After this window, your relationship with assertiveness will be different — for better, if you used the friction; for worse, if you ducked it.",
        "_source": "Roop Chand Joshi Vol III, Mars transit over 6th house (conflict house). Sleeping Mars compounding rule: Vol I, Ch. on dormant planets. Modern reading: U.C. Mahajan, awakening-shock principle.",
        "_softening_applied": "Original LK includes a gendered framing — removed and replaced with 'difficult people' / 'wrong target'. The energy reading is preserved without the gender lock.",
    },
    "mercury_transit_natal_6": {
        "trigger": {
            "type": "transit", "planet": "Mercury", "natal_house": 6,
            "natal_state_required": None, "dasha_match": None,
            "duration_min_days": 7,
        },
        "precedence": {"polarity": "negative", "slowness_rank": 2, "yoga_named": False},
        "headline_negative": "Your words are sharper than the situation deserves.",
        "gist": "Mercury is passing through the part of your chart that holds conflict, daily routines, health, employees, and the small annoyances of life. Mercury here makes you cleverer than the room, but in the worst way — clever at finding faults, clever at the cutting reply, clever at arguments you'll regret winning.",
        "cause": "That part of your chart turns Mercury's brilliance toward what's broken rather than what's possible. You'll see problems other people miss — and you'll be tempted to say so, often, sharply. The result is usually that you alienate people who could have been allies.",
        "do": "Write the cutting reply, then don't send it. Channel the sharpness into actual work — debugging, editing, problem-solving, troubleshooting. This transit is great for finding errors; terrible for raising them in meetings. Take care of small health matters that have been piling up — the routine you've been skipping, the appointment you've been delaying.",
        "dont": "Don't fight with employees, contractors, or anyone you depend on for daily work. Don't write the angry email — Mercury here also rules communication that lingers in the record. Don't pick a health fight with your body by skipping sleep or meals to power through.",
        "areas_affected": [
            {"name": "Communication", "care": True, "bars_override": 1},
            {"name": "Work relationships", "care": True, "bars_override": 0},
            {"name": "Health & routines", "care": True, "bars_override": 1},
        ],
        "remedy_planet": "Mercury", "remedy_variant": "primary",
        "duration_text": "Roughly 2-3 weeks. The sharpness peaks in the middle of the transit; the consequences ripen after.",
        "_source": "Roop Chand Joshi Vol II, Mercury transit through 6th house. Standard reading.",
        "_softening_applied": "None.",
    },
    "jupiter_transit_natal_6": {
        "trigger": {
            "type": "transit", "planet": "Jupiter", "natal_house": 6,
            "natal_state_required": None, "dasha_match": None,
            "duration_min_days": 60,
        },
        "precedence": {"polarity": "negative", "slowness_rank": 7, "yoga_named": False},
        "headline_negative": "Confident moves in directions you'll regret.",
        "gist": "Jupiter is passing through the part of your chart that holds conflict, debt, daily friction, and routine. Jupiter here is the trickiest of all the friction transits, because Jupiter still feels like a blessing — confident, expansive, optimistic — but the confidence is misplaced. You'll feel like the right time to expand is now, and it's not.",
        "cause": "Jupiter's gift is faith. Here, that faith lands on the wrong objects — taking on debt to expand a business that should consolidate, picking up extra obligations because you feel capable, trusting people whose track record you haven't checked. The result is over-commitment that looks confident in the moment and embarrassing later.",
        "do": "Use the confidence on the discipline, not the expansion. Pay down a debt. Finish an old obligation rather than starting a new one. Strengthen routines you've let slip. Address health matters with the optimism the transit gives — Jupiter here IS good for slow steady healing.",
        "dont": "Don't take on new debt — even 'good' debt — during this transit. Don't expand your team, your scope, your obligations. Don't trust your own enthusiasm without three pieces of outside confirmation. Don't sign optimistic contracts.",
        "areas_affected": [
            {"name": "Debt & obligation", "care": True, "bars_override": 1},
            {"name": "Expansion decisions", "care": True, "bars_override": 0},
            {"name": "Health (good news here)", "care": False, "bars_override": 2},
        ],
        "remedy_planet": "Jupiter", "remedy_variant": "primary",
        "duration_text": "Roughly 12 months. The whole year is the trap; the second half is when the over-commitments come due. Decide early to consolidate, not expand.",
        "_source": "Roop Chand Joshi Vol III, Jupiter transit through 6th. The 'false expansion' reading is canonical.",
        "_softening_applied": "None.",
    },
    "venus_transit_natal_12": {
        "trigger": {
            "type": "transit", "planet": "Venus", "natal_house": 12,
            "natal_state_required": None, "dasha_match": None,
            "duration_min_days": 14,
        },
        "precedence": {"polarity": "negative", "slowness_rank": 2, "yoga_named": False},
        "headline_negative": "A month when comfort costs more than usual.",
        "gist": "A passing softness is moving through the part of your chart that holds dissolution, hidden costs, foreign places, sleep, and what we secretly indulge in. Venus here makes pleasure feel slightly off — the comforts that usually feed you taste flat; the relationships that usually warm you require more from you to feel the warmth.",
        "cause": "This is the house of release. Venus there is your pleasure-instinct asked to give rather than receive. The natural reaction — chase the comfort harder — backfires; the more you push for warmth, the further it withdraws. The natural correction is to give pleasure without expecting return.",
        "do": "Be generous with comfort to others without expecting it back. Bring food to someone, buy a friend coffee, send a small gift unprompted. If you can, take a short trip somewhere — Venus here favors foreign or unfamiliar places. Indulge sparingly, with intention.",
        "dont": "Don't try to fill the emptiness with shopping, food, sex, or spending — Venus here doesn't satiate, it amplifies emptiness with consumption. Don't pick a fight with your partner because the warmth feels off; they're not the source, the transit is. Don't lend money you might not see again.",
        "areas_affected": [
            {"name": "Pleasure & comfort", "care": True, "bars_override": 1},
            {"name": "Hidden spending", "care": True, "bars_override": 0},
            {"name": "Partnership warmth", "care": True, "bars_override": 1},
        ],
        "remedy_planet": "Venus", "remedy_variant": "primary",
        "duration_text": "Roughly 3-4 weeks. The drain lifts when Venus moves on; until then, give rather than take.",
        "_source": "Roop Chand Joshi Vol III, Venus transit through 12th. Standard.",
        "_softening_applied": "Original includes gender-specific warnings about affairs; softened without gendering it.",
    },
    "saturn_transit_natal_8": {
        "trigger": {
            "type": "transit", "planet": "Saturn", "natal_house": 8,
            "natal_state_required": None, "dasha_match": None,
            "duration_min_days": 90,
        },
        "precedence": {"polarity": "negative", "slowness_rank": 8, "yoga_named": False},
        "headline_negative": "A long phase of deep, undramatic restructuring.",
        "gist": "Saturn is passing through the deepest, most hidden part of your chart. Things that have been quietly broken for years will start to break visibly. Things you've been avoiding will become unavoidable. This is one of the hardest Saturn transits, but also one of the most useful: it builds the foundation under your foundation.",
        "cause": "Saturn here reveals what was hidden. Financial entanglements you've been ignoring, health matters you've been minimizing, relationship dynamics you've been working around, debts you've stopped acknowledging — they come up for handling. The pressure is real, but the structure that emerges is durable.",
        "do": "Do one slow undramatic act of restructuring per week — pay down debt, sign the will, have the conversation with the partner about finances, address the health thing you've been postponing. Tell the truth to one person who matters. Do this for the whole 2.5-year window.",
        "dont": "Don't launch, announce, or commit to anything large during this transit. Don't pretend things are fine when they aren't — Saturn punishes the pretense, not the problem. Don't borrow money. Don't take big public risks; the transit will expose any weakness.",
        "areas_affected": [
            {"name": "Foundations", "care": True, "bars_override": 0},
            {"name": "Hidden things", "care": True, "bars_override": 0},
            {"name": "Shared finances", "care": True, "bars_override": 0},
            {"name": "Deep health", "care": True, "bars_override": 1},
        ],
        "remedy_planet": "Saturn", "remedy_variant": "primary",
        "duration_text": "Roughly 2.5 years. The first year is the dawning, the middle year is the heavy work, the final year is the rebuild. People who do the work come out grounded; people who duck it come out exhausted.",
        "_source": "Roop Chand Joshi Vol III, Saturn through 8th. The most canonically heavy Saturn transit in LK; cross-confirmed by Sade Sati commentary tradition.",
        "_softening_applied": "Original includes references to surgical operations, parents' death, near-death experiences; softened to 'deep health' as a precaution rather than a verdict.",
    },
    "rahu_transit_natal_12": {
        "trigger": {
            "type": "transit", "planet": "Rahu", "natal_house": 12,
            "natal_state_required": None, "dasha_match": None,
            "duration_min_days": 90,
        },
        "precedence": {"polarity": "negative", "slowness_rank": 9, "yoga_named": False},
        "headline_negative": "An 18-month wrestling match with hidden obsessions.",
        "gist": "Rahu is passing through the most hidden part of your chart — the place of dissolution, sleep, and what's private. Rahu's nature is obsession; here, the obsession runs underground. You'll find yourself ruminating on things you wouldn't normally dwell on. Sleep gets stranger. Foreign or unfamiliar elements enter your life through unexpected doors.",
        "cause": "This part of the chart holds what we don't show. Rahu there amplifies the hidden mind — the fantasies, the anxious loops, the comparisons we make in private, the appetites we don't admit. The transit doesn't create these; it reveals them. Once revealed, they can either be tended or fed.",
        "do": "Establish a daily practice of mental hygiene — meditation, journaling, talking honestly to someone you trust. Write down the obsession that's running, then burn the paper or release it into running water. Travel if you can — Rahu here wants foreign air. Sleep in dark rooms.",
        "dont": "Don't feed the hidden appetite by indulging it in private. Don't make decisions based on the obsessive loops — they're not seeing clearly. Don't isolate excessively, even though the drift will want you to. Don't sign expensive contracts late at night.",
        "areas_affected": [
            {"name": "Hidden mind", "care": True, "bars_override": 0},
            {"name": "Sleep", "care": True, "bars_override": 0},
            {"name": "Foreign elements", "care": True, "bars_override": 2},
            {"name": "Private spending", "care": True, "bars_override": 0},
        ],
        "remedy_planet": "Rahu", "remedy_variant": "primary",
        "duration_text": "Roughly 18 months. The middle 6 months are the strangest. After it passes, what was hidden has either been integrated or has caused real damage; how you used the 18 months determines which.",
        "_source": "Roop Chand Joshi Vol III, Rahu through 12th. LK reads this transit as one of Rahu's heaviest placements.",
        "_softening_applied": "Original includes specific warnings about substance addiction, suicide, foreign incarceration; softened to 'mental hygiene' and 'hidden appetite' as patterns to tend, not fatalities to fear.",
    },
    "ketu_transit_natal_6": {
        "trigger": {
            "type": "transit", "planet": "Ketu", "natal_house": 6,
            "natal_state_required": None, "dasha_match": None,
            "duration_min_days": 90,
        },
        "precedence": {"polarity": "negative", "slowness_rank": 9, "yoga_named": False},
        "headline_negative": "Conflicts ending suddenly — for better and worse.",
        "gist": "Ketu is passing through the part of your chart that holds conflicts, employees, daily routines, debts, and health. Ketu's nature is release; here, things end suddenly. Long-running conflicts resolve without warning. Employees or contractors leave abruptly. Old debts get paid or forgiven unexpectedly. Health patterns that were chronic shift, sometimes by improving, sometimes by clarifying into something requiring attention.",
        "cause": "That part of your chart holds the small daily frictions of life. Ketu's gift is release without warning. The transit doesn't create the resolutions; it lets them happen by removing the energy that was sustaining the conflict. What was unstable becomes stable; what was sustained by your effort dissolves.",
        "do": "Don't fight the endings. If a conflict resolves in a way you didn't choose, sit with it for 30 days before reopening it. If an employee leaves, don't immediately replace them — the gap may teach you what the role actually needs. Address health matters with curiosity rather than alarm; the transit clarifies what's actually happening.",
        "dont": "Don't start new conflicts during this transit — Ketu makes them ungovernable. Don't take on new debts. Don't replace what leaves immediately; let the empty space speak for a while. Don't ignore health signals; Ketu reveals what was hidden.",
        "areas_affected": [
            {"name": "Daily conflicts", "care": True, "bars_override": 1},
            {"name": "Work team", "care": True, "bars_override": 0},
            {"name": "Health", "care": True, "bars_override": 1},
            {"name": "Old debts", "care": False, "bars_override": 2},
        ],
        "remedy_planet": "Ketu", "remedy_variant": "primary",
        "duration_text": "Roughly 18 months. The most volatile period is the middle. The releases — both welcome and unwelcome — cluster in months 6-12.",
        "_source": "Roop Chand Joshi Vol III, Ketu through 6th (Ketu's pakka ghar in LK). The 'sudden release' reading is canonical.",
        "_softening_applied": "Original includes specific warnings about chronic illness becoming acute; softened to 'address health matters with curiosity rather than alarm' as guidance rather than prediction.",
    },
}

# =========================================================================
# OWN-DASHA TRANSITS (9 rows, Batch A)
# Confluence: transit during own MD — doubled activation
# =========================================================================
LK_CONDITIONS["sun_transit_during_sun_md"] = {
    "trigger": {
        "type": "transit_with_dasha", "planet": "Sun", "natal_house": "any",
        "dasha_match": "MD", "duration_min_days": 14,
    },
    "precedence": {"polarity": "positive", "slowness_rank": 3, "yoga_named": False},
    "headline_positive": "A month of doubled focus on authority and visibility.",
    "gist": "The Sun is transiting while it's also the lord of your current long phase — your decade-planet and your daily transit-planet are the same. What the Sun normally does for you — visibility, ego, authority, father-figures, your relationship with hierarchy — happens this month with double weight.",
    "use": "The transit's location tells you where this month's Sun-activation lands. Look at which part of your chart the Sun is in this month; that's the arena where the Sun's gifts and challenges are doubled. Use the month accordingly: visible action where the Sun supports, careful navigation where it doesn't.",
    "do": "Make the visible move you've been preparing for. Address your relationship with your father or a father-figure in your life — this is the long phase that asks it. Take authority in one specific arena even if you don't feel ready.",
    "dont": "Don't burn out trying to be seen everywhere. The Sun's long phase lasts years; you don't have to extract everything from one month. Don't confuse the doubled activation with permanence — when the Sun moves on, the intensity moves with it.",
    "areas_affected": [
        {"name": "Authority", "care": False, "bars_override": 3},
        {"name": "Father / elders", "care": False, "bars_override": 3},
        {"name": "Visibility", "care": False, "bars_override": 3},
    ],
    "remedy_planet": None, "remedy_variant": None,
    "duration_text": "The transit lasts roughly a month. The long-phase context lasts 6 years. The doubled effect lasts the transit window only.",
    "_source": "Roop Chand Joshi Vol II, the principle of dasha-transit confluence.",
    "_softening_applied": "None.",
}
LK_CONDITIONS["moon_transit_during_moon_md"] = {
    "trigger": {
        "type": "transit_with_dasha", "planet": "Moon", "natal_house": "any",
        "dasha_match": "MD", "duration_min_days": 1,
    },
    "precedence": {"polarity": "neutral", "slowness_rank": 1, "yoga_named": False},
    "headline_positive": "Your inner weather, doubled in clarity.",
    "gist": "The Moon is transiting while it is also the lord of your current long phase. The long phase is the ten-year emotional pattern of your life; the transit is the daily emotional weather. This is one of the days where they speak with the same voice. What you feel today is true at both the day-scale and the decade-scale — pay attention.",
    "use": "Listen to what comes up today and treat it as more than passing mood. The clarity of feeling is high; if you've been confused about what you want from this period of life, today's feelings will tell you. Family, mother-figures, home — the recurring themes of your long phase will surface clearly.",
    "do": "Spend an hour somewhere that feels like home. Call a mother-figure. Sit with a feeling that wants to be felt instead of pushing past it. Trust the day's emotional read more than usual.",
    "dont": "Don't dismiss what comes up as 'just a mood' — during this confluence, the mood is the message. Don't make decisions about leaving things based on the day, but do listen to what those decisions want to be.",
    "areas_affected": [
        {"name": "Emotional clarity", "care": False, "bars_override": 3},
        {"name": "Home & family", "care": False, "bars_override": 3},
    ],
    "remedy_planet": None, "remedy_variant": None,
    "duration_text": "The Moon's confluence comes every 2 days during the Moon's long phase — these are the listening days.",
    "_source": "Roop Chand Joshi Vol I, Moon dasha-transit confluence.",
    "_softening_applied": "None.",
}
LK_CONDITIONS["mars_transit_during_mars_md"] = {
    "trigger": {
        "type": "transit_with_dasha", "planet": "Mars", "natal_house": "any",
        "dasha_match": "MD", "duration_min_days": 14,
    },
    "precedence": {"polarity": "positive", "slowness_rank": 4, "yoga_named": False},
    "headline_positive": "Six weeks of concentrated initiative.",
    "gist": "Mars is transiting while it is also the lord of your current long phase. The phase of action and force is in active session, and this is one of the months when the planet that defines the period is moving fast across your chart. Initiative is high. The push you have for hard things doubles.",
    "use": "Take the action you've been preparing for. Start what you've been planning. The long phase of Mars is the phase of doing; this is the month of doing within that phase. The arena depends on which part of your chart Mars is in this month — that's where the doubled push lands.",
    "do": "Pick the project that requires hard, sustained effort and put your back into it for these 6 weeks. Move your body hard daily. Have the conversation that requires courage.",
    "dont": "Don't burn through relationships at the speed of your ambition. Don't drive aggressively, operate sharp tools rushed, or take physical risks beyond your training. The doubled Mars makes accidents more likely too.",
    "areas_affected": [
        {"name": "Initiative", "care": False, "bars_override": 3},
        {"name": "Energy", "care": False, "bars_override": 3},
        {"name": "Conflict (handle carefully)", "care": True, "bars_override": 2},
    ],
    "remedy_planet": None, "remedy_variant": None,
    "duration_text": "Six weeks. After the transit moves on, the long phase's slow burn returns; use the spike while it's available.",
    "_source": "Roop Chand Joshi Vol II, Mars dasha-transit confluence.",
    "_softening_applied": "None.",
}
LK_CONDITIONS["mercury_transit_during_mercury_md"] = {
    "trigger": {
        "type": "transit_with_dasha", "planet": "Mercury", "natal_house": "any",
        "dasha_match": "MD", "duration_min_days": 7,
    },
    "precedence": {"polarity": "positive", "slowness_rank": 2, "yoga_named": False},
    "headline_positive": "Two to three weeks of unusually sharp thinking.",
    "gist": "Mercury is transiting while it is also the lord of your current long phase. The intellectual planet is both your decade-theme and your daily-mover right now. Your thinking is sharper than usual; you can hold more complexity than usual; the right words come for things you usually couldn't articulate.",
    "use": "Write the hard piece. Make the complex decision. Have the difficult conversation that requires precision. Learn the difficult thing. If you've been planning to communicate something subtle, this is the window.",
    "do": "Capture your thoughts — write them down, record them, send them. The clarity won't stay. Make one decision that requires holding complexity. Read something difficult.",
    "dont": "Don't out-talk people just because you can. The sharpness is real but the room may not appreciate it. Don't burn out your mind by overusing it — the long phase is long; pace.",
    "areas_affected": [
        {"name": "Thinking & communication", "care": False, "bars_override": 3},
        {"name": "Decisions", "care": False, "bars_override": 3},
    ],
    "remedy_planet": None, "remedy_variant": None,
    "duration_text": "Roughly 2-3 weeks. The window is bright; use it for what requires brightness.",
    "_source": "Roop Chand Joshi Vol II, Mercury dasha-transit confluence.",
    "_softening_applied": "None.",
}
LK_CONDITIONS["jupiter_transit_during_jupiter_md"] = {
    "trigger": {
        "type": "transit_with_dasha", "planet": "Jupiter", "natal_house": "any",
        "dasha_match": "MD", "duration_min_days": 60,
    },
    "precedence": {"polarity": "positive", "slowness_rank": 7, "yoga_named": False},
    "headline_positive": "A year of widening — growth at both the decade and the year.",
    "gist": "Jupiter is transiting while it is also the lord of your current long phase. This is one of the most blessed dasha-transit confluences. The planet of meaning, expansion, teachers, children, and visible faith is doing its work at both the decade-scale and the year-scale simultaneously.",
    "use": "Make the move that requires faith. Teach what you know. Take on the student, the project, the role that asks for your wisdom. If you've been waiting for the right time to share your work widely, this is it. Travel if you can — Jupiter loves foreign learning during its confluence.",
    "do": "One specific act of teaching, sharing, or expanding this year. Make a public gesture of generosity. Honor a teacher who shaped you. Begin the long-form project you've been postponing because it felt too big.",
    "dont": "Don't over-promise — the same expansive faith opens you and over-extends you. Don't be lazy with detail — Jupiter rewards prepared faith, not blind faith. Don't drift in the warmth; specific action lands.",
    "areas_affected": [
        {"name": "Growth & meaning", "care": False, "bars_override": 3},
        {"name": "Teaching & sharing", "care": False, "bars_override": 3},
        {"name": "Foreign / new arenas", "care": False, "bars_override": 3},
    ],
    "remedy_planet": None, "remedy_variant": None,
    "duration_text": "Roughly 12 months. The confluence is rare; once per Jupiter long-phase in a lifetime.",
    "_source": "Roop Chand Joshi Vol III, Jupiter dasha-transit confluence — described as one of the most auspicious yogas.",
    "_softening_applied": "None.",
}
LK_CONDITIONS["venus_transit_during_venus_md"] = {
    "trigger": {
        "type": "transit_with_dasha", "planet": "Venus", "natal_house": "any",
        "dasha_match": "MD", "duration_min_days": 14,
    },
    "precedence": {"polarity": "positive", "slowness_rank": 2, "yoga_named": False},
    "headline_positive": "A month when warmth, beauty, and pleasure are doubled.",
    "gist": "Venus is transiting while it is also the lord of your current long phase. The planet of connection, beauty, partnership, and comfort is in active flower at both the long phase and the daily transit. What Venus normally gives you — love, comfort, aesthetic joy — comes through doubled doors.",
    "use": "Take the partner — romantic, business, or close friend — somewhere worth going. Buy or make something beautiful. Resolve a relationship tension that's been quiet but unaddressed. If you've been waiting for the right season to deepen a partnership, this is it.",
    "do": "One specific act of deepening with the person who matters most. Bring beauty into the spaces you spend time in. Be more generous with comfort and care than the situation strictly requires.",
    "dont": "Don't confuse the warmth with permanence — the transit ends, the long phase continues, the partnership is in your hands. Don't over-indulge; Venus's confluence has its own self-defeating drift toward excess.",
    "areas_affected": [
        {"name": "Partnership", "care": False, "bars_override": 3},
        {"name": "Beauty & pleasure", "care": False, "bars_override": 3},
    ],
    "remedy_planet": None, "remedy_variant": None,
    "duration_text": "Roughly 3-4 weeks. The Venus long phase is 20 years; the confluence months are the moments to deepen what the long phase is building.",
    "_source": "Roop Chand Joshi Vol II, Venus dasha-transit confluence.",
    "_softening_applied": "Original includes gender-specific marriage advice; softened.",
}
LK_CONDITIONS["saturn_transit_during_saturn_md"] = {
    "trigger": {
        "type": "transit_with_dasha", "planet": "Saturn", "natal_house": "any",
        "dasha_match": "MD", "duration_min_days": 90,
    },
    "precedence": {"polarity": "neutral", "slowness_rank": 8, "yoga_named": False},
    "headline_negative": "Two and a half years where Saturn's long lesson is also Saturn's current weather.",
    "gist": "Saturn is transiting while it is also the lord of your current long phase. The planet of discipline, time, foundation, and slow truth is at work in your long phase AND your current sky. There is no escape from the work Saturn is asking; there is also no shortcut. Every act of patience compounds; every shortcut costs double.",
    "cause": "The Saturn long phase is the long arc of building or stripping. The Saturn transit is the current weather of doing or being slowed. When they overlap, the lesson is concentrated. What you've been ignoring will require attention. What you've been building will be tested.",
    "do": "Do the slow work. Honor the elders. Pay the debts. Tell the truth. Strengthen the routine. This is the period when these acts compound into a foundation that lasts the rest of your life. Don't break the rhythm for short-term gains.",
    "dont": "Don't pretend any difficulty isn't real — Saturn punishes the pretense, not the problem. Don't quit the long project because the short return isn't there. Don't take shortcuts; the cost compounds with the transit.",
    "areas_affected": [
        {"name": "Long-term work", "care": True, "bars_override": 2},
        {"name": "Foundations", "care": True, "bars_override": 1},
        {"name": "Discipline", "care": False, "bars_override": 3},
    ],
    "remedy_planet": "Saturn", "remedy_variant": "primary",
    "duration_text": "The confluence is rare — roughly once per 30 years. When it comes, it is a defining 2.5-year window.",
    "_source": "Roop Chand Joshi Vol III, Saturn dasha-transit confluence. Cross-confirmed in Sade Sati tradition.",
    "_softening_applied": "Original includes references to bereavement, severe illness; softened.",
}
LK_CONDITIONS["rahu_transit_during_rahu_md"] = {
    "trigger": {
        "type": "transit_with_dasha", "planet": "Rahu", "natal_house": "any",
        "dasha_match": "MD", "duration_min_days": 90,
    },
    "precedence": {"polarity": "neutral", "slowness_rank": 9, "yoga_named": False},
    "headline_positive": "An 18-month window where the 18-year Rahu phase shows its hand.",
    "gist": "Rahu is transiting while it is also the lord of your current long phase. The Rahu long phase is an ambitious, foreign-element, rule-bending 18-year arc; this 18-month confluence is where the arc shows its hand. What Rahu is asking of your life will become visible. What you've been resisting in the long phase will surface for decision.",
    "use": "Take the unconventional opportunity. Make the move that breaks the standard pattern. Go to the country, the industry, the relationship, the scale that doesn't fit your previous life. This is the window when the Rahu long phase wants commitment, not just curiosity.",
    "do": "Apply for the thing that scares you. Take the meeting in another country, another scale, another industry. Build something visible and unusual. Stop waiting to be ready.",
    "dont": "Don't burn relationships in pursuit. Don't believe your own hype — the ambition is real but the wisdom isn't automatic. Don't make permanent commitments you can't unwind; Rahu's appetite outpaces its judgment.",
    "areas_affected": [
        {"name": "Ambition", "care": True, "bars_override": 3},
        {"name": "Foreign elements", "care": False, "bars_override": 3},
        {"name": "Long-term direction", "care": True, "bars_override": 2},
    ],
    "remedy_planet": "Rahu", "remedy_variant": "primary",
    "duration_text": "Roughly 18 months. The long phase is 18 years; this confluence is the moment of show-your-hand within it.",
    "_source": "Roop Chand Joshi Vol III, Rahu dasha-transit confluence.",
    "_softening_applied": "None.",
}
LK_CONDITIONS["ketu_transit_during_ketu_md"] = {
    "trigger": {
        "type": "transit_with_dasha", "planet": "Ketu", "natal_house": "any",
        "dasha_match": "MD", "duration_min_days": 90,
    },
    "precedence": {"polarity": "neutral", "slowness_rank": 9, "yoga_named": False},
    "headline_negative": "An 18-month wave of release inside the 7-year wave of release.",
    "gist": "Ketu is transiting while it is also the lord of your current long phase. The Ketu long phase is a 7-year arc of letting go — of attachments, beliefs, identities that have outlived their season. This 18-month confluence is where the letting-go accelerates and clarifies. Things end. Spaces open. The spiritual pull is real and worth following.",
    "cause": "Ketu's nature is release. In its own long phase, in its own transit, the release is real and largely irreversible. What ends now is not coming back. What opens up is genuinely new space, not a temporary clearing.",
    "do": "Don't fight the endings. Sit in the open spaces before filling them — the gift of the confluence is the empty room. Establish a daily silent practice; this is the window where it'll deepen most. Honor what's leaving with attention; don't just move past it.",
    "dont": "Don't replace what leaves immediately. Don't argue with the urge to release; trust it more than you usually would. Don't fill the silence with input — let the quiet teach.",
    "areas_affected": [
        {"name": "Endings & release", "care": False, "bars_override": 3},
        {"name": "Spiritual practice", "care": False, "bars_override": 3},
        {"name": "Identity", "care": True, "bars_override": 2},
    ],
    "remedy_planet": "Ketu", "remedy_variant": "primary",
    "duration_text": "Roughly 18 months inside a 7-year long phase. The confluence is the deepening within the phase.",
    "_source": "Roop Chand Joshi Vol III, Ketu dasha-transit confluence.",
    "_softening_applied": "None.",
}

# =========================================================================
# SLEEPING-STATE AWAKENINGS (8 rows, Batch B)
# All V2 revisions applied:
# - Trauma-attribution scrubbed (B2/B3/B7/B8)
# - Second-sentence variation across all 8
# - Planet-name scaffolding scrubbed
# =========================================================================
LK_CONDITIONS["sun_transit_with_sun_sleeping"] = {
    "trigger": {
        "type": "transit", "planet": "Sun", "natal_house": "any",
        "natal_state_required": "sleeping", "dasha_match": None,
        "duration_min_days": 14,
    },
    "precedence": {"polarity": "negative", "slowness_rank": 3, "yoga_named": False},
    "headline_negative": "Your authority is asking to wake up — and the waking is uncomfortable.",
    "gist": "There's a part of you that holds authority, takes the lead, commands a room, decides what gets to happen. That part has been quiet for a long time in your chart — undeveloped, deferred, often handed off to other people. Right now, conditions are stirring that sleeping authority awake. The poke is real but the waking is uneven.",
    "cause": "Sleeping Sun means a life-pattern of letting others lead, deferring authority, hanging back from visibility. Not a defect — often a survival adaptation. This month, that pattern is being asked to shift. You'll find yourself in situations that require you to step forward, claim space, make a decision out loud. You'll do it badly the first few times. That's how a sleeping planet wakes.",
    "do": "Step into one specific situation this month that requires you to lead — a meeting, a household decision, a creative direction, a stance you'd usually leave to others. Do it badly if necessary. The point is the muscle, not the performance. Watch how it feels — the awkwardness will tell you exactly what's been sleeping.",
    "dont": "Don't over-claim authority you haven't earned just because the impulse is rising. Don't take ego hits as evidence that you should retreat — the room is reacting to a new version of you it hasn't met before. Don't perform leadership; just do it where it's needed.",
    "areas_affected": [
        {"name": "Authority & visibility", "care": True, "bars_override": 1},
        {"name": "Father / elders", "care": True, "bars_override": 1},
        {"name": "Self-expression", "care": True, "bars_override": 1},
    ],
    "remedy_planet": "Sun", "remedy_variant": "awakening",
    "duration_text": "The transit lasts a month. The awakening, if you engage with it, lasts the rest of your life. If you duck it, the same waking-poke comes back next time the Sun transits, harder.",
    "_source": "Roop Chand Joshi Vol I, sleeping planet doctrine; Vol II, Sun transit chapters. The 'awakening shock' framing is from U.C. Mahajan's Lal Kitab Ke Farmaan.",
    "_softening_applied": "Original LK reading frames sleeping Sun as 'pitri dosha' (ancestral father-debt); softened to 'survival adaptation' and 'life pattern' — accurate to lived experience without the karmic fatalism.",
}
LK_CONDITIONS["moon_transit_with_moon_sleeping"] = {
    "trigger": {
        "type": "transit", "planet": "Moon", "natal_house": "any",
        "natal_state_required": "sleeping", "dasha_match": None,
        "duration_min_days": 1,
    },
    "precedence": {"polarity": "negative", "slowness_rank": 1, "yoga_named": False},
    "headline_negative": "Feelings you've been muting are coming through louder.",
    "gist": "There's a part of you that feels — that lets emotion show, that lets attachment matter, that lets care affect decisions. That part has been muted for a long time in your chart — turned down, worked around, kept out of the way of the functional self. Today, conditions are turning up the volume. You'll feel things you usually don't let yourself feel.",
    "cause": "Sleeping Moon means a long-standing habit of muting the feeling-self — staying competent, staying functional, staying in motion to avoid being still. The pattern can have many origins; what matters today is that the chart still holds the muted instrument, and the transit is plucking the strings.",
    "do": "Let one feeling actually arrive today. Don't write it, don't analyze it, don't fix it — just feel it for ten minutes and notice what it actually is. Call your mother or a mother-figure. Eat warm food slowly. Spend time near water if you can. Cry if you need to and don't apologize to anyone for the redness.",
    "dont": "Don't dismiss the surfacing feelings as inconvenient or irrational. Don't bury them harder with work, scrolling, alcohol, or chatter. Don't make decisions based on the muted-feeling logic you usually use — today's feelings are seeing more clearly than your usual lens.",
    "areas_affected": [
        {"name": "Feeling-self", "care": True, "bars_override": 1},
        {"name": "Mother / nurture", "care": True, "bars_override": 1},
        {"name": "Sleep & restfulness", "care": True, "bars_override": 1},
    ],
    "remedy_planet": "Moon", "remedy_variant": "awakening",
    "duration_text": "The transit lasts 2-3 days. The pattern of muting will keep returning until you start letting feeling matter — each Moon transit gets a little softer once you do.",
    "_source": "Roop Chand Joshi Vol I, sleeping Moon doctrine.",
    "_softening_applied": "V2 trauma-attribution scrub: previous draft said 'often built in childhood when feelings were not safe' — overreach. Replaced with origin-neutral pattern description.",
}
LK_CONDITIONS["mercury_transit_with_mercury_sleeping"] = {
    "trigger": {
        "type": "transit", "planet": "Mercury", "natal_house": "any",
        "natal_state_required": "sleeping", "dasha_match": None,
        "duration_min_days": 7,
    },
    "precedence": {"polarity": "negative", "slowness_rank": 2, "yoga_named": False},
    "headline_negative": "Words you've been swallowing are asking to be said.",
    "gist": "There's a part of you that thinks clearly and speaks plainly — the part that names what's happening, asks the question other people are avoiding, tells the truth when the room is dancing around it. That part has been held in check for a long time in your chart — measured, edited, often kept for after the meeting. This week, conditions are pressing that voice toward use. Things that need to be said are pressing against your teeth.",
    "cause": "Sleeping Mercury means a long-running habit of holding your tongue — strategic silence, polite agreement, the swallowed comment in the meeting, the truthful sentence rewritten three times before sending until it loses its truth. Whatever the pattern's origin, the chart still has the clear-speaking instrument; the transit is asking you to use it.",
    "do": "Have one direct conversation this week that you'd usually soften, postpone, or avoid. Write one piece of clear writing — not polished, not perfect, just direct. Ask one question in a meeting that you'd usually save for the hallway after. Notice how it feels — the answer is the medicine.",
    "dont": "Don't release the cumulative silence all at once on whoever happens to be in front of you. Don't confuse 'finally saying it' with 'saying it well' — the first few attempts will be clumsy. Don't write the angry public post; the cleaner work is the direct private conversation.",
    "areas_affected": [
        {"name": "Speech & communication", "care": True, "bars_override": 1},
        {"name": "Truth-telling", "care": True, "bars_override": 1},
        {"name": "Held-back questions", "care": True, "bars_override": 0},
    ],
    "remedy_planet": "Mercury", "remedy_variant": "awakening",
    "duration_text": "The transit lasts 2-3 weeks. The pattern of swallowed speech keeps producing transits like this until the speech starts coming out.",
    "_source": "Roop Chand Joshi Vol II, sleeping Mercury doctrine.",
    "_softening_applied": "V2 trauma-attribution scrub: previous draft said 'often built in environments where direct speech was punished' — overreach. Replaced with origin-neutral pattern description.",
}
LK_CONDITIONS["jupiter_transit_with_jupiter_sleeping"] = {
    "trigger": {
        "type": "transit", "planet": "Jupiter", "natal_house": "any",
        "natal_state_required": "sleeping", "dasha_match": None,
        "duration_min_days": 60,
    },
    "precedence": {"polarity": "negative", "slowness_rank": 7, "yoga_named": False},
    "headline_negative": "Faith you've been withholding is asking to be tried again.",
    "gist": "There's a part of you that believes — in ideas, in people, in the possibility that a thing might work out. That part has been pulled back for a long time in your chart — guarded, conditional, often disguised as wisdom or experience. Right now, the chart is asking you to risk faith again. Not blindly — but actually.",
    "cause": "Sleeping Jupiter means a life-pattern of pulled-back trust. Often built after disappointments — a teacher who failed you, a community that turned out hollow, a belief system that collapsed. The chart still has the trusting instrument; you've just turned it down. The transit is asking you to turn it back up, slowly.",
    "do": "Pick one specific arena where you've been cynical and try a small act of faith. Apply for the thing you assume you won't get. Trust one person you've been guarded with. Read the book you've been suspicious of. Start something whose outcome you can't predict. The risk is the medicine.",
    "dont": "Don't swing to over-trust as a correction — the goal is graduated risk, not a sudden conversion. Don't believe you owe anyone the trust they lost. Don't borrow money on the strength of your new optimism. Don't take on a guru figure to fix the deeper pattern; the work is yours.",
    "areas_affected": [
        {"name": "Trust & faith", "care": True, "bars_override": 1},
        {"name": "Growth & expansion", "care": True, "bars_override": 1},
        {"name": "Teachers & mentors", "care": True, "bars_override": 1},
    ],
    "remedy_planet": "Jupiter", "remedy_variant": "awakening",
    "duration_text": "The transit lasts a year. The pattern of withheld faith is one of the longest sleeping patterns to wake; expect the work to continue past this transit.",
    "_source": "Roop Chand Joshi Vol III, sleeping Jupiter doctrine.",
    "_softening_applied": "Original includes specific spiritual prescriptions (guru-seeking, temple visits); softened to 'graduated risk' and 'specific arena' framings.",
}
LK_CONDITIONS["venus_transit_with_venus_sleeping"] = {
    "trigger": {
        "type": "transit", "planet": "Venus", "natal_house": "any",
        "natal_state_required": "sleeping", "dasha_match": None,
        "duration_min_days": 14,
    },
    "precedence": {"polarity": "negative", "slowness_rank": 2, "yoga_named": False},
    "headline_negative": "The part of you that lets in beauty is asking to be used.",
    "gist": "There's a part of you that lets things be soft — that takes pleasure without earning it, lets a moment be beautiful for its own sake, lets a person be loved without keeping score. That part has been kept at arm's length for a long time in your chart — refused, postponed, only allowed when earned. This month, the chart is asking softness to come back into use.",
    "cause": "Sleeping Venus means a life-pattern of refused softness — staying productive, staying useful, staying earned. Pleasure becomes something you only allow as a reward. Connection becomes something you transact rather than receive. The chart still has the soft instrument; you've been holding it at arm's length. The transit is asking you to bring it close.",
    "do": "Receive one act of warmth this month without immediately repaying it. Let one pleasure happen for its own sake — a long meal, a slow afternoon, an hour with a beautiful object. Compliment someone specifically and let the compliment land without explaining it. Be physical with someone you love without an agenda.",
    "dont": "Don't try to compensate for years of refused softness by overindulging this month. Don't confuse softness with weakness. Don't refuse the warmth that comes — many sleeping-Venus people instinctively decline gifts, kindness, and attention; the practice is in receiving.",
    "areas_affected": [
        {"name": "Pleasure & beauty", "care": True, "bars_override": 1},
        {"name": "Receiving care", "care": True, "bars_override": 0},
        {"name": "Partnership warmth", "care": True, "bars_override": 1},
    ],
    "remedy_planet": "Venus", "remedy_variant": "awakening",
    "duration_text": "The transit lasts about a month. The pattern of refused softness is deep; this transit opens a door, but the practice is daily and long.",
    "_source": "Roop Chand Joshi Vol II, sleeping Venus doctrine.",
    "_softening_applied": "Original includes gender-specific marriage prescriptions; replaced with 'receiving care' as a universal practice.",
}
LK_CONDITIONS["saturn_transit_with_saturn_sleeping"] = {
    "trigger": {
        "type": "transit", "planet": "Saturn", "natal_house": "any",
        "natal_state_required": "sleeping", "dasha_match": None,
        "duration_min_days": 90,
    },
    "precedence": {"polarity": "negative", "slowness_rank": 8, "yoga_named": False},
    "headline_negative": "The slow steady part of you is being asked to grow up.",
    "gist": "There's a part of you that does the unglamorous work — keeps the routine, finishes the boring thing, builds the foundation under the visible win. That part has been deferred for a long time in your chart — compensated for, worked around, replaced with intensity or charm. Right now, the chart is saying: the compensation has run its course; the actual discipline is required.",
    "cause": "Sleeping Saturn means a life-pattern of avoiding the slow grind — getting by on intelligence, charisma, or last-minute heroics. Often this works for the first 30 years; after that the chart wants the foundation built. Saturn's transit isn't punishment; it's the planet of time saying time is real.",
    "do": "Pick ONE thing this transit window — a discipline, a daily practice, a long-form project — and commit to its slow build. Show up daily for it. Tell no one for the first six months — the silence is part of the practice. Honor an elder who has done the slow work. Pay an old debt or finish an old obligation.",
    "dont": "Don't try to compensate with intensity — Saturn rewards consistency over heroics. Don't quit when the slow build feels slow; the slowness is the point. Don't outsource the discipline to a coach, app, or accountability partner; you have to feel the resistance yourself.",
    "areas_affected": [
        {"name": "Discipline & routine", "care": True, "bars_override": 0},
        {"name": "Long-term work", "care": True, "bars_override": 1},
        {"name": "Foundations", "care": True, "bars_override": 1},
    ],
    "remedy_planet": "Saturn", "remedy_variant": "awakening",
    "duration_text": "The transit is 2.5 years. Sleeping Saturn waking is one of the hardest patterns to engage. If you do, the rest of your life is more durable. If you duck it, the next Saturn transit hits harder.",
    "_source": "Roop Chand Joshi Vol III, sleeping Saturn doctrine.",
    "_softening_applied": "Original includes specific warnings about ancestral karma and chronic illness; softened to 'compensation has run its course' as a behavioral observation.",
}
LK_CONDITIONS["rahu_transit_with_rahu_sleeping"] = {
    "trigger": {
        "type": "transit", "planet": "Rahu", "natal_house": "any",
        "natal_state_required": "sleeping", "dasha_match": None,
        "duration_min_days": 90,
    },
    "precedence": {"polarity": "negative", "slowness_rank": 9, "yoga_named": False},
    "headline_negative": "Ambition you've been refusing to name is starting to push through.",
    "gist": "There's a part of you that wants more than you've been letting yourself want — bigger, foreign, unconventional, against the grain of what your life looks like now. That part has been suppressed for a long time in your chart — called impractical, called selfish, called unrealistic. Right now, that ambition won't stay quiet.",
    "cause": "Sleeping Rahu means a long-running habit of suppressed ambition — choosing the smaller, safer, more legible version of what you actually want. The pattern can have many sources; what matters is that the chart holds a larger appetite than the life has been letting you act on. You'll feel restless, dissatisfied with what was previously fine, drawn to foreign or unfamiliar things without quite knowing why.",
    "do": "Name the bigger want, even if only to yourself. Write it down on paper. Spend a week looking at what it would actually take. Take one small action toward it — not the big leap, just a step that acknowledges you've heard it. Travel somewhere unfamiliar for a few days if you can. Read about people who did the version of it you're afraid of.",
    "dont": "Don't blow up your current life in a sudden Rahu surge. Don't believe the first object the ambition fixates on is necessarily the right one — sleeping-Rahu waking tends to chase the wrong target for the right reason. Don't take on a guru, system, or method that promises to channel the ambition; the channeling is yours.",
    "areas_affected": [
        {"name": "Ambition & wanting", "care": True, "bars_override": 1},
        {"name": "Foreign / unfamiliar arenas", "care": False, "bars_override": 2},
        {"name": "Current path stability", "care": True, "bars_override": 1},
    ],
    "remedy_planet": "Rahu", "remedy_variant": "awakening",
    "duration_text": "The transit is 18 months. The ambition will keep pushing until you give it some channel. Ignoring it usually produces a crisis later — Rahu wakes one way or another.",
    "_source": "Roop Chand Joshi Vol III, sleeping Rahu doctrine.",
    "_softening_applied": "V2 trauma-attribution scrub: previous draft said 'often built in families or communities where reaching too far was unsafe' — overreach. Replaced with origin-neutral pattern description.",
}
LK_CONDITIONS["ketu_transit_with_ketu_sleeping"] = {
    "trigger": {
        "type": "transit", "planet": "Ketu", "natal_house": "any",
        "natal_state_required": "sleeping", "dasha_match": None,
        "duration_min_days": 90,
    },
    "precedence": {"polarity": "negative", "slowness_rank": 9, "yoga_named": False},
    "headline_negative": "What you've been holding on to is being asked to be let go.",
    "gist": "There's a part of you that knows how to let things end — that releases an attachment when its season is over, that walks away from what no longer fits, that lets identities expire without funeral. That part has been disused for a long time in your chart — replaced with holding, with keeping, with the survival skill of not letting go. Right now, the pattern of holding is being asked to release.",
    "cause": "Sleeping Ketu means a long-running habit of refused release — accumulating, keeping, holding tight, treating endings as failures. The pattern can come from many places; what matters is that the chart holds a releasing instrument you've been keeping at arm's length. Things will start to end whether you choose them or not.",
    "do": "Give away one specific thing that genuinely costs you — a possession that means something, a role you've been holding past its time, a story about yourself that's no longer true. Reclaim 30 minutes of silent solitude per day. Sit with one ending that you've been refusing to acknowledge. Travel light for a week — only what you can carry.",
    "dont": "Don't try to control which things end. Ketu waking is non-negotiable; the practice is in cooperation, not direction. Don't immediately replace what leaves. Don't confuse the urge to let go with the urge to escape; they look similar, but escape moves you laterally while release moves you forward.",
    "areas_affected": [
        {"name": "Holding on", "care": True, "bars_override": 0},
        {"name": "Identity & roles", "care": True, "bars_override": 1},
        {"name": "Spiritual practice", "care": False, "bars_override": 2},
    ],
    "remedy_planet": "Ketu", "remedy_variant": "awakening",
    "duration_text": "The transit is 18 months. The releases cluster in months 6-12. After it passes, you'll have more open space — and a different relationship with letting go.",
    "_source": "Roop Chand Joshi Vol III, sleeping Ketu doctrine.",
    "_softening_applied": "V2 trauma-attribution scrub: previous draft said 'often built in scarcity or loss-traumatized environments' — overreach. Replaced with origin-neutral pattern description.",
}

# =========================================================================
# NAMED YOGAS (4 rows: 1 sample + 3 from Batch B)
# V2 revisions baked in: parenthetical planet labels scrubbed; Shri financial softened
# =========================================================================
LK_CONDITIONS["vish_yoga_active"] = {
    "trigger": {
        "type": "yoga", "yoga_name": "vish",
        "natal_pattern": "saturn_and_moon_same_house",
        "activation": "moon_transit_over_natal_saturn OR saturn_transit_over_natal_moon",
    },
    "precedence": {"polarity": "negative", "slowness_rank": 6, "yoga_named": True},
    "headline_negative": "A day of low fuel.",
    "gist": "Your inner battery is running low today, even if there's no obvious reason. Sleep was probably restless. Things that normally don't bother you will. This is a known pattern in your chart — Saturn and the Moon meet in a way that drains the feeling-self when the cycle re-activates.",
    "cause": "Two slow energies in your chart — discipline and feeling — were placed together at your birth in a way that, when re-stirred, drains rather than supports. Today is one of those re-stirring days. It's not a verdict; it's a recurring weather pattern your system goes through.",
    "do": "Lower the demands you place on yourself today. Eat warm food, not cold. Drink more water than you think you need. Get to bed an hour early. If you can, walk outside for 20 minutes — moving without effort lifts this pattern more than pushing through. Be slow with people you love; they're not the problem.",
    "dont": "Don't make major decisions today — you're not seeing things in their usual proportions. Don't drink alcohol — it accelerates the drain. Don't take on anyone else's emotional weight — you don't have the spare capacity. Don't believe the dark thoughts the day produces; they're a weather pattern, not the truth.",
    "areas_affected": [
        {"name": "Energy & mood", "care": True, "bars_override": 0},
        {"name": "Sleep", "care": True, "bars_override": 0},
        {"name": "Difficult decisions", "care": True, "bars_override": 0},
    ],
    "remedy_planet": "Moon", "remedy_variant": "primary",
    "duration_text": "These days come roughly every 2-4 weeks for you and last 24-36 hours. Mark the pattern: you'll likely see it cluster around the same days of the lunar cycle each month. Knowing it's coming makes it lighter when it arrives.",
    "_source": "Roop Chand Joshi Vol II, the Vish Yoga (Saturn + Moon conjunction). Standard across all LK commentary.",
    "_softening_applied": "MAJOR. Name 'Vish Yoga' (poison combination) not used user-facing. Original LK text reads as a verdict on the chart's permanent condition; reframed as a recurring weather pattern. Specific fears (death of mother, water accidents) dropped in favor of the felt experience (low fuel, restless sleep). V2: parenthetical planet labels '(Saturn)' and '(the Moon)' scrubbed from cause.",
}
LK_CONDITIONS["guru_chandala_active"] = {
    "trigger": {
        "type": "yoga", "yoga_name": "guru_chandala",
        "natal_pattern": "jupiter_and_rahu_same_house",
        "activation": "jupiter_transit_over_natal_rahu OR rahu_transit_over_natal_jupiter OR transit_aspect_to_either",
    },
    "precedence": {"polarity": "negative", "slowness_rank": 7, "yoga_named": True},
    "headline_negative": "A day when your judgment isn't seeing clearly.",
    "gist": "Two slow energies in your chart — wisdom and ambition — were placed together at your birth in a way that produces a temporary collapse of judgment when the cycle re-activates. You'll feel certain about things you shouldn't be certain about. The advice you'd normally trust from your own instincts is off-calibration today. This is a known pattern in your chart that re-activates periodically.",
    "cause": "Jupiter holds the wisdom of seeing things clearly; Rahu holds the appetite for grand outcomes. When they sit together in your chart and the cycle re-activates, the wisdom serves the appetite — you'll find brilliant-sounding reasons for impulsive moves, articulate cases for things you shouldn't actually do. The clarity feels real but it's pulling you toward Rahu's wanting, not toward truth.",
    "do": "Postpone any major decision by 72 hours. Especially: financial decisions, dramatic public statements, decisions about leaving a current path, decisions to take on a new authority figure or system. Ask one trusted person what they think and listen to them more than to your own conviction. Pause spiritual or philosophical declarations — the conviction is high but the ground is wobbly.",
    "dont": "Don't take on a new teacher, guru, or system in this window. Don't make grand public statements about beliefs. Don't sign contracts that involve trust in a person rather than verification of the work. Don't argue your view down even when it feels obviously right — your own argument is the trap.",
    "areas_affected": [
        {"name": "Judgment & decisions", "care": True, "bars_override": 0},
        {"name": "Teachers & belief systems", "care": True, "bars_override": 0},
        {"name": "Public statements", "care": True, "bars_override": 0},
    ],
    "remedy_planet": "Jupiter", "remedy_variant": "primary",
    "duration_text": "These days come every few months for you and last 24-48 hours. The pattern repeats more strongly during Rahu's long phase. Knowing the weather is the medicine.",
    "_source": "Roop Chand Joshi Vol III, Guru-Chandala Yoga.",
    "_softening_applied": "MAJOR. Name 'Guru-Chandala' (literally 'teacher-outcast' — caste slur) not used user-facing. Reframed from life-long condition to recurring weather pattern. The caste reference is removed entirely — no replacement. V2: parenthetical planet labels '(Jupiter)' and '(Rahu)' scrubbed from gist; mechanism preserved.",
}
LK_CONDITIONS["kemadruma_active"] = {
    "trigger": {
        "type": "yoga", "yoga_name": "kemadruma",
        "natal_pattern": "moon_with_empty_adjacent_houses",
        "activation": "saturn_transit_over_natal_moon OR mars_transit_over_natal_moon OR rahu_transit_over_natal_moon OR ketu_transit_over_natal_moon",
    },
    "precedence": {"polarity": "negative", "slowness_rank": 6, "yoga_named": True},
    "headline_negative": "A day when you feel unsupported, even by the people who care.",
    "gist": "The feeling-self in your chart sits alone in your birth pattern — without planetary neighbors on either side. When a malefic planet moves across it, the loneliness in the chart pattern becomes a loneliness in the day. You'll feel unsupported even when people are around. The phone calls won't reach you. The reassurance won't land. This is a known weather pattern your chart produces; today the wind is blowing through it.",
    "cause": "Kemadruma is a structural loneliness in the chart, not a circumstantial one. Your Moon, the part of you that feels held, has no immediate neighbors in your birth pattern. When the right transit hits, the pattern produces a felt experience of being unheld — even by people who are, in fact, holding you. The mismatch between what the world is offering and what you're able to receive is the painful part.",
    "do": "Tell one person, plainly: 'I'm having a hard day; I don't need you to fix it, but tell me you're there.' That sentence works because Kemadruma's pain is in the un-asked, un-named loneliness; naming it dissolves a layer of it. Eat warm food. Take a hot bath or shower. Sleep early. Limit social media — Kemadruma days amplify the comparison-loneliness.",
    "dont": "Don't believe the day's read of your relationships — Kemadruma makes you misread the warmth in your life as coldness. Don't withdraw from people in response to feeling unheld; the impulse will be strong and the result is the loneliness becoming actual. Don't make decisions about relationships today.",
    "areas_affected": [
        {"name": "Feeling held", "care": True, "bars_override": 0},
        {"name": "Connection", "care": True, "bars_override": 0},
        {"name": "Mood & sleep", "care": True, "bars_override": 1},
    ],
    "remedy_planet": "Moon", "remedy_variant": "primary",
    "duration_text": "Kemadruma days come irregularly — whenever a slow malefic crosses your natal Moon. The longest stretches are when Saturn is the activator (months at a time). The shortest are when Mars or Ketu activate it (a few days). Knowing the pattern is the medicine.",
    "_source": "Roop Chand Joshi Vol II, Kemadruma Yoga. Standard across LK and Parashari.",
    "_softening_applied": "MAJOR. Original LK reading is fatalistic ('the native suffers poverty and loneliness throughout life'). Reframed as recurring weather pattern. Specific predictions about widowhood, childlessness, and poverty removed. V2: 'Your natal Moon — the feeling-self in your chart' rephrased to drop the parenthetical planet name.",
}
LK_CONDITIONS["shri_yoga_active"] = {
    "trigger": {
        "type": "yoga", "yoga_name": "shri",
        "natal_pattern": "jupiter_in_kendra_from_moon",
        "activation": "jupiter_transit_over_natal_benefic_position",
    },
    "precedence": {"polarity": "positive", "slowness_rank": 7, "yoga_named": True},
    "headline_positive": "A window when things flow more easily than they should.",
    "gist": "Your natal chart has a configuration — wisdom sitting in a supportive position relative to your feeling-self — that produces, when re-activated by transit, a felt experience of grace. Things go your way without you forcing them. People say yes to things you'd usually have to push for. Opportunities come through doors you weren't watching. This is one of those windows.",
    "use": "Use this window for the move you've been waiting for permission to make. The proposal, the introduction, the announcement, the leap you'd usually need to prepare for. Shri yoga windows are when you can take action without the usual grinding effort and have it land cleanly. The grace is real — but it won't last past the transit, so the use has to happen in the window.",
    "do": "Identify the one thing you've been waiting for the right moment for, and do it this month. Make the ask, ship the work, send the proposal. Honor a teacher or mentor specifically — acknowledging the wisdom that supports you keeps the channel open. Be open-handed during this window — generous with your time, attention, and credit for others' work. A small open-handed financial gesture, if it fits your means, fits the spirit of this transit.",
    "dont": "Don't take the grace for granted as if it's your new permanent state. Shri yoga windows close. Don't get lazy with rigor just because the wind is favorable — the smooth landing requires that you actually do the thing well. Don't over-promise based on the easy yes; the easy yes is the window, the delivery is yours.",
    "areas_affected": [
        {"name": "Opportunities", "care": False, "bars_override": 3},
        {"name": "Generosity & flow", "care": False, "bars_override": 3},
        {"name": "Big asks", "care": False, "bars_override": 3},
    ],
    "remedy_planet": None, "remedy_variant": None,
    "duration_text": "These windows come a few times in a lifetime. When they come, they last roughly 2-3 months. The 'flow' feeling is strongest in the middle of the window.",
    "_source": "Roop Chand Joshi Vol II, Shri Yoga (Jupiter-Moon kendra combination). Standard across LK; one of the canonically auspicious yogas.",
    "_softening_applied": "Original LK reading includes specific predictions of wealth and high social status; softened to 'things flow more easily.' V2 fix: financial line softened. Previous draft said 'be generous, especially financially' — a daily app prescribing spending is a liability for stressed users. New version leads with time/attention/credit; financial is a conditional 'small gesture, if it fits your means.' V2 also: parenthetical planet labels '(Jupiter)' and '(Moon)' scrubbed from gist.",
}

# ============================================================================
# DICT INTEGRITY CHECK
# ============================================================================
assert len(LK_CONDITIONS) == 40, f"Expected 40 conditions, found {len(LK_CONDITIONS)}"
# Required keys per row
_required = {"trigger", "precedence"}
_user_facing_required_either = {"headline_positive", "headline_negative"}
for cid, c in LK_CONDITIONS.items():
    assert _required.issubset(c.keys()), f"{cid}: missing trigger or precedence"
    assert c["precedence"]["polarity"] in ("positive", "negative", "neutral"), f"{cid}: bad polarity"
    assert _user_facing_required_either.intersection(c.keys()), f"{cid}: no headline_*"
# Verify no house-number leaks in user-facing fields (item #2 enforcement)
import re
_USER_FACING_KEYS = {"headline_positive", "headline_negative", "gist", "cause", "use", "do", "dont", "duration_text"}
_HOUSE_NUM_RE = re.compile(r"\b\d+(?:st|nd|rd|th)\s+house\b", re.IGNORECASE)
_house_leaks = []
for cid, c in LK_CONDITIONS.items():
    for k, v in c.items():
        if k in _USER_FACING_KEYS and isinstance(v, str) and _HOUSE_NUM_RE.search(v):
            _house_leaks.append((cid, k, v[:80]))
assert not _house_leaks, f"House-number leaks: {_house_leaks}"
# Verify underscore-prefixed keys exist (engine-internal, must be filtered before emit)
for cid, c in LK_CONDITIONS.items():
    assert "_source" in c, f"{cid}: missing _source"


def emit_user_facing(condition_id: str) -> dict:
    """
    Helper for emit path: filter out underscore-prefixed engine-internal keys
    before sending to the frontend. The strip layer's source='curated_static'
    branch handles planet-name passthrough; this filter handles structural
    cleanliness.
    """
    cond = LK_CONDITIONS[condition_id]
    return {k: v for k, v in cond.items() if not k.startswith("_")}
