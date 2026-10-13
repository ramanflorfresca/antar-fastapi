"""
Rule registry + deterministic astrologer.

A rule is a statement from a book of the form "if THIS is in the chart, THEN this follows".
`applies` checks the natal condition; a rule whose condition is not met says nothing. Nothing in
here scores the books against events.

Families registered:
  KAR.*   Rao, karakamsha readings (fame, spiritual tilt)
  LK.*    Lal Kitab planet-in-house verdicts (fixed frame, Aries = house 1; classified only where the
          books do not contradict each other) with the matching Lal Kitab remedies
  YOGA.*  Raman's yogas as detected by yogas.py, in the engine's plain language
Timing questions ("when") come from the dasha engines (Jaimini Chara, Mandook, Parashari, D-10) through the
forecast and the reading composer; the registry supplies the "what / which / why / how / where" answers and
the remedies.

Policies (see answer()):
  - silence is an answer: if no rule applies to the subject, the astrologer says so.
  - conflicts are not voted: a placement the books contradict is left unclassified (mixed), never forced.
  - every statement carries its evidence (the chart fact) and its source book; precision is flagged
    ("specific" vs "tone": the book only calls the placement good or bad).
  - death, disease and longevity rules are never registered; investment questions get a caution, not a call.
"""
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Callable, Dict, Iterable, List, Optional

from antar_engine.jaimini_engine import SIGN_NAMES
from antar_engine import jaimini_rao_events as jre
from antar_engine.lk_annual_forecast import GOOD_PLACE, BAD_PLACE
from antar_engine.lal_kitab import get_remedies_for_planet
from antar_engine.lal_kitab_events import lal_kitab_profile, AGE_TRIGGERS, MATURITY

# ----------------------------------------------------------------------------- subjects
SUBJECTS: Dict[str, dict] = {
    "money":        {"houses": {2, 11}, "area": "money",        "label": {"en": "money", "es": "dinero"}},
    "funding":      {"houses": {8, 2, 11}, "area": "money",     "label": {"en": "funding", "es": "financiamiento"}},
    "career":       {"houses": {10, 11}, "area": "career",      "label": {"en": "career", "es": "carrera"}},
    "job":          {"houses": {6, 10}, "area": "career",       "label": {"en": "a job", "es": "un empleo"}},
    "business":     {"houses": {7, 10, 11}, "area": "career",   "label": {"en": "business", "es": "negocio"}},
    "love":         {"houses": {5, 7}, "area": "relationship",  "label": {"en": "love", "es": "amor"}},
    "marriage":     {"houses": {7, 2}, "area": "relationship",  "label": {"en": "marriage", "es": "matrimonio"}},
    "children":     {"houses": {5}, "area": None,               "label": {"en": "children", "es": "hijos"}},
    "education":    {"houses": {4, 5}, "area": "learning",      "label": {"en": "study", "es": "estudios"}},
    "property":     {"houses": {4}, "area": None,               "label": {"en": "property", "es": "propiedad"}},
    "foreign":      {"houses": {12, 9}, "area": None,           "label": {"en": "life abroad", "es": "vida en el extranjero"}},
    "spirituality": {"houses": {9, 12}, "area": None,           "label": {"en": "your spiritual path", "es": "tu camino espiritual"}},
    "speculation":  {"houses": {5, 8}, "area": None,            "label": {"en": "speculation", "es": "especulación"}},
    "health":       {"houses": {6, 1}, "area": None,            "label": {"en": "health", "es": "salud"}},
}
# a question about a child subject also draws on its parent subject's rules
PARENTS = {"funding": ["money"], "job": ["career"], "business": ["career", "money"], "marriage": ["love"],
           "love": ["marriage"]}
HOUSE_SUBJECTS = {2: ["money"], 11: ["money", "career"], 8: ["funding", "speculation", "money"], 10: ["career"],
                  6: ["job", "health"], 7: ["marriage", "love", "business"], 5: ["love", "children", "education", "speculation"],
                  4: ["property", "education"], 9: ["foreign", "spirituality"], 12: ["foreign", "spirituality", "money"],
                  1: ["health"], 3: ["career"]}

