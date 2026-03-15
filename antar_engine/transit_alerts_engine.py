"""
antar_engine/transit_alerts_engine.py

Practical Transit Alert Engine
================================
NOT: "Jupiter enters Aries on April 21"
YES: "The expansion planet just entered your money zone —
      the next 12 months are your best window for income growth
      since 2012. Here's exactly what to do."

Every alert answers 3 questions:
  1. What is happening? (plain language)
  2. What does it mean FOR ME specifically? (natal chart impact)
  3. What do I do about it? (action + caution + remedy)

Alert types:
  - Major planet sign changes (Jupiter, Saturn, Rahu/Ketu)
  - Slow planet hitting natal planet (within 3°)
  - Retrograde periods (Mercury, Venus, Mars)
  - Eclipse alerts (Solar + Lunar)
  - Saturn-Jupiter conjunctions (rare)
  - Rahu/Ketu axis shift
  - Personal transits (planet crossing natal Sun/Moon/Lagna)
"""

from datetime import datetime, date, timedelta
from typing import Optional

SIGNS = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"
]
SIGN_LORDS = {
    "Aries":"Mars","Taurus":"Venus","Gemini":"Mercury","Cancer":"Moon",
    "Leo":"Sun","Virgo":"Mercury","Libra":"Venus","Scorpio":"Mars",
    "Sagittarius":"Jupiter","Capricorn":"Saturn","Aquarius":"Saturn","Pisces":"Jupiter"
}

# Plain language planet meanings
PLANET_ENERGY = {
    "Jupiter": "expansion, opportunity, wisdom, and abundance",
    "Saturn":  "discipline, pressure, karmic lessons, and restructuring",
    "Rahu":    "transformation, ambition, foreign connections, and disruption",
    "Ketu":    "release, spirituality, past-life completion, and detachment",
    "Mars":    "energy, conflict, action, and drive",
    "Venus":   "relationships, creativity, comfort, and pleasure",
    "Mercury": "communication, deals, thinking, and information",
    "Sun":     "identity, authority, and vital force",
    "Moon":    "emotions, public life, and intuition",
}

# House meanings in plain language
HOUSE_LIFE_AREAS = {
    1:  ("your identity and body",        "how you show up in the world"),
    2:  ("your money and family",         "savings, speech, and family wealth"),
    3:  ("your courage and communication","writing, siblings, and short travel"),
    4:  ("your home and inner peace",     "family life, property, and emotional foundation"),
    5:  ("your creativity and children",  "intelligence, romance, and speculation"),
    6:  ("your health and challenges",    "work routine, enemies, and debts"),
    7:  ("your partnerships",             "business and romantic relationships"),
    8:  ("your transformation",           "inheritance, secrets, and sudden changes"),
    9:  ("your fortune and dharma",       "long journeys, father, and higher purpose"),
    10: ("your career and reputation",    "authority, public recognition, and calling"),
    11: ("your income and goals",         "friendships, networks, and ambitions"),
    12: ("your inner world and release",  "spirituality, foreign lands, and endings"),
}

