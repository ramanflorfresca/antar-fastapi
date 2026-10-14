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
from datetime import date, datetime
from typing import Callable, Dict, Iterable, List, Optional

from antar_engine.jaimini_engine import SIGN_NAMES
from antar_engine import jaimini_rao_events as jre
from antar_engine import rc_rules as rc
from antar_engine import combo_rules as cb
from antar_engine import lk_remedies as lkr
from antar_engine import vim_levels as vl
from antar_engine import book_rules as br
from antar_engine.transit_signs import transit_signs, transit_longitudes, transit_longitudes_tropical
from antar_engine.varshaphal_table import get_annual_house
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
    "remedies":     {"houses": set(), "area": None,             "label": {"en": "remedies", "es": "remedios"}},
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
    "remedies": ["remedy", "remedies", "cure", "upay", "upaya", "upaye", "remedio", "remedios", "solución", "solucion",
                 "~fix"],
}
SUBJECT_PRIORITY = ["remedies", "funding", "speculation", "marriage", "love", "children", "job", "business", "career", "education",
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
           "rc_why_planet": "{p} sits in the part of your chart that governs {t}, and the traditional text speaks to exactly that arrangement.",
           "rc_why_chart": "It follows from how your chart is arranged, which the traditional text addresses directly.",
           "combo_why": "The planets in your chart relate to each other in a combination the classical text describes.",
           "none": "The chart gives no rule on {s}, so there is nothing to predict here.",
           "head_remedies": "Remedies from the traditional text that fit your chart", "head_what": "What your chart says about {s}", "head_why": "Why your chart reads this way about {s}",
           "head_when": "When {s} is most active", "head_how": "How to work with {s}",
           "head_where": "Where {s} points", "head_which": "Which part of your chart leads on {s}",
           "none_when": "No window for {s} stands out in the next 24 months.",
           "windows": "Windows", "remedies": "Practical remedies", "strengths": "Working for you", "lean_on": "Lean on", "worth_knowing": "Worth knowing", "active_now": "Active right now", "for_days": "Keep it up for {d}.", "timing_note": "Timing: {d}.",
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
           "rc_why_planet": "{p} está en la parte de tu carta que rige {t}, y el texto tradicional habla exactamente de esa disposición.",
           "rc_why_chart": "Se deriva de cómo está dispuesta tu carta, algo que el texto tradicional aborda directamente.",
           "combo_why": "Los planetas de tu carta se relacionan entre sí en una combinación que describe el texto clásico.",
           "none": "La carta no da ninguna regla sobre {s}, así que no hay nada que predecir aquí.",
           "head_remedies": "Remedios del texto tradicional que corresponden a tu carta", "head_what": "Lo que dice tu carta sobre {s}", "head_why": "Por qué tu carta se lee así sobre {s}",
           "head_when": "Cuándo {s} está más activo", "head_how": "Cómo trabajar con {s}",
           "head_where": "Hacia dónde apunta {s}", "head_which": "Qué parte de tu carta lidera en {s}",
           "none_when": "Ninguna ventana para {s} destaca en los próximos 24 meses.",
           "windows": "Ventanas", "remedies": "Remedios prácticos", "strengths": "A tu favor", "lean_on": "Apóyate en", "worth_knowing": "Conviene saber", "active_now": "Activo ahora mismo", "for_days": "Mantenlo durante {d}.", "timing_note": "Momento: {d}.",
           "challenges": "Para manejar con cuidado", "tone_only": "Esta lectura solo dice si ayuda o presiona; los libros no dan más detalle.",
           "spec": "Trata la especulación con cautela: limita cualquier apuesta a lo que puedas perder. Es una precaución, no una indicación sobre ninguna operación.",
           "step": "Primer paso: {a}", "wake": "Un área latente despierta hacia los {age} años.", "lead": "La pista más fuerte es {x}."},
}


