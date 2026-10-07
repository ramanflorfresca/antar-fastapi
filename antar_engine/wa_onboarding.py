"""[wa-onboarding 2026-10-06] Chat-first onboarding: a stranger messages Antar's WhatsApp number and we
collect name → date → time → birthplace → (optional) where they live now → confirm, one question at a time.

Pure state machine: no network, no database in `advance()`. The caller (main._wa_handle) owns consent
(the in-chat policy gate runs first), geocoding, account + chart creation, and persistence (`load`/`save`,
table `wa_onboarding`, sql_wa_onboarding.sql). Anything that could silently produce a WRONG chart is
echoed back for a yes/no before the chart is built — month is always written as a word, never a number.
"""
import re
import time
from datetime import date, datetime, timezone
from typing import Optional

STEPS = ("name", "dob", "tob", "pob", "current", "confirm")
STALE_S = 7 * 24 * 3600          # a half-finished onboarding older than this restarts

_MONTHS = {
    1: ("january", "jan", "enero", "ene", "janeiro", "janvari"),
    2: ("february", "feb", "febrero", "fevereiro", "fev", "farvari"),
    3: ("march", "mar", "marzo", "março", "marco", "maarch"),
    4: ("april", "apr", "abril", "abr"),
    5: ("may", "mayo", "maio", "mai"),
    6: ("june", "jun", "junio", "junho"),
    7: ("july", "jul", "julio", "julho"),
    8: ("august", "aug", "agosto", "ago"),
    9: ("september", "sep", "sept", "septiembre", "setembro", "set"),
    10: ("october", "oct", "octubre", "outubro", "out"),
    11: ("november", "nov", "noviembre", "novembro"),
    12: ("december", "dec", "diciembre", "dic", "dezembro", "dez"),
}
_MONTH_LOOKUP = {w: n for n, ws in _MONTHS.items() for w in ws}
_MONTH_NAME = {1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June", 7: "July",
               8: "August", 9: "September", 10: "October", 11: "November", 12: "December"}
# countries that write the month first
_MONTH_FIRST = {"US", "CA", "PH"}


# ── parsers ────────────────────────────────────────────────────────────────

# [hi 2026-10-07] Devanagari input. Digits and the handful of Hindi words the parsers
# key on are folded to the Latin forms they already understand, so a Hindi reader can
# answer the Hindi prompts in Hindi ("१४ मार्च १९९०", "सुबह ६:४०", "पता नहीं", "नाम").
_DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
_DEV_FOLD = (
    ("जनवरी", "january"), ("फ़रवरी", "february"), ("फरवरी", "february"), ("मार्च", "march"),
    ("अप्रैल", "april"), ("मई", "may"), ("जून", "june"), ("जुलाई", "july"), ("अगस्त", "august"),
    ("सितंबर", "september"), ("सितम्बर", "september"), ("अक्टूबर", "october"),
    ("अक्तूबर", "october"), ("नवंबर", "november"), ("नवम्बर", "november"),
    ("दिसंबर", "december"), ("दिसम्बर", "december"),
    ("पता नहीं", "pata nahi"), ("मालूम नहीं", "maloom nahi"), ("आधी रात", "midnight"),
    ("दोपहर", "noon"), ("सुबह", "morning"), ("शाम", "evening"), ("रात", "night"), ("लगभग", "lagbhag"),
)


def _deva(text: str) -> str:
    t = (text or "").translate(_DEV_DIGITS)
    for hi, lat in _DEV_FOLD:
        if hi in t:
            t = t.replace(hi, f" {lat} ")
    return t


_NAME_LEAD = re.compile(
    r"^\s*(?:hi+|hello|hola|ol[aá]|namaste|hey)?[\s,!.]*"
    r"(?:my name is|i am|i'm|im|this is|me llamo|mi nombre es|soy|meu nome [eé]|eu sou|me chamo|"
    r"mera naam|mera nam|main|मेरा नाम(?: है)?|मैं|मेरा नाम)?\s*", re.I)


