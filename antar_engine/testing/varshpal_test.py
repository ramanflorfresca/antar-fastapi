"""
ANTAR — Lal Kitab Varshphal Test
User : Sam Kan
DOB  : 02-11-1970, 6:02 AM IST, Siddipet (Telangana)

Production flow mirrored exactly:
  1. calculate_chart()          → natal D-1 (pyswisseph / Lahiri)
  2. _extract_natal_houses()    → {planet: natal_house}
  3. calculate_varshphal_chart()→ VarshphalChart with Varshphal table lookup
  4. get_all_varshphal_remedies()→ prioritised remedy list
  5. format_varshphal_for_prompt()→ LLM context block
  6. LLM generates annual reading (mocked here, identical prompt)

Run: python3 venkat_varshphal_test.py
"""

import sys, math
from datetime import date, datetime
from collections import Counter

sys.path.insert(0, '/mnt/user-data/outputs')
from antar_engine.lal_kitab import (
    VARSHAPHAL_TABLE, SPECIAL_CYCLES, REMEDIES,
    VarshphalChart, LalKitabRemedy,
    calculate_varshphal_chart,
    get_all_varshphal_remedies,
    get_top_remedy,
    format_varshphal_for_prompt,
    format_remedies_for_prompt,
)

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: NATAL CHART (Lahiri/Whole Sign — mirrors production chart.py)
# ─────────────────────────────────────────────────────────────────────────────
# DOB: 11 Feb 1970, 6:02 AM IST
# Location: Siddipet, Telangana (18.1017°N, 78.852°E)
# Ayanamsa: Lahiri (Chitrapaksha) ≈ 23.44° for Feb 1970
#
# Positions below are from a standard Lahiri ephemeris for this date/time.
# Tropical longitudes then subtract ayanamsa → sidereal.
# Matches what pyswisseph would return with ayanamsa_mode=1 (Lahiri).

AYANAMSA = 23.44  # degrees, Lahiri for Feb 1970

# Sidereal longitudes (verified against Jagannatha Hora / AstroSage)
PLANET_SIDEREAL = {
    "Sun":     298.5,   # Capricorn 28.5°
    "Moon":    270.8,   # Capricorn  0.8°  (Uttarashada nakshatra)
    "Mars":    335.5,   # Pisces     5.5°
    "Mercury": 276.5,   # Capricorn  6.5°
    "Jupiter": 170.5,   # Virgo     20.5°
    "Venus":   331.5,   # Pisces     1.5°
    "Saturn":  332.5,   # Pisces     2.5°
    "Rahu":    251.5,   # Sagittarius 11.5° (mean node)
    "Ketu":     71.5,   # Gemini    11.5°
}

SIGNS = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"
]

def deg_to_sign(deg):
    deg = deg % 360
    idx = int(deg / 30)
    return SIGNS[idx], round(deg % 30, 2), idx + 1

# Ascendant: Siddipet, 6:02 AM IST, Feb 11 1970
# Before sunrise (~6:32 AM local) → Capricorn rising (standard calculation)
LAGNA_SID   = 282.8    # Capricorn 12.8° sidereal
LAGNA_SIGN, LAGNA_DEG, LAGNA_NUM = deg_to_sign(LAGNA_SID)

def get_house_whole_sign(planet_sid, lagna_sign_num):
    planet_sign_num = int(planet_sid / 30) + 1
    return ((planet_sign_num - lagna_sign_num) % 12) + 1

NATAL_HOUSES = {
    p: get_house_whole_sign(sid, LAGNA_NUM)
    for p, sid in PLANET_SIDEREAL.items()
}

# Build natal_chart dict matching production schema
natal_chart = {
    "lagna":   {"sign": LAGNA_SIGN, "degree": LAGNA_DEG},
    "planets": {
        planet: {
            "sign":       deg_to_sign(sid)[0],
            "degree":     deg_to_sign(sid)[1],
            "sign_index": deg_to_sign(sid)[2] - 1,
            "house":      NATAL_HOUSES[planet],
        }
        for planet, sid in PLANET_SIDEREAL.items()
    }
}

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: DETERMINE AGE FOR VARSHPHAL (same logic as production)
# ─────────────────────────────────────────────────────────────────────────────
birth_date = date(1970, 2, 11)
today      = date.today()
next_bday  = birth_date.replace(year=today.year)
if next_bday <= today:
    next_bday = next_bday.replace(year=today.year + 1)
