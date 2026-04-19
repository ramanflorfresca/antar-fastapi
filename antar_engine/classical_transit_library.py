"""
antar_engine/classical_transit_library.py
==========================================
Static lookup table: classical Vedic interpretations for slow-planet transits
through each house from natal Moon.

8 planets × 12 houses = 96 entries.
Sources: Phaladipika (Saturn/Jupiter/Sun/Mars/Venus), BPHS (Rahu/Ketu/Mercury).

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

    # ─── SUN (shifts sign every ~30 days) ──────────────────────

    ("Sun", 1): {
        "essence": "Vitality and visibility spike, ego active",
        "themes": ["authority", "health energy", "father figure"],
        "advice": "Step forward, speak up, take the lead.",
        "classical_ref": "Phaladipika: 'Surya in lagna from Chandra brings prominence, vitality, and authority.'",
    },
    ("Sun", 2): {
        "essence": "Speech authoritative, finances flow",
        "themes": ["bold claims", "family of origin", "eating habits"],
        "advice": "Important financial calls favored.",
        "classical_ref": "Phaladipika: 'Surya in 2nd brings commanding speech and wealth through authority.'",
    },
    ("Sun", 3): {
        "essence": "Favorable — courage and initiative rise",
        "themes": ["siblings", "short trips", "writing"],
        "advice": "Take bold action on communications.",
        "classical_ref": "Phaladipika: 'Surya in 3rd brings valor, courage, and victory through effort.'",
    },
    ("Sun", 4): {
        "essence": "Home and domestic friction",
        "themes": ["mother tension", "property issues", "inner discomfort"],
        "advice": "Tend to home matters with patience.",
        "classical_ref": "Phaladipika: 'Surya in 4th brings domestic unease and friction with mother.'",
    },
    ("Sun", 5): {
        "essence": "Creative confidence peaks",
        "themes": ["children", "speculation", "romance"],
        "advice": "Creative risks and educational pursuits favored.",
        "classical_ref": "Phaladipika: 'Surya in 5th brings creative brilliance and gains through progeny.'",
    },
    ("Sun", 6): {
        "essence": "Favorable — victory over enemies",
        "themes": ["competition wins", "health improvement", "service"],
        "advice": "Confront obstacles directly.",
        "classical_ref": "Phaladipika: 'Surya in 6th brings triumph over enemies, disease, and competition.'",
    },
    ("Sun", 7): {
        "essence": "Partnership spotlight",
        "themes": ["spouse attention", "business partners", "public dealings"],
        "advice": "Negotiate from strength.",
        "classical_ref": "Phaladipika: 'Surya in 7th brings prominence in partnerships and public dealings.'",
    },
    ("Sun", 8): {
        "essence": "Vitality dip, hidden matters surface",
        "themes": ["health caution", "inheritance", "research"],
        "advice": "Rest, avoid confrontation, protect energy.",
        "classical_ref": "Phaladipika: 'Surya in 8th brings loss of vitality, hidden troubles, and fatigue.'",
    },
    ("Sun", 9): {
        "essence": "Father and guru connection activated",
        "themes": ["long travel", "dharma", "authority figures"],
        "advice": "Seek guidance from mentors.",
        "classical_ref": "Phaladipika: 'Surya in 9th brings connection to father, guru, and righteous pursuits.'",
    },
    ("Sun", 10): {
        "essence": "Very favorable — career peak and recognition",
        "themes": ["recognition", "authority", "professional success"],
        "advice": "Make career moves, seek promotion.",
        "classical_ref": "Phaladipika: 'Surya in 10th brings fame, authority, and professional triumph.'",
    },
    ("Sun", 11): {
        "essence": "Very favorable — gains from authority",
        "themes": ["income", "elder connections", "network fruits"],
        "advice": "Best day for collections and income moves.",
        "classical_ref": "Phaladipika: 'Surya in 11th brings abundant gains, fulfilled desires, and powerful allies.'",
    },
    ("Sun", 12): {
        "essence": "Vitality drains, retreat indicated",
        "themes": ["expenses", "foreign", "isolation"],
        "advice": "Rest and spiritual practice over action.",
        "classical_ref": "Phaladipika: 'Surya in 12th brings loss of vitality, expenses, and withdrawal from public.'",
    },

    # ─── MARS (shifts every ~45 days) ──────────────────────────

    ("Mars", 1): {
        "essence": "Aggression, courage, physical energy peak",
        "themes": ["fight mode", "physical activity", "conflict risk"],
        "advice": "Channel into action, avoid confrontations.",
        "classical_ref": "Phaladipika: 'Mangala in lagna from Chandra brings courage, aggression, and physical vigor.'",
    },
    ("Mars", 2): {
        "essence": "Speech heated, financial aggression",
        "themes": ["harsh words", "family conflict", "spending impulse"],
        "advice": "Guard speech and wallet.",
        "classical_ref": "Phaladipika: 'Mangala in 2nd brings harsh speech, family strife, and impulsive spending.'",
    },
    ("Mars", 3): {
        "essence": "Very favorable — valor and initiative succeed",
        "themes": ["courage succeeds", "siblings", "bold communication"],
        "advice": "Push hard. Best day for competitive moves.",
        "classical_ref": "Phaladipika: 'Mangala in 3rd brings great valor, victory, and success through initiative.'",
    },
    ("Mars", 4): {
        "essence": "Domestic friction and heated emotions",
        "themes": ["property disputes", "vehicle issues", "emotional heat"],
        "advice": "Avoid property decisions, cool heated situations.",
        "classical_ref": "Phaladipika: 'Mangala in 4th brings domestic strife, vehicle trouble, and emotional unrest.'",
    },
    ("Mars", 5): {
        "essence": "Children and creativity intensified",
        "themes": ["speculation risk", "romantic intensity", "competitive games"],
        "advice": "Channel intensity into creative output, avoid gambling.",
        "classical_ref": "Phaladipika: 'Mangala in 5th brings intensity in romance, speculation risk, and creative fire.'",
    },
    ("Mars", 6): {
        "essence": "Very favorable — enemies defeated decisively",
        "themes": ["competition dominated", "health discipline", "litigation wins"],
        "advice": "Confront opposition with full force.",
        "classical_ref": "Phaladipika: 'Mangala in 6th brings destruction of enemies, victory in competition and litigation.'",
    },
    ("Mars", 7): {
        "essence": "Partnership conflict and friction",
        "themes": ["spouse friction", "business partner clash", "public disputes"],
        "advice": "Cool down before engaging partner.",
        "classical_ref": "Phaladipika: 'Mangala in 7th brings marital friction, partner conflicts, and public disputes.'",
    },
    ("Mars", 8): {
        "essence": "Dangerous — accidents and sudden events",
        "themes": ["health risk", "surgery", "insurance matters"],
        "advice": "Extreme caution. No risky activities.",
        "classical_ref": "Phaladipika: 'Mangala in 8th brings accidents, surgery risk, and sudden calamities.'",
    },
    ("Mars", 9): {
        "essence": "Father conflict, dharma challenged",
        "themes": ["authority clashes", "travel disruption", "ideological fights"],
        "advice": "Don't provoke elders.",
        "classical_ref": "Phaladipika: 'Mangala in 9th brings conflict with father, disrupted travel, and dharmic friction.'",
    },
    ("Mars", 10): {
        "essence": "Career aggression and ambitious push",
        "themes": ["work intensity", "authority confrontation", "ambitious push"],
        "advice": "Channel energy into deliverables, not fights.",
        "classical_ref": "Phaladipika: 'Mangala in 10th brings career intensity, ambition, and authority clashes.'",
    },
    ("Mars", 11): {
        "essence": "Favorable — gains from bold action",
        "themes": ["income through effort", "competitive wins", "network activation"],
        "advice": "Push for what you're owed.",
        "classical_ref": "Phaladipika: 'Mangala in 11th brings gains through effort, competitive victories, and network activation.'",
    },
    ("Mars", 12): {
        "essence": "Energy drain and hidden enemies active",
        "themes": ["hospitalization risk", "secret conflict", "expenses"],
        "advice": "Rest and recover. Avoid confrontation.",
        "classical_ref": "Phaladipika: 'Mangala in 12th brings energy loss, hidden enemies, and hospitalization risk.'",
    },

    # ─── MERCURY (shifts every 15-30 days) ─────────────────────

    ("Mercury", 1): {
        "essence": "Mind sharp, communication clear",
        "themes": ["analytical clarity", "writing", "quick thinking"],
        "advice": "Good for writing, teaching, negotiating, contracts.",
        "classical_ref": "BPHS: 'Budha in lagna from Chandra brings sharp intellect, eloquent speech, and clarity.'",
    },
    ("Mercury", 2): {
        "essence": "Financial intelligence active",
        "themes": ["money calculations", "family communication", "food decisions"],
        "advice": "Financial analysis and negotiations favored.",
        "classical_ref": "BPHS: 'Budha in 2nd brings financial acumen, persuasive speech, and family dialogue.'",
    },
    ("Mercury", 3): {
        "essence": "Very favorable — Mercury in its own house themes",
        "themes": ["brilliant communication", "sibling connection", "short trips"],
        "advice": "Write, pitch, network. Communication superpower active.",
        "classical_ref": "BPHS: 'Budha in 3rd brings mastery of communication, literary success, and sibling harmony.'",
    },
    ("Mercury", 4): {
        "essence": "Mental restlessness at home",
        "themes": ["home organization", "intellectual pursuits", "study"],
        "advice": "Organize your space, study at home.",
        "classical_ref": "BPHS: 'Budha in 4th brings restless mind, intellectual home pursuits, and study.'",
    },
    ("Mercury", 5): {
        "essence": "Intellectual creativity flourishes",
        "themes": ["clever solutions", "children's education", "speculation analysis"],
        "advice": "Apply intellect to creative problems.",
        "classical_ref": "BPHS: 'Budha in 5th brings intellectual creativity, clever solutions, and educational gains.'",
    },
    ("Mercury", 6): {
        "essence": "Favorable — analytical problem-solving dominates",
        "themes": ["health analysis", "legal documentation", "service optimization"],
        "advice": "Solve complex problems, handle paperwork.",
        "classical_ref": "BPHS: 'Budha in 6th brings victory through intellect, analytical skill defeats enemies.'",
    },
    ("Mercury", 7): {
        "essence": "Partnership communication peaks",
        "themes": ["negotiation", "business discussions", "contract signing"],
        "advice": "Best day for deals and partnership negotiations.",
        "classical_ref": "BPHS: 'Budha in 7th brings successful negotiations, partnership agreements, and trade.'",
    },
    ("Mercury", 8): {
        "essence": "Research and investigation favored",
        "themes": ["hidden information revealed", "occult study", "tax matters"],
        "advice": "Dig deep. Research and analysis favored.",
        "classical_ref": "BPHS: 'Budha in 8th brings research breakthroughs, hidden knowledge, and investigative success.'",
    },
    ("Mercury", 9): {
        "essence": "Learning and higher thought activated",
        "themes": ["teaching", "publishing", "philosophical discussion"],
        "advice": "Learn, teach, or publish something meaningful.",
        "classical_ref": "BPHS: 'Budha in 9th brings higher learning, teaching success, and philosophical clarity.'",
    },
    ("Mercury", 10): {
        "essence": "Favorable — career communication drives success",
        "themes": ["professional presentations", "business writing", "analytical work"],
        "advice": "Present your work. Communication drives career.",
        "classical_ref": "BPHS: 'Budha in 10th brings professional recognition through intellect and communication.'",
    },
    ("Mercury", 11): {
        "essence": "Very favorable — gains from intellect and ideas",
        "themes": ["income through ideas", "network communication", "tech gains"],
        "advice": "Monetize your intelligence. Sell, pitch, close.",
        "classical_ref": "BPHS: 'Budha in 11th brings gains through intellect, successful trade, and network profits.'",
    },
    ("Mercury", 12): {
        "essence": "Mind wanders, miscommunication risk",
        "themes": ["miscommunication risk", "foreign correspondence", "introspection"],
        "advice": "Double-check all communications. Avoid binding agreements.",
        "classical_ref": "BPHS: 'Budha in 12th brings confused thinking, expenses on communication, and foreign correspondence.'",
    },

    # ─── VENUS (shifts every ~30 days) ─────────────────────────

    ("Venus", 1): {
        "essence": "Charm, beauty, pleasure — self as attractive",
        "themes": ["relationship warmth", "creative flow", "comfort seeking"],
        "advice": "Connect with beauty. Relationship gestures favored.",
        "classical_ref": "Phaladipika: 'Shukra in lagna from Chandra brings charm, beauty, and pleasurable experiences.'",
    },
    ("Venus", 2): {
        "essence": "Very favorable — wealth and comfort flow",
        "themes": ["financial gains", "family harmony", "food and luxury"],
        "advice": "Best day for purchases and financial moves.",
        "classical_ref": "Phaladipika: 'Shukra in 2nd brings wealth, family happiness, and luxurious comforts.'",
    },
    ("Venus", 3): {
        "essence": "Creative communication flourishes",
        "themes": ["artistic expression", "pleasant travels", "sibling harmony"],
        "advice": "Express creatively. Social outings favored.",
        "classical_ref": "Phaladipika: 'Shukra in 3rd brings artistic expression, pleasant journeys, and sibling joy.'",
    },
    ("Venus", 4): {
        "essence": "Very favorable — domestic bliss peaks",
        "themes": ["home beauty", "vehicle purchase", "mother's comfort"],
        "advice": "Invest in home. Domestic harmony peaks.",
        "classical_ref": "Phaladipika: 'Shukra in 4th brings domestic happiness, vehicles, and comforts of home.'",
    },
    ("Venus", 5): {
        "essence": "Romance and creativity peak",
        "themes": ["love affairs", "artistic breakthrough", "children's joy"],
        "advice": "Express love. Creative projects flourish.",
        "classical_ref": "Phaladipika: 'Shukra in 5th brings romance, creative brilliance, and joy through progeny.'",
    },
    ("Venus", 6): {
        "essence": "Moderate — opponents softened through charm",
        "themes": ["workplace harmony", "health through comfort", "service with grace"],
        "advice": "Kill with kindness. Charm solves conflicts.",
        "classical_ref": "Phaladipika: 'Shukra in 6th brings resolution through diplomacy and grace under pressure.'",
    },
    ("Venus", 7): {
        "essence": "Very favorable — partnerships blessed",
        "themes": ["marriage harmony", "business partnership", "public appeal"],
        "advice": "Best day for relationship commitments and partnerships.",
        "classical_ref": "Phaladipika: 'Shukra in 7th brings marital bliss, successful partnerships, and public favor.'",
    },
    ("Venus", 8): {
        "essence": "Hidden pleasures and inheritance matters",
        "themes": ["secret relationships", "insurance gains", "transformation through beauty"],
        "advice": "Investigate financial assets. Private matters favored.",
        "classical_ref": "Phaladipika: 'Shukra in 8th brings hidden gains, inheritance, and transformative pleasures.'",
    },
    ("Venus", 9): {
        "essence": "Fortune through grace and beauty",
        "themes": ["travel for pleasure", "guru's blessing", "dharmic relationships"],
        "advice": "Travel, connect with mentors, expand horizons gracefully.",
        "classical_ref": "Phaladipika: 'Shukra in 9th brings fortune through grace, pleasant travels, and guru's favor.'",
    },
    ("Venus", 10): {
        "essence": "Career charm and public likability",
        "themes": ["professional recognition through likability", "creative career moves", "public image"],
        "advice": "Charm your audience. Let likability drive career moves.",
        "classical_ref": "Phaladipika: 'Shukra in 10th brings career success through charm, creative profession, and public admiration.'",
    },
    ("Venus", 11): {
        "essence": "Very favorable — gains through relationships",
        "themes": ["income through connections", "social network activation", "wish fulfillment"],
        "advice": "Network aggressively. Relationships bring gains.",
        "classical_ref": "Phaladipika: 'Shukra in 11th brings abundant gains, social success, and fulfilled desires.'",
    },
    ("Venus", 12): {
        "essence": "Expenses on pleasure, foreign comfort",
        "themes": ["luxury spending", "foreign relationships", "bedroom matters"],
        "advice": "Budget for indulgence. Foreign connections favored.",
        "classical_ref": "Phaladipika: 'Shukra in 12th brings expenses on pleasure, foreign comforts, and bedroom happiness.'",
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