# ----------------------------------------------------------------------------- context
class Ctx:
    """Everything a rule needs about one chart, computed once."""

    def __init__(self, chart_data: dict, birth_date, vim_rows=None, today: Optional[date] = None,
                 birth_time_accuracy: Optional[str] = None, gender: Optional[str] = None):
        from antar_engine.event_forecast import _planets, _lagna
        self.chart_data = chart_data
        self.today = today or date.today()
        self.birth_date = birth_date
        self.vim_rows = vim_rows or []
        self.birth_time_accuracy = birth_time_accuracy
        g = (gender or "").lower()
        self.gender = g if g in ("male", "female") else None
        self.planets = _planets(chart_data)
        self.lagna, self.lagna_lon = _lagna(chart_data)
        self.ok = self.lagna is not None and len(self.planets) >= 9
        self.age = None
        if self.ok and birth_date:
            self.age = (self.today - date.fromisoformat(str(birth_date)[:10])).days // 365
        self.j = jre.Chart(self.lagna, self.lagna_lon, self.planets) if self.ok else None
        self._forecast = None
        self._reading = None
        self._vim = None

    @property
    def vim(self) -> List[dict]:
        """Parsed Vimshottari MD/AD rows. Computed from the Moon when none are stored, so pratyantara and sookshma
        are always available."""
        if self._vim is None:
            rows = vl.parse_rows(self.vim_rows)
            if not rows and self.ok and self.birth_date and "Moon" in self.planets:
                b = vl._dt(self.birth_date)
                if b:
                    rows = vl.rows_from_moon(self.planets["Moon"].degree, b.replace(hour=12))
            self._vim = rows
        return self._vim

    def periods_at(self, when: date) -> dict:
        """Running Vimshottari major, sub, pratyantara and sookshma lords on a date (internal names)."""
        return vl.running_lords(self.vim, datetime(when.year, when.month, when.day))

    def lk_house(self, planet: str) -> int:
        return self.planets[planet].sign + 1          # fixed frame: Aries = house 1

    def chart_state(self) -> dict:
        """State the book-rule evaluator reads: lagna, signs, gender, Jaimini karakas and points, age."""
        if not hasattr(self, "_chart_state"):
            self._chart_state = {"lagna": self.lagna, "signs": {p: pl.sign for p, pl in self.planets.items()},
                                 "gender": self.gender, "karakas": dict(self.j.k),
                                 "points": {"AL": self.j.al, "UL": self.j.ul, "A7": self.j.a7, "KL": self.j.kl},
                                 "age_year": (self.age + 1) if self.age is not None else None}
        return self._chart_state

    def timed_book_rules(self) -> List[dict]:
        """Timed book rules whose natal conditions hold in this chart (activation is checked per date)."""
        if not hasattr(self, "_timed_book"):
            st = self.chart_state()
            self._timed_book = [r for r in br.load_rules() if r.get("activation") and cb.applies(r, st)]
        return self._timed_book

    def rc_state(self) -> dict:
        """State the Roop Chand rules read: natal houses (fixed frame), this year's annual houses, gender, rising sign."""
        if not hasattr(self, "_rc_state"):
            annual = None
            if self.birth_date:
                b = date.fromisoformat(str(self.birth_date)[:10])
                age = self.today.year - b.year - ((self.today.month, self.today.day) < (b.month, b.day))
                annual = {p: get_annual_house(self.lk_house(p), age) for p in self.planets}
            self._rc_state = {"natal": {p: self.lk_house(p) for p in self.planets}, "annual": annual,
                              "gender": self.gender, "lagna_sign": SIGN_NAMES[self.lagna]}
        return self._rc_state

    @property
    def forecast(self):
        if self._forecast is None:
            from antar_engine.event_forecast import build_forecast
            self._forecast = build_forecast(self.chart_data, self.birth_date, self.vim_rows, today=self.today,
                                            birth_time_accuracy=self.birth_time_accuracy, gender=self.gender)
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
    remedy: Optional[dict] = None     # {lang: sentence}
    planets: tuple = ()            # planets the rule is about (a dasha of one of them runs the rule)
    signs: tuple = ()              # signs the rule is about (a Jaimini sub-period in one of them runs the rule)


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
                            {l: T[l]["kar_fame"] for l in T}, {l: T[l]["kar_fame_why"] for l in T},
                            planets=("Saturn", "Mercury"), signs=(kl, tenth)))
    if T_(P["Moon"].sign, tenth) and T_(P["Venus"].sign, tenth):
        out.append(Evidence("KAR.fame_moon_venus", "K.N. Rao, Karakamsha", ["career", "business"], "good", "specific",
                            {l: T[l]["kar_fame"] for l in T}, {l: T[l]["kar_fame_why"] for l in T},
                            planets=("Moon", "Venus"), signs=(kl, tenth)))
    if T_(j.k_sign["AmK"], tenth):
        out.append(Evidence("KAR.fame_amk", "K.N. Rao, Karakamsha", ["career", "business"], "good", "specific",
                            {l: T[l]["kar_fame"] for l in T}, {l: T[l]["kar_fame_why"] for l in T},
                            planets=(j.k["AmK"],), signs=(kl, tenth)))
    if any(P[b].sign == (kl + 11) % 12 for b in ("Jupiter", "Venus", "Mercury")):
        out.append(Evidence("KAR.spiritual_12th_from_KL", "K.N. Rao, Karakamsha", ["spirituality", "foreign"], "info",
                            "specific", {l: T[l]["kar_spirit"] for l in T}, {l: T[l]["kar_spirit_why"] for l in T},
                            planets=("Jupiter", "Venus", "Mercury"), signs=((kl + 11) % 12,)))
    return out


