"""
antar_engine/understand.py — ONE understanding of a message, shared by every
surface (app /ask, WhatsApp), instead of a dozen keyword lists.

[nlu 2026-10-03] Owner: "create a proper NLP / NLQ so antar.world is a proper
conversational AI astrologer who listens". Every live failure that night was a
keyword list misreading meaning:
  * "the" (Hindi थे) turned an English question Hinglish;
  * "Will my partnership break" → generic money read;
  * "girl friend" → generic; "speculation" → unmapped; "60’days" → no horizon;
  * 4 weeks of shadow data (intent_classify_log, 1,000 questions): the keyword
    router answered "general" for 56% of questions, Haiku for 31%, and Haiku
    read "move forward" as purpose where keywords read a house move.

This module asks a small model for a structured reading of the message —
language, what is being asked, the life area, who it is about, whether the
event is wanted or feared, the horizon, safety — validated against fixed menus.
Pure helpers + one async call; main.py owns rollout:

  NLU_MODE=off | shadow (default) | primary
    shadow  — computed in the background and logged next to the keyword result;
              nothing user-facing changes.
    primary — (phase 2) drives language / yes-no offer / KP type / concern.

Hard rules (never relaxed by the model):
  * Safety is an OR: a crisis / gambling flag from EITHER the keyword guards OR
    the model wins. The model can add caution, never remove it.
  * The model never produces a verdict, date or chart fact — it only reads the
    question. Engines answer.
  * Fail-open: any error / timeout / invalid JSON → None and the existing
    keyword path runs unchanged.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from typing import Optional

LANGS = ("en", "es", "pt", "hinglish", "hi", "other")

INTENTS = (
    "yes_no",        # will / should / is it … — a binary answer is wanted
    "when",          # timing: when will…, which day/month…
    "how",           # how is / how will … go
    "why",           # why is this happening / why me
    "what_to_do",    # what should I do / focus on / avoid
    "which",         # choose between options (A or B)
    "where_who",     # where will … come from / who …
    "open",          # anything else that is a real question
    "statement",     # sharing / venting with no question
    "greeting", "thanks", "meta",   # hi · thanks · questions about Antar itself
)

# area → (KP question type or None, Ask concern). One source of truth: a new
# area MUST say how KP and Ask read it. Concerns are ask_consultation.CONCERN_HOUSES
# keys (a test enforces it).
AREAS = {
    "career_job":          ("job_new", "career"),
    "promotion":           ("promotion", "career"),
    "business_venture":    ("gain", "business"),
    "clients_sales":       ("deal_closes", "business"),
    "funding_investment":  ("money", "funding"),
    "income_money":        ("gain", "finance"),
    "debt_owed_money":     ("gain", "finance"),
    "speculation_betting": ("speculation", "speculation"),
    "property":            ("property", "property"),
    "residence_move":      ("residence", "domestic_move"),
    "foreign_travel_visa": ("foreign_travel", "foreign_move"),
    "education_exam":      ("education", "education"),
    "marriage":            ("marriage", "marriage"),
    "new_romance":         ("romance", "love"),
    "existing_relationship": (None, "love"),
    "reunion_ex":          ("reunion", "reconciliation"),
    "separation":          ("loss", "divorce"),
    "business_partnership": (None, "business"),
    "partnership_ending":  ("loss", "business"),
    "children_conception": ("childbirth", "children"),
    "children_wellbeing":  (None, "children"),
    "health_self":         ("recovery", "health"),
    "health_other":        (None, "health"),
    "legal_case":          ("litigation_win", "legal"),
    "lost_item":           ("lost_found", "general"),
    "family":              (None, "general"),
    "purpose_spiritual":   (None, "spiritual"),
    "daily_timing":        (None, "general"),
    "general":             (None, "general"),
}

# how the person sounds in THIS message (drives the opening line, never the verdict)
FEELINGS = ("neutral", "curious", "hopeful", "excited", "worried", "anxious", "stuck",
            "overwhelmed", "sad", "lonely", "frustrated", "ashamed", "grieving", "angry")
STRUGGLING = frozenset({"worried", "anxious", "stuck", "overwhelmed", "sad", "lonely",
                        "frustrated", "ashamed", "grieving", "angry"})

EARNING = ("advisory", "commission", "equity", "salary", "own_operations", "trading",
           "investing", "freelance", "rental", "royalties")
_EARNING_PLAIN = {"advisory": "advisory fees", "commission": "commission", "equity": "equity / sweat equity",
                  "salary": "a salary", "own_operations": "running the operation themselves",
                  "trading": "trading", "investing": "investing their own capital",
                  "freelance": "freelance work", "rental": "rental income", "royalties": "royalties"}

# [profile-updates 2026-10-03] owner: a clear, present-tense statement updates the
# profile. The message itself must carry the status word (a bare "my wife" does
# not prove "married"; questions/hypotheticals never count — see explicit_now).
_EXPLICIT_EVIDENCE = {
    "work": re.compile(
        r"(?i)\b(unemployed|laid off|lost my job|fired|let go|got a (new )?job|new job|started (a|my) "
        r"(job|business|company)|i work (at|for|as|in)|i'?m (a |an )?(student|retired|self.?employed|freelancer)|"
        r"i run (a|my)|i own (a|my)|quit my job|desempleado|sin trabajo|me despidieron|tengo (un )?trabajo|"
        r"desempregad|fui demitid|consegui (um )?emprego|naukri (chali gayi|lag gayi|mil gayi))\b"),
    "relationship": re.compile(
        r"(?i)\b(i'?m|i am|we'?re|we are|i got|we got|we just|i just|i'?ve been|we'?ve been|i have been|"
        r"we have been|i recently|we recently)\b[^.?!]{0,25}\b(married|single|divorced|separated|widow(ed)?|"
        r"engaged|dating|in a relationship|split up|broke up)\b"
        r"|\b(estoy|soy|somos|estamos|nos)\b[^.?!]{0,20}\b(casad[oa]s?|solter[oa]|divorciad[oa]s?|"
        r"separad[oa]s?|viud[oa]|comprometid[oa]s?|casamos|separamos|divorciamos)\b"
        r"|\b(sou|estou|somos|estamos|nos)\b[^.?!]{0,20}\b(casad[oa]s?|solteir[oa]|divorciad[oa]s?|"
        r"separad[oa]s?|viúv[oa]|noiv[oa]s?|namorando)\b"),
    "children": re.compile(
        r"(?i)\b(i|we) (have|has|'?ve got) (a |an |\d+ |one |two |three |four |no )?(kids?|children|"
        r"son|daughter|sons|daughters|baby)\b|\bno (kids|children)\b|\b(tengo|tenemos) (un |una |\d+ |dos |tres )?"
        r"(hij[oa]s?|bebé)\b|\b(tenho|temos) (um |uma |\d+ |dois |duas |três )?(filh[oa]s?|bebê)\b"),
}

_WORK_EV = {
    "unemployed": re.compile(r"(?i)\b(unemployed|jobless|out of work|between jobs|no job|laid off|lost my job|"
                             r"fired|let go|not working|doing nothing|desempleado|sin (trabajo|empleo)|me despidieron|"
                             r"desempregad|sem (trabalho|emprego)|fui demitid|berozgaar|naukri (nahi|chali gayi)|"
                             r"kaam nahi)\b"),
    "employed": re.compile(r"(?i)\b(my (job|boss|manager|employer|office|salary)|i work (at|for|as|in)|"
                           r"got a (new )?job|mi (trabajo|jefe|empleo)|trabajo en|meu (trabalho|chefe|emprego)|"
                           r"trabalho na|meri naukri|mera (boss|office))\b"),
    "self_employed": re.compile(r"(?i)\b(my (own )?(business|startup|company|firm|agency|practice|shop|venture|"
                                r"clients?)|i (run|own|founded|started) (a|an|my)|self.?employed|freelanc\w*|"
                                r"founder|mi (propio )?(negocio|empresa|emprendimiento)|minha (pr[oó]pria )?empresa|"
                                r"meu (pr[oó]prio )?neg[oó]cio|mera (apna )?(business|dhandha))\b"),
    "student": re.compile(r"(?i)\b(i'?m (a )?student|i am (a )?student|my (studies|exams?|college|university|"
                          r"degree)|studying|estudiante|estudio|estudante|estudo|padhai)\b"),
    "retired": re.compile(r"(?i)\b(retired|retiring|jubilad[oa]|aposentad[oa]|retire ho)\b"),
    "homemaker": re.compile(r"(?i)\b(homemaker|housewife|stay.at.home|ama de casa|dona de casa|grihini)\b"),
}
_REL_EV = re.compile(
    r"(?i)\b(married|single|divorced|separated|widow(ed|er)?|engaged|dating|girlfriend|boyfriend|"
    r"my (wife|husband|spouse|fianc[eé]e?|partner)|casad[oa]|solter[oa]|divorciad[oa]|separad[oa]|viud[oa]|"
    r"comprometid[oa]|mi (esposa|esposo|novi[oa]|pareja)|solteir[oa]|vi[uú]v[oa]|noiv[oa]|"
    r"minha (esposa|mulher|namorada)|meu (marido|namorado)|shaadi(shuda)?|meri (wife|biwi|patni)|mere pati)\b")
_KIDS_EV = {
    "yes": re.compile(r"(?i)\b(my (son|daughter|kids?|children|child|baby|boy|girl)|our (son|daughter|kids?|"
                      r"children|baby)|i have (a |\d+ |two |three )?(kids?|children|son|daughter)|"
                      r"mi(s)? (hij[oa]s?|beb[eé])|meu(s)? filh[oa]s?|minha(s)? filha(s)?|"
                      r"mera (beta|bachcha|beti)|meri (beti|bachchi)|mere (bachche|bete))\b"),
    "no": re.compile(r"(?i)\b(no (kids|children)|don'?t have (kids|children)|childless|sin hijos|"
                     r"no tengo hijos|sem filhos|n[aã]o tenho filhos|koi bachcha nahi)\b"),
}

_PAST_WORK_EVIDENCE = re.compile(
    r"(?i)\b(worked as|working as|was (a|an)|used to (be|work)|former(ly)?|previously|"
    r"laid off|fired|let go|my last job|trabajaba|trabaj[eé] como|era (un|una)|trabalhava|"
    r"trabalhei como|pehle .{0,20}(kaam|job))\b")

_EARNING_EVIDENCE = {
    "advisory": re.compile(r"(?i)advis|consult|asesor|assessor|consultor"),
    "commission": re.compile(r"(?i)commis|comisi|comiss"),
    "equity": re.compile(r"(?i)equity|sweat|stake|acciones|participaci|participa[cç][aã]o"),
    "salary": re.compile(r"(?i)salar|sueldo|wage|paycheck|n[oó]mina"),
    "own_operations": re.compile(r"(?i)\b(i|we) (run|own|operate)\b|my own (plant|factory|mine|shop|business)|opero|manejo"),
    "trading": re.compile(r"(?i)\btrad(e|es|ing|er)\b|day.?trad|compraventa|negociar"),
    "investing": re.compile(r"(?i)invest|inversi|investiment"),
    "freelance": re.compile(r"(?i)freelanc|independ|aut[oó]nom"),
    "rental": re.compile(r"(?i)\brent|alquil|aluguel|arriend"),
    "royalties": re.compile(r"(?i)royalt|regal[ií]a"),
}

# [wealth-promise backstop 2026-10-03] live: "which helps me most with wealth
# creation or reaching my maximum potential?" wasn't flagged by the model.
_OUTCOME_Q = re.compile(
    r"(?i)\b(millionaire|billionaire|get rich|become rich|make me rich|wealth creation|create wealth|"
    r"build wealth|maximum potential|max(imum)? potential|most potential|full potential|most money|"
    r"richest|millonari[oa]|hacerme rico|volverme rico|riqueza|m[aá]ximo potencial|"
    r"milion[aá]ri[oa]|ficar rico|maior potencial|crorepati|amir ban)\b")

_OUTCOME_MARKERS = re.compile(
    r"(?i)\b(most|highest|maximum|max|biggest|best.paying|richest|rich|wealthy|millions?|billions?|crore|lakh|"
    r"potential|\d[\d,.]*\s?(k|m|usd|dollars|pesos|rupees)|\$\s?\d|rank|ranking|top|m[aá]s dinero|"
    r"mais dinheiro|sabse zyada)\b")

WORK = ("employed", "unemployed", "self_employed", "student", "retired", "homemaker")
RELATIONSHIP = ("single", "dating", "married", "separated", "divorced", "widowed")

SUBJECTS = ("self", "partner_romantic", "business_partner", "child", "parent",
            "sibling", "friend", "colleague_boss", "other")
POLARITY = ("wanted", "feared", "neutral")

SYSTEM = (
    "You read ONE message sent to an astrology guidance app (WhatsApp or in-app) and "
    "return STRICT JSON only — no prose, no code fences. You never answer the "
    "question and never predict anything; you only describe what is being asked.\n"
    "Schema:\n"
    '{"language": one of ' + json.dumps(list(LANGS)) + ",\n"
    ' "standalone": the message rewritten as a complete, self-contained question in '
    "the SAME language (resolve 'and tomorrow?', 'what about money?' from the recent "
    "turns; fix obvious typos; keep the person's meaning; never add facts),\n"
    ' "intent": one of ' + json.dumps(list(INTENTS)) + ",\n"
    ' "area": one of ' + json.dumps(list(AREAS)) + ",\n"
    ' "subject": one of ' + json.dumps(list(SUBJECTS)) + ",\n"
    ' "polarity": one of ' + json.dumps(list(POLARITY)) + " (feared = the person "
    "asks whether something they do NOT want will happen, e.g. a break-up, a loss, "
    "an illness getting worse),\n"
    ' "horizon_days": integer days the question looks ahead, or null if unstated '
    '("next 60 days" → 60, "this month" → 31, "today" → 1),\n'
    ' "yes_no_fit": true only if a straight yes-or-no answer makes sense for this '
    "exact question,\n"
    ' "crisis": true if the message shows distress, hopelessness, self-harm or '
    "danger,\n"
    ' "gambling": true for betting, lottery, casino, trading/speculation punts,\n'
    ' "needs_clarification": true only if the question cannot be read at all '
    "without one more detail,\n"
    ' "clarify": one short question to ask back (same language) or "",\n'
    ' "confidence": 0.0-1.0 for the area,\n'
    ' "feeling": how the person sounds in this message, one of ' + json.dumps(list(FEELINGS)) + ',\n'
    ' "stated_facts": facts the person STATES about their own life in THIS message '
    '(never infer, never guess): {"work": one of ' + json.dumps(list(WORK)) + ' or null, '
    '"relationship": one of ' + json.dumps(list(RELATIONSHIP)) + ' or null, '
    '"children": "yes" | "no" | null, "other": up to 3 short plain facts they said '
    '(e.g. "has debt", "recently laid off", "caring for a sick parent") or [], '
    '"earning": how THEY say they earn or would earn from the work in question, a list '
    'from ' + json.dumps(list(EARNING)) + ' or [] (e.g. "advisory + commission + sweat '
    'equity" → ["advisory","commission","equity"]; never guess), '
    '"past_work": the job/field they SAY they did before, in their words (e.g. "finance / '
    'bookkeeping manager"), or null, '
    '"explicit_now": which of ["work","relationship","children"] they EXPLICITLY state as their '
    'CURRENT situation in this message ("I\'m married now", "I was laid off", "we separated", '
    '"I just got a job") — never for questions or hypotheticals ("will I get married?")},\n'
    ' "outcome_claim": true if they ask the reading to promise a wealth level or rank '
    'options by how much money / potential / success they will bring (e.g. "will it make me '
    'a millionaire", "which work gives me the most potential", "which will make me rich"),\n'
    ' "options": the distinct options they are choosing between, as short labels in '
    'their words (e.g. ["gold mine deals", "defence contracts", "real estate"]) — [] if '
    'they are not comparing options}\n'
    "Rules: language = the language the message is WRITTEN in (English that mentions "
    "India is English; Hinglish = Hindi words in Latin script). A question about a "
    "partnership BREAKING, ending, splitting or a partner leaving is partnership_ending "
    "(business) or separation (romantic) — not business_partnership. A girlfriend/boyfriend is "
    "new_romance or existing_relationship. 'Move forward in life' is purpose, a "
    "house move is residence_move. Use general ONLY when nothing else fits. JSON only."
)


def _clean_enum(v, allowed, default):
    v = str(v or "").strip().lower()
    return v if v in allowed else default


def parse(raw: str, original: str = "") -> Optional[dict]:
    """Strict parse + menu validation. Any structural failure → None."""
    try:
        raw = (raw or "").strip()
        obj = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
    except Exception:
        return None
    if not isinstance(obj, dict):
        return None
    area = str(obj.get("area") or "").strip().lower()
    if area not in AREAS:
        return None
    hz = obj.get("horizon_days")
    try:
        hz = int(hz) if hz is not None and str(hz).strip().lower() not in ("", "null") else None
        hz = hz if hz is None or 1 <= hz <= 3650 else None
    except (TypeError, ValueError):
        hz = None
    standalone = str(obj.get("standalone") or "").strip() or original
    if len(standalone) > 600:
        standalone = original
    try:
        conf = max(0.0, min(1.0, float(obj.get("confidence") or 0.0)))
    except (TypeError, ValueError):
        conf = 0.0
    polarity = _clean_enum(obj.get("polarity"), POLARITY, "neutral")
    # A FEARED event inside a partnership / relationship is its ending (the model
    # reliably marks "will my partnership break" feared but files the area as the
    # partnership itself).
    if polarity == "feared":
        area = {"business_partnership": "partnership_ending",
                "existing_relationship": "separation"}.get(area, area)
    sf = obj.get("stated_facts") if isinstance(obj.get("stated_facts"), dict) else {}
    other = sf.get("other") if isinstance(sf.get("other"), list) else []
    # [stated-evidence 2026-10-03] a stated fact counts only if the message says it
    # (live eval: "¿Cuándo voy a conseguir trabajo estable?" → work=unemployed;
    # "talk to my ex again" → relationship=single; "meu sócio… da empresa" →
    # self_employed — all guesses that would have reached the profile/narrator).
    _w = _clean_enum(sf.get("work"), WORK, None) if sf.get("work") else None
    _r = _clean_enum(sf.get("relationship"), RELATIONSHIP, None) if sf.get("relationship") else None
    _c = str(sf.get("children")).lower() if str(sf.get("children")).lower() in ("yes", "no") else None
    facts = {
        "work": _w if (_w and _WORK_EV.get(_w) and _WORK_EV[_w].search(original or "")) else None,
        "relationship": _r if (_r and _REL_EV.search(original or "")) else None,
        "children": _c if (_c and _KIDS_EV[_c].search(original or "")) else None,
        "other": [str(x).strip()[:80] for x in other if str(x).strip()][:3],
        # an earning type counts only if the message itself says it (live: the
        # model "stated" trading for "Gold or defence?" — never said)
        "earning": [e for e in (str(x).strip().lower() for x in (sf.get("earning") or [])
                                if isinstance(sf.get("earning"), list))
                    if e in EARNING and _EARNING_EVIDENCE[e].search(original or "")][:4],
    }
    ex = sf.get("explicit_now") if isinstance(sf.get("explicit_now"), list) else []
    # evidence must sit in a sentence that is NOT a question
    # [question-forms] the shared EN/ES/PT/Hinglish lexicon decides "is this a question?"
    from antar_engine import question_forms as _qf
    _stmts = " ".join(m.group(0) for m in re.finditer(r"[^.!?]+[.!?]?", original or "")
                      if not _qf.is_question(m.group(0)))
    facts["explicit_now"] = [f for f in ("work", "relationship", "children")
                             if f in [str(x).lower() for x in ex] and _EXPLICIT_EVIDENCE[f].search(_stmts)]
    pw = str(sf.get("past_work") or "").strip()[:60]
    facts["past_work"] = pw if (pw and _PAST_WORK_EVIDENCE.search(original or "")) else None
    opts = obj.get("options") if isinstance(obj.get("options"), list) else []
    options = [str(o).strip()[:60] for o in opts if str(o).strip()][:5]
    # [question-forms 2026-10-03] a clear open question word decides the intent
    # when the model gave the vaguer what_to_do / open (live check: "How is my
    # income looking?" / "¿Cómo va mi deuda?" / "Where will … take me?" → what_to_do).
    _intent = _clean_enum(obj.get("intent"), INTENTS, "open")
    try:
        from antar_engine import question_forms as _qf
        _lex = _qf.intent(original or "")
        if _lex in ("when", "how", "why", "where_who") and _intent in ("what_to_do", "open"):
            _intent = _lex
    except Exception:
        pass
    return {
        "has_choice": bool(_CHOICE_RX.search(original or "")),
        # the model's flag counts only when the wording really asks for an amount or a ranking
        # (audit r6: "Will I make good money doing deals with…" is an ordinary yes/no, but the
        # model called it a wealth promise and the verdict was suppressed)
        "outcome_claim": bool(_OUTCOME_Q.search(original or "")) or (
            bool(obj.get("outcome_claim")) and bool(_OUTCOME_MARKERS.search(original or ""))),
        "options": options,
        "feeling": _clean_enum(obj.get("feeling"), FEELINGS, "neutral"),
        "stated_facts": facts,
        "language": _clean_enum(obj.get("language"), LANGS, "other"),
        "standalone": standalone,
        "intent": _intent,
        "area": area,
        "subject": _clean_enum(obj.get("subject"), SUBJECTS, "self"),
        "polarity": polarity,
        "horizon_days": hz,
        "yes_no_fit": bool(obj.get("yes_no_fit")),
        "crisis": bool(obj.get("crisis")),
        "gambling": bool(obj.get("gambling")),
        "needs_clarification": bool(obj.get("needs_clarification")),
        "clarify": str(obj.get("clarify") or "").strip()[:200],
        "confidence": conf,
    }


def kp_type(u: Optional[dict]) -> Optional[str]:
    """The KP Prashna question type this understanding maps to (None = KP has no
    specific reading for it → never offer a yes/no)."""
    return AREAS.get((u or {}).get("area"), (None, None))[0]


def concern(u: Optional[dict]) -> Optional[str]:
    return AREAS.get((u or {}).get("area"), (None, None))[1]


def safety(u: Optional[dict], keyword_crisis: bool, keyword_gambling: bool) -> dict:
    """OR of model and keyword guards — the model can only add caution."""
    u = u or {}
    return {"crisis": bool(keyword_crisis or u.get("crisis")),
            "gambling": bool(keyword_gambling or u.get("gambling"))}


def request(message: str, thread: list, saved_lang: str = "") -> str:
    """User turn for the model: the last turns (for follow-ups) + the message."""
    lines = []
    for t in (thread or [])[-2:]:
        q = str((t or {}).get("question") or "").strip()
        a = str((t or {}).get("answer") or (t or {}).get("plain_summary") or "").strip()
        if q:
            lines.append(f"Earlier question: {q[:200]}")
        if a:
            lines.append(f"Earlier answer: {a[:240]}")
    if saved_lang:
        lines.append(f"(Their app language setting: {saved_lang} — use it only if the "
                     "message itself gives no language.)")
    lines.append(f"Message: {message.strip()[:600]}")
    return "\n".join(lines)


# per-worker memo: the same message + thread is read once (WhatsApp retries,
# replays, the choice step re-asking the same question)
_MEMO: dict = {}
_MEMO_TTL_S = 900
_MEMO_MAX = 2000


def memo_key(message: str, thread: list, saved_lang: str = "") -> str:
    tail = "|".join(str((t or {}).get("question") or "") for t in (thread or [])[-2:])
    return hashlib.sha1(f"{message.strip().lower()}§{tail}§{saved_lang}".encode()).hexdigest()


def memo_get(k: str) -> Optional[dict]:
    hit = _MEMO.get(k)
    if hit and time.time() - hit[0] < _MEMO_TTL_S:
        return hit[1]
    return None


def memo_put(k: str, u: dict) -> None:
    if len(_MEMO) >= _MEMO_MAX:
        for old in sorted(_MEMO, key=lambda x: _MEMO[x][0])[: _MEMO_MAX // 4]:
            _MEMO.pop(old, None)
    _MEMO[k] = (time.time(), u)


def compare(u: Optional[dict], kw: dict) -> dict:
    """Shadow diff: what the model read vs what the keyword path decided."""
    u = u or {}
    out = {}
    for f in ("language", "kp_type", "concern", "yes_no", "gambling", "crisis"):
        mv = {"kp_type": kp_type(u), "concern": concern(u),
              "yes_no": u.get("yes_no_fit"), "language": u.get("language"),
              "gambling": u.get("gambling"), "crisis": u.get("crisis")}[f]
        kv = kw.get(f)
        out[f] = {"model": mv, "keyword": kv, "agree": mv == kv}
    return out


_WORD = re.compile(r"\w+")


def worth_reading(message: str) -> bool:
    """Skip the model for bare numbers / single command words."""
    w = _WORD.findall(message or "")
    return len(w) >= 2 or (len(w) == 1 and not w[0].isdigit() and len(w[0]) > 3)


# ── stated life facts → narrator constraints ─────────────────────────────────
# [life-facts-in-answer 2026-10-03] live: "I am unemployed… how do I get over
# this hurdle?" was answered "a new role fits better than waiting for a promotion
# that isn't coming". What the person says in THIS message outranks the stored
# profile for this answer.
_WORK_RULE = {
    "unemployed": ("The reader is currently UNEMPLOYED (they said so). NEVER mention a "
                   "promotion, raise, appraisal, boss, manager, colleagues or 'your current "
                   "job'. Career = finding the next role or path, from where they are now."),
    "student": ("The reader is a STUDENT (they said so). No boss, promotion or salary as a "
                "present fact — frame work as studies, first roles and skills."),
    "retired": ("The reader is RETIRED (they said so). No boss, promotion or job hunt "
                "unless they ask — frame work as purpose, projects or advisory."),
    "self_employed": ("The reader is SELF-EMPLOYED / runs a business (they said so). Never "
                      "write boss, manager, employer or promotion."),
    "homemaker": ("The reader runs the home (they said so). No boss or promotion as a "
                  "present fact."),
    "employed": None,
}
_REL_RULE = {
    "single": "The reader is SINGLE (they said so) — no 'your partner/spouse' as a present fact.",
    "divorced": "The reader is DIVORCED (they said so) — no 'your spouse' as a present fact.",
    "separated": "The reader is SEPARATED (they said so) — no 'your spouse' as a settled present fact.",
    "widowed": "The reader is WIDOWED (they said so) — never refer to a living spouse; be gentle.",
}


def stated_block(u: Optional[dict]) -> str:
    """Prompt block: what the person told us in this message. '' when nothing."""
    f = (u or {}).get("stated_facts") or {}
    lines = []
    w = _WORK_RULE.get(f.get("work") or "")
    if w:
        lines.append("- " + w)
    r = _REL_RULE.get(f.get("relationship") or "")
    if r:
        lines.append("- " + r)
    if f.get("children") == "no":
        lines.append("- The reader has NO children (they said so) — never mention 'your child'.")
    for o in f.get("other") or []:
        lines.append(f"- They told you: {o}.")
    if not lines:
        return ""
    return ("\n\nWHAT THEY TOLD YOU IN THIS MESSAGE — this outranks anything else you "
            "know about them. Answer the person in front of you; acknowledge their "
            "situation; NEVER write anything that contradicts it:\n" + "\n".join(lines))


# stated facts → chart columns (written only into EMPTY fields, see profile_harvest)
WORK_TO_CAREER_STAGE = {"unemployed": "seeking", "self_employed": "running_business",
                        "student": "studying", "employed": "employed"}


def life_overrides(u: Optional[dict]) -> dict:
    """Overrides for life_context.resolve_life_facts() output for THIS answer."""
    f = (u or {}).get("stated_facts") or {}
    out = {}
    w = f.get("work")
    if w in ("unemployed", "student", "retired", "self_employed", "homemaker"):
        out["employed"] = False
    elif w == "employed":
        out["employed"] = True
    r = f.get("relationship")
    if r in ("single", "divorced", "separated", "widowed"):
        out["partnered"] = False
    elif r in ("married", "dating"):
        out["partnered"] = True
    if f.get("children") in ("yes", "no"):
        out["has_children"] = f["children"] == "yes"
    return out


# ── warm opening (owner 2026-10-03) ─────────────────────────────────────────
# Same question, two answers: "Harleen, this paralysis is real — but it's not
# permanent." (lands) vs "Harleen, this freeze is costing you savings you can't
# afford to lose right now." (blames). When someone sounds like they're
# struggling, the first line meets them before the reading starts.
def tone_block(u: Optional[dict]) -> str:
    """Narrator instruction for the opening line; '' unless the person sounds
    like they are struggling. Never changes the verdict, dates or advice."""
    f = (u or {}).get("feeling")
    if f not in STRUGGLING:
        return ""
    return ("\n\nOPENING LINE — they sound " + f + ". Start the answer with ONE short, warm "
            "sentence that names what they are going through in plain words and gives "
            "steady hope (e.g. \"this paralysis is real — but it's not permanent.\"). "
            "Never open with blame, cost, fear or a warning (NOT \"this is costing you…\", "
            "NOT \"you can't afford…\"). Be honest after that — the reading, timing and "
            "the one move stay exactly as they are. No pity, no therapy-speak, one sentence.")


# ── comparisons + how they earn (owner 2026-10-03) ──────────────────────────
# Live: "Gold or defence — which should I focus on?" → "Defence is the stronger
# bet… Gold is a store of value, not a business-builder" — a winner the chart
# can't support (business-vertical study: no better than chance), reasoned from a
# deal structure he never stated (his gold work is advisory + commission + sweat
# equity, the SAME role as his defence and real-estate deals).
_CHOICE_RX = re.compile(
    r"(?i)\b(or|vs\.?|versus|either|better|which|whether|ou|ya|ya phir|between|entre|cu[aá]l|qual|quais|"
    r"kaun(?:sa|si)?)\b|¿[^?]*\bo\b")


def is_comparison(u: Optional[dict]) -> bool:
    """A choice between options. [audit r6] Listing several things ('deals with a gold mine,
    a processing plant and a refinery') is NOT a choice — it needs an or/vs/which/better
    marker, else 'Will I make good money doing X, Y and Z?' lost its Yes/Not-yet answer."""
    u = u or {}
    return u.get("intent") == "which" or (len(u.get("options") or []) >= 2 and bool(u.get("has_choice")))


def earning_text(earning: list) -> str:
    return " + ".join(_EARNING_PLAIN.get(e, e) for e in (earning or []))


def comparison_block(u: Optional[dict], known_earning: str = "", fit_fields: Optional[list] = None,
                     profession: str = "") -> str:
    """Narrator rules for a choose-between question. '' when not a comparison."""
    if not is_comparison(u):
        return ""
    opts = (u or {}).get("options") or []
    told = earning_text(((u or {}).get("stated_facts") or {}).get("earning") or []) or known_earning
    lines = [
        "\n\nCOMPARISON — they are weighing: " + ("; ".join(opts) if opts else "options") + ".",
        "- Do NOT open with Yes/No. Do NOT name a winner, and never say one will make more "
        "money or is 'the stronger bet' — the reading cannot rank industries or sectors.",
        "- Compare ONLY on: (a) the ROLE they would play in each, (b) their TIMING window, "
        "(c) practical risks to check (their capital at risk, how long until they get paid, "
        "price swings, counterparties) — as things to check, not predictions.",
        "- If the role is the same in every option, say so plainly: the reading backs that "
        "role and their timing, not one industry.",
        "- If the options are FIELDS of work or study for THEM (e.g. accounting vs something new, "
        "finance vs law), DO say which fits their nature better, using the fields the reading favours "
        "— framed as fit, never as earnings.",
        "- If the options are about SOMEONE ELSE (a child's course, a partner's job), say plainly this is "
        "THEIR reading, not the other person's, so it can't pick for them; then give 2-3 concrete ways "
        "to decide (the other person's own interest, aptitude, a trial/visit).",
        "- If the options are INVESTMENTS (crypto, gold, stocks, property as an investment), say plainly "
        "you don't advise where to put money; give only timing and caution from the reading.",
        "- You may say one option suits their way of working better ONLY if their role "
        "really differs between the options, and say why in one sentence.",
        "- NEVER assume how a deal is structured or how they earn from it (no 'trading', "
        "'investing', 'owning' unless they said so). If you don't know their role, say 'your "
        "role in these deals'. If knowing it would change the answer, end with ONE short "
        "question asking it.",
        "- Close with how to decide: the deal closest to signing, with the shortest path to "
        "their pay and the least of their own money at risk.",
    ]
    if told:
        lines.insert(1, f"- How they earn (they told you): {told}. Use exactly this; never replace it.")
    if fit_fields:
        # deterministic match: which option names one of their top fields?
        _hits = []
        for o in opts:
            ow = set(re.findall(r"[a-z]{4,}", o.lower()))
            for i, f in enumerate(fit_fields):
                if ow & set(re.findall(r"[a-z]{4,}", f.lower())):
                    _hits.append((i, o))
                    break
        if _hits and len({o for _, o in _hits}) < len(opts):
            best = sorted(_hits)[0]
            lines.append(f"- MATCH: the option \"{best[1]}\" matches their #{best[0] + 1} field "
                         f"(\"{fit_fields[best[0]]}\"). Say plainly that it fits their nature better and "
                         "why, in the FIRST sentence — fit, not earnings.")
        prof = (profession or "").strip()
        lines.append(
            "- The reading's strongest fields for them: " + ", ".join(fit_fields)
            + (f" (their profile says: {prof})" if prof and not prof.lower().startswith("earns via") else "")
            + ". If one option clearly matches these or the work they already do, and their ROLE would "
            "differ between the options (e.g. building as a founder vs earning commission as a broker), "
            "say plainly that it fits their nature better and why — fit, never earnings.")
    return "\n".join(lines)


EARNS_PREFIX = "Earns via "


def stored_earning(profession: str) -> str:
    p = (profession or "").strip()
    return p[len(EARNS_PREFIX):].strip() if p.lower().startswith(EARNS_PREFIX.lower()) else ""


def past_work_line(life_work: str) -> str:
    lw = (life_work or "").strip()
    if not lw.lower().startswith("formerly"):
        return ""
    return "\n- Their work history (they told you earlier): " + lw + "."


def earning_line(profession: str) -> str:
    """Life-block line from what they told us earlier (stored on the chart)."""
    e = stored_earning(profession)
    if not e:
        return ""
    return ("\n- How they earn (they told you earlier): " + e
            + ". Never assume a different deal structure.")


def outcome_block(u: Optional[dict]) -> str:
    """[ask-outcome-honesty] Wealth level / 'most potential' can't be read (D-2 wealth
    study and business-vertical study both failed) — say so once, then help."""
    if not (u or {}).get("outcome_claim"):
        return ""
    return ("\n\nWEALTH / POTENTIAL — they asked the reading to promise a wealth level or "
            "rank options by how much they will make. In ONE plain sentence, say the reading "
            "can't honestly promise an amount ('millionaire') or say which field earns most. "
            "Then give what it CAN: how the work fits their nature and way of working, their "
            "timing window, and how to approach it to give it the best chance. Never use "
            "words like 'millionaire', 'rich', 'most potential' as a promise or a ranking.")


# [no-invented-role 2026-10-03] Even with the rule, a comparison answer said
# "your trading role" for someone who never said he trades (Andres: advisory +
# commission + sweat equity). When we don't know how they earn, a role the
# model named is replaced with a neutral one. Known/stated roles are untouched.
_ROLE_WORDS = r"(?:trading|trader|investing|investor|ownership|owner|operating|operator|broker(?:ing)?|dealer)"
def role_phrase(known: str) -> str:
    """'your role as an advisor earning commission and equity' from the stored /
    stated earning text; '' when unknown."""
    k = (known or "").lower()
    if not k:
        return ""
    earn = [w for w, key in (("commission", "commission"), ("equity", "equity"), ("fees", "fees"))
            if key in k]
    if "advisory" in k:
        tail = [w for w in earn if w != "fees"]
        return "your role as an advisor" + (" earning " + " and ".join(tail) if tail else "")
    return f"your role ({known.strip()})"


_INVENTED_ROLE = [
    re.compile(r"\b[Yy]our role as an? " + _ROLE_WORDS + r"\b"),
    re.compile(r"\b[Yy]our " + _ROLE_WORDS + r" role\b"),
    re.compile(r"\b[Aa]s an? " + _ROLE_WORDS + r"\b"),
]


def scrub_invented_role(text, known: str = ""):
    """Replace a role they never stated ('your trading role') with the one they DID
    state ('your role as an advisor earning commission and equity'), or with a
    neutral 'your role in these deals' when we don't know how they earn."""
    if not isinstance(text, str) or not text:
        return text
    real = role_phrase(known if isinstance(known, str) else "")

    def _sub(m, neutral):
        rep = real or neutral
        return rep[0].upper() + rep[1:] if m.group(0)[0].isupper() else rep
    text = _INVENTED_ROLE[0].sub(lambda m: _sub(m, "your role"), text)
    text = _INVENTED_ROLE[1].sub(lambda m: _sub(m, "your role in these deals"), text)
    text = _INVENTED_ROLE[2].sub(lambda m: _sub(m, "in your role").replace(
        "Your role as", "In your role as").replace("your role as", "in your role as")
        if real else _sub(m, "in your role"), text)
    return text
    for rx, rep in _INVENTED_ROLE:
        text = rx.sub(rep, text)
    return text


