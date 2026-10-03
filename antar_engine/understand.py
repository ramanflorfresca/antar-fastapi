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
    ' "stated_facts": facts the person STATES about their own life in THIS message '
    '(never infer, never guess): {"work": one of ' + json.dumps(list(WORK)) + ' or null, '
    '"relationship": one of ' + json.dumps(list(RELATIONSHIP)) + ' or null, '
    '"children": "yes" | "no" | null, "other": up to 3 short plain facts they said '
    '(e.g. "has debt", "recently laid off", "caring for a sick parent") or []}}\n'
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
    }
    return {
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