ALIASES = {
    "funding": ["funding", "investor", "raise capital", "raising", "seed round", "venture capital", "financiamiento",
                "inversionista", "inversor", "financiamento", "investimento"],
    "money": ["money", "income", "cash", "~earn", "salary", "wealth", "rich", "dinero", "ingreso", "ingresos", "plata", "riqueza",
              "dinheiro", "renda", "paisa", "kamai", "paise"],
    "job": ["job", "employment", "hired", "employer", "empleo", "trabajo", "emprego", "naukri"],
    "career": ["career", "promotion", "profession", "carrera", "ascenso", "profesión", "carreira", "promoção"],
    "business": ["business", "startup", "start-up", "company", "negocio", "empresa", "emprendimiento", "vyapar"],
    "marriage": ["marriage", "~marry", "~married", "wedding", "spouse", "husband", "wife", "matrimonio", "~casar",
                 "esposo", "esposa", "casamento", "shaadi", "vivah"],
    "love": ["love", "romance", "relationship", "girlfriend", "boyfriend", "partner", "amor", "pareja", "novio",
             "novia", "namoro", "pyaar", "pyar"],
    "children": ["child", "children", "kids", "baby", "~pregnan", "hijo", "hijos", "bebé", "bebe", "niños", "filho",
                 "bachcha", "santan"],
    "education": ["study", "studies", "degree", "exam", "college", "university", "~learn", "~estudi",
                  "examen", "universidad", "curso", "padhai"],
    "property": ["house", "home", "property", "real estate", "casa", "propiedad", "inmueble", "imóvel", "ghar"],
    "foreign": ["abroad", "foreign", "~relocat", "visa", "~migrat", "~emigrat", "extranjero", "mudarme", "exterior",
                "videsh"],
    "spirituality": ["spiritual", "guru", "meditation", "dharma", "espiritual", "meditación", "adhyatm"],
    "speculation": ["stock", "stocks", "trading", "~gambl", "lottery", "bet", "crypto", "casino", "bolsa", "apuesta",
                    "lotería", "loteria", "satta"],
    "health": ["health", "illness", "salud", "saúde", "swasthya"],
}
SUBJECT_PRIORITY = ["funding", "speculation", "marriage", "love", "children", "job", "business", "career", "education",
                    "property", "foreign", "spirituality", "money", "health"]
QWORDS = {
    "when": ["when", "cuándo", "cuando", "quando", "kab"],
    "how": ["how", "cómo", "como", "kaise"],
    "why": ["why", "por qué", "porque", "por que", "kyun", "kyon"],
    "where": ["where", "dónde", "donde", "onde", "kahan"],
    "which": ["which", "cuál", "cual", "cuáles", "qual", "kaun"],
    "what": ["what", "qué", "que", "o que", "kya"],
}


def _alias_hit(alias: str, q: str) -> bool:
    """Whole-word match; an alias starting with '~' matches as a word prefix (casar -> casarme)."""
    prefix = alias.startswith("~")
    a = re.escape(alias.lstrip("~").strip())
    return re.search(r"(?<!\w)" + a + ("" if prefix else r"(?!\w)"), q) is not None


def parse_question(question: str):
    """(subject or None, question word) from free text, EN/ES/PT/Hinglish keywords."""
    q = " " + (question or "").lower() + " "
    scores = {}
    for subj, words in ALIASES.items():
        scores[subj] = sum(1 for w in words if _alias_hit(w, q))
    best = [s for s in SUBJECT_PRIORITY if scores.get(s)]
    subject = max(best, key=lambda s: (scores[s], -SUBJECT_PRIORITY.index(s))) if best else None
    qword = "what"
    for k in ("when", "why", "how", "where", "which", "what"):
        if any(re.search(r"(?<!\w)" + re.escape(w) + r"(?!\w)", q) for w in QWORDS[k]):
            qword = k
            break
    return subject, qword