# What each planet's transit through each house means practically
TRANSIT_HOUSE_MEANING = {
    "Jupiter": {
        1: ("A year of personal growth and opportunity — you become more visible and magnetic",
            "Start new projects, put yourself forward, invest in your health and appearance",
            "Don't waste this energy on small thinking — Jupiter in your 1st expands everything you ARE"),
        2: ("Income grows — family wealth improves — your words carry more weight",
            "Good time to negotiate salary, save, and invest. Family matters resolve favorably",
            "Best year in 12 for accumulating wealth. Don't be passive about money now"),
        3: ("Courage expands — communication projects thrive — siblings may bring good news",
            "Write, publish, pitch, travel. Sibling relationships improve",
            "Your ideas have Jupiter's backing. Speak up, submit proposals, take the trip"),
        4: ("Home life brightens — property matters favor you — inner peace grows",
            "Buy property, renovate, move if you've been wanting to. Family harmony peaks",
            "Best time in 12 years for real estate decisions"),
        5: ("Creative intelligence peaks — children bring joy — romance and speculation favor you",
            "Launch creative projects, spend quality time with children, consider investments",
            "Your best year for creative output — whatever you make now has Jupiter's blessing"),
        6: ("Health improves — you overcome obstacles — work becomes more rewarding",
            "Take on challenging tasks, get health checkups, address long-standing problems",
            "Enemies lose power over you. Debts can be cleared. Health investments pay off"),
        7: ("Partnerships blossom — marriage prospects improve — business alliances are favorable",
            "Meet potential partners, sign agreements, expand your business relationships",
            "The best year for marriage or business partnerships in 12 years"),
        8: ("Hidden resources surface — inheritance possible — transformation is supported",
            "Research, investigate, address unresolved matters. Unexpected gains possible",
            "Deep work and occult studies bring rewards. Old matters finally resolve"),
        9: ("Fortune flows — travel brings wisdom — father relationships improve",
            "Take that important journey, pursue higher education, connect with teachers",
            "Your lucky year. Act on your biggest dreams — Jupiter's fortune is strongest in 9th"),
        10: ("Career peaks — public recognition arrives — authority increases",
            "Apply for promotions, launch businesses, make your work public",
            "This is your professional peak year. Don't stay small — Jupiter demands expansion"),
        11: ("Income surges — goals are achieved — networks expand powerfully",
            "Pursue ambitious goals, join organizations, expect financial gains",
            "Best year in 12 for income growth and achieving long-held ambitions"),
        12: ("Spiritual growth deepens — foreign opportunities arise — inner wealth grows",
            "Meditate, travel abroad, do inner work, let go of what no longer serves",
            "Apparent setbacks are Jupiter moving you toward something better"),
    },
    "Saturn": {
        1: ("A restructuring period for your identity — Sade Sati or Saturn transit demands honesty about who you are",
            "Get serious about health, streamline your commitments, eliminate what doesn't serve",
            "Saturn strips away what was false. What remains is your authentic foundation"),
        2: ("Financial discipline required — family karma activates — watch spending",
            "Budget carefully, avoid unnecessary loans, resolve family financial issues",
            "Saturn in your money house tests your financial habits. Build not borrow"),
        3: ("Communication becomes more serious — courage is tested — siblings may need support",
            "Think before speaking, honor commitments in writing, support your siblings",
            "Every word matters now. Discipline in communication builds lasting reputation"),
        4: ("Home life needs attention — property matters may be complex — emotional stability is earned",
            "Address home repairs, support parents, create genuine domestic stability",
            "Saturn in 4th builds lasting foundations — but it requires real work on the home front"),
        5: ("Creative work requires discipline — children may need extra attention — speculative risks backfire",
            "Work systematically on creative projects, spend structured time with children, avoid gambling",
            "Saturn in 5th rewards disciplined creators and patient parents"),
        6: ("Health demands attention — work ethic is tested — overcome obstacles through persistence",
            "Get checkups, improve work routines, address chronic health issues head-on",
            "Saturn in 6th: serve well, stay healthy, defeat enemies through consistent effort"),
        7: ("Partnerships face tests — marriage requires work — business deals need scrutiny",
            "Work consciously on relationships, choose partners carefully, review contracts thoroughly",
            "Saturn in 7th teaches you what a real partnership looks like"),
        8: ("Transformation is deep and unavoidable — hidden matters surface — face fears directly",
            "Address unresolved issues, manage inheritance matters carefully, embrace necessary change",
            "Saturn in 8th: the deepest restructuring. What doesn't serve you falls away completely"),
        9: ("Fortune requires effort — dharma is tested — father may need support",
            "Work hard at your principles, support your father, earn your luck through discipline",
            "Saturn in 9th: blessings come only through genuine merit now"),
        10: ("Career demands maximum effort — authority is tested — reputation is being built",
            "Work harder than ever, avoid shortcuts, build your professional reputation stone by stone",
            "Saturn in 10th is the career-building period. The work you do now echoes for 30 years"),
        11: ("Goals require patience — income comes slowly but surely — networks need cultivation",
            "Play the long game with income, invest time in genuine relationships",
            "Saturn in 11th: slow steady gains beat quick wins. Build your network with integrity"),
        12: ("Inner work is called — hidden karma surfaces — spirituality deepens",
            "Meditate, release grudges, address hidden fears, consider retreats",
            "Saturn in 12th prepares for your next big cycle. Clear old karma consciously"),
    },
    "Rahu": {
        1: ("Identity transformation — unconventional path forward — magnetic but restless energy",
            "Embrace the new version of yourself, pursue unconventional opportunities",
            "Rahu in 1st: you'll do things differently now. Don't fight it — direct it"),
        2: ("Wealth through unconventional means — foreign income — complex family dynamics",
            "Pursue non-traditional income streams, be careful with speech and honesty",
            "Rahu in 2nd: big money is possible but deceptive financial deals are dangerous"),
        4: ("Home and family transformation — possible relocation — restlessness at home",
            "Consider the relocation you've been avoiding, address deep family patterns",
            "Rahu in 4th: the home you know will change. Embrace it rather than resist"),
        7: ("Unconventional partnerships — foreign or unusual relationships — karmic connections",
            "Be extra careful in choosing partners, watch for people who aren't what they seem",
            "Rahu in 7th: powerful connections but choose wisely — karmic relationship territory"),
        10: ("Unconventional career rise — sudden recognition — disruption in public life",
            "Take the unusual career path, embrace technology and foreign opportunities",
            "Rahu in 10th: the next 18 months can transform your career trajectory completely"),
        11: ("Sudden income from unexpected sources — unconventional gains — network explodes",
            "Pursue foreign income, build digital networks, act on unconventional income ideas",
            "Rahu in 11th: your biggest gains come from where you least expect"),
    },
}