# ── answer guardrails (owner 2026-10-03, Raman's chart) ─────────────────────
# Live answers: "Put your savings into a few different tech companies" (investment
# advice), "Defense and gold mining need lots of physical work and careful
# cost-cutting" (an invented claim about an industry), "Since you don't have much
# extra money saved up" (a chart inference stated as a fact about their life).
def guardrails_block() -> str:
    """Always-on narrator rules for the explore answer."""
    return ("\n\nNEVER IN AN ANSWER:\n"
            "- Never tell them where to put savings or money (no 'invest in', 'put your savings "
            "into', 'diversify across companies/funds/stocks/crypto/property'). You may talk about "
            "protecting a cushion or capping what rides on one venture — never where to invest.\n"
            "- Never describe what an industry or option demands (physical work, cost-cutting, "
            "capital, regulation, connections) unless they said it. Speak about THEIR role, fit "
            "and timing only.\n"
            "- Never state their money situation as a fact ('you don't have much saved', 'you have "
            "debt') unless they told you. Say what the reading shows: 'the reading shows pressure "
            "on savings'.\n"
            "- Loans and debts: mention them ONLY when the question is about money, and never as a "
            "fact they have one (no 'your loan', 'existing debt', 'debt repayments') unless they told "
            "you. For career, business-launch, relationship or other questions, leave loans out.\n"
            "- Never state what OTHER people are like or are going through as fact (a brother's reliability, a "
            "child 'in trouble', a partner's behaviour, 'you are far from family'). Say only what the reading "
            "shows about THEM and the situation.\n"
            "- Never name what a legal matter is about (fraud, manipulation, tax, regulation, a contract) "
            "unless they said it.\n"
            "- Never invent their past: no 'your finance years', 'your old company', 'when you "
            "worked in…' unless they told you. Fields the reading favours are possibilities, not "
            "their history.")


