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
        "dedupe_key": f"{chart_id}|{(topic or 'general').lower()}|{claim_type}|"
                      f"{start.isoformat() if start else ''}|{end.isoformat()}",
        "checkin_due_at": datetime.combine(end + timedelta(days=CHECKIN_DELAY_DAYS),
                                           datetime.min.time(), tzinfo=timezone.utc).isoformat(),
    }


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
    said = (claim.get("text_shown") or "").strip()
    head = said_t.format(said=said) if said and not sensitive else ""
    tail = moved_t.format(noun=noun) if (noun and claim.get("claim_type") == "window"
                                         and not sensitive) else plain_t
    return (head + "\n\n" + tail).strip()


def due_claims(sb, chart_id: str, now: Optional[datetime] = None, limit: int = 2) -> list:
    """Claims whose check-in is due and that have no outcome yet (oldest first)."""
    now = now or datetime.now(timezone.utc)
    try:
        rows = (sb.table("prediction_claims").select("*").eq("chart_id", chart_id)
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