def parse_name(text: str) -> Optional[str]:
    t = _NAME_LEAD.sub("", (text or "").strip(), count=1).strip(" .!,")
    t = re.sub(r"\s+(?:hai|here|aqui|aquí|है|हूँ|हूं)$", "", t, flags=re.I)
    if not t or len(t) > 60 or "?" in t or re.search(r"\d", t) or len(t.split()) > 5:
        return None
    if not re.fullmatch(r"[^\W\d_\u0900-\u097F]+(?:[ '\-.][^\W\d_\u0900-\u097F]+)*|"
                        r"[\u0900-\u0963\u0966-\u097F]+(?: [\u0900-\u0963\u0966-\u097F]+)*", t, flags=re.UNICODE):
        return None
    return " ".join(w[:1].upper() + w[1:] for w in t.split())


def parse_dob(text: str, country: str = "") -> tuple:
    """(iso_date | None, ambiguous). `ambiguous` = 04/05/1990 style where day/month could swap; the
    caller still echoes the month as a word at the confirm step, which is what catches a wrong guess."""
    t = _deva(text).strip().lower()
    t = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", t)
    t = t.replace(",", " ").replace(" of ", " ").replace(" de ", " ")
    today = date.today()

    def ok(y, m, d):
        try:
            v = date(y, m, d)
        except ValueError:
            return None
        return v.isoformat() if 1900 <= y <= today.year and v <= today else None

    m = re.fullmatch(r"\s*(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\s*", t)
    if m:
        return ok(int(m[1]), int(m[2]), int(m[3])), False
    m = re.fullmatch(r"\s*(\d{1,2})[-/. ](\d{1,2})[-/. ](\d{4})\s*", t)
    if m:
        a, b, y = int(m[1]), int(m[2]), int(m[3])
        first_month = (country or "").upper() in _MONTH_FIRST
        d, mo = (b, a) if first_month else (a, b)
        if mo > 12 and d <= 12:       # only one reading is possible
            d, mo = mo, d
        return ok(y, mo, d), (a <= 12 and b <= 12 and a != b)
    words = re.findall(r"[^\W\d_]+|\d+", t, flags=re.UNICODE)
    mon = next((_MONTH_LOOKUP[w] for w in words if w in _MONTH_LOOKUP), None)
    nums = [int(w) for w in words if w.isdigit()]
    if mon and len(nums) == 2:
        y = next((n for n in nums if n > 31), None)
        d = next((n for n in nums if n <= 31), None)
        if y and d:
            return ok(y, mon, d), False
    return None, False


def fmt_date(iso: str) -> str:
    y, m, d = (int(x) for x in iso.split("-"))
    return f"{d} {_MONTH_NAME[m]} {y}"


_UNKNOWN_TIME = re.compile(
    r"don'?t know|do not know|dont know|no idea|not sure|unknown|no s[eé]|nao sei|não sei|"
    r"pata nahi|nahi pata|maloom nahi|\bidk\b|^\s*skip\s*$", re.I)