_INVEST_SENT = re.compile(
    r"(?i)\b(put|invest|move|park|allocate|split|spread|place)\b[^.!?]{0,30}\b(your |the )?"
    r"(savings|money|capital|funds|cash|portfolio)\b[^.!?]{0,40}\b(in|into|across|between|among)\b"
    r"[^.!?]{0,40}\b(compan(y|ies)|stocks?|shares|funds?|crypto|bonds?|gold|real estate|propert(y|ies)|"
    r"startups?|ventures|assets)\b"
    r"|\bdiversif\w*\b[^.!?]{0,30}\b(savings|investments?|portfolio|money|capital)\b")

_FIN_FACT = [
    (re.compile(r"(?i)\b(since|because|as) you (don't|do not|didn't) have (much |enough |a lot of )?(extra )?"
                r"(money|savings|cash)( saved( up)?)?\b"), "since the reading shows pressure on your savings"),
    (re.compile(r"(?i)\byou (don't|do not) have (much |enough |a lot of )?(extra )?(money|savings|cash)"
                r"( saved( up)?)?\b"), "the reading shows pressure on your savings"),
    (re.compile(r"(?i)\byou have (a lot of |some |heavy )?debts?\b"), "the reading shows loan pressure"),
    # [audit 2026-10-03] "the loan you took", "your loan", "a loan or debt situation…"
    (re.compile(r"(?i)\bthe loans? you (took|have|got|are paying)\b"), "any loan pressure the reading shows"),
    (re.compile(r"(?i)\ba loan or debt situation\b"), "the loan pressure the reading shows"),
    (re.compile(r"(?i)\byou owe (money )?on (a|the|your) loans?\b"), "the reading shows loan pressure"),
    (re.compile(r"(?i)\byou owe money\b"), "the reading shows loan pressure"),
    (re.compile(r"(?i)\b(a|your|the) live loan burden\b"), "the loan pressure the reading shows"),
    # [audit round 5 2026-10-03] loans/debts asserted as existing — EN / ES / PT
    (re.compile(r"(?i)\b(the |your )?debt (repayments?|service)( payments?)?\b"), "the loan pressure the reading shows"),
    (re.compile(r"(?i)\b(an? |your |any )?existing (loans?|debts?)\b"), "the loan pressure the reading shows"),
    (re.compile(r"(?i)\b(un |el |tu |tus )?pr[eé]stamos? (existentes?|vigentes?|actuales?)\b"),
     "la presión de préstamos que muestra la lectura"),
    (re.compile(r"(?i)\b(una |la |tu )?(carga de )?deudas? (vigentes?|pendientes?|existentes?|actuales?)\b"),
     "la presión de deudas que muestra la lectura"),
    (re.compile(r"(?i)\btus t[eé]rminos de pr[eé]stamo( actuales)?\b"), "cualquier presión de préstamos que muestre la lectura"),
    (re.compile(r"(?i)\b(um |o |seu |seus )?empr[eé]stimos? (existentes?|atuais?|vigentes?)\b"),
     "a pressão de empréstimos que a leitura mostra"),
    (re.compile(r"(?i)\b(as |suas |uma )?d[ií]vidas? (existentes?|atuais?|pendentes?|vigentes?)\b"),
     "a pressão de dívidas que a leitura mostra"),
    (re.compile(r"(?i)\byour debt\b"), "loan pressure in the reading"),
]
_FIN_WORDS = re.compile(r"(?i)sav(e|ing|ings)|debt|loan|owe|broke|deud|pr[eé]stamo|ahorro|d[ií]vida|empr[eé]stimo|poupan|karz|udhaar")