def _rc_family(ctx: Ctx):
    """Pt. Roop Chand's Lal Kitab rules (atomic rules, applied only where every condition holds)."""
    out = []
    state = ctx.rc_state()
    for r in rc.applying(state, kind="natal") + rc.applying(state, kind="annual"):
        ages = [a for a in (r.get("ages") or []) if isinstance(a, (int, float))]
        if ages and ctx.age is not None and max(ages) < ctx.age:
            continue                                        # every age the text names is already past: history, not guidance
        tone = r["tone"] if r["tone"] in ("good", "bad") else "info"
        p, h = r.get("planet"), (r.get("houses") or [None])[0]
        plain = {"en": r["effect"]}
        if r.get("effect_es"):
            plain["es"] = r["effect_es"]
        why = {}
        for l in T:
            if p and h:
                why[l] = T[l]["rc_why_planet"].format(p=PLANET_PHRASE[l][p], t=HOUSE_THEME[l][h])
            else:
                why[l] = T[l]["rc_why_chart"]
        rem = {l: v for l, v in (("en", r.get("remedy")), ("es", r.get("remedy_es"))) if v and _plain_ok(v)} or None
        out.append(Evidence(f"LK.{r['id']}", "Lal Kitab (Roop Chand)", rc.subjects_of(r), tone,
                            "specific" if r.get("clarity") == "clear" else "tone", plain, why,
                            planet=p, house=h, remedy=rem,
                            planets=(p,) if p else ()))
    return out


_YOGA_SUBJECTS = {"wealth": ["money", "funding"], "raj_yoga": ["career", "job", "business"],
                  "mahapurusha": ["career", "business"], "intelligence": ["education", "career"],
                  "reputation": ["career"], "karmic": [], "challenge": [], "general": []}


def _combo_family(ctx: Ctx):
    """B.V. Raman's combinations (Part I, entries 1-162), applied only where every condition holds."""
    state = ctx.chart_state()
    out = []
    for r in cb.applying(state):
        tone = r["tone"] if r["tone"] in ("good", "bad") else "info"
        plain = {"en": r["effect"]}
        if r.get("effect_es"):
            plain["es"] = r["effect_es"]
        subs = []
        for t in r.get("topics", []):
            for sj in rc.TOPIC_SUBJECTS.get(t, []):
                if sj not in subs:
                    subs.append(sj)
        out.append(Evidence(f"CB.{r['id'].split('.', 1)[1]}", "B.V. Raman, combinations", subs, tone, "specific",
                            plain, {l: T[l]["combo_why"] for l in T}))
    return out


def _book_evidence(r: dict) -> Evidence:
    tone = r["tone"] if r["tone"] in ("good", "bad") else "info"
    plain = {"en": r["effect"]}
    if r.get("effect_es"):
        plain["es"] = r["effect_es"]
    subs = []
    for t in r.get("topics", []):
        for sj in rc.TOPIC_SUBJECTS.get(t, []):
            if sj not in subs:
                subs.append(sj)
    rem = {l: v for l, v in (("en", r.get("remedy")), ("es", r.get("remedy_es"))) if v and _plain_ok(v)} or None
    return Evidence(f"BK.{r['id']}", br.label(r), subs, tone, "specific" if r.get("clarity") == "clear" else "tone",
                    plain, {l: T[l]["combo_why"] for l in T}, remedy=rem)