def parse_tob(text: str) -> Optional[tuple]:
    """(HH:MM, accuracy) — accuracy ∈ exact | approximate | unknown (birth_time_confidence.py's vocabulary).
    'unknown' gets 12:00 so a chart can still be built; the engine hedges house claims for it."""
    t = _deva(text).strip().lower().replace(".", "")
    if _UNKNOWN_TIME.search(t):
        return "12:00", "unknown"
    approx = bool(re.search(r"around|about|approx|roughly|aprox|alrededor|mas o menos|mais ou menos|"
                            r"lagbhag|takriban|~", t))
    for pat, hhmm in ((r"\bnoon\b|mediod[ií]a|meio[- ]?dia|dopahar", "12:00"),
                      (r"midnight|medianoche|meia[- ]?noite|aadhi raat", "00:00")):
        if re.search(pat, t):
            return hhmm, "approximate"
    t = re.sub(r"\b([ap])\s*m\b", r"\1m", t)
    pm = bool(re.search(r"\bpm\b|\bp m\b|tarde|noche|night|evening|shaam|raat", t))
    am = bool(re.search(r"\bam\b|ma[ñn]ana|morning|subah|manh[ãa]", t))
    m = re.search(r"(\d{1,2})\s*[:h]\s*(\d{2})|\b(\d{1,2})\s*(?:am|pm)\b|\b(\d{1,2})(\d{2})\b|^\s*(\d{1,2})\s*$",
                  t)
    if not m:
        return None
    if m[1] is not None:
        h, mi = int(m[1]), int(m[2])
    elif m[3] is not None:
        h, mi = int(m[3]), 0
    elif m[4] is not None:
        h, mi = int(m[4]), int(m[5])
    else:
        h, mi = int(m[6]), 0
        if not (am or pm):
            return None               # a bare "6" is ambiguous — ask for AM/PM
    if mi > 59 or h > 24:
        return None
    if pm and h < 12:
        h += 12
    elif am and h == 12:
        h = 0
    if h == 24:
        h = 0
    if h > 23:
        return None
    return f"{h:02d}:{mi:02d}", ("approximate" if approx else "exact")


_YES = {"yes", "y", "yeah", "yep", "ok", "okay", "correct", "right", "si", "sí", "sim", "correcto", "certo",
        "haan", "han", "ha", "theek", "sahi", "confirm", "confirmo", "👍", "✅",
        "हाँ", "हां", "जी", "जी हाँ", "जी हां", "ठीक", "ठीक है", "सही", "सही है"}
_NO = {"no", "n", "nope", "wrong", "incorrect", "nao", "não", "nahi", "nahin", "galat", "incorrecto", "errado",
       "नहीं", "नही", "ना", "गलत", "ग़लत", "गलत है"}


def parse_yes_no(text: str, choice_id: str = "") -> Optional[str]:
    if choice_id in ("wob:yes", "wob:no"):
        return choice_id.split(":")[1]
    t = re.sub(r"[^\w\sñáéíóúãç👍✅\u0900-\u0963]", "", (text or "").lower()).strip()
    if t in _YES or t.startswith(("yes ", "si ", "sí ", "haan ", "correct ")):
        return "yes"
    if t in _NO or t.startswith(("no ", "nahi ", "wrong ")):
        return "no"
    return None


_FIX = {"name": ("name", "nombre", "nome", "naam", "नाम"),
        "dob": ("date", "fecha", "data", "tareekh", "dob", "तारीख़", "तारीख", "तिथि"),
        "tob": ("time", "hora", "samay", "waqt", "समय"),
        "pob": ("place", "lugar", "local", "jagah", "city", "ciudad", "जगह", "स्थान", "शहर"),
        "current": ("current", "now", "actual", "agora", "abhi", "live", "अभी", "वर्तमान")}


def parse_fix(text: str, choice_id: str = "") -> Optional[str]:
    if choice_id.startswith("wob:fix:"):
        return choice_id.split(":")[2]
    t = (text or "").lower()
    for step, words in _FIX.items():
        if any((w in t) if ord(w[0]) > 0x900 else re.search(rf"\b{w}\b", t) for w in words):
            return step
    return None


_SKIP = re.compile(r"^\s*(skip|saltar|omitir|pular|pass|later|despu[eé]s|depois|baad mein|no thanks|"
                   r"prefiero no|prefiro n[aã]o|छोड़ें|छोड़ो|स्किप|बाद में)\s*[.!]?\s*$", re.I)


def is_skip(text: str) -> bool:
    return bool(_SKIP.match(text or ""))


# ── copy ───────────────────────────────────────────────────────────────────