# Mercury retrograde periods 2025-2026
MERCURY_RETROGRADE_2025_2026 = [
    {"start": "2025-03-15", "end": "2025-04-07", "sign": "Pisces",
     "theme": "Pisces — intuition, dreams, and hidden matters"},
    {"start": "2025-07-18", "end": "2025-08-11", "sign": "Leo",
     "theme": "Leo — creativity, confidence, and self-expression"},
    {"start": "2025-11-09", "end": "2025-11-29", "sign": "Scorpio",
     "theme": "Scorpio — transformation, secrets, and intensity"},
    {"start": "2026-03-15", "end": "2026-04-07", "sign": "Pisces",
     "theme": "Pisces — intuition, spiritual matters, and past connections"},
]

# Retrograde plain language
RETROGRADE_MEANING = {
    "Mercury": {
        "general": "Mercury backward = review, revise, reconnect. NOT the time to sign new contracts, launch products, or start major new projects. Great time to finish what's unfinished.",
        "do": [
            "Reconnect with old contacts — they're thinking of you too",
            "Review and revise existing projects",
            "Complete unfinished work that's been sitting",
            "Back up all important data",
            "Re-read contracts before signing anything",
        ],
        "dont": [
            "Sign new major contracts if you can avoid it",
            "Launch new products or businesses",
            "Send important emails without re-reading them",
            "Assume people received your messages — follow up",
            "Make irreversible tech purchases",
        ],
    },
    "Venus": {
        "general": "Venus backward = love under review. Exes return, relationships get tested, self-worth questions arise. Not the time for cosmetic procedures or major luxury purchases.",
        "do": [
            "Reflect on what you truly want in relationships",
            "Reconnect with creative projects you abandoned",
            "Review your finances and values",
        ],
        "dont": [
            "Start new romantic relationships (they rarely last)",
            "Get cosmetic surgery or major beauty procedures",
            "Make luxury purchases",
        ],
    },
    "Mars": {
        "general": "Mars backward = energy turns inward. Action slows, conflicts simmer, motivation dips. Focus on strategy not execution.",
        "do": [
            "Plan and strategize rather than execute",
            "Address underlying conflicts rather than suppressing them",
            "Do inner work on anger and drive",
        ],
        "dont": [
            "Start major new initiatives",
            "Pick fights or make aggressive moves",
            "Begin new fitness routines (injury risk is higher)",
        ],
    },
}