# ----------------------------------------------------------------------------- plain text pieces
PLANET_PHRASE = {
    "en": {"Sun": "your confidence and authority", "Moon": "your mind and emotional steadiness",
           "Mars": "your drive", "Mercury": "your intellect and dealmaking", "Jupiter": "your wisdom and luck",
           "Venus": "your comfort and relationships", "Saturn": "your discipline and endurance",
           "Rahu": "your ambition and appetite for the unconventional", "Ketu": "your detachment"},
    "es": {"Sun": "tu confianza y autoridad", "Moon": "tu mente y estabilidad emocional", "Mars": "tu impulso",
           "Mercury": "tu intelecto y tu manejo de acuerdos", "Jupiter": "tu sabiduría y suerte",
           "Venus": "tu comodidad y tus relaciones", "Saturn": "tu disciplina y resistencia",
           "Rahu": "tu ambición y apetito por lo no convencional", "Ketu": "tu desapego"},
}
HOUSE_THEME = {
    "en": {1: "your drive and identity", 2: "savings and family", 3: "effort and courage", 4: "home and peace of mind",
           5: "children and creativity", 6: "health and daily work", 7: "partnerships", 8: "hidden and sudden matters",
           9: "luck and guidance", 10: "career and standing", 11: "income and gains", 12: "expenses and foreign matters"},
    "es": {1: "tu impulso e identidad", 2: "ahorros y familia", 3: "esfuerzo y valentía", 4: "hogar y tranquilidad",
           5: "hijos y creatividad", 6: "salud y trabajo diario", 7: "relaciones y sociedades",
           8: "asuntos ocultos y repentinos", 9: "suerte y guía", 10: "carrera y posición", 11: "ingresos y ganancias",
           12: "gastos y asuntos en el extranjero"},
}
T = {
    "en": {"lk_good": "{p} is well placed for {t}.", "lk_bad": "{p} is under strain around {t}.",
           "lk_why": "It sits in the part of the chart that governs {t}, and the traditional reading calls that placement {v}.",
           "v_good": "supportive", "v_bad": "difficult",
           "kar_fame": "Your chart carries a recognition tendency: the planets of intellect and discipline touch the sign of your life purpose.",
           "kar_fame_why": "Saturn or Mercury aspects or sits in the sign of your life purpose or its career position.",
           "kar_spirit": "Your chart carries a spiritual or foreign tilt, a supportive planet sits in the sign of release.",
           "kar_spirit_why": "A benefic occupies the 12th position from the sign of your life purpose.",
           "yoga_why": "This combination is present in your birth chart.",
           "none": "The chart gives no rule on {s}, so there is nothing to predict here.",
           "head_what": "What your chart says about {s}", "head_why": "Why your chart reads this way about {s}",
           "head_when": "When {s} is most active", "head_how": "How to work with {s}",
           "head_where": "Where {s} points", "head_which": "Which part of your chart leads on {s}",
           "none_when": "No window for {s} stands out in the next 24 months.",
           "windows": "Windows", "remedies": "Practical remedies", "strengths": "Working for you", "lean_on": "Lean on",
           "challenges": "To handle with care", "tone_only": "This reading only says whether it helps or strains; the books give no more detail.",
           "spec": "Treat speculation with caution: size any bet to what you can afford to lose. This is a caution, not a call on any trade.",
           "step": "First step: {a}", "wake": "A dormant area wakes around age {age}.", "lead": "The strongest lead is {x}."},
    "es": {"lk_good": "{p} está bien ubicada para {t}.", "lk_bad": "{p} está bajo tensión en torno a {t}.",
           "lk_why": "Está en la parte de la carta que rige {t}, y la lectura tradicional considera esa posición {v}.",
           "v_good": "favorable", "v_bad": "difícil",
           "kar_fame": "Tu carta tiene tendencia al reconocimiento: los planetas del intelecto y la disciplina tocan el signo de tu propósito de vida.",
           "kar_fame_why": "Saturno o Mercurio aspecta u ocupa el signo de tu propósito de vida o su posición de carrera.",
           "kar_spirit": "Tu carta tiene una inclinación espiritual o hacia lo extranjero: un planeta favorable está en el signo de la liberación.",
           "kar_spirit_why": "Un planeta benéfico ocupa la posición 12 desde el signo de tu propósito de vida.",
           "yoga_why": "Esta combinación está presente en tu carta natal.",
           "none": "La carta no da ninguna regla sobre {s}, así que no hay nada que predecir aquí.",
           "head_what": "Lo que dice tu carta sobre {s}", "head_why": "Por qué tu carta se lee así sobre {s}",
           "head_when": "Cuándo {s} está más activo", "head_how": "Cómo trabajar con {s}",
           "head_where": "Hacia dónde apunta {s}", "head_which": "Qué parte de tu carta lidera en {s}",
           "none_when": "Ninguna ventana para {s} destaca en los próximos 24 meses.",
           "windows": "Ventanas", "remedies": "Remedios prácticos", "strengths": "A tu favor", "lean_on": "Apóyate en",
           "challenges": "Para manejar con cuidado", "tone_only": "Esta lectura solo dice si ayuda o presiona; los libros no dan más detalle.",
           "spec": "Trata la especulación con cautela: limita cualquier apuesta a lo que puedas perder. Es una precaución, no una indicación sobre ninguna operación.",
           "step": "Primer paso: {a}", "wake": "Un área latente despierta hacia los {age} años.", "lead": "La pista más fuerte es {x}."},
}