T = {
    "hello": {
        "en": "Welcome to Antar 🙏 I read your birth chart — in this chat, no app needed.\n\nFirst, what should I call you?",
        "es": "Bienvenido a Antar 🙏 Leo tu carta natal — aquí mismo, sin app.\n\nPrimero, ¿cómo te llamo?",
        "pt": "Bem-vindo à Antar 🙏 Eu leio seu mapa natal — aqui mesmo, sem app.\n\nPrimeiro, como devo te chamar?",
        "hinglish": "Antar mein swagat hai 🙏 Main aapka janam chart padhta hoon — isi chat mein, app ki zaroorat nahi.\n\nPehle bataiye, aapko kya kehkar bulaun?"},
    "ask_dob": {
        "en": "Nice to meet you, *{name}*. What's your date of birth? (e.g. 14 March 1990)",
        "es": "Mucho gusto, *{name}*. ¿Cuál es tu fecha de nacimiento? (ej. 14 marzo 1990)",
        "pt": "Prazer, *{name}*. Qual é sua data de nascimento? (ex. 14 março 1990)",
        "hinglish": "Aapse mil kar achha laga, *{name}*. Aapki janam tareekh? (jaise 14 March 1990)"},
    "bad_name": {
        "en": "Just your first name is fine — what should I call you?",
        "es": "Con tu nombre basta — ¿cómo te llamo?",
        "pt": "Só o seu nome já basta — como devo te chamar?",
        "hinglish": "Bas aapka naam kaafi hai — aapko kya kehkar bulaun?"},
    "bad_dob": {
        "en": "I couldn't read that date. Please write it like *14 March 1990* (day, month name, 4-digit year).",
        "es": "No pude leer esa fecha. Escríbela como *14 marzo 1990* (día, mes, año de 4 cifras).",
        "pt": "Não consegui ler essa data. Escreva como *14 março 1990* (dia, mês, ano com 4 dígitos).",
        "hinglish": "Yeh tareekh samajh nahi aayi. Aise likhiye: *14 March 1990* (din, mahine ka naam, 4 ank ka saal)."},
    "ask_tob": {
        "en": "What time were you born? (e.g. 6:40 am). Not sure? Say *approx* with your best guess, or *don't know* — I'll still read your chart, just with less certainty about houses.",
        "es": "¿A qué hora naciste? (ej. 6:40 am). ¿No estás seguro? Di tu mejor estimación con *aprox*, o *no sé* — igual leo tu carta, con menos certeza en las casas.",
        "pt": "A que horas você nasceu? (ex. 6:40 am). Não tem certeza? Diga seu palpite com *aprox*, ou *não sei* — eu leio mesmo assim, com menos certeza nas casas.",
        "hinglish": "Aap kis samay paida hue? (jaise 6:40 am). Pakka nahi pata? *approx* ke saath andaza bataiye, ya *pata nahi* — phir bhi chart padhunga, bas houses mein thodi kam certainty hogi."},
    "bad_tob": {
        "en": "I couldn't read that time. Try *6:40 am*, *18:40*, or *don't know*.",
        "es": "No pude leer esa hora. Prueba *6:40 am*, *18:40* o *no sé*.",
        "pt": "Não consegui ler esse horário. Tente *6:40 am*, *18:40* ou *não sei*.",
        "hinglish": "Yeh samay samajh nahi aaya. Aise likhiye: *6:40 am*, *18:40* ya *pata nahi*."},
    "ask_pob": {
        "en": "Where were you born? City and country (e.g. *Pune, India*). If you're not sure of the spelling, you can also share a location pin.",
        "es": "¿Dónde naciste? Ciudad y país (ej. *Bogotá, Colombia*). También puedes compartir una ubicación.",
        "pt": "Onde você nasceu? Cidade e país (ex. *São Paulo, Brasil*). Também pode compartilhar uma localização.",
        "hinglish": "Aap kahan paida hue? Shehar aur desh (jaise *Pune, India*). Chahein toh location pin bhi bhej sakte hain."},
    "bad_pob": {
        "en": "I couldn't find that place. Add the country — like *Springfield, Illinois, USA* — or share a location pin.",
        "es": "No encontré ese lugar. Agrega el país — como *Medellín, Colombia* — o comparte una ubicación.",
        "pt": "Não encontrei esse lugar. Adicione o país — como *Recife, Brasil* — ou compartilhe uma localização.",
        "hinglish": "Yeh jagah nahi mili. Desh bhi likhiye — jaise *Jaipur, India* — ya location pin bhejiye."},
    "ask_current": {
        "en": "Last one (optional): which city do you live in now? It makes timing and alerts local to you. Or reply *skip*.",
        "es": "Última (opcional): ¿en qué ciudad vives ahora? Así los tiempos y alertas son locales. O responde *saltar*.",
        "pt": "Última (opcional): em que cidade você mora agora? Assim os tempos e alertas ficam locais. Ou responda *pular*.",
        "hinglish": "Aakhri (optional): abhi aap kis shehar mein rehte hain? Isse timing aur alerts aapke local hote hain. Ya *skip* bhejiye."},
    "confirm": {
        "en": "Let me check I have this right:\n\n*{name}*\n📅 {dob}\n🕐 {tob}\n📍 {pob} ({tz})\n{cur}\nShall I build your chart?",
        "es": "Verifico que todo esté bien:\n\n*{name}*\n📅 {dob}\n🕐 {tob}\n📍 {pob} ({tz})\n{cur}\n¿Construyo tu carta?",
        "pt": "Vou conferir se está tudo certo:\n\n*{name}*\n📅 {dob}\n🕐 {tob}\n📍 {pob} ({tz})\n{cur}\nPosso montar seu mapa?",
        "hinglish": "Ek baar check kar leta hoon:\n\n*{name}*\n📅 {dob}\n🕐 {tob}\n📍 {pob} ({tz})\n{cur}\nChart bana doon?"},
    "which_fix": {
        "en": "What should I change? Reply *name*, *date*, *time* or *place*.",
        "es": "¿Qué cambio? Responde *nombre*, *fecha*, *hora* o *lugar*.",
        "pt": "O que devo mudar? Responda *nome*, *data*, *hora* ou *local*.",
        "hinglish": "Kya badalna hai? *naam*, *date*, *time* ya *place* bhejiye."},
    "yes_no": {
        "en": "Please answer *yes* to build the chart, or *no* to fix something.",
        "es": "Responde *sí* para construir la carta, o *no* para corregir algo.",
        "pt": "Responda *sim* para montar o mapa, ou *não* para corrigir algo.",
        "hinglish": "Chart banane ke liye *haan* bhejiye, kuch theek karna ho toh *nahi*."},
    "building": {
        "en": "Building your chart — this takes a few seconds…",
        "es": "Construyendo tu carta — tarda unos segundos…",
        "pt": "Montando seu mapa — leva alguns segundos…",
        "hinglish": "Aapka chart ban raha hai — kuch second lagenge…"},
    "failed": {
        "en": "I couldn't finish your chart just now. Nothing is lost — send *hi* in a minute and we'll pick up where we left off.",
        "es": "No pude terminar tu carta ahora. No se pierde nada — escribe *hola* en un minuto y seguimos donde quedamos.",
        "pt": "Não consegui terminar seu mapa agora. Nada se perde — mande *oi* em um minuto e continuamos de onde paramos.",
        "hinglish": "Abhi chart poora nahi ho paya. Kuch khota nahi — ek minute baad *hi* bhejiye, wahin se aage badhenge."},
    "web_nudge": {
        "en": "Want the full chart, daily view and everything in one place? Open it here (signs you in — link expires in 15 min): {url}",
        "es": "¿Quieres la carta completa y el día a día en un solo lugar? Ábrela aquí (te inicia sesión — el enlace vence en 15 min): {url}",
        "pt": "Quer o mapa completo e o dia a dia num só lugar? Abra aqui (faz seu login — o link expira em 15 min): {url}",
        "hinglish": "Poora chart aur roz ka view ek jagah chahiye? Yahan kholiye (sign-in ho jayega — link 15 min mein expire): {url}"},
    "resumed": {
        "en": "Welcome back 🙏 Let's pick up where we left off.",
        "es": "Qué bueno verte de nuevo 🙏 Seguimos donde quedamos.",
        "pt": "Que bom te ver de novo 🙏 Vamos continuar de onde paramos.",
        "hinglish": "Wapas swagat hai 🙏 Wahin se aage badhte hain."},
}
_CUR_LINE = {"en": "🏠 Now living in {c}\n", "es": "🏠 Vives ahora en {c}\n", "pt": "🏠 Mora agora em {c}\n",
             "hinglish": "🏠 Abhi {c} mein rehte hain\n"}
