"""
antar_engine/classical_transit_library.py
==========================================
Static lookup table: classical Vedic interpretations for slow-planet transits
through each house from natal Moon.

Phase 1: 4 planets × 12 houses = 48 entries.
Sources: Phaladipika (Saturn/Jupiter), BPHS (Rahu/Ketu).

Called by: daily_transit_analyzer.py
"""

# ─────────────────────────────────────────────────────────────────
# CLASSICAL_TRANSITS_FROM_MOON
# Key: (planet_name: str, house_from_moon: int 1-12)
# Value: dict with essence, themes, advice, classical_ref
# ─────────────────────────────────────────────────────────────────

CLASSICAL_TRANSITS_FROM_MOON = {

    # ─── SATURN ─────────────────────────────────────────────────

    ("Saturn", 1): {
        "essence": "Sade Sati peak — restriction, health challenges, introspection",
        "themes": ["health caution", "mental strain", "inward focus", "restructuring"],
        "advice": "Avoid major launches. Focus inward. Audit your routines.",
        "classical_ref": "Phaladipika: 'Shani in lagna from Chandra brings grief, fatigue, misfortune. User must endure with patience.'",
    },
    ("Saturn", 2): {
        "essence": "Sade Sati pressure on speech, family, and wealth",
        "themes": ["family tension", "speech conflicts", "financial pressure"],
        "advice": "Guard words. Conserve resources. Avoid family confrontations.",
        "classical_ref": "Phaladipika: 'Shani in 2nd brings loss of wealth, harsh speech, family discord.'",
    },
    ("Saturn", 3): {
        "essence": "Favorable — Saturn's good house. Effort rewards.",
        "themes": ["hard work pays", "sibling dynamics", "short trips productive"],
        "advice": "Push through with discipline. Initiative succeeds.",
        "classical_ref": "Phaladipika: 'Shani in 3rd brings valor, resources, victory over enemies.'",
    },
    ("Saturn", 4): {
        "essence": "Home, mother, comfort under pressure",
        "themes": ["domestic tension", "property matters strained", "mother's health"],
        "advice": "Tend to home and family. Not a day for real estate moves.",
        "classical_ref": "Phaladipika: 'Shani in 4th brings loss of comfort, family separation.'",
    },
    ("Saturn", 5): {
        "essence": "Children, creativity, speculation stressed",
        "themes": ["creative block", "child matters", "investment caution"],
        "advice": "Don't speculate. Support children patiently.",
        "classical_ref": "Phaladipika: 'Shani in 5th brings loss of progeny, mental anxiety, hindrance in studies.'",
    },
    ("Saturn", 6): {
        "essence": "Favorable — Saturn in upachaya. Enemies subside.",
        "themes": ["victory over conflict", "health recovery", "service rewards"],
        "advice": "Good for legal matters, health regimens, disciplined work.",
        "classical_ref": "Phaladipika: 'Shani in 6th brings victory, freedom from enemies, gains from labor.'",
    },
    ("Saturn", 7): {
        "essence": "Partnership strain. Sade Sati trailing phase.",
        "themes": ["marital tension", "business partner conflict", "public opposition"],
        "advice": "Be patient in relationships. Don't sign contracts today.",
        "classical_ref": "Phaladipika: 'Shani in 7th brings separation from spouse, travels far from home.'",
    },
    ("Saturn", 8): {
        "essence": "Dangerous house — health, accidents, hidden losses",
        "themes": ["health risk", "accident caution", "sudden losses"],
        "advice": "Extreme caution today. Defensive posture. No risk-taking.",
        "classical_ref": "Phaladipika: 'Shani in 8th brings calamities, disease, even death-like experiences.'",
    },
    ("Saturn", 9): {
        "essence": "Dharma, father, guru under strain",
        "themes": ["father's health", "teacher conflicts", "religious doubt"],
        "advice": "Honor elders. Don't challenge authority today.",
        "classical_ref": "Phaladipika: 'Shani in 9th brings loss of father, obstacles in long-distance travel.'",
    },
    ("Saturn", 10): {
        "essence": "Career/authority shake-up. Karma-heavy day.",
        "themes": ["work pressure", "authority conflicts", "reputation risk"],
        "advice": "Deliver, don't pitch. Avoid confrontations with boss.",
        "classical_ref": "Phaladipika: 'Shani in 10th brings loss of position, criticism, professional setbacks.'",
    },
    ("Saturn", 11): {
        "essence": "Favorable — Saturn in upachaya. Gains ripen slowly.",
        "themes": ["delayed gains arrive", "network activation", "elder friends"],
        "advice": "Reach out to older contacts. Gains from patience.",
        "classical_ref": "Phaladipika: 'Shani in 11th brings gains, elder friendships, fulfilled desires.'",
    },
    ("Saturn", 12): {
        "essence": "Isolation, foreign, contemplation — Sade Sati opening",
        "themes": ["withdrawal", "secret enemies", "spiritual retreat"],
        "advice": "Rest. Retreat is not defeat today. Avoid public action.",
        "classical_ref": "Phaladipika: 'Shani in 12th brings expenses, imprisonment-like isolation, foreign travel.'",
    },

    # ─── JUPITER ────────────────────────────────────────────────

    ("Jupiter", 1): {
        "essence": "Favorable — Jupiter graces the self",
        "themes": ["personal growth", "optimism", "new beginnings bless"],
        "advice": "Step forward. Public moves favored. Teach or be taught.",
        "classical_ref": "Phaladipika: 'Guru in lagna brings wisdom, reputation, good fortune.'",
    },
    ("Jupiter", 2): {
        "essence": "Strong — wealth and speech amplified",
        "themes": ["financial flow", "family blessing", "truthful speech"],
        "advice": "Good day for financial decisions, family gatherings, meaningful conversations.",
        "classical_ref": "Phaladipika: 'Guru in 2nd brings wealth, family happiness, eloquent speech.'",
    },
    ("Jupiter", 3): {
        "essence": "Weak — Jupiter in 3H brings fatigue",
        "themes": ["energy drain", "minor setbacks", "communication friction"],
        "advice": "Conserve energy. Short trips may tire more than usual.",
        "classical_ref": "Phaladipika: 'Guru in 3rd brings obstacles, unfriendly siblings.'",
    },
    ("Jupiter", 4): {
        "essence": "Favorable — home and heart expand",
        "themes": ["domestic bliss", "property gains", "mother's blessing"],
        "advice": "Time at home is well-spent. Property moves favored.",
        "classical_ref": "Phaladipika: 'Guru in 4th brings comforts, vehicles, happiness from family.'",
    },
    ("Jupiter", 5): {
        "essence": "Very favorable — creativity, children, speculation thrive",
        "themes": ["creative breakthrough", "good news about kids", "wise counsel"],
        "advice": "Take creative risks. Investments in children's futures favored.",
        "classical_ref": "Phaladipika: 'Guru in 5th brings progeny, wisdom, success in education, speculation gains.'",
    },
    ("Jupiter", 6): {
        "essence": "Mildly weak — competition and conflict heightened",
        "themes": ["visible rivals", "legal matters tense", "health caution"],
        "advice": "Document disputes. Avoid confrontation when possible.",
        "classical_ref": "Phaladipika: 'Guru in 6th brings enemies, obstacles, risk of debt.'",
    },
    ("Jupiter", 7): {
        "essence": "Strong — partnerships blessed",
        "themes": ["marriage harmony", "business partner wisdom", "public support"],
        "advice": "Sign contracts, propose partnerships, engage with public.",
        "classical_ref": "Phaladipika: 'Guru in 7th brings wife, partners, success in business.'",
    },
    ("Jupiter", 8): {
        "essence": "Moderate — inheritance, occult, research favored",
        "themes": ["hidden wisdom surfaces", "inheritance news", "research breakthroughs"],
        "advice": "Deep research and hidden matters favored; avoid surgery today.",
        "classical_ref": "Phaladipika: 'Guru in 8th brings legacy, research success, though also expenses.'",
    },
    ("Jupiter", 9): {
        "essence": "Very favorable — own house. Dharma expands.",
        "themes": ["spiritual growth", "father's blessing", "long-distance fortune"],
        "advice": "Teachers, elders, distant opportunities all favored.",
        "classical_ref": "Phaladipika: 'Guru in 9th brings dharma, fortune, guru's grace, pilgrimages.'",
    },
    ("Jupiter", 10): {
        "essence": "Very favorable — career luck peaks",
        "themes": ["career recognition", "authority blesses", "visible reputation"],
        "advice": "Make career moves. Ask for promotion, launch publicly.",
        "classical_ref": "Phaladipika: 'Guru in 10th brings reputation, professional success, noble employment.'",
    },
    ("Jupiter", 11): {
        "essence": "Very favorable — gains flow freely",
        "themes": ["income jumps", "network bears fruit", "wishes fulfilled"],
        "advice": "Best day for sales, collections, closing deals.",
        "classical_ref": "Phaladipika: 'Guru in 11th brings fulfillment of all desires, great gains, elder friendships.'",
    },
    ("Jupiter", 12): {
        "essence": "Weak — expansion goes to expenses",
        "themes": ["generous spending", "foreign connections", "meditation favored"],
        "advice": "Spend on lasting things, not impulse. Good for retreat.",
        "classical_ref": "Phaladipika: 'Guru in 12th brings expenses, though also moksha and foreign blessings.'",
    },

    # ─── RAHU ───────────────────────────────────────────────────

    ("Rahu", 1): {
        "essence": "Identity disruption — ambitious but unstable",
        "themes": ["identity crisis", "bold moves", "foreign influences"],
        "advice": "Ambition peaks but keep actions grounded. Foreign matters favored.",
        "classical_ref": "BPHS: 'Rahu in lagna brings obsession, unconventional behavior, foreign attractions.'",
    },
    ("Rahu", 2): {
        "essence": "Wealth through unconventional means; speech volatility",
        "themes": ["unusual income", "speech regret risk", "family outsider"],
        "advice": "Speak carefully. Income from unusual sources possible.",
        "classical_ref": "BPHS: 'Rahu in 2nd brings unconventional wealth, harsh speech, separation from family.'",
    },
    ("Rahu", 3): {
        "essence": "Favorable — courage and initiative amplify",
        "themes": ["bold moves succeed", "sibling tension", "risk rewards"],
        "advice": "Push hard. Short trips, communications, courage favored.",
        "classical_ref": "BPHS: 'Rahu in 3rd brings fame, courage, victory over enemies.'",
    },
    ("Rahu", 4): {
        "essence": "Home and emotions turbulent",
        "themes": ["domestic upheaval", "foreign home", "mother tension"],
        "advice": "Avoid property disputes. Emotional stability priority.",
        "classical_ref": "BPHS: 'Rahu in 4th brings loss of mother, foreign residence, domestic disturbance.'",
    },
    ("Rahu", 5): {
        "essence": "Creativity and speculation volatile",
        "themes": ["sudden creative insight", "child-related surprise", "gambling caution"],
        "advice": "Creative risks possible but speculation dangerous.",
        "classical_ref": "BPHS: 'Rahu in 5th brings unusual offspring, sudden creative inspiration, speculative losses.'",
    },
    ("Rahu", 6): {
        "essence": "Favorable — enemies defeated, health challenges overcome",
        "themes": ["triumph over rivals", "unconventional healing", "legal wins"],
        "advice": "Excellent day for confronting difficulties, lawsuits, disputes.",
        "classical_ref": "BPHS: 'Rahu in 6th brings victory over enemies, success against disease, gains through service.'",
    },
    ("Rahu", 7): {
        "essence": "Partnership turbulence — unusual connections",
        "themes": ["foreign partnerships", "marital confusion", "public controversy"],
        "advice": "Delay major partnership decisions. Avoid new contracts.",
        "classical_ref": "BPHS: 'Rahu in 7th brings unusual spouse, foreign partnerships, marital discord.'",
    },
    ("Rahu", 8): {
        "essence": "Dangerous — sudden changes, hidden losses",
        "themes": ["accident caution", "secret matters surface", "sudden inheritance"],
        "advice": "Avoid travel, surgery, risky activities today.",
        "classical_ref": "BPHS: 'Rahu in 8th brings calamities, surgeries, occult experiences.'",
    },
    ("Rahu", 9): {
        "essence": "Dharma challenged — foreign teachers",
        "themes": ["religious doubt", "foreign travel", "guru conflict"],
        "advice": "Question beliefs constructively. Foreign connections favored.",
        "classical_ref": "BPHS: 'Rahu in 9th brings non-traditional beliefs, foreign influences on dharma.'",
    },
    ("Rahu", 10): {
        "essence": "Career disruption — unconventional rise",
        "themes": ["sudden career shift", "foreign opportunity", "public controversy"],
        "advice": "Career moves possible but unconventional paths favored.",
        "classical_ref": "BPHS: 'Rahu in 10th brings sudden rise, foreign career, unconventional professions.'",
    },
    ("Rahu", 11): {
        "essence": "Very favorable — unusual gains, foreign networks",
        "themes": ["income surge", "foreign contacts", "unusual alliances"],
        "advice": "Excellent for gains, networking with foreign or unusual contacts.",
        "classical_ref": "BPHS: 'Rahu in 11th brings immense gains, fulfillment of unconventional desires.'",
    },
    ("Rahu", 12): {
        "essence": "Foreign, expenses, isolation, hidden matters",
        "themes": ["foreign expenses", "hidden enemies", "spiritual depth"],
        "advice": "Travel abroad favored. Avoid large purchases.",
        "classical_ref": "BPHS: 'Rahu in 12th brings foreign residence, heavy expenses, imprisonment-like confinement.'",
    },

    # ─── KETU ───────────────────────────────────────────────────

    ("Ketu", 1): {
        "essence": "Spiritual detachment from self-image",
        "themes": ["identity dissolution", "spiritual insight", "physical fatigue"],
        "advice": "Introspection over action. Question self-image.",
        "classical_ref": "BPHS: 'Ketu in lagna brings detachment, spiritual inclination, physical weakness.'",
    },
    ("Ketu", 2): {
        "essence": "Speech and wealth detachment",
        "themes": ["financial uncertainty", "silent speech", "family distance"],
        "advice": "Guard wealth. Speak less. Avoid family arguments.",
        "classical_ref": "BPHS: 'Ketu in 2nd brings loss of wealth, harsh speech, family issues.'",
    },
    ("Ketu", 3): {
        "essence": "Courage tested — introspective effort",
        "themes": ["energy drain", "sibling distance", "quiet breakthroughs"],
        "advice": "Effort feels heavier; persistence matters more than boldness.",
        "classical_ref": "BPHS: 'Ketu in 3rd brings obstacles, weakness, difficulties with siblings.'",
    },
    ("Ketu", 4): {
        "essence": "Home unsettled, mother distant",
        "themes": ["domestic disconnection", "property issues", "emotional detachment"],
        "advice": "Time alone at home helps. Avoid major domestic decisions.",
        "classical_ref": "BPHS: 'Ketu in 4th brings loss of happiness, mother distance, foreign travel.'",
    },
    ("Ketu", 5): {
        "essence": "Creativity blocked, children distant",
        "themes": ["creative block", "child-related anxiety", "investment caution"],
        "advice": "Don't force creativity. Avoid speculation today.",
        "classical_ref": "BPHS: 'Ketu in 5th brings difficulties with progeny, mental troubles, speculation losses.'",
    },
    ("Ketu", 6): {
        "essence": "Favorable — enemies dissolve",
        "themes": ["mysterious resolution", "health improves", "hidden wins"],
        "advice": "Good for subtle moves against opposition; legal matters favored.",
        "classical_ref": "BPHS: 'Ketu in 6th brings victory, freedom from disease, defeat of enemies.'",
    },
    ("Ketu", 7): {
        "essence": "Partnership detachment",
        "themes": ["marital distance", "business partner absence", "public withdrawal"],
        "advice": "Not a day for partnership commitments.",
        "classical_ref": "BPHS: 'Ketu in 7th brings loss of spouse, business partner issues, foreign travels.'",
    },
    ("Ketu", 8): {
        "essence": "Mystical, transformational, risky",
        "themes": ["occult insight", "inheritance matters", "accident risk"],
        "advice": "Meditation, research favored. Avoid risky physical activity.",
        "classical_ref": "BPHS: 'Ketu in 8th brings calamities, surgery, spiritual awakening through suffering.'",
    },
    ("Ketu", 9): {
        "essence": "Dharma transcended — pure spiritual focus",
        "themes": ["guru distant", "father's detachment", "pilgrimage inclination"],
        "advice": "Unconventional spiritual paths favored.",
        "classical_ref": "BPHS: 'Ketu in 9th brings loss of father, detachment from religion, foreign pilgrimages.'",
    },
    ("Ketu", 10): {
        "essence": "Career dissolves or transforms",
        "themes": ["career uncertainty", "authority distance", "reputation shift"],
        "advice": "Avoid big career moves. Reflect on purpose.",
        "classical_ref": "BPHS: 'Ketu in 10th brings career obstacles, loss of position, non-traditional work.'",
    },
    ("Ketu", 11): {
        "essence": "Gains through unusual or detached means",
        "themes": ["unexpected gains", "friend distance", "unusual income"],
        "advice": "Gains come from letting go, not chasing.",
        "classical_ref": "BPHS: 'Ketu in 11th brings gains from unexpected sources, though friendships are distant.'",
    },
    ("Ketu", 12): {
        "essence": "Moksha, foreign, hidden — the highest placement for Ketu",
        "themes": ["spiritual breakthrough", "foreign ease", "expenses for meaning"],
        "advice": "Retreat, meditation, foreign travel all favored.",
        "classical_ref": "BPHS: 'Ketu in 12th brings moksha, foreign residence, liberation from karmic burdens.'",
    },
}


def lookup_classical_transit(planet: str, house_from_moon: int) -> dict:
    """Returns the interpretation block, or a sensible default."""
    entry = CLASSICAL_TRANSITS_FROM_MOON.get((planet, house_from_moon))
    if not entry:
        return {
            "essence": f"{planet} in {house_from_moon}H from Moon — neutral influence today.",
            "themes": [],
            "advice": "Standard day for this planet's karaka.",
            "classical_ref": "",
        }
    return entry
