# antar_engine/remedies.py
"""
Remedies and chakra balancing module based on karakas and user queries.
Date: 2026-03-10
"""

# Planet to life area mapping
PLANET_LIFE_AREAS = {
    "Sun": ["career", "confidence", "health", "vitality", "leadership"],
    "Moon": ["emotions", "mind", "peace", "mother", "intuition"],
    "Mars": ["courage", "energy", "conflict", "protection", "ambition"],
    "Mercury": ["communication", "business", "intellect", "education"],
    "Jupiter": ["wealth", "wisdom", "expansion", "children", "spirituality"],
    "Venus": ["love", "relationship", "marriage", "beauty", "luxury"],
    "Saturn": ["career", "longevity", "discipline", "karma", "delays"],
    "Rahu": ["unconventional", "foreign", "obsession", "sudden events"],
    "Ketu": ["detachment", "heartbreak", "spiritual", "loss"]
}

# Planet to chakra mapping
PLANET_CHAKRA = {
    "Sun": 3,  # Solar Plexus
    "Moon": 4,  # Heart
    "Mars": 1,  # Root
    "Mercury": 5, # Throat
    "Jupiter": 6, # Third Eye
    "Venus": 2,  # Sacral
    "Venus": 4,  # also Heart
    "Saturn": 1, # Root
    "Saturn": 7, # also Crown
    "Rahu": "varies",
    "Ketu": 7    # Crown
}

CHAKRA_INFO = {
    1: {"name": "Root (Muladhara)", "color": "Red", "element": "Earth", "beej": "Lam", "location": "Base of spine"},
    2: {"name": "Sacral (Svadhisthana)", "color": "Orange", "element": "Water", "beej": "Vam", "location": "Lower abdomen"},
    3: {"name": "Solar Plexus (Manipura)", "color": "Yellow", "element": "Fire", "beej": "Ram", "location": "Navel"},
    4: {"name": "Heart (Anahata)", "color": "Green", "element": "Air", "beej": "Yam", "location": "Chest"},
    5: {"name": "Throat (Vishuddha)", "color": "Blue", "element": "Ether", "beej": "Ham", "location": "Throat"},
    6: {"name": "Third Eye (Ajna)", "color": "Indigo", "element": "Light", "beej": "Om", "location": "Forehead"},
    7: {"name": "Crown (Sahasrara)", "color": "Violet", "element": "Consciousness", "beej": "Aum", "location": "Top of head"},
}

# Mantras by planet (text only - for audio, we'll produce our own recordings)
PLANET_MANTRAS = {
    "Sun": {
        "simple": "Om Suryaya Namaha",
        "beej": "Om Hram Hreem Hraum Sah Suryaya Namaha",
        "gayatri": "Om Bhaskaraya Vidmahe Mahadyutikaraya Dhimahi Tanno Suryah Prachodayat",
        "recommended_day": "Sunday",
        "count": 108,
        "purpose": "Vitality, confidence, leadership, health"
    },
    "Moon": {
        "simple": "Om Somaya Namaha",
        "beej": "Om Shram Shreem Shraum Sah Chandraya Namaha",
        "recommended_day": "Monday",
        "count": 108,
        "purpose": "Emotional balance, peace of mind, intuition"
    },
    "Mars": {
        "simple": "Om Mangalaya Namaha",
        "beej": "Om Kram Kreem Kraum Sah Bhaumaya Namaha",
        "recommended_day": "Tuesday",
        "count": 108,
        "purpose": "Courage, energy, protection from conflicts"
    },
    "Mercury": {
        "simple": "Om Budhaya Namaha",
        "beej": "Om Bram Breem Braum Sah Budhaya Namaha",
        "recommended_day": "Wednesday",
        "count": 108,
        "purpose": "Communication, business success, intellect"
    },
    "Jupiter": {
        "simple": "Om Gurave Namaha",
        "beej": "Om Gram Greem Graum Sah Gurave Namaha",
        "gayatri": "Om Gram Greem Graum Sah Gurave Namaha",
        "recommended_day": "Thursday",
        "count": 108,
        "purpose": "Wealth, wisdom, expansion, children"
    },
    "Venus": {
        "simple": "Om Shukraya Namaha",
        "beej": "Om Draam Dreem Draum Sah Shukraya Namaha",
        "recommended_day": "Friday",
        "count": 108,
        "purpose": "Love, relationships, beauty, luxury"
    },
    "Saturn": {
        "simple": "Om Shanaye Namaha",
        "beej": "Om Pram Preem Praum Sah Shanaye Namaha",
        "recommended_day": "Saturday",
        "count": 108,
        "purpose": "Discipline, career, longevity, karmic lessons"
    },
    "Rahu": {
        "simple": "Om Rahave Namaha",
        "beej": "Om Bhram Bhreem Bhraum Sah Rahave Namaha",
        "recommended_day": "No specific day",
        "count": 108,
        "purpose": "Removing obstacles, unconventional success"
    },
    "Ketu": {
        "simple": "Om Ketave Namaha",
        "beej": "Om Shram Shreem Shraum Sah Ketave Namaha",
        "recommended_day": "No specific day",
        "count": 108,
        "purpose": "Spiritual growth, healing from loss, detachment"
    }
}

