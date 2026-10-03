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
# area MUST say how KP and Ask read it.
AREAS = {
    "career_job":          ("job_new", "career"),
    "promotion":           ("promotion", "career"),
    "business_venture":    ("gain", "business"),
    "clients_sales":       ("deal_closes", "business"),
    "funding_investment":  ("money", "funding"),
    "income_money":        ("gain", "finance"),
    "debt_owed_money":     ("gain", "finance"),
    "speculation_betting": ("speculation", "finance"),
    "property":            ("property", "property"),
    "residence_move":      ("residence", "property"),
    "foreign_travel_visa": ("foreign_travel", "foreign"),
    "education_exam":      ("education", "education"),
    "marriage":            ("marriage", "relationship"),
    "new_romance":         ("romance", "relationship"),
    "existing_relationship": (None, "relationship"),
    "reunion_ex":          ("reunion", "relationship"),
    "separation":          ("loss", "relationship"),
    "business_partnership": (None, "business"),
    "partnership_ending":  ("loss", "business"),
    "children_conception": ("childbirth", "children"),
    "children_wellbeing":  (None, "children"),
    "health_self":         ("recovery", "health"),
    "health_other":        (None, "health"),
    "legal_case":          ("litigation_win", "legal"),
    "lost_item":           ("lost_found", "general"),
    "family":              (None, "family"),
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
    'equity" → ["advisory","commission","equity"]; never guess)},\n'
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
    facts = {
        "work": _clean_enum(sf.get("work"), WORK, None) if sf.get("work") else None,
        "relationship": (_clean_enum(sf.get("relationship"), RELATIONSHIP, None)
                         if sf.get("relationship") else None),
        "children": (str(sf.get("children")).lower() if str(sf.get("children")).lower() in ("yes", "no")
                     else None),
        "other": [str(x).strip()[:80] for x in other if str(x).strip()][:3],
        # an earning type counts only if the message itself says it (live: the
        # model "stated" trading for "Gold or defence?" — never said)
        "earning": [e for e in (str(x).strip().lower() for x in (sf.get("earning") or [])
                                if isinstance(sf.get("earning"), list))
                    if e in EARNING and _EARNING_EVIDENCE[e].search(original or "")][:4],
    }
    opts = obj.get("options") if isinstance(obj.get("options"), list) else []
    options = [str(o).strip()[:60] for o in opts if str(o).strip()][:5]
    return {
        "outcome_claim": bool(obj.get("outcome_claim")) or bool(_OUTCOME_Q.search(original or "")),
        "options": options,
        "feeling": _clean_enum(obj.get("feeling"), FEELINGS, "neutral"),
        "stated_facts": facts,
        "language": _clean_enum(obj.get("language"), LANGS, "other"),
        "standalone": standalone,
        "intent": _clean_enum(obj.get("intent"), INTENTS, "open"),
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
def is_comparison(u: Optional[dict]) -> bool:
    u = u or {}
    return len(u.get("options") or []) >= 2 or u.get("intent") == "which"


def earning_text(earning: list) -> str:
    return " + ".join(_EARNING_PLAIN.get(e, e) for e in (earning or []))


def comparison_block(u: Optional[dict], known_earning: str = "") -> str:
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
    return "\n".join(lines)


EARNS_PREFIX = "Earns via "


def stored_earning(profession: str) -> str:
    p = (profession or "").strip()
    return p[len(EARNS_PREFIX):].strip() if p.lower().startswith(EARNS_PREFIX.lower()) else ""


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
            "on savings'.")


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
    (re.compile(r"(?i)\byour debt\b"), "loan pressure in the reading"),
]
_FIN_WORDS = re.compile(r"(?i)sav(e|ing|ings)|debt|loan|money|cash|broke|deud|ahorro|d[ií]vida|poupan|karz|udhaar")


def _sentences(t: str) -> list:
    return [x for x in re.split(r"(?<=[.!?])\s+", (t or "").strip()) if x.strip()]


def guard_answer(text, question: str = "", options: Optional[list] = None):
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
        if opt_rx and opt_rx.search(snt):
            continue
        kept.append(snt)
    out = " ".join(kept).strip() if kept else text
    if not _FIN_WORDS.search(question or ""):
        for rx, rep in _FIN_FACT:
            out = rx.sub(lambda m, r=rep: (r[0].upper() + r[1:]) if m.group(0)[0].isupper() else r, out)
    return out