def _sentences(t: str) -> list:
    return [x for x in re.split(r"(?<=[.!?])\s+", (t or "").strip()) if x.strip()]


_WORKPLACE = re.compile(r"(?i)\byour (boss|manager|employer|colleagues|co-?workers|team lead)"
                        r"(?:,? and (?:your )?(boss|manager|colleagues|co-?workers))?\b")
_JOB_ONLY_SENT = re.compile(r"(?i)\b(promotion|pay rise|a raise|appraisal|your current job|your current role)\b")
NOT_EMPLOYED_STAGES = frozenset({"between_jobs", "seeking", "unemployed"})


def not_employed(u: Optional[dict], career_stage: str = "") -> bool:
    """Known to be out of work: stated in this message, or the profile says so."""
    w = (((u or {}).get("stated_facts") or {}).get("work") or "")
    return w == "unemployed" or (career_stage or "").strip().lower() in NOT_EMPLOYED_STAGES


_PARENT_GAINS = re.compile(
    r"(?i)\b(some of )?(your )?(gains|good fortune|fortune|success|money|income|luck)( have| has)? "
    r"(come|came|flowed|flow|arrived|arrive)s? (through|from) (him|her|them|your (?:father|mother|dad|mom|parents?))\b")
_AT_YOUR_JOB = re.compile(r"(?i)\b(at|in|from) your (?:[a-z]+ ){0,3}(job|role|company|office|workplace)\b")


