# constants.py

# Planets (in standard order)
PLANETS = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu', 'Ketu']

# Planet to index mapping
PLANET_INDICES = {p: i for i, p in enumerate(PLANETS)}

# Sign names (0 = Aries, 11 = Pisces)
SIGNS = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
         'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']

# Sign rulers (traditional)
SIGN_LORDS = [
    'Mars',      # Aries
    'Venus',     # Taurus
    'Mercury',   # Gemini
    'Moon',      # Cancer
    'Sun',       # Leo
    'Mercury',   # Virgo
    'Venus',     # Libra
    'Mars',      # Scorpio (dual with Ketu)
    'Jupiter',   # Sagittarius
    'Saturn',    # Capricorn
    'Saturn',    # Aquarius (dual with Rahu)
    'Jupiter'    # Pisces
]

# Nakshatras (27)
NAKSHATRAS = [
    'Ashvini', 'Bharani', 'Krittika', 'Rohini', 'Mrigashira', 'Ardra',
    'Punarvasu', 'Pushya', 'Ashlesha', 'Magha', 'Purva Phalguni', 'Uttara Phalguni',
    'Hasta', 'Chitra', 'Swati', 'Vishakha', 'Anuradha', 'Jyeshtha',
    'Mula', 'Purva Ashadha', 'Uttara Ashadha', 'Shravana', 'Dhanishta', 'Shatabhisha',
    'Purva Bhadrapada', 'Uttara Bhadrapada', 'Revati'
]

# Nakshatra lords (in order)
NAKSHATRA_LORDS = [
    'Ketu', 'Venus', 'Sun', 'Moon', 'Mars', 'Rahu',
    'Jupiter', 'Saturn', 'Mercury', 'Ketu', 'Venus', 'Sun',
    'Moon', 'Mars', 'Rahu', 'Jupiter', 'Saturn', 'Mercury',
    'Ketu', 'Venus', 'Sun', 'Moon', 'Mars', 'Rahu',
    'Jupiter', 'Saturn', 'Mercury'
]

# Vimsottari dasha sequence (mahadasha lords)
VIMSOTTARI_SEQUENCE = ['Ketu', 'Venus', 'Sun', 'Moon', 'Mars', 'Rahu', 'Jupiter', 'Saturn', 'Mercury']

# Vimsottari dasha years
VIMSOTTARI_YEARS = {
    'Ketu': 7,
    'Venus': 20,
    'Sun': 6,
    'Moon': 10,
    'Mars': 7,
    'Rahu': 18,
    'Jupiter': 16,
    'Saturn': 19,
    'Mercury': 17
}

# Ashtottari dasha sequence and years (different from Vimsottari)
ASHTOTTARI_SEQUENCE = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu']
ASHTOTTARI_YEARS = {
    'Sun': 6,
    'Moon': 15,
    'Mars': 8,
    'Mercury': 17,
    'Jupiter': 19,
    'Venus': 21,
    'Saturn': 24,
    'Rahu': 12
}

# Yogini dasha (optional, can be added later)
YOGINI_SEQUENCE = ['Mangala', 'Pingala', 'Dhanya', 'Bhramari', 'Bhadrika', 'Ulka', 'Siddha', 'Sankata']
YOGINI_YEARS = [1, 2, 3, 4, 5, 6, 7, 8]

# Sign classifications for Jaimini
FIXED_SIGNS = [1, 4, 7, 9, 10]      # Taurus, Leo, Scorpio, Capricorn, Aquarius
MOVABLE_SIGNS = [0, 3, 6]           # Aries, Cancer, Libra
DUAL_SIGNS = [2, 5, 8, 11]          # Gemini, Virgo, Sagittarius, Pisces

# Karaka significations (for Jaimini)
KARAKA_NAMES = {
    1: 'Atmakaraka',
    2: 'Amatyakaraka',
    3: 'Bhratrikaraka',
    4: 'Matrikaraka',
    5: 'Putrakaraka',
    6: 'Gnatikaraka',
    7: 'Darakaraka'
}

# Ayanamsa options
AYANAMSA_MODES = {
    'Lahiri': 1,
    'Raman': 3,
    'Krishnamurti': 5,
    'Yukteshwar': 7
}