def _book_family(ctx: Ctx):
    """Library rules with no timing condition (standing traits), applied only where their natal conditions hold."""
    st = ctx.chart_state()
    return [_book_evidence(r) for r in br.load_rules() if not r.get("activation") and cb.applies(r, st)]


def timed_book_evidence(ctx: Ctx, when: date) -> List[Evidence]:
    """Timed library rules that hold on `when` (natal conditions + dasha/transit activation)."""
    st = dict(ctx.chart_state())
    st["periods"] = ctx.periods_at(when)
    st["transit"] = transit_signs(when)
    st["transit_lon"] = transit_longitudes(when)
    st["transit_lon_trop"] = transit_longitudes_tropical(when)
    return [_book_evidence(r) for r in ctx.timed_book_rules() if all(cb.act_holds(a, st) for a in r["activation"])]


def _combo_stems() -> set:
    return {re.sub(r"\s*\(.*\)", "", (r.get("name") or "")).replace(" Yoga", "").strip() for r in cb.load_rules()}


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
        if stem.replace(" Yoga", "").strip() in _combo_stems() - {"Dhana", "Raj"}:
            continue                                         # the book's own definition of this yoga is registered instead
        seen.add(stem)
        pl = {l: plain_yoga(y["name"], l) for l in ("en", "es")}
        tone = "good" if pl["en"]["kind"] == "strength" else "bad"
        plain = {l: pl[l]["title"] + ((": " + pl["en"]["effect_en"]) if l == "en" and pl["en"]["effect_en"] else "")
                 for l in pl}
        out.append(Evidence(f"YOGA.{stem.replace(' ', '_')}", "B.V. Raman, combinations",
                            _YOGA_SUBJECTS.get(y.get("category", "general"), []), tone, "specific",
                            plain, {l: T[l]["yoga_why"] for l in T},
                            planets=tuple(p for p in (y.get("planets") or []) if p in ctx.planets)))
    return out