def get_transit_house(transit_sign: str, natal_lagna_sign: str) -> int:
    """Calculate which house a transiting planet is in relative to natal lagna."""
    if transit_sign not in SIGNS or natal_lagna_sign not in SIGNS:
        return 0
    lagna_idx   = SIGNS.index(natal_lagna_sign)
    transit_idx = SIGNS.index(transit_sign)
    return ((transit_idx - lagna_idx) % 12) + 1


def get_natal_planet_house_impact(
    transit_planet: str,
    transit_sign: str,
    natal_planets: dict,
) -> list:
    """
    Check if transit planet is conjunct or opposing natal planets.
    Returns list of natal planets being impacted.
    """
    impacts = []
    if transit_sign not in SIGNS:
        return impacts

    transit_idx = SIGNS.index(transit_sign)

    for planet, data in natal_planets.items():
        natal_sign = data.get("sign","")
        if natal_sign not in SIGNS:
            continue
        natal_idx = SIGNS.index(natal_sign)

        # Conjunction (same sign)
        if transit_idx == natal_idx:
            impacts.append({
                "natal_planet": planet,
                "aspect":       "conjunction",
                "intensity":    "high",
                "natal_house":  data.get("house", 0),
            })
        # Opposition (7 signs away)
        elif abs(transit_idx - natal_idx) == 6:
            impacts.append({
                "natal_planet": planet,
                "aspect":       "opposition",
                "intensity":    "high",
                "natal_house":  data.get("house", 0),
            })
        # Trine (4 or 8 signs away — Jaimini rashi aspect approximation)
        elif abs(transit_idx - natal_idx) in [3, 9]:
            impacts.append({
                "natal_planet": planet,
                "aspect":       "trine",
                "intensity":    "moderate",
                "natal_house":  data.get("house", 0),
            })

    return impacts