def _parent_gains(m):
    who = m.group(7).lower()
    poss = {"him": "his", "her": "her", "them": "their"}.get(who, who + "'s" if not who.endswith("s") else who + "'")
    return f"{poss} backing tends to help {m.group(2) or ''}{m.group(3)}".replace("  ", " ")


def guard_answer(text, question: str = "", options: Optional[list] = None,
                 unemployed: bool = False, known_background: str = ""):
    """Deterministic backstop for the rules above. Drops investment-advice and
    invented-industry sentences; rewrites stated-as-fact finances (unless the
    person mentioned their money). Never empties an answer."""
    if not isinstance(text, str) or not text.strip():
        return text
    opt_rx = None
    words = [w for o in (options or []) for w in re.findall(r"[A-Za-z\u00C0-\u00FF]{4,}", o or "")]
    if words:
        opt_rx = re.compile(r"(?i)\b(" + "|".join(sorted(set(map(re.escape, words)))) + r")\b[^.!?]{0,60}"
                            r"\b(needs?|requires?|demands?|involves?|relies on|rely on|depends? on)\b")
    kept = []
    for snt in _sentences(text):
        if _INVEST_SENT.search(snt):
            continue
        if unemployed and _JOB_ONLY_SENT.search(snt):
            continue
        if opt_rx and opt_rx.search(snt):
            continue
        kept.append(snt)
    out = " ".join(kept).strip() if kept else text
    # [audit r6] "some of your gains have come through him" — a past fact about a parent the
    # reading cannot know; the reading shows a tendency, not a history
    out = _PARENT_GAINS.sub(_parent_gains, out)
    if unemployed:
        out = _AT_YOUR_JOB.sub("in your field", out)
        # [between-jobs 2026-10-03] live: "a specialist your boss and colleagues come to"
        out = _WORKPLACE.sub(lambda m: "People" if m.group(0)[0].isupper() else "people", out)
        if not re.search(r"(?i)laid off|fired|let go|despid|demitid|layoff",
                         (question or "") + " " + (known_background or "")):
            out = re.sub(r"(?i)\b(being|getting) (laid off|let go|fired)\b",
                         lambda m: ("Being" if m.group(0)[0].isupper() else "being") + " between jobs", out)
    if not _FIN_WORDS.search(question or ""):
        for rx, rep in _FIN_FACT:
            out = rx.sub(lambda m, r=rep: (r[0].upper() + r[1:]) if m.group(0)[0].isupper() else r, out)
    return out


# [audit r7 2026-10-04] business / loan / savings pressure is real for this person, but it
# bled into health, marriage, exam and old-age answers ("loan aur business ka stress bhi
# body pe load dalta hai"). On a topic that isn't about work or money, those sentences go.
_MONEY_TOPIC_AREAS = frozenset({
    "career_job", "promotion", "business_venture", "clients_sales", "funding_investment",
    "income_money", "debt_owed_money", "speculation_betting", "property", "business_partnership",
    "partnership_ending", "daily_timing", "general"})
_BIZ_PRESSURE = re.compile(
    r"(?i)\b(business(es)?|loans?|debts?|savings?|cash ?flow|money pressure|financial (stress|pressure|strain)|"
    r"negocio|neg[oó]cio|pr[eé]stamos?|empr[eé]stimos?|deudas?|d[ií]vidas?|ahorros?|poupan[cç]a|"
    r"dinero|dinheiro|karz|udhaar|paisa|paise|dhandha|vyapar)\b")


_RELATIONSHIP_AREAS = frozenset({"marriage", "new_romance", "existing_relationship", "reunion_ex",
                                 "separation", "children_conception", "children_wellbeing"})
_DEAL_TALK = re.compile(
    r"(?i)\b(partnership agreements?|business partner\w*|deals?|commercial|contracts?|asociaci[oó]n comercial|"
    r"acuerdo|socio\w*|parceria|neg[oó]cio|sociedade|saajhedari|sauda)\b")


def drop_off_topic_pressure(text, area: str = "", question: str = ""):
    """Drops business/loan/savings sentences from answers about non-money topics, unless
    the person's own question brought money up. Never empties the text."""
    if not isinstance(text, str) or not text.strip() or not area or area in _MONEY_TOPIC_AREAS:
        return text
    if _BIZ_PRESSURE.search(question or "") or _FIN_WORDS.search(question or ""):
        return text
    rxs = [_BIZ_PRESSURE]
    if area in _RELATIONSHIP_AREAS and not _DEAL_TALK.search(question or ""):
        # the 7th-house partner signal reads as "business partnership" — a personal relationship
        # question must not be answered with deals and agreements
        rxs.append(_DEAL_TALK)
    if (area in ("separation", "existing_relationship") and not _NEW_RELATIONSHIP_Q.search(question or "")
            and not _DEAL_TALK.search(question or "")):
        rxs.append(_NEW_PARTNER_TALK)
    kept = [x for x in _sentences(text) if not any(r.search(x) for r in rxs)]
    return " ".join(kept).strip() if kept else text


_NEW_RELATIONSHIP_Q = re.compile(
    r"(?i)\b(re-?marry|new (partner|relationship|love|girlfriend|boyfriend|wife|husband)|another (partner|relationship)|"
    r"meet (someone|a partner)|find (love|a partner)|dobara shaadi|nayi shaadi|nueva pareja|nuevo amor|"
    r"volver a casarme|novo parceiro|novo amor|casar de novo)\b")


def separation_question(u: Optional[dict], question: str = "") -> bool:
    """A question about a separation / divorce itself (not about a new relationship)."""
    return (u or {}).get("area") == "separation" and not _NEW_RELATIONSHIP_Q.search(question or "")


def separation_block() -> str:
    return ("\n\nSEPARATION / DIVORCE — the question is about the separation ITSELF.\n"
            "- Speak to how it is going for them: the strain, what steadies it, and one concrete, human step "
            "(a conversation, a boundary, leaning on someone they trust, rest).\n"
            "- Do NOT assume legal proceedings, a settlement, papers, a lawyer, a shared home or assets — they "
            "did not mention any. Only if THEY raise legal papers may you point to a professional.\n"
            "- Do NOT talk about a new partner, a new relationship, a 'partnership chapter', deals or business. "
            "Do NOT give a date window for a 'next partnership'. No Yes / Not-yet verdict line.\n"
            "- Never predict the outcome of legal proceedings; the reading speaks to the emotional and "
            "practical season, not the court result.")


_NEW_PARTNER_TALK = re.compile(
    r"(?i)\b((new|future|next|potential|fresh) (partnership|partner|relationship|romance|chapter in love)|"
    r"partnership (chapter|transition|window)|a (new )?partnership|"
    r"(nueva|futura|pr[oó]xima) (pareja|relaci[oó]n|asociaci[oó]n)|(nova|futura|pr[oó]xima) (parceria|relaci[oó]n|rela[cç][aã]o)|"
    r"(naya|nayi|nai|future) (partner|partnership|rishta)|naye (partner|rishte)|"
    r"(novo|nuevo|new|naya) (v[ií]nculo|bond|relacionamento|bandhan)|promessa de um novo|"
    r"promise of a new)\b")