# ----------------------------------------------------------------------------- context
class Ctx:
    """Everything a rule needs about one chart, computed once."""

    def __init__(self, chart_data: dict, birth_date, vim_rows=None, today: Optional[date] = None,
                 birth_time_accuracy: Optional[str] = None):
        from antar_engine.event_forecast import _planets, _lagna
        self.chart_data = chart_data
        self.today = today or date.today()
        self.birth_date = birth_date
        self.vim_rows = vim_rows or []
        self.birth_time_accuracy = birth_time_accuracy
        self.planets = _planets(chart_data)
        self.lagna, self.lagna_lon = _lagna(chart_data)
        self.ok = self.lagna is not None and len(self.planets) >= 9
        self.age = None
        if self.ok and birth_date:
            self.age = (self.today - date.fromisoformat(str(birth_date)[:10])).days // 365
        self.j = jre.Chart(self.lagna, self.lagna_lon, self.planets) if self.ok else None
        self._forecast = None
        self._reading = None

    def lk_house(self, planet: str) -> int:
        return self.planets[planet].sign + 1          # fixed frame: Aries = house 1

    @property
    def forecast(self):
        if self._forecast is None:
            from antar_engine.event_forecast import build_forecast
            self._forecast = build_forecast(self.chart_data, self.birth_date, self.vim_rows, today=self.today,
                                            birth_time_accuracy=self.birth_time_accuracy)
        return self._forecast

    def reading(self, lang):
        from antar_engine.reading_composer import compose
        if self._reading is None:
            self._reading = {}
        if lang not in self._reading:
            self._reading[lang] = compose(self.forecast, lang, self.today)
        return self._reading[lang]


@dataclass
class Evidence:
    rule_id: str
    book: str
    subjects: List[str]
    tone: str                      # good | bad | info
    precision: str                 # specific | tone
    plain: Dict[str, str]
    why: Dict[str, str]
    planet: Optional[str] = None
    house: Optional[int] = None


@dataclass
class Rule:
    id: str
    book: str
    applies: Callable[[Ctx], Iterable[Evidence]]


# ----------------------------------------------------------------------------- rule families
def _kar_rules(ctx: Ctx):
    j, P = ctx.j, ctx.planets
    kl = j.kl
    tenth = (kl + 9) % 12
    T_ = jre._touches
    out = []
    if any(T_(P[x].sign, tenth) or T_(P[x].sign, kl) for x in ("Saturn", "Mercury")):
        out.append(Evidence("KAR.fame_sat_mer", "K.N. Rao, Karakamsha", ["career", "business"], "good", "specific",
                            {l: T[l]["kar_fame"] for l in T}, {l: T[l]["kar_fame_why"] for l in T}))
    if T_(P["Moon"].sign, tenth) and T_(P["Venus"].sign, tenth):
        out.append(Evidence("KAR.fame_moon_venus", "K.N. Rao, Karakamsha", ["career", "business"], "good", "specific",
                            {l: T[l]["kar_fame"] for l in T}, {l: T[l]["kar_fame_why"] for l in T}))
    if T_(j.k_sign["AmK"], tenth):
        out.append(Evidence("KAR.fame_amk", "K.N. Rao, Karakamsha", ["career", "business"], "good", "specific",
                            {l: T[l]["kar_fame"] for l in T}, {l: T[l]["kar_fame_why"] for l in T}))
    if any(P[b].sign == (kl + 11) % 12 for b in ("Jupiter", "Venus", "Mercury")):
        out.append(Evidence("KAR.spiritual_12th_from_KL", "K.N. Rao, Karakamsha", ["spirituality", "foreign"], "info",
                            "specific", {l: T[l]["kar_spirit"] for l in T}, {l: T[l]["kar_spirit_why"] for l in T}))
    return out