def build_transit_alert(
    transit_planet: str,
    transit_sign: str,
    natal_chart: dict,
    alert_type: str = "sign_change",
    retrograde: bool = False,
    retrograde_period: dict = None,
    additional_context: str = "",
) -> dict:
    """
    Build a complete practical transit alert for a specific person.
    """
    natal_planets  = natal_chart.get("planets", {})
    natal_lagna    = natal_chart.get("lagna", {})
    natal_lagna_sign = natal_lagna.get("sign","") if isinstance(natal_lagna,dict) else str(natal_lagna)
    atmakaraka     = natal_chart.get("atmakaraka","")

    # Calculate house
    transit_house = get_transit_house(transit_sign, natal_lagna_sign)

    # Get natal planet impacts
    natal_impacts = get_natal_planet_house_impact(
        transit_planet, transit_sign, natal_planets)

    # Get house meaning
    house_area = HOUSE_LIFE_AREAS.get(transit_house, ("your life", "general areas"))

    # Get transit meaning for this planet+house
    planet_meanings = TRANSIT_HOUSE_MEANING.get(transit_planet, {})
    house_meaning   = planet_meanings.get(transit_house, None)

    if retrograde and transit_planet in RETROGRADE_MEANING:
        retro_info = RETROGRADE_MEANING[transit_planet]
        period_str = ""
        if retrograde_period:
            period_str = f"{retrograde_period.get('start','')} to {retrograde_period.get('end','')}"
    else:
        retro_info  = None
        period_str  = ""

    # Build the alert
    planet_energy = PLANET_ENERGY.get(transit_planet,"")

    # Headline
    if retrograde:
        headline = f"{transit_planet} Retrograde in {transit_sign} — Time to Review, Not Launch"
    else:
        headline = f"{transit_planet} Moves Into Your {_ordinal(transit_house)} House of {house_area[0].title()}"

    # What's happening
    what = (f"{transit_planet} — the planet of {planet_energy} — "
            f"{'is going retrograde in' if retrograde else 'has moved into'} {transit_sign}, "
            f"which falls in your {_ordinal(transit_house)} house of {house_area[0]}.")

    # What it means for you specifically
    if house_meaning:
        means_for_you = house_meaning[0]
        action        = house_meaning[1]
        key_insight   = house_meaning[2]
    elif retrograde and retro_info:
        means_for_you = retro_info["general"]
        action        = " | ".join(retro_info.get("do",[])[:3])
        key_insight   = "This retrograde activates your " + house_area[0]
    else:
        means_for_you = f"{transit_planet}'s energy is now focused on {house_area[1]}"
        action        = f"Pay attention to {house_area[1]} during this transit"
        key_insight   = ""

    # Natal planet impacts
    impact_notes = []
    for impact in natal_impacts[:2]:
        nat_p = impact["natal_planet"]
        aspect = impact["aspect"]
        nat_h  = impact["natal_house"]
        if aspect == "conjunction":
            impact_notes.append(
                f"This directly activates your natal {nat_p} — "
                f"{_natal_planet_transit_meaning(transit_planet, nat_p, nat_h)}")
        elif aspect == "opposition":
            impact_notes.append(
                f"Creates tension between {transit_planet}'s agenda and your natal {nat_p} — "
                f"balance these two life areas consciously")

    # Caution
    if transit_planet == "Saturn":
        caution = f"Saturn demands honesty and effort in {house_area[0]}. Shortcuts backfire now."
    elif transit_planet == "Rahu":
        caution = f"Rahu's energy in {house_area[0]} is powerful but can lead to obsession. Stay grounded."
    elif retrograde:
        caution = f"Don't force new beginnings — review what already exists instead."
    else:
        caution = f"Don't let this opportunity pass without taking action in {house_area[0]}."

    # Remedy
    remedy = _get_transit_remedy(transit_planet, transit_house, retrograde)

    # Duration
    duration = _get_transit_duration(transit_planet)

    # Do/Don't for retrograde
    do_list   = retro_info.get("do",[])[:3]   if retro_info else []
    dont_list = retro_info.get("dont",[])[:3] if retro_info else []

    return {
        "planet":         transit_planet,
        "sign":           transit_sign,
        "house":          transit_house,
        "house_area":     house_area[0],
        "alert_type":     alert_type,
        "retrograde":     retrograde,
        "period":         period_str,
        "duration":       duration,
        "headline":       headline,
        "what":           what,
        "means_for_you":  means_for_you,
        "action":         action,
        "caution":        caution,
        "key_insight":    key_insight,
        "natal_impacts":  impact_notes,
        "do_list":        do_list,
        "dont_list":      dont_list,
        "remedy":         remedy,
        "urgency":        _get_urgency(transit_planet, transit_house, retrograde),
        "generated_at":   datetime.utcnow().isoformat(),
    }


