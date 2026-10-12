"""
antar_engine/case_now.py

The "RIGHT NOW" read for a creditor matter — a moment (Prashna) chart cast for the instant of
the question, judged with the SAME user-vs-other-side posture as the natal read
(debt.analyze_creditor). Classical rule: the birth chart shows the promise, the moment chart
shows the present reality — so the natal posture is the base and this adds only what is true
right now (and says so when the two agree).

DOCTRINE: cast at the fixed astrologer's seat (Edgewater, NJ — same as the KP horary), houses
whole-sign from the moment's ascendant sign so the same analyzers read it. This is an ADDITIONAL
clause inside the normal answer. It is NOT the Yes/No Prashna oracle: it never produces a
verdict, never routes the question, and carries no outcome claim — a negotiating posture only.
Never raises.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from antar_engine.d10_career import SIGNS

_PLANETS = {"Sun": 0, "Moon": 1, "Mercury": 2, "Venus": 3, "Mars": 4, "Jupiter": 5, "Saturn": 6}


def moment_chart_data(now: Optional[datetime] = None) -> dict:
    """chart_data-shaped dict ({lagna:{sign}, planets:{name:{sign,house}}}) for the moment at the
    astrologer's seat, whole-sign houses. {} if the ephemeris is unavailable."""
    try:
        from antar_engine.kp.kp_prashna import ASTROLOGER_SEAT
        from antar_engine.prashna_engine import cast_prashna_chart, planet_name_from_id
        now = now or datetime.now(timezone.utc)
        c = cast_prashna_chart(ASTROLOGER_SEAT["lat"], ASTROLOGER_SEAT["lon"], now)
        li = int(c["lagna_sign"]) % 12
        planets = {}
        for pid, p in (c.get("planets") or {}).items():
            name = planet_name_from_id(pid)
            si = int(p["sign"]) % 12
            planets[name] = {"sign": SIGNS[si], "house": (si - li) % 12 + 1}
        for name, key in (("Rahu", "rahu_longitude"), ("Ketu", "ketu_longitude")):
            si = int(float(c[key]) / 30) % 12
            planets[name] = {"sign": SIGNS[si], "house": (si - li) % 12 + 1}
        return {"lagna": {"sign": SIGNS[li]}, "planets": planets}
    except Exception:
        return {}


def creditor_now(now: Optional[datetime] = None) -> dict:
    """{available, posture, user_score, creditor_score} read on the moment chart."""
    from antar_engine.debt import analyze_creditor
    cd = moment_chart_data(now)
    return analyze_creditor(cd) if cd else {"available": False}


def _lang(language) -> str:
    b = str(language or "en").split("_")[0].split("-")[0].lower()
    return b if b in ("en", "es", "pt") else "en"


_AGREES = {
    "en": " That holds right now as well.",
    "es": " Eso se sostiene también ahora mismo.",
    "pt": " Isso também se sustenta agora.",
}
_NOW = {
    "user_ahead": {
        "en": " Right now you hold the better hand — a good moment to open the conversation yourself.",
        "es": " Ahora mismo tienes la mejor mano — buen momento para abrir tú la conversación.",
        "pt": " Agora você tem a melhor mão — bom momento para abrir você mesmo a conversa.",
    },
    "creditor_ahead": {
        "en": " Right now the other side is pressing harder — don't leave their contact unanswered.",
        "es": " Ahora mismo la otra parte presiona más — no dejes su contacto sin responder.",
        "pt": " Agora a outra parte pressiona mais — não deixe o contato dela sem resposta.",
    },
    "evenly_matched": {
        "en": " Right now it reads balanced — no need to rush a decision either way.",
        "es": " Ahora mismo se lee parejo — no hace falta apresurar una decisión.",
        "pt": " Agora se lê equilibrado — não há necessidade de apressar uma decisão.",
    },
    "both_quiet": {
        "en": " Right now neither side is pressing — a quiet moment to get your own paperwork in order.",
        "es": " Ahora mismo ninguna parte presiona — un momento tranquilo para ordenar tus propios papeles.",
        "pt": " Agora nenhum dos lados pressiona — um momento calmo para organizar seus próprios papéis.",
    },
}


def now_clause(natal_posture: str, now_posture: Optional[str], language: str = "en") -> str:
    """The extra sentence for the answer: confirms when the moment agrees with the natal posture,
    otherwise says what is true right now. '' if the moment read is unavailable."""
    try:
        if not now_posture:
            return ""
        L = _lang(language)
        return _AGREES[L] if now_posture == natal_posture else _NOW[now_posture][L]
    except Exception:
        return ""