REGISTRY: List[Rule] = [
    Rule("KAR", "K.N. Rao, Karakamsha", _kar_rules),
    Rule("LK.RC", "Lal Kitab (Roop Chand)", _rc_family),
    Rule("CB", "B.V. Raman, combinations", _combo_family),
    Rule("BK", "Library (K.N. Rao, B.V. Raman)", _book_family),
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


def _interleave(items: List[Evidence]) -> List[Evidence]:
    """Round-robin across books so a capped answer draws from every source, not just the biggest one."""
    by_book: Dict[str, List[Evidence]] = {}
    for e in items:
        by_book.setdefault(e.book, []).append(e)
    out, lists = [], list(by_book.values())
    while any(lists):
        for lst in lists:
            if lst:
                out.append(lst.pop(0))
    return out


def for_subject(evs: List[Evidence], subject: str) -> List[Evidence]:
    want = {subject, *PARENTS.get(subject, [])}
    return [e for e in evs if want & set(e.subjects)]


# ----------------------------------------------------------------------------- remedies
_PLANET_WORDS = ("sun ", "moon ", "mars", "mercury", "jupiter", "venus", "saturn ", "rahu", "ketu")


def _plain_ok(text: str) -> bool:
    low = text.lower()
    return not any(w in low for w in ("rahu", "ketu", "jupiter", "mars", "mercury", "venus"))


def remedies_for(evs: List[Evidence], limit: int = 3, lang: str = "en") -> List[dict]:
    """Remedies the text attaches to the applicable rules that strain this subject. Remedies that name a
    planet are skipped. Roop Chand's text: easy, affordable measures (donations, feeding, running water)."""
    out, seen = [], set()
    for e in evs:
        text = (e.remedy or {}).get(lang)
        if e.tone != "bad" or not text or text in seen:
            continue
        seen.add(text)
        out.append({"rule_id": e.rule_id, "do": text, "timing": "", "duration": ""})
        if len(out) >= limit:
            break
    return out


# ----------------------------------------------------------------------------- dashas drive the rules
from datetime import datetime, timedelta


def _dt(v):
    try:
        return v if isinstance(v, datetime) else datetime.fromisoformat(str(v)[:10])
    except Exception:
        return None


def dasha_state(ctx: Ctx, when: date) -> dict:
    """Running Vimshottari major/sub lords and Jaimini Chara major/sub signs on `when`."""
    from antar_engine.jaimini_engine import compute_chara_dasha
    if not hasattr(ctx, "_chara"):
        bd = _dt(ctx.birth_date)
        ctx._chara = compute_chara_dasha(ctx.lagna, ctx.planets, bd, num_cycles=3) if bd else []
    w = datetime(when.year, when.month, when.day)
    vmd = vad = None
    for r in ctx.vim_rows:
        s, e = _dt(r.get("start_date") or r.get("start")), _dt(r.get("end_date") or r.get("end"))
        lord = r.get("planet_or_sign") or r.get("lord_or_sign")
        lvl = str(r.get("level") or r.get("type") or "").lower()
        if s and e and s <= w < e:
            if lvl in ("1", "mahadasha"):
                vmd = lord
            elif lvl in ("2", "antardasha", "bhukti"):
                vad = lord
    lv = ctx.periods_at(when)
    vmd, vad = lv["md"] or vmd, lv["ad"] or vad
    cmd = cad = None
    for md in ctx._chara:
        if md.start_date <= w < md.end_date:
            cmd = md.sign
            for ad in md.sub_periods:
                if ad.start_date <= w < ad.end_date:
                    cad = ad.sign
    return {"vim_md": vmd, "vim_ad": vad, "vim_pd": lv["pd"], "vim_sd": lv["sd"], "chara_md": cmd, "chara_ad": cad}


def running(ctx: Ctx, e: Evidence, st: dict, levels=("vim_md", "vim_ad")) -> List[str]:
    """Which timing systems run this rule on that date. [] = the rule is dormant. Pass levels=("vim_md", "vim_ad",
    "vim_pd", "vim_sd") for week- and day-level questions."""
    out = []
    if any(p in tuple(st.get(l) for l in levels) for p in e.planets):
        out.append("vimshottari")
    cad = st["chara_ad"]
    if cad is not None:
        hit = any(ctx.planets[p].sign == cad or jre._aspects(ctx.planets[p].sign, cad) for p in e.planets if p in ctx.planets)
        hit = hit or cad in e.signs
        if hit:
            out.append("jaimini")
    return out


def running_rules(ctx: Ctx, when: date, subject: Optional[str] = None):
    """[(Evidence, [systems])] of the applicable rules that the dashas are running on `when`."""
    st = dasha_state(ctx, when)
    evs = applicable(ctx)
    if subject:
        evs = for_subject(evs, subject)
    return [(e, s) for e in evs if (s := running(ctx, e, st))], st


def timeline(ctx: Ctx, subject: str, months: int = 24, lang: str = "en"):
    """Segments of the next `months` months with the tone the running rules give `subject`:
    supportive / strained / mixed. Months with no running rule are silent."""
    tx = {"en": {"good": "supportive", "bad": "strained", "mixed": "mixed"},
          "es": {"good": "favorable", "bad": "tenso", "mixed": "mixto"}}[lang if lang in ("en", "es") else "en"]
    monthly = []
    for k in range(months):
        d = ctx.today + timedelta(days=30 * k)
        rr_, _ = running_rules(ctx, d, subject)
        tones = {e.tone for e, _ in rr_ if e.tone in ("good", "bad")}
        # library rules timed by dasha/transit: many fire at once, so they vote (2:1 wins, else mixed) instead of every rule counting
        bk = [e for e in for_subject(timed_book_evidence(ctx, d), subject) if e.tone in ("good", "bad")]
        g, b = sum(e.tone == "good" for e in bk), sum(e.tone == "bad" for e in bk)
        if g and g >= 2 * b:
            tones.add("good")
        elif b and b >= 2 * g:
            tones.add("bad")
        elif g and b:
            tones |= {"good", "bad"}
        rr_ = list(rr_) + [(e, ["book"]) for e in bk]
        tone = "mixed" if tones == {"good", "bad"} else ("good" if tones == {"good"} else ("bad" if tones == {"bad"} else None))
        two = any(len(sy) == 2 for _, sy in rr_)
        ids = tuple(sorted(e.rule_id for e, _ in rr_ if e.tone in ("good", "bad")))
        monthly.append((d, tone, two, ids))
    segs = []
    for d, tone, two, ids in monthly:
        if tone is None:
            continue
        if segs and segs[-1]["tone"] == tone and (d - segs[-1]["end"]).days <= 31:
            segs[-1]["end"] = d
            segs[-1]["both"] = segs[-1]["both"] or two
            segs[-1]["ids"] = sorted(set(segs[-1]["ids"]) | set(ids))
        else:
            segs.append({"start": d, "end": d, "tone": tone, "both": two, "ids": list(ids)})
    for s_ in segs:
        s_["tone_label"] = tx[s_["tone"]]
        s_["start"], s_["end"] = s_["start"].isoformat(), (s_["end"] + timedelta(days=30)).isoformat()
    return segs


def remedy_plan(ctx: Ctx, subject: Optional[str], lang: str, limit: int = 3) -> List[dict]:
    """Roop Chand remedies whose chart condition holds, for this subject (or all when subject is 'remedies')."""
    state = ctx.rc_state()
    want = None if subject in (None, "remedies") else {subject, *PARENTS.get(subject, [])}
    out = []
    for r in lkr.applying(state):
        if want is not None and not (want & set(lkr.subjects_of(r))):
            continue
        if want is None and not r.get("requires"):
            continue            # a remedy with no chart condition is offered only when the user asks about its topic
        item = lkr.render(r, lang)
        if item:
            out.append(item)
        if len(out) >= limit:
            break
    return out


_REM_REASON = {
    "en": {"month": "A phase tied to this remedy is running right now.",
           "six_months": "A phase tied to this remedy runs within the next six months.",
           "year": "This year's chart brings this area into play.",
           "ease": "To ease it", "strengthen": "To strengthen it",
           "none": "No remedy is called for in this window: nothing the text treats is being activated."},
    "es": {"month": "Una fase ligada a este remedio está en marcha ahora mismo.",
           "six_months": "Una fase ligada a este remedio ocurre en los próximos seis meses.",
           "year": "La carta de este año pone esta área en juego.",
           "ease": "Para aliviarlo", "strengthen": "Para fortalecerlo",
           "none": "Ningún remedio es necesario en esta ventana: no se activa nada de lo que trata el texto."},
}
_STRENGTHEN_WORDS = ("want", "wish", "more ease", "wellbeing", "do well", "success", "improve")


def _remedy_planets(remedy: dict) -> set:
    """Planets named in a remedy's chart condition: the planets whose activation makes it relevant."""
    out = set()
    for c in remedy.get("requires", []):
        for k in ("planet", "with"):
            if isinstance(c.get(k), str) and c[k] in rc.PLANETS:
                out.add(c[k])
    return out


def remedy_calendar(ctx: Ctx, lang: str = "en", subject: Optional[str] = None) -> dict:
    """Which Roop Chand remedies are live now, in the next six months, and this year, and why.
    A remedy is live in a window when a planet its chart condition names is activated in that window:
      this month   : that planet rules a Vimshottari pratyantara or sookshma running within 30 days
      six months   : that planet rules a major, sub or pratyantara period within 183 days
      this year    : that planet is the year lord or is named by a bad annual rule applying this year
    A remedy with no named planet (no chart condition) is never live by timing; it is offered only on its topic.
    Remedies mostly ease a trouble; one is marked 'strengthen' only when its own problem text is about gaining ease or success."""
    lang = lang if lang in _REM_REASON else "en"
    tx = _REM_REASON[lang]
    if not ctx.ok:
        return {"available": False}
    from datetime import datetime as _dtm, timedelta as _td
    rows = ctx.vim
    now = _dtm(ctx.today.year, ctx.today.month, ctx.today.day)
    month_planets = vl.lords_in_window(rows, now, now + _td(days=30), levels=("pd", "sd"), step_days=1) if rows else set()
    six_planets = vl.lords_in_window(rows, now, now + _td(days=183), levels=("md", "ad", "pd"), step_days=3) if rows else set()
    year_planets = set()
    state = ctx.rc_state()
    if state.get("annual"):
        yl = None
        try:
            from antar_engine.lk_year_lord import year_lord_by_age
            yl = year_lord_by_age(ctx.birth_date, ctx.today)
        except Exception:
            pass
        year_planets = {yl} if yl else set()
        year_planets |= {r["planet"] for r in rc.applying(state, kind="annual") if r["tone"] == "bad" and r.get("planet")}
    want = None if subject in (None, "remedies") else {subject, *PARENTS.get(subject, [])}
    buckets = {"this_month": [], "six_months": [], "this_year": []}
    placed = set()
    for r in lkr.applying(state):
        planets = _remedy_planets(r)
        if not planets:
            continue
        if want is not None and not (want & set(lkr.subjects_of(r))):
            continue
        item = lkr.render(r, lang)
        if not item:
            continue
        low = (r.get("problem") or "").lower()
        item["purpose"] = tx["strengthen"] if any(w in low for w in _STRENGTHEN_WORDS) else tx["ease"]
        for key, pset, why in (("this_month", month_planets, "month"), ("six_months", six_planets, "six_months"),
                               ("this_year", year_planets, "year")):
            if planets & pset and r["id"] not in placed:
                buckets[key].append({**item, "why_now": tx[why]})
                placed.add(r["id"])
    return {"available": True, "language": lang, "principle": rc_principle(lang), **buckets,
            "none": tx["none"] if not placed else None}


def rc_principle(lang: str) -> str:
    from antar_engine.lk_annual_forecast import PRINCIPLE
    return PRINCIPLE.get(lang, PRINCIPLE["en"])


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


_SPEC_STANCE = {
    "en": {"good": "Overall your chart leans supportive toward speculation.",
           "bad": "Overall your chart leans costly toward speculation; take extra care.",
           "mixed": "Overall your chart swings both ways on speculation: gains can come, and so can losses."},
    "es": {"good": "En general tu carta se inclina a favor de la especulación.",
           "bad": "En general tu carta se inclina a que la especulación te cueste; ten más cuidado.",
           "mixed": "En general tu carta oscila en la especulación: pueden llegar ganancias y también pérdidas."}}


def _spec_stance(evs, lang: str) -> Optional[str]:
    """One verdict for speculation from the distinct placements that speak to it (a placement counts once, however many
    books or lists repeat it); 2:1 wins, otherwise the chart swings."""
    groups: Dict[tuple, set] = {}
    for e in evs:
        if e.tone in ("good", "bad"):
            groups.setdefault((e.planet, e.house, tuple(sorted(e.signs))) if e.planet else (e.rule_id,), set()).add(e.tone)
    g = sum(t == {"good"} for t in groups.values())
    b = sum(t == {"bad"} for t in groups.values())
    m = sum(len(t) == 2 for t in groups.values())
    tx = _SPEC_STANCE.get(lang, _SPEC_STANCE["en"])
    if not (g or b or m):
        return None
    if g and g >= 2 * (b + m):
        return tx["good"]
    if b and b >= 2 * (g + m):
        return tx["bad"]
    return tx["mixed"]


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
    rem = remedies_for(bad, lang=lang)
    plan = remedy_plan(ctx, subject, lang, 8 if subject == 'remedies' else 3)
    wins = _windows(ctx, subject, lang)
    wake = []
    if ctx.age is not None:
        prof = lal_kitab_profile({n: p.sign for n, p in ctx.planets.items()}, ctx.age, horizon=3)
        wake = [w for w in prof["wake_ups"]]

    def add(items, evidence=False, cap=6):
        """Effect lines, deduplicated and capped. With evidence, lines are grouped by placement and the reason
        ('because your X sits in Y') is stated once per placement instead of after every sentence."""
        seen_text, shown = set(), 0
        groups = {}
        for e in _interleave(items):
            txt = e.plain.get(lang)
            if not txt or txt in seen_text:
                continue                                   # no text in this language, or a repeat
            seen_text.add(txt)
            groups.setdefault((e.planet, e.house) if evidence else id(e), []).append((e, txt))
            shown += 1
            if shown >= cap:
                break
        for grp in groups.values():
            if evidence:
                w = grp[0][0].why[lang]
                lines.append(w[0].upper() + w[1:])
            for e, txt in grp:
                lines.append(("- " if evidence else "") + txt)
                used.append(e.rule_id)

    head = (tx["head_remedies"] if subject == "remedies" else tx["head_" + qword].format(s=label))

    def add_remedies():
        shown = rem + plan
        if not shown:
            return
        lines.append(tx["remedies"] + ":")
        for r in shown:
            if r.get("problem"):
                lines.append(r["problem"])
                for st in r.get("steps", []):
                    lines.append("- " + st)
                if r.get("duration"):
                    d = r["duration"]
                    lines.append("- " + (tx["for_days"].format(d=d) if re.match(r"\s*\d", d) else tx["timing_note"].format(d=d)))
            else:
                lines.append(r["do"] + (f' ({r["timing"]}, {r["duration"]})' if r["timing"] or r["duration"] else ""))
            used.append(r["rule_id"])

    if subject == "remedies":
        calendar = remedy_calendar(ctx, lang, subject)
        titles = {"this_month": {"en": "This month", "es": "Este mes"}, "six_months": {"en": "Next six months", "es": "Próximos seis meses"},
                  "this_year": {"en": "This year", "es": "Este año"}}
        for key in ("this_month", "six_months", "this_year"):
            items = calendar.get(key, [])[:3]
            if not items:
                continue
            lines.append(titles[key][lang] + ":")
            for r in items:
                lines.append(r["problem"] + " (" + r["purpose"] + ")")
                for st in r.get("steps", []):
                    lines.append("- " + st)
                if r.get("duration"):
                    d = r["duration"]
                    lines.append("- " + (tx["for_days"].format(d=d) if re.match(r"\s*\d", d) else tx["timing_note"].format(d=d)))
                lines.append(r["why_now"])
                used.append(r["rule_id"])
        if lines:
            lines.append(calendar["principle"])
        plan = [r for k in ("this_month", "six_months", "this_year") for r in calendar.get(k, [])]
    elif qword in ("what", "why"):
        ev_on = (qword == "why")
        if subject == "speculation":
            st_line = _spec_stance(evs, lang)
            if st_line:
                lines.append(st_line)
        blocks = [(tx["challenges"], bad), (tx["strengths"], good)] if ev_on else [(tx["strengths"], good), (tx["challenges"], bad)]
        for title, items in blocks:
            if items:
                lines.append(title + ":")
                add(items, evidence=ev_on)
        if any(e.precision == "tone" for e in evs):
            lines.append(tx["tone_only"])
        add_remedies()
    elif qword == "when":
        for w in wins:
            lines.append(f'{w["label"]} ({w["strength_label"]}): {w["headline"]}. {w["why"]}')
        for w in wake:
            lines.append(tx["wake"].format(age=w["age"]))
        tl = timeline(ctx, subject, 24, lang) if ctx.vim_rows else []
        for sg in tl:
            lines.append(f'{sg["start"][:7]} to {sg["end"][:7]}: {sg["tone_label"]}' + (" (both timing systems)" if sg["both"] and lang == "en" else ""))
            used += sg["ids"]
        if not wins and not wake and not tl:
            lines.append(tx["none_when"].format(s=label))
        used += [f"WINDOW.{subject}"] if wins else []
    elif qword == "how":
        for w in wins[:2]:
            lines.append(tx["step"].format(a=w["action"]))
        lean = [e for e in good if e.tone == "good"]
        note = [e for e in good if e.tone == "info"]
        if lean:
            lines.append(tx["lean_on"] + ":")
            add(lean)
        if note:
            lines.append(tx["worth_knowing"] + ":")
            add(note, cap=3)
        add_remedies()
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
    if qword in ("what", "how", "why", "which") and subject not in ("remedies",):
        now_ev = [e for e in for_subject(timed_book_evidence(ctx, ctx.today), subject)]
        shown, seen_t = [], set()
        for e in _interleave(now_ev):
            t = e.plain.get(lang)
            if t and t not in seen_t:
                seen_t.add(t); shown.append((e, t))
            if len(shown) >= 4:
                break
        if shown:
            lines.append(tx["active_now"] + ":")
            for e, t in shown:
                lines.append(("- " if qword == "why" else "") + t)
                used.append(e.rule_id)
    if subject == "speculation":
        lines.append(tx["spec"])
    applicable_any = bool(evs or wins or wake or plan or subject == "speculation")
    if not applicable_any:
        lines = [tx["none"].format(s=label)]
    return {"available": True, "subject": subject, "subject_label": label, "qword": qword, "language": lang,
            "headline": head, "lines": lines, "rules_used": sorted(set(used)), "windows": wins,
            "remedies": (rem + plan) if (qword in ("how", "what", "why") or subject == "remedies") else [],
            "applicable": applicable_any,
            "text": head + "\n" + "\n".join(lines)}