def generate_all_active_alerts(natal_chart: dict, current_transits: dict) -> list:
    """
    Generate all active transit alerts for a person right now.
    Returns sorted list by urgency.
    """
    alerts = []
    natal_lagna_sign = natal_chart.get("lagna",{}).get("sign","") if isinstance(natal_chart.get("lagna"),dict) else ""
    today = date.today()

    # Check slow planets (Jupiter, Saturn, Rahu)
    SLOW_PLANETS = ["Jupiter","Saturn","Rahu","Ketu"]
    for planet in SLOW_PLANETS:
        transit_data = current_transits.get(planet,{}) if isinstance(current_transits,dict) else {}
        if not transit_data:
            continue
        transit_sign = transit_data.get("sign","")
        if not transit_sign:
            continue

        alert = build_transit_alert(
            transit_planet=planet,
            transit_sign=transit_sign,
            natal_chart=natal_chart,
            alert_type="slow_planet",
        )
        if alert.get("house"):
            alerts.append(alert)

    # Check Mercury retrograde
    for retro in MERCURY_RETROGRADE_2025_2026:
        try:
            start = date.fromisoformat(retro["start"])
            end   = date.fromisoformat(retro["end"])
            if start <= today <= end:
                # Active retrograde
                alert = build_transit_alert(
                    transit_planet="Mercury",
                    transit_sign=retro["sign"],
                    natal_chart=natal_chart,
                    alert_type="retrograde",
                    retrograde=True,
                    retrograde_period=retro,
                )
                alerts.append(alert)
            elif today < start and (start - today).days <= 14:
                # Upcoming retrograde — warn 2 weeks ahead
                alert = build_transit_alert(
                    transit_planet="Mercury",
                    transit_sign=retro["sign"],
                    natal_chart=natal_chart,
                    alert_type="retrograde_upcoming",
                    retrograde=True,
                    retrograde_period=retro,
                )
                alert["headline"] = f"⚠ Mercury Retrograde begins {retro['start']} — Prepare Now"
                alert["urgency"] = "high"
                alerts.append(alert)
        except Exception:
            pass

    # Sort by urgency
    URGENCY_ORDER = {"critical":0, "high":1, "medium":2, "low":3}
    alerts.sort(key=lambda x: URGENCY_ORDER.get(x.get("urgency","low"), 3))

    return alerts[:6]  # max 6 active alerts


def build_transit_alerts_context(natal_chart: dict, current_transits: dict) -> str:
    """Build transit alerts context block for LLM."""
    alerts = generate_all_active_alerts(natal_chart, current_transits)

    if not alerts:
        return ""

    lines = [
        "═══════════════════════════════════════════════════════",
        "ACTIVE TRANSIT ALERTS — PRACTICAL IMPACT RIGHT NOW",
        "═══════════════════════════════════════════════════════",
    ]

    for alert in alerts:
        urgency_icon = {"critical":"🔴","high":"🟡","medium":"🟢","low":"⚪"}.get(
            alert.get("urgency","low"), "⚪")

        lines += [
            f"",
            f"{urgency_icon} {alert['headline']}",
            f"  Duration: {alert['duration']}",
            f"  What's happening: {alert['what']}",
            f"  What this means for you: {alert['means_for_you']}",
            f"  Action: {alert['action']}",
            f"  Caution: {alert['caution']}",
        ]

        if alert.get("natal_impacts"):
            for imp in alert["natal_impacts"]:
                lines.append(f"  Personal impact: {imp}")

        if alert.get("do_list"):
            lines.append(f"  DO: {' | '.join(alert['do_list'][:2])}")
        if alert.get("dont_list"):
            lines.append(f"  DON'T: {' | '.join(alert['dont_list'][:2])}")

        lines.append(f"  Remedy: {alert['remedy']}")

    lines += [
        "",
        "INSTRUCTION: When answering questions, reference these active transits.",
        "Always explain WHAT the transit means for THIS person's specific houses.",
        "═══════════════════════════════════════════════════════",
    ]

    return "\n".join(lines)


def format_alerts_for_api(alerts: list) -> list:
    """Format alerts for frontend display."""
    formatted = []
    for alert in alerts:
        formatted.append({
            "id":           f"{alert['planet']}_{alert['house']}_{alert['alert_type']}",
            "planet":       alert["planet"],
            "urgency":      alert["urgency"],
            "headline":     alert["headline"],
            "summary":      alert["means_for_you"][:150],
            "action":       alert["action"],
            "caution":      alert["caution"],
            "do_list":      alert.get("do_list",[]),
            "dont_list":    alert.get("dont_list",[]),
            "remedy":       alert["remedy"],
            "house":        alert["house"],
            "house_area":   alert["house_area"],
            "duration":     alert["duration"],
            "retrograde":   alert["retrograde"],
            "period":       alert.get("period",""),
            "key_insight":  alert.get("key_insight",""),
            "natal_impacts":alert.get("natal_impacts",[]),
        })
    return formatted