_TOB_LABEL = {
    "exact": {"en": "{t}", "es": "{t}", "pt": "{t}", "hinglish": "{t}"},
    "approximate": {"en": "around {t}", "es": "aprox. {t}", "pt": "aprox. {t}", "hinglish": "lagbhag {t}"},
    "unknown": {"en": "unknown (I'll hedge house claims)", "es": "desconocida (seré cauto con las casas)",
                "pt": "desconhecida (serei cauto com as casas)", "hinglish": "pata nahi (houses mein andaza rakhunga)"},
}


# [hi 2026-10-07] Devanagari Hindi column (kept in wa_hi.py with the other WhatsApp Hindi copy)
from antar_engine import wa_hi as _wa_hi
for _k, _v in _wa_hi.ONBOARDING_HI.items():
    T[_k]["hi"] = _v
_CUR_LINE["hi"] = _wa_hi.ONBOARDING_CUR_HI
for _acc, _lab in _wa_hi.ONBOARDING_TOB_HI.items():
    _TOB_LABEL[_acc]["hi"] = _lab
_TOB_LABEL["unknown"]["hi"] = _wa_hi.ONBOARDING_TOB_UNKNOWN_HI


_HI_MONTH = ("जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर",
             "अक्टूबर", "नवंबर", "दिसंबर")