def _lk_rules(ctx: Ctx):
    out = []
    for planet in ctx.planets:
        if planet not in GOOD_PLACE:
            continue
        h = ctx.lk_house(planet)
        if h in GOOD_PLACE[planet]:
            tone = "good"
        elif h in BAD_PLACE[planet]:
            tone = "bad"
        else:
            continue                                   # contradicted or unclassified: says nothing
        plain, why = {}, {}
        for l in T:
            p = PLANET_PHRASE[l][planet]
            p = p[0].upper() + p[1:]
            t = HOUSE_THEME[l][h]
            plain[l] = T[l]["lk_good" if tone == "good" else "lk_bad"].format(p=p, t=t)
            why[l] = T[l]["lk_why"].format(t=t, v=T[l]["v_good" if tone == "good" else "v_bad"])
        out.append(Evidence(f"LK.{planet}_{h}.{tone}", "Lal Kitab", HOUSE_SUBJECTS.get(h, []), tone, "tone",
                            plain, why, planet=planet, house=h))
    return out


_YOGA_SUBJECTS = {"wealth": ["money", "funding"], "raj_yoga": ["career", "job", "business"],
                  "mahapurusha": ["career", "business"], "intelligence": ["education", "career"],
                  "reputation": ["career"], "karmic": [], "challenge": [], "general": []}


def _yoga_rules(ctx: Ctx):
    from antar_engine.yogas import detect_all_yogas, plain_yoga
    cd = ctx.chart_data
    try:
        found = detect_all_yogas(cd.get("planets") or {}, (cd.get("lagna") or {}).get("sign"))
    except Exception:
        return []
    out, seen = [], set()
    for y in found:
        stem = y["name"].split("(")[0].strip()
        if stem in seen:
            continue
        seen.add(stem)
        pl = {l: plain_yoga(y["name"], l) for l in ("en", "es")}
        tone = "good" if pl["en"]["kind"] == "strength" else "bad"
        plain = {l: pl[l]["title"] + ((": " + pl["en"]["effect_en"]) if l == "en" and pl["en"]["effect_en"] else "")
                 for l in pl}
        out.append(Evidence(f"YOGA.{stem.replace(' ', '_')}", "B.V. Raman, combinations",
                            _YOGA_SUBJECTS.get(y.get("category", "general"), []), tone, "specific",
                            plain, {l: T[l]["yoga_why"] for l in T}))
    return out


REGISTRY: List[Rule] = [
    Rule("KAR", "K.N. Rao, Karakamsha", _kar_rules),
    Rule("LK.placements", "Lal Kitab", _lk_rules),
    Rule("YOGA", "B.V. Raman, combinations", _yoga_rules),
]


def applicable(ctx: Ctx) -> List[Evidence]:
    """Every rule whose natal condition holds in this chart. A rule that does not apply is absent."""
    if not ctx.ok:
        return []
    out: List[Evidence] = []
    for r in REGISTRY:
        out.extend(r.applies(ctx))
    return out


def for_subject(evs: List[Evidence], subject: str) -> List[Evidence]:
    want = {subject, *PARENTS.get(subject, [])}
    return [e for e in evs if want & set(e.subjects)]


# ----------------------------------------------------------------------------- remedies
_PLANET_WORDS = ("sun ", "moon ", "mars", "mercury", "jupiter", "venus", "saturn ", "rahu", "ketu")


def _plain_ok(text: str) -> bool:
    low = text.lower()
    return not any(w in low for w in ("rahu", "ketu", "jupiter", "mars", "mercury", "venus"))


def remedies_for(evs: List[Evidence], limit: int = 3) -> List[dict]:
    """Lal Kitab remedies for the placements that strain this subject. Remedies that name a planet are skipped."""
    out = []
    for e in evs:
        if e.tone != "bad" or not e.planet:
            continue
        for r in get_remedies_for_planet(e.planet, e.house):
            if r.instructions and _plain_ok(r.instructions):
                out.append({"rule_id": e.rule_id, "do": r.instructions, "timing": r.timing, "duration": r.duration})
                break
        if len(out) >= limit:
            break
    return out


