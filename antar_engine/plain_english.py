"""
antar_engine/plain_english.py

Takes a raw astrological prediction and produces:
1. Plain English summary — zero jargon, pure life advice
2. One-line domain signal — for dashboard display
3. Action item — the ONE thing to do
"""

DOMAIN_KEYWORDS = {
    "career":           ["career","job","work","profession","business","promotion","authority","leadership","status","employment","occupation"],
    "wealth":           ["wealth","money","income","financial","gains","investment","property","assets","savings","earnings","revenue"],
    "relationships":    ["marriage","partner","relationship","spouse","family","children","divorce","separation","wedding","dating","commitment"],
    "love":             ["love","romance","attraction","passion","intimacy","dating","affair","crush","soulmate","compatibility"],
    "health":           ["health","body","energy","vitality","illness","healing","stress","disease","recovery","fitness","mental health"],
    "spirituality":     ["spiritual","purpose","meaning","soul","dharma","direction","wisdom","meditation","religion","faith"],
    "luck":             ["luck","speculation","gambling","lottery","windfall","sudden gains","unexpected","fortune","risk","chance","bet"],
    "travel":           ["travel","journey","trip","vacation","relocation","move","migration","abroad","overseas","foreign travel"],
    "foreign":          ["foreign","abroad","overseas","immigration","settlement","visa","emigration","international","foreign country"],
    "legal":            ["legal","lawsuit","court","litigation","divorce","taxes","tax","dispute","contract","lawyer","attorney","settlement","judgment"],
    "job_change":       ["job change","new job","resignation","fired","layoff","switch career","new role","promotion","transfer","career change"],
    "business":         ["business","startup","venture","company","enterprise","partnership","deal","client","revenue","profit","loss","scale"],
    "loans":            ["loan","borrow","debt","mortgage","credit","funding","finance","bank","lender","emi","repayment","liability"],
    "funding":          ["funding","investment","investor","startup","venture capital","seed","series","raise","capital","pitch"],
    "property":         ["property","real estate","house","land","plot","apartment","buy home","sell home","construction","renovation"],
    "education":        ["education","study","exam","degree","college","university","course","learning","scholarship","admission"],
    "children":         ["children","child","baby","pregnancy","fertility","adoption","son","daughter","parenting"],
    "mother":           ["mother","mom","maternal","parent","family home","domestic"],
    "father":           ["father","dad","paternal","authority figure","mentor","boss"],
}


def detect_domain(text: str) -> str:
    """Returns primary domain."""
    text_lower = text.lower()
    scores = {d: sum(1 for k in kws if k in text_lower) for d, kws in DOMAIN_KEYWORDS.items()}
    return max(scores, key=scores.get) if any(scores.values()) else "general"


def detect_all_domains(text: str, min_score: int = 1) -> list:
    """Returns all domains that match — a prediction can cover multiple areas."""
    text_lower = text.lower()
    scores = {d: sum(1 for k in kws if k in text_lower) for d, kws in DOMAIN_KEYWORDS.items()}
    matched = [d for d, s in scores.items() if s >= min_score]
    return matched if matched else ["general"]


def build_plain_english_prompt(prediction_text: str, question: str, concern: str, first_name: str = "") -> str:
    name = first_name or "the person"
    return f"""You are a life coach summarizing an astrological reading for {name}.

ORIGINAL PREDICTION:
{prediction_text}

RULES:
1. Write in plain English — NO astrological terms whatsoever
2. No planet names, no house numbers, no Sanskrit terms
3. Speak directly to the person — use "you" not "the person"
4. Focus on practical life implications only
5. Maximum 3 sentences for the summary
6. End with ONE specific action to take this week

OUTPUT FORMAT (exactly):
SUMMARY: [2-3 sentences of plain life advice]
ACTION: [One specific thing to do this week]
SIGNAL: [One sentence — the single most important thing happening for them right now]
"""