def text(key: str, lang: str, **kw) -> str:
    s = T[key].get(lang) or T[key]["en"]
    return s.format(**kw) if kw else s


def confirm_text(st: dict, lang: str) -> str:
    acc = st.get("tob_acc") or "exact"
    tob = (_TOB_LABEL.get(acc) or _TOB_LABEL["exact"]).get(lang, "{t}").format(t=st.get("tob", ""))
    cur = _CUR_LINE.get(lang, _CUR_LINE["en"]).format(c=st["current"]) if st.get("current") else ""
    dob = fmt_date(st["dob"])
    if lang == "hi":   # [hi] Hindi month name inside the Hindi confirm message
        y, m, d = (int(x) for x in st["dob"].split("-"))
        dob = f"{d} {_HI_MONTH[m - 1]} {y}"
    return text("confirm", lang, name=st.get("name", ""), dob=dob, tob=tob,
                pob=st.get("pob_label") or st.get("pob", ""), tz=st.get("tz_label") or "—", cur=cur)


# ── state machine ──────────────────────────────────────────────────────────

def new_state(lang: str = "en", country: str = "") -> dict:
    return {"step": "name", "lang": lang, "country": country, "started": int(time.time()),
            "updated": int(time.time())}


def is_stale(st: Optional[dict], now: Optional[float] = None) -> bool:
    return not st or ((now or time.time()) - int(st.get("updated") or 0)) > STALE_S


