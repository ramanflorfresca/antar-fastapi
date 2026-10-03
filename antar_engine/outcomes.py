"""
antar_engine/outcomes.py — the outcome loop: record checkable predictions and
the person's answer to "did it happen?".

[outcome-loop 2026-10-02] Spec: "Outcome Loop & Accuracy Board — Spec" (Claude
Doc). Before this, 826 stored predictions had 0 recorded answers, and
`user_predictions.fulfilled` defaulted to false — so "didn't happen" and
"never asked" were indistinguishable. Here an outcome only exists when the
person answered; absence means unanswered, never "no".

Pure helpers + thin Supabase calls; fail-open (a missing table never breaks Ask).
Tables (Lovable DDL): prediction_claims, prediction_outcomes — see
sql_outcome_loop.sql.
"""
from __future__ import annotations

import calendar
import re
from datetime import date, datetime, timedelta, timezone
from typing import Optional

OUTCOMES = ("yes", "partly", "no", "not_sure")
# Only these sources get a check-in. Migrated life-arc rows are THEMES ("current
# chapter", "sub-theme"), often in astrology wording ("Saturn is asking…") — not
# events a person can answer yes/no to. They stay stored, never asked about.
CHECKABLE_SOURCES = ("ask_explore", "ask_yesno", "decoy")
CHECKIN_DELAY_DAYS = 3
_VERDICTS_TRACKED = {"LIKELY", "NOT_YET", "YES", "NO", "LEAN_YES", "LEAN_NO", "MIXED"}

_MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_abbr) if m}
_MONTHS.update({m.lower(): i for i, m in enumerate(calendar.month_name) if m})
_MONTHS.update({"sept": 9, "ene": 1, "enero": 1, "febrero": 2, "marzo": 3, "abr": 4,
                "abril": 4, "mayo": 5, "junio": 6, "julio": 7, "ago": 8, "agosto": 8,
                "septiembre": 9, "octubre": 10, "noviembre": 11, "dic": 12, "diciembre": 12,
                "fevereiro": 2, "março": 3, "maio": 5, "junho": 6, "julho": 7,
                "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12})
_MON = "|".join(sorted((re.escape(m) for m in _MONTHS), key=len, reverse=True))
_RX_MY = re.compile(rf"(?i)\b({_MON})\.?\s+(?:de\s+)?(\d{{4}})\b")
_RX_DM = re.compile(rf"(?i)\b(\d{{1,2}})(?:st|nd|rd|th)?(?:\s+de)?\s+({_MON})\b")
_RX_MD = re.compile(rf"(?i)\b({_MON})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?\b(?!\s*\d{{4}})")


_RX_NAMED_WINDOW = re.compile(
    r"(?i)(?:window|ventana|janela|stretch)\s+(?:is|es|é|opens?|abre)\s+([^.;]+)")


def _month_end(y: int, m: int) -> date:
    return date(y, m, calendar.monthrange(y, m)[1])


def parse_window(label: Optional[str], today: Optional[date] = None) -> tuple:
    """(start, end) dates from a window label — 'Nov 2026 – Jan 2027',
    'Oct 2026', '24 Nov – 12 Dec' — or (None, None)."""
    if not isinstance(label, str) or not label.strip():
        return None, None
    today = today or date.today()
    my = [(int(y), _MONTHS[m.lower()]) for m, y in _RX_MY.findall(label)]
    if my:
        (y1, m1), (y2, m2) = my[0], my[-1]
        try:
            return date(y1, m1, 1), _month_end(y2, m2)
        except ValueError:
            return None, None
    days = [(_MONTHS[m.lower()], int(d)) for d, m in _RX_DM.findall(label)]
    days += [(_MONTHS[m.lower()], int(d)) for m, d in _RX_MD.findall(label)]
    if days:
        def _upcoming(m, d):
            for y in (today.year, today.year + 1):
                try:
                    c = date(y, m, d)
                except ValueError:
                    return None
                if c >= today - timedelta(days=31):
                    return c
            return None
        start, end = _upcoming(*days[0]), _upcoming(*days[-1])
        if start and end and end < start:
            end = date(end.year + 1, end.month, end.day)
        if start and end:
            return start, end
    return None, None


def build_claim(chart_id: str, question: str, payload: dict, *, mode: str,
                topic: str, language: str, channel: str = "app",
                engines: Optional[dict] = None, today: Optional[date] = None) -> Optional[dict]:
    """A prediction_claims row for an answer that makes a checkable claim, else
    None. Only dated verdicts and Yes/No leans count — mood and advice don't."""
    p = payload or {}
    if p.get("locked"):
        return None          # a replay of an earlier answer, not a new prediction
    verdict = str(p.get("verdict") or "").upper().strip()
    if mode == "yesno":
        lean = str(p.get("lean") or verdict or "").upper().strip()
        end = None
        if p.get("verify_after"):
            try:
                end = date.fromisoformat(str(p["verify_after"])[:10])
            except ValueError:
                end = None
        start, _ = parse_window(p.get("timing"), today)
        if not (lean and end):
            return None
        claim_type, verdict, start = "yesno", lean, (start or (today or date.today()))
    else:
        if verdict not in _VERDICTS_TRACKED:
            return None
        # The claim is the window the VERDICT names ("…the strong funding window
        # is Jun 2027 – Oct 2027"), not the timing chip, which can be the current
        # groundwork month ("Oct 2026"). Fall back to the chip only if no window
        # is named.
        start = end = None
        m = _RX_NAMED_WINDOW.search(p.get("read") or "")
        if m:
            start, end = parse_window(m.group(1), today)
        if not end:
            start, end = parse_window(p.get("timing") or "", today)
        if not end:
            return None
        claim_type = "window"
    first = re.split(r"(?<=[.!?])\s", (p.get("read") or p.get("why") or "").strip(), 1)[0]
    return {
        "chart_id": chart_id,
        "source": "ask_yesno" if claim_type == "yesno" else "ask_explore",
        "topic": (topic or "general").lower(),
        "claim_type": claim_type,
        "window_start": start.isoformat() if start else None,
        "window_end": end.isoformat(),
        "text_shown": first[:500],
        "question": (question or "")[:500],
        "language": language or "en",
        "channel": channel or "app",
        "verdict": verdict,
        "confidence_word": str(p.get("confidence") or p.get("confidence_label") or "")[:40] or None,
        "engines": engines or {},
        # every Prashna is its own question cast at its own moment — a Yes/No claim
        # is keyed by its question too, so two different questions never merge
        "dedupe_key": (f"{chart_id}|{(topic or 'general').lower()}|{claim_type}|"
                       f"{start.isoformat() if start else ''}|{end.isoformat()}"
                       + (f"|q:{_qkey(question)}" if claim_type == "yesno" else "")),
        "checkin_due_at": datetime.combine(end + timedelta(days=CHECKIN_DELAY_DAYS),
                                           datetime.min.time(), tzinfo=timezone.utc).isoformat(),
    }


def _qkey(question: str) -> str:
    import hashlib
    norm = " ".join(re.findall(r"[\w']+", (question or "").lower()))
    return hashlib.sha1(norm.encode()).hexdigest()[:12]


def _table_missing(e) -> bool:
    m = str(e).lower()
    return "pgrst205" in m or "could not find the table" in m or "does not exist" in m


def record_claim(sb, claim: Optional[dict]) -> Optional[str]:
    """Upsert on dedupe_key (the same topic + window is one claim, however often
    it was repeated). Returns the claim id, or None. Never raises."""
    if not claim:
        return None
    try:
        res = (sb.table("prediction_claims")
               .upsert(claim, on_conflict="dedupe_key", ignore_duplicates=True).execute())
        rows = res.data or []
        if rows:
            return rows[0].get("id")
        got = (sb.table("prediction_claims").select("id")
               .eq("dedupe_key", claim["dedupe_key"]).limit(1).execute()).data or []
        return got[0]["id"] if got else None
    except Exception as e:
        if not _table_missing(e):
            print(f"[outcomes] record_claim failed: {e}")
        return None


def record_outcome(sb, claim_id: str, outcome: str, note: Optional[str] = None,
                   via: str = "app") -> bool:
    if outcome not in OUTCOMES:
        raise ValueError(f"outcome must be one of {OUTCOMES}")
    try:
        sb.table("prediction_outcomes").upsert({
            "claim_id": claim_id, "outcome": outcome,
            "note": (note or "").strip()[:500] or None,
            "answered_at": datetime.now(timezone.utc).isoformat(),
            "answered_via": via,
        }, on_conflict="claim_id").execute()
        return True
    except Exception as e:
        print(f"[outcomes] record_outcome failed: {e}")
        return False


_TOPIC_NOUN = {
    "en": {"business": "your business", "startup": "your business", "career": "your work",
           "funding": "funding", "money": "money", "finance": "money", "wealth": "money",
           "love": "your love life", "marriage": "marriage", "relationship": "your relationship",
           "property": "property", "foreign": "a move abroad", "health": "your health",
           "family": "your family", "speculation": "your investments"},
    "es": {"business": "tu negocio", "startup": "tu negocio", "career": "tu trabajo",
           "funding": "la financiación", "money": "el dinero", "finance": "el dinero",
           "love": "tu vida amorosa", "marriage": "el matrimonio", "property": "una propiedad"},
    "pt": {"business": "seu negócio", "startup": "seu negócio", "career": "seu trabalho",
           "funding": "o investimento", "money": "o dinheiro", "finance": "o dinheiro",
           "love": "sua vida amorosa", "marriage": "o casamento", "property": "um imóvel"},
}
_CHECKIN = {
    "en": ("We said: “{said}”", "Did things move for {noun} in that time?", "Did it happen?"),
    "es": ("Te dijimos: “{said}”", "¿Se movió algo en {noun} en ese tiempo?", "¿Pasó?"),
    "pt": ("Dissemos: “{said}”", "Algo mudou em {noun} nesse período?", "Aconteceu?"),
}
OPTION_LABELS = {
    "en": {"yes": "Yes", "partly": "Partly", "no": "No", "not_sure": "Not sure yet"},
    "es": {"yes": "Sí", "partly": "En parte", "no": "No", "not_sure": "Aún no sé"},
    "pt": {"yes": "Sim", "partly": "Em parte", "no": "Não", "not_sure": "Ainda não sei"},
}


def checkin_text(claim: dict) -> str:
    """The did-it-happen question for a claim, in its language. Sensitive topics
    (health, separation, pregnancy) use the neutral form only."""
    lang = (claim.get("language") or "en")[:2]
    lang = lang if lang in _CHECKIN else "en"
    said_t, moved_t, plain_t = _CHECKIN[lang]
    topic = (claim.get("topic") or "").lower()
    sensitive = topic in ("health", "separation", "divorce", "pregnancy", "children")
    noun = _TOPIC_NOUN.get(lang, {}).get(topic)
    # quote only what Ask said (plain-language by construction); never old texts
    said = ((claim.get("text_shown") or "").strip()
            if claim.get("source") in ("ask_explore", "ask_yesno") else "")
    head = said_t.format(said=said) if said and not sensitive else ""
    tail = moved_t.format(noun=noun) if (noun and claim.get("claim_type") == "window"
                                         and not sensitive) else plain_t
    if claim.get("_reask"):
        head = (_REASK_LEAD.get(lang, _REASK_LEAD["en"]) + (" " + head if head else "")).strip()
    return (head + "\n\n" + tail).strip()


def due_claims(sb, chart_id: str, now: Optional[datetime] = None, limit: int = 2) -> list:
    """Claims whose check-in is due and that have no outcome yet (oldest first)."""
    now = now or datetime.now(timezone.utc)
    try:
        rows = (sb.table("prediction_claims").select("*").eq("chart_id", chart_id)
                .in_("source", list(CHECKABLE_SOURCES))
                .lte("checkin_due_at", now.isoformat()).order("checkin_due_at")
                .limit(20).execute()).data or []
        if not rows:
            return []
        answered = {r["claim_id"] for r in (sb.table("prediction_outcomes").select("claim_id")
                    .in_("claim_id", [r["id"] for r in rows]).execute().data or [])}
        return [r for r in rows if r["id"] not in answered][:limit]
    except Exception as e:
        if not _table_missing(e):
            print(f"[outcomes] due_claims failed: {e}")
        return []


# ── week 2: sending check-ins ──
# [outcome-loop-checkins 2026-10-02] Dated Ask claims (source ask_explore) get one
# "did it happen?" after the window ends, at ~8 AM local, at most 2 a week per
# person, one a day. Yes/No claims keep the existing yesno_checkback job (their
# answers live in user_correlations) — bridging is a follow-up.
CHECKIN_SOURCES = ("ask_explore",)
# [reask-not-sure 2026-10-02] owner: a "Not sure yet" is asked ONCE more, 30 days
# later, then never again. The re-ask is marked in checkin_channel ("push+reask")
# — no DDL.
REASK_AFTER_DAYS = 30
REASK_MARK = "+reask"
_REASK_LEAD = {"en": "Last time you weren't sure yet.",
               "es": "La última vez aún no estabas seguro.",
               "pt": "Da última vez você ainda não tinha certeza."}
WEEKLY_CAP = 2
LOCAL_HOUR = 8
LOOKBACK_DAYS = 30


def pick_due(claims: list, sent_last_week: dict, answered: set) -> list:
    """At most ONE claim per chart per run, honouring the weekly cap; oldest due first."""
    chosen, seen = [], set()
    for c in sorted(claims, key=lambda r: r.get("checkin_due_at") or ""):
        cid = c.get("chart_id")
        if (not cid or cid in seen or c.get("source") not in CHECKIN_SOURCES
                or (not c.get("_reask") and (c.get("id") in answered or c.get("checkin_sent_at")))):
            continue
        if sent_last_week.get(cid, 0) >= WEEKLY_CAP:
            continue
        seen.add(cid)
        chosen.append(c)
    return chosen


_PUSH_TITLE = {"en": "Did it happen?", "es": "¿Pasó?", "pt": "Aconteceu?"}


def push_message(claim: dict) -> tuple:
    lang = (claim.get("language") or "en")[:2]
    lang = lang if lang in _PUSH_TITLE else "en"
    body = checkin_text(claim).replace("\n\n", " ")
    return _PUSH_TITLE[lang], (body[:177] + "…") if len(body) > 178 else body


_WA_OPTIONS_LINE = {"en": "Reply with a number:", "es": "Responde con un número:",
                    "pt": "Responda com um número:"}


def whatsapp_checkin(claim: dict) -> tuple:
    """(text, options) — options are [claim_id, outcome] pairs in display order."""
    lang = (claim.get("language") or "en")[:2]
    lang = lang if lang in OPTION_LABELS else "en"
    labels = OPTION_LABELS[lang]
    lines = [checkin_text(claim), "", _WA_OPTIONS_LINE[lang]]
    lines += [f"{i}  {labels[o]}" for i, o in enumerate(OUTCOMES, 1)]
    return "\n".join(lines), [[claim["id"], o] for o in OUTCOMES]


def template_vars(claim: dict, first_name: str = "") -> Optional[dict]:
    """Variables for the antar_checkin_v1 template: {1: name, 2: date said, 3: what
    Antar said}. None when there's nothing safe to quote (sensitive topics, no
    Ask text) — those stay on push / in-app where the neutral wording lives."""
    topic = (claim.get("topic") or "").lower()
    if topic in ("health", "separation", "divorce", "pregnancy", "children", "loss"):
        return None
    said = ((claim.get("text_shown") or "").strip()
            if claim.get("source") in ("ask_explore", "ask_yesno") else "")
    if not said:
        return None
    try:
        d = datetime.fromisoformat(str(claim.get("created_at"))[:19])
        when = f"{d.strftime('%b')} {d.day}"
    except Exception:
        return None
    said = said.rstrip(" .")
    if len(said) > 110:
        said = said[:109].rsplit(" ", 1)[0] + "\u2026"
    lang = (claim.get("language") or "en")[:2]
    name = (first_name or "").strip() or {"es": "de nuevo", "pt": "de novo"}.get(lang, "there")
    return {"1": name, "2": when, "3": said}


_THANKS_FOR_OUTCOME = {
    "en": "Thanks — noted. Every answer like this makes Antar's readings sharper.",
    "es": "Gracias — anotado. Cada respuesta así hace más precisas las lecturas de Antar.",
    "pt": "Obrigado — anotado. Cada resposta assim deixa as leituras do Antar mais precisas.",
}


def outcome_thanks(lang: str) -> str:
    return _THANKS_FOR_OUTCOME.get((lang or "en")[:2], _THANKS_FOR_OUTCOME["en"])


# ── bridge: Yes/No "did it happen?" answers → prediction_outcomes ──
# [yesno-bridge 2026-10-02] Yes/No (KP Prashna) answers are collected by the
# existing check-back card into user_correlations (POST /api/v1/predictions/
# feedback). Mirror each into prediction_outcomes so the accuracy board sees KP
# results. Matching is by chart + nearest timestamp (both rows are written within
# a second of each other at answer time) — NOT by text: the claim keeps what was
# typed, the correlation row keeps the conversation layer's resolved question.
FEEDBACK_TO_OUTCOME = {"yes": "yes", "partial": "partly", "no": "no"}   # skipped → none
MATCH_WINDOW_S = 120


def _ts(v) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except Exception:
        return None


def find_yesno_claim(sb, chart_id: str, created_at) -> Optional[str]:
    t = _ts(created_at)
    if not (chart_id and t):
        return None
    lo = (t - timedelta(seconds=MATCH_WINDOW_S)).isoformat()
    hi = (t + timedelta(seconds=MATCH_WINDOW_S)).isoformat()
    try:
        rows = (sb.table("prediction_claims").select("id,created_at")
                .eq("chart_id", chart_id).eq("source", "ask_yesno")
                .gte("created_at", lo).lte("created_at", hi).limit(10).execute()).data or []
    except Exception as e:
        if not _table_missing(e):
            print(f"[outcomes] yesno match failed: {e}")
        return None
    best = min(rows, key=lambda r: abs(((_ts(r["created_at"]) or t) - t).total_seconds()),
               default=None)
    return best["id"] if best else None


def bridge_yesno_feedback(sb, correlation_id: str, status: str,
                          note: Optional[str] = None, via: str = "app") -> Optional[str]:
    """Mirror one Yes/No feedback answer into prediction_outcomes. Returns the
    claim id it was written to, or None. Never raises."""
    outcome = FEEDBACK_TO_OUTCOME.get((status or "").lower())
    if not outcome:
        return None
    try:
        rows = (sb.table("user_correlations").select("id,chart_id,concern,created_at")
                .eq("id", correlation_id).limit(1).execute()).data or []
        if not rows or rows[0].get("concern") != "yesno":
            return None
        claim_id = find_yesno_claim(sb, rows[0]["chart_id"], rows[0]["created_at"])
        if claim_id and record_outcome(sb, claim_id, outcome, note, via=via):
            return claim_id
    except Exception as e:
        print(f"[outcomes] yesno bridge skipped: {e}")
    return None



def reask_candidates(sb, now: Optional[datetime] = None) -> list:
    """Claims answered "not_sure" at least REASK_AFTER_DAYS ago that haven't been
    re-asked yet — each marked _reask=True for pick_due / checkin_text."""
    now = now or datetime.now(timezone.utc)
    try:
        outs = (sb.table("prediction_outcomes").select("claim_id,answered_at")
                .eq("outcome", "not_sure")
                .lte("answered_at", (now - timedelta(days=REASK_AFTER_DAYS)).isoformat())
                .limit(500).execute()).data or []
        if not outs:
            return []
        rows = (sb.table("prediction_claims")
                .select("id,chart_id,source,topic,claim_type,window_end,text_shown,language,"
                        "checkin_due_at,checkin_sent_at,checkin_channel")
                .in_("id", [o["claim_id"] for o in outs])
                .in_("source", list(CHECKIN_SOURCES)).execute()).data or []
    except Exception as e:
        if not _table_missing(e):
            print(f"[outcomes] reask lookup failed: {e}")
        return []
    return [dict(r, _reask=True) for r in rows if REASK_MARK not in (r.get("checkin_channel") or "")]


def reasks_awaiting_answer(sb, chart_id: str) -> list:
    """For the in-app card: re-asked "not_sure" claims not answered since the re-ask."""
    try:
        rows = (sb.table("prediction_claims").select("*").eq("chart_id", chart_id)
                .like("checkin_channel", f"%{REASK_MARK}").execute()).data or []
        if not rows:
            return []
        outs = {o["claim_id"]: o for o in (sb.table("prediction_outcomes")
                .select("claim_id,outcome,answered_at")
                .in_("claim_id", [r["id"] for r in rows]).execute().data or [])}
    except Exception as e:
        if not _table_missing(e):
            print(f"[outcomes] reask due lookup failed: {e}")
        return []
    out = []
    for r in rows:
        o = outs.get(r["id"])
        if (o and o.get("outcome") == "not_sure"
                and str(o.get("answered_at") or "") < str(r.get("checkin_sent_at") or "")):
            out.append(dict(r, _reask=True))
    return out