# loans / outside capital / credit asserted as part of the person's situation
_ASSERTED_LOAN = re.compile(
    r"(?i)(\bloans? or (credit|capital)\b|\b(loan|credit) (terms|or payment terms|payments?)\b|"
    r"\bnot (a )?loans? or (external )?capital\b|\b(external|outside) capital as a last resort\b|"
    r"\btermos d[eo] empr[eé]stimo|\bempr[eé]stimo ou (capital|pagamento)|\bnão (um )?empr[eé]stimo|"
    r"\bpr[eé]stamo o (capital|pago)|\bcapital externo\b|"
    # [audit r10] any loan wording, EN / ES / PT, when nobody raised money
    r"\bloans?\b|\bempr[eé]stimos?\b|\bpr[eé]stamos?\b)")
_LOAN_CLAUSE = re.compile(
    r"(?i)(?:\s*(?:,|\band\b|\be\b|\by\b|\bo\b|\bou\b)\s+)?(?:(?:any|quaisquer|cualquier(?:a)?)\s+)?"
    r"(?:(?:terms?|termos?|t[eé]rminos?)\s+(?:of|de|do)\s+)?(?:the\s+|o\s+|el\s+)?"
    r"(?:loans?|empr[eé]stimos?|pr[eé]stamos?)\b(?:\s+terms?)?")
_LOAN_OK_AREAS = frozenset({"funding_investment", "debt_owed_money", "property"})


def drop_asserted_loans(text, question: str = "", area: str = ""):
    """Drops sentences that assert loans / credit / outside capital nobody mentioned. Never empties."""
    if not isinstance(text, str) or not text.strip() or _FIN_WORDS.search(question or "") \
            or area in _LOAN_OK_AREAS:
        return text
    kept = [x for x in _sentences(text) if not _ASSERTED_LOAN.search(x)]
    if kept:
        return " ".join(kept).strip()
    # [audit r12] a one-sentence next-step: cut just the loan clause, keep the step
    cut = _LOAN_CLAUSE.sub("", text)
    cut = re.sub(r"\s{2,}", " ", cut).strip(" ,;")
    return cut if len(cut) >= 12 else text


_LEGAL_ASSUMED = re.compile(
    r"(?i)\b(settlement|documents?|paperwork|sign(ing)?|lawyer|attorney|legal|agreement|documentos?|advogado|"
    r"abogado|acuerdo|acordo|assinar|firmar|dastavez|vakeel)\b")
_LEGAL_Q = re.compile(r"(?i)\b(settlement|documents?|papers?|lawyer|attorney|court|legal|custody|alimony|"
                      r"documentos?|advogado|abogado|tribunal|juicio|vakeel|adalat|court)\b")
_BUSINESS_NEXT = re.compile(
    r"(?i)\b(business|deal|deals|client|clients|customer|customers|pitch|revenue|blocker|network|"
    r"negocio|neg[oó]cio|cliente|clientes|contrato|sauda|dhandha)\b")

_NEXT_FALLBACK = {
    "separation": {
        "en": "Tell one person you trust how you are really doing this week — out loud, in your own words.",
        "es": "Cuéntale a una persona de confianza cómo estás de verdad esta semana — en voz alta, con tus palabras.",
        "pt": "Conte a uma pessoa de confiança como você realmente está esta semana — em voz alta, com suas palavras.",
        "hinglish": "Is hafte kisi trusted insaan ko batao ki aap sach mein kaisa feel kar rahe ho — apne shabdon mein, bol kar.",
    },
    "retirement": {
        "en": "This week, sketch the monthly income you would want in later life and list where each part would come from.",
        "es": "Esta semana esboza el ingreso mensual que querrías en la vejez y anota de dónde saldría cada parte.",
        "pt": "Esta semana, esboce a renda mensal que você quer na velhice e liste de onde viria cada parte.",
        "hinglish": "Is hafte likho ki later life mein aapko mahine ki kitni income chahiye aur har hissa kahan se aayega.",
    },
    "purpose": {
        "en": "Tonight, write one sentence finishing 'I feel most like myself when…' — then do one small thing this week that fits it.",
        "es": "Esta noche escribe una frase que termine 'Me siento más yo cuando…' — y haz esta semana una cosa pequeña que encaje con ella.",
        "pt": "Hoje à noite escreva uma frase terminando 'Me sinto mais eu quando…' — e faça esta semana uma coisa pequena que combine com ela.",
        "hinglish": "Aaj raat ek line likho: 'Main sabse zyada khud jaisa tab feel karta hoon jab…' — aur is hafte ek chhota kaam karo jo usse match kare.",
    },
}


def safe_next(area: str, nxt, question: str = "", language: str = "en"):
    """[audit r10] Replace a next-step that assumes something the person never said: legal papers for a
    separation, business work for a life-purpose question. Otherwise unchanged."""
    if not isinstance(nxt, str) or not nxt.strip():
        return nxt
    kind = None
    if area == "separation" and _LEGAL_ASSUMED.search(nxt) and not _LEGAL_Q.search(question or ""):
        kind = "separation"
    elif area == "purpose_spiritual" and _BUSINESS_NEXT.search(nxt) and not _BUSINESS_NEXT.search(question or ""):
        kind = "purpose"
    elif is_retirement_q(question) and _BUSINESS_NEXT.search(nxt) and not _BUSINESS_NEXT.search(question or ""):
        kind = "retirement"
    if not kind:
        return nxt
    return _NEXT_FALLBACK[kind].get(language if language in ("es", "pt", "hinglish") else "en")


def purpose_block(u: Optional[dict]) -> str:
    if (u or {}).get("area") != "purpose_spiritual":
        return ""
    return ("\n\nLIFE PURPOSE / MEANING — the question is about meaning and direction, not work.\n"
            "- Speak to what gives their life meaning: what the season is asking (reflection, values, "
            "service, a slower look inward), and what tends to feel aligned versus forced.\n"
            "- Do NOT turn it into business, clients, deals, pitches, reputation or a career window. "
            "The step is reflective and personal (a question to sit with, a walk, a conversation).")


_KIDS_OFFTOPIC = re.compile(
    r"(?i)\b(mentors?|mentees?|elders?|anciano|ancião|mayor de confianza|your father'?s (side|area)|"
    r"el lado de tu padre|o lado do seu pai|your (child|baby) (is |are )?(arriving|coming|on the way)|"
    r"tu (hijo|bebé) (est[aá] )?(llegando|por llegar)|seu (filho|bebê) (est[aá] )?chegando)\b"
    r"|\b(fam[ií]lia|familia|lado|side)\b[^.!?]{0,25}\b(pai|padre|father)\b"
    r"|\bperspectiv\w+ (do|de|of) (seu|tu|your) (filho|hijo|child)\b")
_PARENT_Q = re.compile(r"(?i)\b(father|dad|papa|pap[aá]|padre|pai|mother|mom|madre|m[aã]e)\b")


_KIDS_CONGRATS = re.compile(
    r"(?i)\b(congratulat\w+|felicidades|felicitaciones|parab[eé]ns|mubarak|badhai|"
    r"(arrival|llegada|chegada) (of|de|do|da) (your|tu|seu|sua) (child|baby|hijo|beb[eé]|filho|beb[eê]))\b")
_KIDS_OLDER_HELP = re.compile(
    r"(?i)\b((seu|tu|your) (pai|padre|father|m[aã]e|madre|mother)( ou)?\b[^.!?]{0,30}(mais velho|mayor|older|elder)|"
    r"alguém mais velho|alguien mayor|someone older|an elder|um anci[aã]o)\b")


_KIDS_FLOOR = {
    "en": "The reading shows a mixed season for family growth — unhurried steps and a conversation with your doctor serve you better than pushing a timeline.",
    "es": "La lectura muestra una temporada mixta para el crecimiento familiar — los pasos sin prisa y una conversación con tu médico te sirven más que forzar un calendario.",
    "pt": "A leitura mostra uma temporada mista para o crescimento da família — passos sem pressa e uma conversa com seu médico ajudam mais do que forçar um calendário.",
    "hinglish": "Reading family growth ke liye ek mixed season dikhati hai — bina jaldi ke kadam aur doctor se baat, timeline ko dhakelne se zyada kaam aate hain.",
}


def kids_offtopic(text, area: str = "", question: str = "", language: str = "en"):
    """[audit r10/r13] Pregnancy / child answers drift to mentors, 'your father's side', an asserted
    arriving child, a congratulation nobody asked for. Those sentences go (never emptying the text);
    if what is left no longer mentions children/family at all, one on-topic sentence is added back."""
    if not isinstance(text, str) or not text.strip() or area not in ("children_wellbeing", "children_conception"):
        return text
    rxs = [_KIDS_CONGRATS]
    if not _PARENT_Q.search(question or ""):
        rxs += [_KIDS_OFFTOPIC, _KIDS_OLDER_HELP]
    kept = [x for x in _sentences(text) if not any(r.search(x) for r in rxs)]
    if not kept:
        return text
    out = " ".join(kept).strip()
    if len(kept) < len(_sentences(text)) and not _CHILD_WORD.search(out) \
            and not re.search(r"(?i)\b(family|familia|fam[ií]lia|pregnan\w*|embaraz\w*|gravidez)\b", out):
        lg = language if language in ("es", "pt", "hinglish") else "en"
        out = (_KIDS_FLOOR[lg] + " " + out).strip()
    return out