def advance(st: dict, body: str, choice_id: str = "") -> dict:
    """One inbound message → {state, reply (key), params, action}. Never touches the network.

    action: None | "geocode_pob" (arg = place text) | "geocode_current" | "build".
    The caller geocodes, then calls `set_place()` / `place_failed()` and continues with the result.
    """
    st = dict(st)
    st["updated"] = int(time.time())
    lang = st.get("lang") or "en"
    step = st.get("step") or "name"
    body = (body or "").strip()

    def out(reply, action=None, arg=None, **params):
        return {"state": st, "reply": reply, "params": params, "action": action, "arg": arg}

    if step == "name":
        nm = parse_name(body)
        if not nm:
            return out("bad_name")
        st["name"], st["step"] = nm, "dob"
        return out("ask_dob", name=nm)

    if step == "dob":
        iso, _amb = parse_dob(body, st.get("country", ""))
        if not iso:
            return out("bad_dob")
        st["dob"], st["step"] = iso, "tob"
        return out("ask_tob")

    if step == "tob":
        r = parse_tob(body)
        if not r:
            return out("bad_tob")
        st["tob"], st["tob_acc"], st["step"] = r[0], r[1], "pob"
        return out("ask_pob")

    if step == "pob":
        if not body:
            return out("bad_pob")
        return out(None, action="geocode_pob", arg=body)

    if step == "current":
        if is_skip(body):
            st.pop("current", None)
            st["step"] = "confirm"
            return out("__confirm__")
        if not body:
            return out("ask_current")
        return out(None, action="geocode_current", arg=body)

    if step == "confirm":
        if st.get("fixing"):
            fix = parse_fix(body, choice_id)
            if not fix:
                return out("which_fix")
            st.pop("fixing", None)
            st["step"] = fix
            return out({"name": "bad_name", "dob": "bad_dob", "tob": "bad_tob",
                        "pob": "bad_pob", "current": "ask_current"}[fix])
        ans = parse_yes_no(body, choice_id)
        if ans == "yes":
            return out("building", action="build")
        if ans == "no":
            fix = parse_fix(body, choice_id)
            if fix:
                st["step"] = fix
                return out({"name": "bad_name", "dob": "bad_dob", "tob": "bad_tob",
                            "pob": "bad_pob", "current": "ask_current"}[fix])
            st["fixing"] = True
            return out("which_fix")
        return out("yes_no")

    st["step"] = "name"
    return out("hello")


def set_place(st: dict, which: str, label: str, lat: float, lon: float, tz_name: str, tz_label: str) -> dict:
    """Record a geocoded place (which = 'pob' | 'current') and move on."""
    st = dict(st)
    if which == "pob":
        st.update(pob=label, pob_label=label, lat=lat, lon=lon, tz=tz_name, tz_label=tz_label,
                  step="current")
    else:
        st.update(current=label, current_lat=lat, current_lon=lon, current_tz=tz_name, step="confirm")
    st["updated"] = int(time.time())
    return st


def to_chart_fields(st: dict) -> dict:
    """The ChartCreateRequest kwargs. Coordinates are the canonical birth pin — never re-geocoded."""
    f = {
        "birth_date": st["dob"], "birth_time": st["tob"] + ":00", "birth_lat": st["lat"],
        "birth_lng": st["lon"], "full_name": st["name"], "birth_place": st.get("pob"),
        "language_preference": st.get("lang") or "en",
    }
    if st.get("tz"):
        f["timezone_name"] = st["tz"]
    if st.get("current"):
        f["current_city"] = st["current"]
    return f


# ── persistence (table wa_onboarding; fail-closed to today's "connect in the app" message) ────────────

def _missing(e) -> bool:
    m = str(e).lower()
    return "pgrst205" in m or "could not find the table" in m or "does not exist" in m


def load(sb, number: str) -> tuple:
    """(state | None, available). available=False when the table isn't there yet."""
    try:
        rows = (sb.table("wa_onboarding").select("state").eq("number", number).limit(1).execute()).data or []
        return (rows[0].get("state") if rows else None), True
    except Exception as e:
        if not _missing(e):
            print(f"[wa-onboarding] load failed …{number[-4:]}: {e}")
        return None, False


def save(sb, number: str, st: dict, status: str = "open", chart_id: Optional[str] = None,
         user_id: Optional[str] = None) -> bool:
    row = {"number": number, "state": st, "status": status,
           "updated_at": datetime.now(timezone.utc).isoformat()}
    if chart_id:
        row["chart_id"] = chart_id
    if user_id:
        row["user_id"] = user_id
    try:
        sb.table("wa_onboarding").upsert(row, on_conflict="number").execute()
        return True
    except Exception as e:
        print(f"[wa-onboarding] save failed …{number[-4:]}: {e}")
        return False