# ── Helper functions ─────────────────────────────────────────────

def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1:"st",2:"nd",3:"rd"}.get(n%10,"th")
    return f"{n}{suffix}"


def _natal_planet_transit_meaning(transit: str, natal: str, natal_house: int) -> str:
    meanings = {
        ("Jupiter","Sun"):    "your authority and identity get a major expansion — career recognition peaks",
        ("Jupiter","Moon"):   "emotional life flourishes — public recognition and family harmony improve",
        ("Jupiter","Mars"):   "energy and courage get Jupiter's blessing — bold action succeeds now",
        ("Jupiter","Mercury"):"communication and business ideas get amplified — launch your ideas",
        ("Jupiter","Venus"):  "relationships and creative work peak — best time for love and art",
        ("Jupiter","Saturn"): "discipline meets expansion — hard work finally pays off",
        ("Saturn","Sun"):     "identity and career face karmic audit — only authentic work survives",
        ("Saturn","Moon"):    "emotional patterns are restructured — genuine inner work is called",
        ("Saturn","Mars"):    "aggressive patterns are disciplined — channel energy through structure",
        ("Saturn","Jupiter"): "expansion is tested — only sustainable growth survives this transit",
        ("Rahu","Sun"):       "identity transformation — conventional path disrupted by something bigger",
        ("Rahu","Moon"):      "emotional and mental patterns accelerate — obsessive thinking possible",
        ("Rahu","Jupiter"):   "wisdom and opportunities arrive from unexpected directions",
    }
    key = (transit, natal)
    return meanings.get(key, f"your natal {natal} in house {natal_house} is being directly activated")


def _get_transit_remedy(planet: str, house: int, retrograde: bool) -> str:
    if retrograde:
        remedies = {
            "Mercury": "Chant Mercury mantra: Om Budhaya Namah. Review all pending communications.",
            "Venus":   "Offer white flowers to Venus on Friday. Review relationships honestly.",
            "Mars":    "Pray to Hanuman. Channel anger into exercise not confrontation.",
        }
        return remedies.get(planet, f"Strengthen {planet} through its natural remedy during retrograde")

    remedies = {
        "Jupiter": "Offer yellow sweets on Thursday. Thank your teachers. Donate to education.",
        "Saturn":  "Serve the poor on Saturday. Oil lamps. Keep commitments.",
        "Rahu":    "Feed crows. Keep elephant figurine. Donate on Saturdays.",
        "Ketu":    "Meditate daily. Keep cat. Donate blankets to poor.",
    }
    return remedies.get(planet, f"Strengthen {planet} through its natural remedy")


def _get_transit_duration(planet: str) -> str:
    durations = {
        "Jupiter": "~12 months in this sign",
        "Saturn":  "~2.5 years in this sign",
        "Rahu":    "~18 months in this sign",
        "Ketu":    "~18 months in this sign (always opposite Rahu)",
        "Mercury": "~3 weeks (or 3 months if retrograde)",
        "Venus":   "~4 weeks (or 4 months if retrograde)",
        "Mars":    "~6 weeks (or 6 months if retrograde)",
        "Sun":     "~1 month in this sign",
        "Moon":    "~2.5 days in this sign",
    }
    return durations.get(planet, "varies")


def _get_urgency(planet: str, house: int, retrograde: bool) -> str:
    if retrograde:
        return "high"
    if planet in ["Saturn","Rahu"] and house in [1,4,7,8,10,12]:
        return "high"
    if planet == "Jupiter" and house in [1,5,9,10,11]:
        return "high"
    if planet in ["Saturn","Rahu"] and house in [2,3,5,6,9,11]:
        return "medium"
    if planet == "Jupiter":
        return "medium"
    return "low"