_WHY_FLOOR = {
    "relationship": {
        "en": "The reading shows this stretch puts real strain on close bonds — pressure and distance between you and the people closest to you is what makes it feel so heavy.",
        "es": "La lectura muestra que esta etapa pone una tensión real en los vínculos cercanos — la presión y la distancia con las personas más cercanas es lo que la hace tan pesada.",
        "pt": "A leitura mostra que esta fase coloca uma tensão real nos vínculos próximos — a pressão e a distância com as pessoas mais próximas é o que a torna tão pesada.",
        "hinglish": "Reading dikhata hai ki yeh daur close rishton par asli strain daal raha hai — apne sabse kareebi logon ke saath pressure aur doori hi ise itna bhaari bana rahi hai.",
    },
    "general": {
        "en": "The reading shows pressure building in this area right now — that is what makes it feel heavier than it should.",
        "es": "La lectura muestra presión acumulándose en esta área ahora mismo — eso es lo que la hace sentir más pesada de lo que debería.",
        "pt": "A leitura mostra pressão se acumulando nesta área agora — é isso que a faz parecer mais pesada do que deveria.",
        "hinglish": "Reading dikhata hai ki is area mein abhi pressure badh raha hai — yahi ise zaroorat se zyada bhaari bana raha hai.",
    },
}
_WHEN_SOFT = {
    "en": "No single date shows for this — the reading points to a slow easing over the coming months, the strain lifting gradually rather than at one moment.",
    "es": "No aparece una fecha única para esto — la lectura apunta a un alivio lento en los próximos meses, con la tensión aflojando poco a poco y no en un solo momento.",
    "pt": "Nenhuma data única aparece para isso — a leitura aponta para um alívio lento nos próximos meses, com a tensão diminuindo aos poucos e não em um único momento.",
    "hinglish": "Iske liye koi ek tareekh nahi dikhti — reading agle kuch mahinon mein dheere dheere rahat dikhati hai, strain ek hi pal mein nahi balki dheere dheere kam hota hai.",
}
_HAS_DATE = re.compile(r"(?i)\b(20\d\d|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|ene|abr|ago|set|out|dic|"
                       r"enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\b")


def relationship_floor(text, u: Optional[dict], language: str = "en"):
    """[audit r13] After the filters a relationship answer can be a single sentence with no reason
    ('Mera shaadi itna mushkil kyun hai?' → one line), and a separation 'when' question gets no
    timing at all (the 'next partnership window' is suppressed on purpose). Add ONE deterministic,
    date-free sentence: a reason for why-questions, a gradual-easing line for when-questions."""
    if not isinstance(text, str) or not text.strip():
        return text
    area, intent = (u or {}).get("area"), (u or {}).get("intent")
    lg = language if language in ("es", "pt", "hinglish") else "en"
    fam = "relationship" if area in _RELATIONSHIP_AREAS or area == "separation" else "general"
    if intent == "why" and len(_sentences(text)) < 2:
        return (text.rstrip() + " " + _WHY_FLOOR[fam][lg]).strip()
    if intent == "when" and area in ("separation", "existing_relationship") and not _HAS_DATE.search(text):
        return (text.rstrip() + " " + _WHEN_SOFT[lg]).strip()
    return text


# ── round 11 ─────────────────────────────────────────────────────────────────
_LEGAL_CAUSE = re.compile(
    r"(?i)\b(fraud|manipulat\w+|regulatory|regulation|tax(es)?( matter| angle)?|fraude|manipula\w+|"
    r"regulat\w+|imposto|impuestos?)\b")
_OTHER_TRAIT = re.compile(
    r"(?i)\b(your|tu|seu|sua|aapka|aapke|aapki) (brother|sister|partner|child|son|daughter|hermano|hermana|"
    r"hijo|hija|irm[aã]o|irm[aã]|filho|filha|bachcha|bachche|bhai)('s)?\b[^.!?]{0,40}"
    r"\b(unreliab\w+|reliab\w+|follow-?through|in trouble|struggling|dishonest|lazy|weaker|d[eé]bil|mais fraco|"
    r"confiabilid\w+|mushkil mein)\b"
    r"|\b(reliability|follow-?through|seguimiento|confiabilidad|confiabilidade)\b[^.!?]{0,40}\b(weaker|d[eé]bil|"
    r"mais fraca?)\b"
    r"|\b(aapka|your|tu|seu) (bachcha|child|hijo|filho) mushkil mein\b")
_FAR_FROM_FAMILY = re.compile(
    r"(?i)(family se door|away from (your )?family|far from (your )?family|lejos de (tu )?familia|"
    r"longe da (sua )?fam[ií]lia)")
_FOREIGN_DEAL = re.compile(
    r"(?i)\b(property|contract|deal|propiedad|contrato|im[oó]vel|propriedade)s?\b[^.!?]{0,30}"
    r"\b(property|contract|deal|propiedad|contrato|im[oó]vel|propriedade)s?\b")
_REL_ASSUMED = re.compile(
    r"(?i)\b(hidden gains|ganhos ocultos|ganancias ocultas|(your|tu|sua|aapka|aapke|apna|apne) (own )?(home|casa|ghar)|"
    r"agreements?|acordos?|acuerdos?|shared finances?|finan[cç]as compartilhadas)\b")


def drop_other_people_claims(text, area: str = "", question: str = ""):
    """[audit r11] Sentences that state traits/circumstances of other people, a legal matter's nature, or
    a foreign deal/home as fact when nobody said so. Never empties the text."""
    if not isinstance(text, str) or not text.strip():
        return text
    q = question or ""
    rxs = [_OTHER_TRAIT]
    if not _LEGAL_CAUSE.search(q):
        rxs.append(_LEGAL_CAUSE) if area == "legal_case" else None
    if area == "separation":
        rxs.append(_FAR_FROM_FAMILY)
    if area == "foreign_travel_visa":
        rxs.append(_FOREIGN_DEAL)
    if area in _RELATIONSHIP_AREAS and not _HOME_Q.search(q):
        rxs.append(_REL_ASSUMED)
    kept = [x for x in _sentences(text) if not any(r.search(x) for r in rxs)]
    return " ".join(kept).strip() if kept else text


_RETIRE_Q = re.compile(r"(?i)\b(retire\w*|pension|jubilaci[oó]n|jubilarme|aposentadoria|aposentar\w*|old age|"
                       r"vejez|velhice|budhapa)\b")


def is_retirement_q(question: str) -> bool:
    return bool(_RETIRE_Q.search(question or ""))


def retirement_block(question: str) -> str:
    if not is_retirement_q(question):
        return ""
    return ("\n\nRETIREMENT / LATER LIFE — the question is about security and ease in later life.\n"
            "- Speak to: how steady the base is that later years would rest on (savings cushion, income that "
            "doesn't depend on constant effort), energy and health in later years, and the season the reading "
            "shows for building that base — in plain words.\n"
            "- Do NOT answer with client wins, deals, reputation or a business-growth window.\n"
            "- No investment advice and no product names. The step is planning-level: sketch the monthly income "
            "they would need later and where it would come from.")


# ── round 14 ─────────────────────────────────────────────────────────────────
_DHARMA_PAREN = re.compile(r"(?i)\bdharma\s*\(([^)]{3,40})\)")
_SYSTEM_WORD = {"en": "purpose", "es": "propósito", "pt": "propósito", "hinglish": "maqsad"}


def strip_system_terms(text, language: str = "en"):
    """[audit r14] 'o dharma (propósito de vida)' reached a Portuguese answer: system/Sanskrit words
    are never user-facing. 'dharma (X)' → 'X'; a bare 'dharma' → the plain word."""
    if not isinstance(text, str) or "dharma" not in text.lower():
        return text
    out = _DHARMA_PAREN.sub(lambda m: m.group(1), text)
    lg = language if language in ("es", "pt", "hinglish") else "en"
    out = re.sub(r"(?i)\bdharma\b", _SYSTEM_WORD[lg], out)
    return re.sub(r"\b(o|a|el|la) (propósito de vida)", r"\1 \2", out)


_INVENTED_LEGAL = re.compile(r"(?i)\b(cau[cç][aã]o|fian[cç]a|bail|bond posted|garant[ií]a judicial)\b")


def drop_invented_legal(text, question: str = ""):
    """A bail / deposit nobody mentioned is not part of someone's case."""
    if not isinstance(text, str) or not text.strip() or _INVENTED_LEGAL.search(question or ""):
        return text
    kept = [x for x in _sentences(text) if not _INVENTED_LEGAL.search(x)]
    return " ".join(kept).strip() if kept else text


_STUDY_WORDS = re.compile(r"(?i)\b(exam\w*|study|studying|studies|prova|provas|estud\w+|examen\w*|test|resultados?|"
                          r"results?|course|curso|college|school|aprend\w+|learn\w*|pariksha|padhai)\b")
_EDU_FLOOR = {
    "en": "The reading shows a steady, preparation-favouring season for study — consistent, unhurried preparation beats last-minute pushes.",
    "es": "La lectura muestra una temporada estable que favorece la preparación para el estudio — la preparación constante y sin prisa supera los empujones de último momento.",
    "pt": "A leitura mostra uma temporada estável que favorece a preparação para o estudo — a preparação constante e sem pressa vence os arrancos de última hora.",
    "hinglish": "Reading padhai ke liye ek steady, taiyari-wala season dikhati hai — lagatar aur bina jaldi ki taiyari aakhri minute ke dabaav se behtar hai.",
}
_EDU_NEXT = {
    "en": "This week, set a fixed daily study block and list the two topics that need the most work.",
    "es": "Esta semana fija un bloque de estudio diario y anota los dos temas que más trabajo necesitan.",
    "pt": "Esta semana, defina um bloco diário de estudo e liste os dois temas que mais precisam de trabalho.",
    "hinglish": "Is hafte roz ka ek fixed study block rakho aur un do topics ko likho jin par sabse zyada kaam chahiye.",
}


def education_floor(read, nxt, u: Optional[dict], question: str = "", language: str = "en"):
    """[audit r14] Exam questions fell back to the business reading ('O que devo fazer com meu prova?' →
    business timing; an empty next step). If the answer never mentions study, one on-topic sentence
    leads it, and a business / empty next step becomes a study step. Returns (read, next)."""
    if (u or {}).get("area") != "education_exam":
        return read, nxt
    lg = language if language in ("es", "pt", "hinglish") else "en"
    if isinstance(read, str) and read.strip() and not _STUDY_WORDS.search(read):
        read = (_EDU_FLOOR[lg] + " " + read).strip()
    if (not isinstance(nxt, str) or not nxt.strip()
            or (_BUSINESS_NEXT.search(nxt) and not _BUSINESS_NEXT.search(question or ""))):
        nxt = _EDU_NEXT[lg]
    return read, nxt


def education_block(u: Optional[dict]) -> str:
    if (u or {}).get("area") != "education_exam":
        return ""
    return ("\n\nEXAM / STUDY — the question is about studying, an exam or its results.\n"
            "- Speak to preparation, focus and the season for results — not business, clients or a "
            "career window.\n"
            "- Do NOT mention their money or home situation unless they did.")