# ----------------------------------------------------------------------------- the astrologer
def _windows(ctx: Ctx, subject: str, lang: str):
    area = SUBJECTS[subject]["area"]
    if not area:
        return []
    rd = ctx.reading(lang)
    if not rd.get("available"):
        return []
    for a in rd["areas"]:
        if a["area"] == area:
            return a["windows"]
    return []


def answer(ctx: Ctx, subject: Optional[str], qword: str = "what", lang: str = "en") -> dict:
    lang = lang if lang in T else "en"
    tx = T[lang]
    if not ctx.ok:
        return {"available": False}
    if subject not in SUBJECTS:
        return {"available": True, "subject": subject, "qword": qword, "applicable": False, "lines": [],
                "rules_used": [], "windows": [], "remedies": [], "text": ""}
    label = SUBJECTS[subject]["label"][lang]
    evs = for_subject(applicable(ctx), subject)
    good = [e for e in evs if e.tone in ("good", "info")]
    bad = [e for e in evs if e.tone == "bad"]
    lines, used = [], []
    rem = remedies_for(bad)
    wins = _windows(ctx, subject, lang)
    wake = []
    if ctx.age is not None:
        prof = lal_kitab_profile({n: p.sign for n, p in ctx.planets.items()}, ctx.age, horizon=3)
        wake = [w for w in prof["wake_ups"]]

    def add(items, evidence=False):
        for e in items:
            lines.append(e.plain[lang] + ((" " + e.why[lang]) if evidence else ""))
            used.append(e.rule_id)

    head = tx["head_" + qword].format(s=label)
    if qword in ("what", "why"):
        ev_on = (qword == "why")
        blocks = [(tx["challenges"], bad), (tx["strengths"], good)] if ev_on else [(tx["strengths"], good), (tx["challenges"], bad)]
        for title, items in blocks:
            if items:
                lines.append(title + ":")
                add(items, evidence=ev_on)
        if any(e.precision == "tone" for e in evs):
            lines.append(tx["tone_only"])
        if rem:
            lines.append(tx["remedies"] + ":")
            for r in rem:
                lines.append(r["do"] + (f' ({r["timing"]}, {r["duration"]})' if r["timing"] or r["duration"] else ""))
    elif qword == "when":
        for w in wins:
            lines.append(f'{w["label"]} ({w["strength_label"]}): {w["headline"]}. {w["why"]}')
        for w in wake:
            lines.append(tx["wake"].format(age=w["age"]))
        if not wins and not wake:
            lines.append(tx["none_when"].format(s=label))
        used += [f"WINDOW.{subject}"] if wins else []
    elif qword == "how":
        for w in wins[:2]:
            lines.append(tx["step"].format(a=w["action"]))
        if good:
            lines.append(tx["lean_on"] + ":")
            add(good)
        if rem:
            lines.append(tx["remedies"] + ":")
            for r in rem:
                lines.append(r["do"] + (f' ({r["timing"]}, {r["duration"]})' if r["timing"] or r["duration"] else ""))
                used.append(r["rule_id"])
    elif qword == "where":
        foreign = [e for e in applicable(ctx) if {"foreign", "spirituality"} & set(e.subjects)] if subject in ("foreign", "spirituality") else evs
        add(foreign)
    elif qword == "which":
        if wins:
            best = sorted(wins, key=lambda w: ({"strong": 0, "good": 1, "possible": 2}[w["strength"]], w["start"]))[0]
            lines.append(tx["lead"].format(x=f'{best["label"]}: {best["headline"]}'))
            used.append(f"WINDOW.{subject}")
        lead = (good + bad)[:1]
        if lead:
            add(lead)
    if subject == "speculation":
        lines.append(tx["spec"])
    applicable_any = bool(evs or wins or wake or subject == "speculation")
    if not applicable_any:
        lines = [tx["none"].format(s=label)]
    return {"available": True, "subject": subject, "subject_label": label, "qword": qword, "language": lang,
            "headline": head, "lines": lines, "rules_used": sorted(set(used)), "windows": wins,
            "remedies": rem if qword in ("how", "what", "why") else [], "applicable": applicable_any,
            "text": head + "\n" + "\n".join(lines)}