def get_remedies_for_question(question: str, chart_data: dict, dashas: dict, karakas: list = None):
    """
    Analyze user question and return relevant remedies.
    """
    # Simplified keyword mapping
    question_lower = question.lower()
    relevant_planets = set()
    
    # Map question keywords to planets
    if any(word in question_lower for word in ["love", "relationship", "marriage", "partner", "girlfriend", "boyfriend"]):
        relevant_planets.add("Venus")
        relevant_planets.add("Moon")
        if "breakup" in question_lower or "heartbreak" in question_lower:
            relevant_planets.add("Ketu")
    
    if any(word in question_lower for word in ["money", "wealth", "rich", "loan", "finance", "business", "profit"]):
        relevant_planets.add("Jupiter")
        relevant_planets.add("Mercury")
        relevant_planets.add("Venus")
        if "loss" in question_lower:
            relevant_planets.add("Ketu")
            relevant_planets.add("Saturn")
    
    if any(word in question_lower for word in ["career", "job", "promotion", "work", "profession"]):
        relevant_planets.add("Sun")
        relevant_planets.add("Saturn")
        relevant_planets.add("Mercury")
    
    if any(word in question_lower for word in ["health", "sick", "disease", "pain", "energy"]):
        relevant_planets.add("Sun")
        relevant_planets.add("Moon")
        relevant_planets.add("Mars")
    
    if any(word in question_lower for word in ["spiritual", "meditation", "peace", "enlightenment"]):
        relevant_planets.add("Jupiter")
        relevant_planets.add("Ketu")
        relevant_planets.add("Sun")
    
    # If no keywords matched, use karakas
    if not relevant_planets and karakas:
        # Use the most relevant karaka based on question (simplified)
        relevant_planets.add(karakas[0]['planet'])  # Atmakaraka
    
    # Build remedies list
    remedies = []
    for planet in relevant_planets:
        if planet in PLANET_MANTRAS:
            mantra = PLANET_MANTRAS[planet]
            chakra_idx = PLANET_CHAKRA.get(planet, 4)  # default to heart
            if isinstance(chakra_idx, int):
                chakra = CHAKRA_INFO[chakra_idx]
            else:
                chakra = CHAKRA_INFO[4]  # default
            
            remedies.append({
                "planet": planet,
                "mantra": mantra["simple"],
                "beej_mantra": mantra["beej"],
                "recommended_day": mantra["recommended_day"],
                "count": mantra["count"],
                "purpose": mantra["purpose"],
                "chakra": chakra["name"],
                "chakra_color": chakra["color"],
                "chakra_beej": chakra["beej"],
                "chakra_location": chakra["location"],
                "chakra_element": chakra["element"],
                "chakra_meditation": f"Visualize {chakra['color']} light at your {chakra['location']}"
            })
    
    return remedies