def parse_model_json(raw) -> Optional[dict]:
    """[audit r9] The answer JSON from model text. The model sometimes writes a JSON object, then
    'Wait — let me correct that:' and a second one (live: the whole mess reached the user as text).
    Take the LAST well-formed object that has a 'read'; None when there is none."""
    import json as _json
    txt = raw if isinstance(raw, str) else ""
    try:
        o = _json.loads(txt[txt.find("{"): txt.rfind("}") + 1])
        if isinstance(o, dict):
            return o
    except Exception:
        pass
    dec, best, i = _json.JSONDecoder(), None, 0
    while True:
        i = txt.find("{", i)
        if i < 0:
            break
        try:
            o, end = dec.raw_decode(txt[i:])
            if isinstance(o, dict) and isinstance(o.get("read"), str) and o["read"].strip():
                best = o
            i += max(end, 1)
        except Exception:
            i += 1
    return best


_JSONISH = re.compile(r'^\s*(`{1,3}\s*json|\{\s*"(read|next|why)")', re.I)


def looks_like_json_leak(text) -> bool:
    return isinstance(text, str) and bool(_JSONISH.search(text))


def why_block(u: Optional[dict]) -> str:
    """Narrator rule for 'why is X so hard / why does X keep happening' questions."""
    if (u or {}).get("intent") != "why":
        return ""
    return ("\n\nWHY QUESTION — they asked for the REASON.\n"
            "- Give the reason the reading shows in plain words BEFORE any reassurance: the specific "
            "pressure or pattern in this area and what feeds it ('it is hard because …').\n"
            "- One reason, concrete, about this topic only; then what eases it. Reassurance alone, or "
            "'this will pass', is not an answer.")


def kids_block(u: Optional[dict], question: str = "", gender: str = "") -> str:
    if (u or {}).get("area") not in ("children_wellbeing", "children_conception"):
        return ""
    out = ("\n\nCHILDREN / PREGNANCY — the question is about children or a pregnancy; answer exactly that.\n"
           "- This OVERRIDES any earlier rule that treats their children as 'grown adults' / a creative project: "
           "when the question names a child or a pregnancy, answer about THAT.\n"
           "- NEVER reinterpret it as a mentee, a project, a venture or a creative work.\n"
           "- Do NOT bring up career windows, business, mentors or elders; the human step is a conversation "
           "with the partner (if there is one) or a doctor/midwife for a pregnancy.\n"
           "- NEVER state that a pregnancy or a baby IS happening unless they said so ('you are already in "
           "the window' about a pregnancy they did not mention is wrong). Say what the reading shows for the "
           "season of family growth.\n")
    if (gender or "").strip().lower() in ("male", "m", "man"):
        out += ("- The reader is a MAN: a pregnancy is his partner's. Speak of 'a pregnancy in your family / your "
                "partner's pregnancy' as the reading's family-growth season, and if no partner is known, say "
                "plainly that you are reading the family-growth season and ask nothing more.")
    return out


def separation_assumes_home(text, question: str = ""):
    """Separation answers must not assume a shared home, property or assets."""
    if not isinstance(text, str) or not text.strip():
        return text
    if _HOME_Q.search(question or ""):
        return text
    kept = [x for x in _sentences(text) if not _HOME_ASSUMED.search(x)]
    return " ".join(kept).strip() if kept else text


_HOME_Q = re.compile(r"(?i)\b(home|house|property|assets?|casa|propiedad|im[oó]vel|ghar|jaaydaad|sampatti)\b")
_HOME_ASSUMED = re.compile(
    r"(?i)\b(your (home|house)|shared (home|house|assets?)|(your|tu|sua|aapke|aapka|apna|apne) (own )?(casa|ghar)|ghar|"
    r"sus bienes|seus bens|assets?|hidden gains|financial agreement|acuerdo financiero|acordo financeiro|"
    r"bienes compartidos)\b")

CONCERN_MIN_CONFIDENCE = 0.75
OWN_TOPIC_MIN_CONFIDENCE = 0.6   # own topic vs inheriting the previous turn's


_CHILD_WORD = re.compile(
    r"(?i)\b(child|children|kids?|son|sons|daughter|daughters|baby|babies|pregnan\w*|conceiv\w*|"
    r"bachch?[ae]\w*|bacha|beta|beti|hij[oa]s?|embaraz\w*|filh[oa]s?|gravidez|gr[aá]vida|bebé|bebê)\b")


def concern_override(u: Optional[dict], keyword_concern: str,
                     min_confidence: float = None, question: str = "") -> Optional[str]:
    """[nlu-primary: concern 2026-10-03] The Ask concern to use instead of the
    keyword router's, or None to keep it. Live: "How is my work with partners?"
    → keyword concern 'love' → an answer about his SPOUSE. Only a confident,
    specific reading overrides; 'general' never overrides anything."""
    c = concern(u)
    if not c or c == "general" or c == keyword_concern:
        return None
    floor = CONCERN_MIN_CONFIDENCE if min_confidence is None else min_confidence
    # [audit r9] "Mere bachcha ke liye kya karun?" read as children at 0.65 and lost to a career
    # guess: a child word IN the message is evidence enough for the children topic
    if (u or {}).get("area") in ("children_wellbeing", "children_conception") \
            and _CHILD_WORD.search(question or ""):
        floor = min(floor, 0.4)
    if float((u or {}).get("confidence") or 0) < floor:
        return None
    return c



# ── no verdict on "what should I do" questions; no invented background ──────
# [intent-verdict 2026-10-03] live (Harleen, voice): "What type of courses should I
# take?" → "Not yet — right now (Oct 2026) is for laying groundwork…". The keyword
# decision detector marked it a decision; the understanding read intent=what_to_do.
NO_VERDICT_INTENTS = frozenset({"what_to_do", "why", "which", "where_who", "statement",
                                "greeting", "thanks", "meta"})


def suppress_verdict(u: Optional[dict]) -> bool:
    """True when a Yes / Not-yet lead line doesn't answer this kind of question."""
    return (u or {}).get("intent") in NO_VERDICT_INTENTS


_BACKGROUND_CLAIM = re.compile(
    r"(?i)\b(already built|already have the (skills|experience)|your (existing |proven |deep |core )?"
    r"(expertise|experience|background|track record|years) (in|with|as)|you(?:'ve| have) (already )?"
    r"(built|spent years|worked (in|as)|got experience)|from your \w+ years)\b"
    r"|\byour [\w ,&/-]{0,50}\b(expertise|experience|background|track record|know-how)\b[^.!?]{0,30}"
    r"\b(is|are) (already|real|proven|solid)\b"
    r"|\b(expertise|experience|background) (is|are) already your\b")


def drop_invented_background(text, background_known: bool):
    """Live: 'Your strongest asset is already built — finance and bookkeeping
    management expertise is real' for someone who never said she worked in
    finance. Without a known background, such sentences are dropped."""
    if background_known or not isinstance(text, str) or not text.strip():
        return text
    kept = [snt for snt in _sentences(text) if not _BACKGROUND_CLAIM.search(snt)]
    out = " ".join(kept).strip() if kept else text
    # "your finance network / contacts" → "your network / contacts"
    return re.sub(r"\b([Yy]our) (?!own\b|professional\b|personal\b)[A-Za-z]+(?: [A-Za-z]+)? "
                  r"(network|contacts|circle)\b", r"\1 \2", out)



# ── explicit statements update the profile (owner 2026-10-03) ───────────────
_WORK_STORE = {"unemployed": "between_jobs", "employed": "employed", "self_employed": "running_business",
               "student": "student", "retired": "retired", "homemaker": "homemaker"}
_WORK_CLASS = {"running_business": "biz", "entrepreneur": "biz", "business_owner": "biz", "founder": "biz",
               "self_employed": "biz", "between_jobs": "out", "seeking": "out", "unemployed": "out",
               "job_seeking": "out", "transition": "out", "in_transition": "out", "student": "study",
               "studying": "study", "retired": "retired", "homemaker": "home", "employed": "job",
               "early_career": "job", "mid_career": "job", "senior_career": "job", "creative": "job"}
_REL_STORE = {"single": "single", "dating": "in_relationship", "married": "married",
              "separated": "separated", "divorced": "divorced", "widowed": "widowed"}
_KIDS_CLASS = {"adult_children": "yes", "grown_children": "yes", "has_children": "yes", "young_children": "yes",
               "older_children": "yes", "yes": "yes", "kids": "yes", "parent": "yes", "expecting": "yes",
               "no_children": "no", "no": "no", "none": "no", "childless": "no", "no_children_wants": "no",
               "no_children_by_choice": "no"}


def explicit_updates(u: Optional[dict], row: dict) -> dict:
    """{field: (old, new)} for explicit present-tense statements that CHANGE a
    stored value (same-meaning values are left alone)."""
    f = (u or {}).get("stated_facts") or {}
    ex = set(f.get("explicit_now") or [])
    row = row or {}
    out = {}
    if "work" in ex and f.get("work") in _WORK_STORE:
        new = _WORK_STORE[f["work"]]
        old = str(row.get("career_stage") or "").strip()
        if old and _WORK_CLASS.get(old, old) != _WORK_CLASS.get(new, new):
            out["career_stage"] = (old, new)
    if "relationship" in ex and f.get("relationship") in _REL_STORE:
        new = _REL_STORE[f["relationship"]]
        old = str(row.get("marital_status") or "").strip()
        if old and old != new:
            out["marital_status"] = (old, new)
    if "children" in ex and f.get("children") in ("yes", "no"):
        new = "has_children" if f["children"] == "yes" else "no_children"
        old = str(row.get("children_status") or "").strip()
        if old and _KIDS_CLASS.get(old) != f["children"]:
            out["children_status"] = (old, new)
    return out



# ── concreteness for "what should I do" questions (answer audit 2026-10-03) ──
def what_to_do_block(u: Optional[dict]) -> str:
    """Live audit: 'What type of courses should I take?' got a general career read
    that named no course at all."""
    if (u or {}).get("intent") != "what_to_do":
        return ""
    return ("\n\nANSWER THE PRACTICAL QUESTION — they asked what to DO. The FIRST sentence of "
            "\"read\" must name 2-3 concrete options that answer it (e.g. for courses: actual course "
            "types like 'management accounting', 'data analysis', 'negotiation'), drawn from what the "
            "reading favours, each with a short reason it fits them. Timing or caution comes after, "
            "only if it changes what to do. \"next\" is the first step on the best of those options.")