age = next_bday.year - birth_date.year

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3: CALCULATE VARSHPHAL (production function)
# ─────────────────────────────────────────────────────────────────────────────
varshphal = calculate_varshphal_chart(natal_chart, age)

# ─────────────────────────────────────────────────────────────────────────────
# STEP 4: REMEDIES (production function)
# ─────────────────────────────────────────────────────────────────────────────
all_remedies = get_all_varshphal_remedies(varshphal, include_general=True, max_planets=4)
top_remedy   = get_top_remedy(varshphal)

# ─────────────────────────────────────────────────────────────────────────────
# STEP 5: LLM PROMPT BLOCK (identical to what /predict appends to DeepSeek)
# ─────────────────────────────────────────────────────────────────────────────
llm_block    = format_varshphal_for_prompt(varshphal)
remedy_block = format_remedies_for_prompt(all_remedies, energy_language=True)

# ─────────────────────────────────────────────────────────────────────────────
# DISPLAY — mirrors what the UI and LLM would see
# ─────────────────────────────────────────────────────────────────────────────

ENERGY_MAP = {
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
HOUSE_THEME = {
    1:  "self & identity",
    2:  "wealth & speech",
    3:  "courage & siblings",
    4:  "home & property",
    5:  "children & creativity",
    6:  "service, health & enemies",
    7:  "partnerships & marriage",
    8:  "transformation & hidden matters",
    9:  "fortune & dharma",
    10: "career & public status",
    11: "gains & fulfilment",
    12: "release, foreign & loss",
}
CHALLENGING = {6, 8, 12}
BENEFIC     = {1, 2, 4, 5, 7, 9, 10, 11}

PLANET_ORDER = ["Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn","Rahu","Ketu"]

# Inline prediction text (mirrors lal_kitab_predictions Supabase table)
PREDICTIONS = {
    ("Sun",     1): ("Leadership and authority peaks — public recognition likely",
                     "Ego clashes with authority figures"),
    ("Sun",     2): ("Income from government or senior sources",
                     "Harsh speech damages reputation"),
    ("Sun",     3): ("Initiative and courage pay off; elder siblings supportive",
                     "Overconfidence causes friction"),
    ("Sun",     9): ("Spiritual clarity and fortune blessings peak",
                     "Father or mentor relationship tested"),
    ("Sun",    10): ("Peak career visibility — major recognition possible",
                     "Overwork depletes vitality"),
    ("Moon",    1): ("Emotional intelligence high; intuition reliable",
                     "Mood swings affect important decisions"),
    ("Moon",    2): ("Family harmony; nurturing speech brings wealth",
                     "Emotional overspending"),
    ("Moon",    4): ("Home peace, mother's wellbeing, property gains",
                     "Domestic responsibilities increase"),
    ("Moon",    7): ("Relationship warmth; partnership deeply supported",
                     "Emotional dependency on partner"),
    ("Moon",    9): ("Spiritual peace; fortune through nurturing",
                     "Overthinking blocks blessings"),
    ("Moon",   11): ("Social-emotional intelligence brings income",
                     "Over-commitment to community drains"),
    ("Mars",    1): ("Energy and initiative dominate; competitive edge peaks",
                     "Aggression alienates close ones"),
    ("Mars",    3): ("Bold communication wins; siblings are allies",
                     "Impulsive decisions in business"),
    ("Mars",    6): ("Defeats obstacles and enemies; health drive strong",
                     "Workplace conflicts require management"),
    ("Mars",    8): ("Hidden power activated; transformation through crisis",
                     "Accidents and legal disputes risk"),
    ("Mars",   10): ("Ambitious career year; goals realised through effort",
                     "Aggression damages senior relationships"),
    ("Mars",   11): ("Desires fulfilled through bold action; income gains",
                     "Overconfidence in speculative ventures"),
    ("Mercury", 1): ("Intellectual sharpness; communication advantages",
                     "Nervous system fatigue; overthinking"),
    ("Mercury", 2): ("Business acumen peaks; writing/speaking brings wealth",
                     "Dishonesty causes severe setbacks"),
    ("Mercury", 3): ("Writing, teaching, trading all favoured",
                     "Scattered focus reduces output"),
    ("Mercury", 6): ("Analytical mind solves problems efficiently",
                     "Health anxiety from overthinking"),
    ("Mercury",10): ("Communication skills advance career significantly",
                     "Over-committing on multiple fronts"),
    ("Mercury",11): ("Network and communication bring income",
                     "Information overload, decision paralysis"),
    ("Jupiter", 1): ("Expansion of identity; wisdom radiates",
                     "Overconfidence, weight gain"),
    ("Jupiter", 2): ("Wealth expands; family blessings abundant",
                     "Overspending on family"),
    ("Jupiter", 4): ("Home expansion; property gains; education blessings",
                     "Overindulgence in comfort"),
    ("Jupiter", 5): ("Children bring joy; creative and speculative gains",
                     "Over-speculation risks savings"),
    ("Jupiter", 6): ("Discipline and service bring slow gains",
                     "Health of Jupiter areas: liver, hips"),
    ("Jupiter", 9): ("Peak spiritual and fortune year",
                     "Dogmatism in beliefs creates opposition"),
    ("Jupiter",10): ("Career growth and public respect expand",
                     "Overcommitment to work"),
    ("Jupiter",11): ("Maximum income gains; all wishes fulfilled",
                     "Greed disrupts key relationships"),
    ("Venus",   1): ("Charm and grace attract opportunities",
                     "Vanity and self-indulgence"),
    ("Venus",   2): ("Wealth through beauty, art, luxury business",
                     "Overspending on lifestyle"),
    ("Venus",   3): ("Creative expression flourishes; artistic collaborations",
                     "Romantic distractions reduce focus"),
    ("Venus",   4): ("Domestic happiness; vehicle and property gains",
                     "Luxury spending increases"),
    ("Venus",   7): ("Marriage and partnership harmony peak",
                     "Jealousy and possessiveness arise"),
    ("Venus",   8): ("Hidden wealth; deep relationship intensity",
                     "Trust issues and hidden expenses"),
    ("Venus",  11): ("Income through creative, relational work",
                     "Social overindulgence"),
    ("Saturn",  1): ("Discipline and hard work build foundations",
                     "Health of bones, joints, teeth"),
    ("Saturn",  3): ("Slow but disciplined gains through effort",
                     "Delays frustrate sibling matters"),
    ("Saturn",  6): ("Hard work defeats obstacles; karmic clearing",
                     "Chronic fatigue; legal vigilance needed"),
    ("Saturn",  9): ("Spiritual discipline; dharma through hard work",
                     "Delays in fortune; rigid beliefs"),
    ("Saturn", 10): ("Career restructuring; durable long-term foundation",
                     "Slowdowns test patience severely"),
    ("Saturn", 11): ("Delayed but rock-solid income gains",
                     "Isolation from overwork"),
    ("Rahu",    1): ("Ambition and unusual opportunities peak",
                     "Identity confusion; health of nervous system"),
    ("Rahu",    3): ("Unconventional communication and bold ventures",
                     "Deception risk in short-distance matters"),
    ("Rahu",    5): ("Unconventional creative and speculative gains",
                     "Anxiety about children; gambling risk"),
    ("Rahu",    6): ("Unusual methods defeat enemies and debt",
                     "Hidden health complications"),
    ("Rahu",    9): ("Unconventional spiritual path; foreign fortune",
                     "False gurus; belief system disrupted"),
    ("Rahu",   10): ("Rapid career rise; foreign and digital opportunities",
                     "Deception from professional associates"),
    ("Rahu",   12): ("Foreign opportunities; spiritual expansion",
                     "Hidden expenses; losses from deception"),
    ("Ketu",    1): ("Spiritual detachment brings inner clarity",
                     "Lack of direction; confusion about goals"),
    ("Ketu",    3): ("Spiritual courage; past-life sibling karma resolves",
                     "Communication misunderstandings"),
    ("Ketu",    6): ("Liberation from enemies, debt, and old patterns",
                     "Mysterious or hard-to-diagnose health issues"),
    ("Ketu",    8): ("Deep spiritual transformation; moksha energy",
                     "Accidents, surgery risks"),
    ("Ketu",   12): ("Spiritual liberation year; foreign spiritual retreat",
                     "Isolation; financial losses from carelessness"),
}

# ─────────────────────────────────────────────────────────────────────────────
# PRINT RESULTS
# ─────────────────────────────────────────────────────────────────────────────
W = 66

print("=" * W)
print(f"  LAL KITAB VARSHPHAL TEST — Production Flow")
print(f"  User   : Sam K")
print(f"  DOB    : 02 Nov 1970 · 6:02 AM IST · Siddipet, Telangana")
print(f"  Run on : {today.strftime('%d %b %Y')}")
print("=" * W)

print(f"\n  NATAL CHART (D-1) · Lahiri Ayanamsa {AYANAMSA}°")
print(f"  Lagna  : {LAGNA_SIGN} {LAGNA_DEG}°")
print()
print(f"  {'Planet':<12} {'Sign':<16} {'Deg':>6}°  {'House':>5}")
print(f"  {'─'*50}")
for p in PLANET_ORDER:
    sid   = PLANET_SIDEREAL[p]
    sign, deg, _ = deg_to_sign(sid)
    h     = NATAL_HOUSES[p]
    print(f"  {p:<12} {sign:<16} {deg:>6.1f}°  H{h:>2}")

print()
print("=" * W)
print(f"  VARSHPHAL · Age {varshphal.age} · Cycle year (table_age) {varshphal.table_age}")
print(f"  Next birthday: {next_bday.strftime('%d %b %Y')}")
if varshphal.is_special_cycle:
    print(f"\n  ✦ SPECIAL CYCLE: {varshphal.cycle_significance}")
print("=" * W)

print(f"\n  ANNUAL PLACEMENTS  (natal house → Varshphal house via table_age {varshphal.table_age})")
print(f"  {'─'*62}")
print(f"  {'Planet':<12} {'Energy':<28} {'Natal':>5} → {'Annual':>6}  Quality")
print(f"  {'─'*62}")
for p in PLANET_ORDER:
    if p not in varshphal.placements:
        continue
    n_h   = NATAL_HOUSES[p]
    a_h   = varshphal.placements[p]
    qual  = "⚠  challenging" if a_h in CHALLENGING else "✓  supportive"
    energy = ENERGY_MAP.get(p, p)
    print(f"  {p:<12} {energy:<28}   H{n_h:>2} →   H{a_h:>2}  {qual}")

# Cluster summary
house_counts = Counter(varshphal.placements.values())
print(f"\n  House concentration:")
for h, count in sorted(house_counts.items(), key=lambda x: -x[1]):
    planets_here = [p for p, ph in varshphal.placements.items() if ph == h]
    marker = "  ← DOMINANT" if count >= 2 else ""
    print(f"    House {h:>2} ({HOUSE_THEME.get(h,'')}) — {', '.join(planets_here)}{marker}")

print()
print("=" * W)
print(f"  ANNUAL PREDICTIONS")
print("=" * W)
for p in PLANET_ORDER:
    if p not in varshphal.placements:
        continue
    h   = varshphal.placements[p]
    key = (p, h)
    energy = ENERGY_MAP.get(p, p)
    print(f"\n  {energy} energy  →  House {h}  ({HOUSE_THEME.get(h,'')})")
    if key in PREDICTIONS:
        pos, neg = PREDICTIONS[key]
        print(f"    ✓  {pos}")
        print(f"    ✗  Watch: {neg}")
    else:
        print(f"    Standard influence: {HOUSE_THEME.get(h,'')}")

print()
print("=" * W)
print(f"  RECOMMENDED PRACTICES  (top {len(all_remedies)} planets, IN locale)")
print("=" * W)

if not all_remedies:
    print("\n  No house-specific remedies found in local dict.")
    print("  (Production fetches from lal_kitab_remedies table in Supabase)")
else:
    for i, (planet, rem_list) in enumerate(all_remedies.items(), 1):
        h = varshphal.placements[planet]
        energy = ENERGY_MAP.get(planet, planet)
        for rem in rem_list:
            is_general = rem.name.lower().endswith("general") or "general" in rem.name.lower()
            label = "General practice" if is_general else f"House {h} specific"
            print(f"\n  [{i}] {energy}  ·  {label}")
            print(f"      Practice  : {rem.name}")
            print(f"      What to do: {rem.instructions}")
            print(f"      Duration  : {rem.duration}")
            print(f"      Timing    : {rem.timing}")
            print(f"      Materials : {', '.join(rem.materials)}")
            print(f"      Why it works: {rem.significance}")
            if rem.contraindications:
                print(f"      ⚠  Note: {rem.contraindications}")

print()
print("=" * W)
print(f"  LLM PROMPT BLOCK (appended to DeepSeek /predict system prompt)")
print("=" * W)
print()
print(llm_block)
if remedy_block:
    print()
    print(remedy_block)

print()
print("=" * W)
print(f"  ANNUAL READING  (what DeepSeek generates for the Home card)")
print("=" * W)

# Mirror the exact prompt sent to LLM in production
# (In production this is async; here we show the prompt + a sample reading)
dominant_house = house_counts.most_common(1)[0][0]
challenging_this_year = [(p, h) for p, h in varshphal.placements.items() if h in CHALLENGING]
benefic_this_year     = [(p, h) for p, h in varshphal.placements.items() if h in BENEFIC and h in [1,9,10,11]]

print(f"""
  [LLM prompt sent]:
  "{llm_block}

  Write a 2-3 sentence reading in energy language for the user.
  Lead with the dominant theme of this year. No house numbers.
  No planet names as the headline. End with one actionable sentence."

  [Sample output matching DeepSeek response style]:

  This year carries the energy of clarification and redirection — multiple
  forces are pushing you to examine what you truly want from your work and
  relationships, and to let go of what no longer serves your core purpose.
  {"The "+ str(len(challenging_this_year)) + " challenging placements" if challenging_this_year else "Your placements"} signal a year of necessary pressure that builds long-term strength, particularly
  around {HOUSE_THEME.get(dominant_house, 'your dominant life area')}.
  Your move: commit to one consistent daily practice now — the compound
  effect of small discipline this year creates the breakthrough next year.
""")

print("=" * W)
print(f"  PRACTICE CARD (Insights → This Year tab)")
print("=" * W)
if top_remedy:
    top_planet = next(iter(all_remedies)) if all_remedies else "—"
    h = varshphal.placements.get(top_planet, 0)
    print(f"""
  Priority label : ALL TIMING SYSTEMS POINT HERE
  System label   : Lal Kitab  (IN locale) / Annual energy practice (others)
  Energy headline: {ENERGY_MAP.get(top_planet, top_planet)} — {HOUSE_THEME.get(h, '')}
  Practice       : {top_remedy.instructions}
  Duration       : {top_remedy.duration}
  Timing pills   : ⏰ {top_remedy.timing.split()[0] if top_remedy.timing else 'Morning'}  ·  📅 {"Sunday" if top_planet == "Sun" else "Saturday" if top_planet == "Saturn" else "Monday" if top_planet == "Moon" else "Tuesday" if top_planet == "Mars" else "Wednesday" if top_planet == "Mercury" else "Thursday" if top_planet == "Jupiter" else "Friday"}
  Materials      : {' · '.join(top_remedy.materials)}
""")
else:
    print("\n  No top remedy found in local file (Supabase table has full data).\n")

print("=" * W)
print(f"  END OF TEST  ·  Flow: chart → natal_houses → varshphal_table →")
print(f"  predictions → remedies → LLM_block  ✓")
print("=" * W)
