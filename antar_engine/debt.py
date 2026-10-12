"""
antar_engine/debt.py

Deterministic DEBT-pressure engine. Answers, from the real chart:
  • PRESSURE — how prone to debt/obligation strain (6th = loans & obligations,
    12th = outflow, 8th = other people's money; weak 2nd/11th = thin inflow).
  • RECOVERY — capacity to clear it (11th/2nd lords, Jupiter's grace on the money
    houses, a malefic in the 6th = classical "debts get beaten down").
  • TIMING — the next pressure window and the next RELIEF window, via the shared
    multi-system convergence.

HONESTY BY DESIGN: a lean, never a promise ("you'll be debt-free by X" is not
ours). Debt collection / bankruptcy / settlement is for a qualified professional.
LLM narrates only. v1 — calibrate against real outcomes.
"""
from __future__ import annotations

import re
from typing import Optional

from antar_engine.d10_career import SIGN_LORD, _sign_n_from
from antar_engine.relationships import (
    _dig, _house_of, _in_house, _malefics_on, _benefics_on, _aspects)
from antar_engine.domain_timing import domain_convergence

DEBT_PRESSURE_SPEC = {
    "noun": "debt and obligation pressure",
    "houses": [6, 8, 12, 2],
    "activator_houses": [6, 8, 12],
    "karakas": ["Saturn", "Rahu", "Mars"],
    "varsh_houses": [6, 12],
    "transit_grahas": ["Saturn", "Rahu", "Mars"],
    "transit_houses": [2, 6, 12],
    "malefic_varsh": True,
    "varsh_weight": 1.4,
    "min_score": 2.0,
}
DEBT_RELIEF_SPEC = {
    "noun": "income and debt relief",
    "houses": [2, 11, 6],
    "activator_houses": [2, 11],
    "karakas": ["Jupiter", "Venus", "Mercury"],
    "varsh_houses": [2, 11],
    "transit_grahas": ["Jupiter", "Venus"],
    "transit_houses": [2, 11],
    "malefic_varsh": False,
    "varsh_weight": 1.4,
    "min_score": 2.0,
}

_DEBT_RE = re.compile(
    r"\bdebts?\b|debt-free|in debt|\bowe\b|\bowed\b|\bowing\b|creditor|collections? agency|"
    r"debt collector|bankrupt|foreclos|repossess|insolven|loan default|default on (my|a|the) loan|"
    r"can'?t pay|cannot pay|unable to pay|pay(ing)? off (my|the|this)|\bemis?\b|"
    r"credit card (balance|debt|bill)|mortgage arrears|behind on (my )?(payments|rent|mortgage)|"
    r"deudas?\b|endeudad|acreedor|bancarrota|\bquiebra\b|"
    r"d[ií]vidas?\b|endividad|credor|fal[eê]ncia|"
    r"\bkarz[a]?\b|\bqarz\b|\budh?aar\b")


def is_debt_q(question) -> bool:
    """True for debt / loan-burden / bankruptcy questions (en/es/pt/hinglish).
    A 'raise funding / get a loan for my business' question is NOT a debt-pressure one."""
    ql = (question or "").lower()
    return bool(ql and _DEBT_RE.search(ql))


def analyze_debt(chart_data: dict) -> dict:
    """Return {available, pressure{level,score,plain}, recovery{level,score,plain},
    lean, nature, summary}. Never raises."""
    try:
        cd = chart_data if isinstance(chart_data, dict) else {}
        d1 = cd.get("planets") or {}
        lagna = ((cd.get("lagna") or {}).get("sign"))
        if not d1 or not lagna:
            return {"available": False}

        def _lord(h):
            return SIGN_LORD.get(_sign_n_from(lagna, h))

        l2, l6, l8, l11, l12 = _lord(2), _lord(6), _lord(8), _lord(11), _lord(12)

        def _dg(p):
            return _dig(p, (d1.get(p) or {}).get("sign"))[0]

        # ── PRESSURE ────────────────────────────────────────────────────────
        pr, pplain = 0.0, []
        for h, nm in ((6, "obligations"), (8, "other people's money"), (12, "outflow")):
            m = _malefics_on(d1, h)
            if m:
                pr += 0.4 * len(m)
        # inflow houses afflicted / their lords sent into the trouble houses
        for lord, nm in ((l2, "savings"), (l11, "income")):
            if _house_of(lord, d1) in (6, 8, 12):
                pr += 0.9
                pplain.append(f"{nm} gets pulled toward obligations and outflow")
        if _house_of(l6, d1) in (2, 11, 12):
            pr += 0.6
            pplain.append("obligations reach into your everyday money")
        if _house_of(l12, d1) in (2, 11):
            pr += 0.7
            pplain.append("spending runs into what you earn")
        for p in ("Saturn", "Rahu"):
            if _house_of(p, d1) in (2, 6):
                pr += 0.5
        if _dg(l2) < 0 or _dg(l11) < 0:
            pr += 0.6
            pplain.append("the money houses are under strain")
        p_level = "high" if pr >= 2.5 else "some" if pr >= 1.0 else "low"

        # ── RECOVERY ────────────────────────────────────────────────────────
        rc, rplain = 0.0, []
        if _dg(l11) > 0:
            rc += 0.9 + (0.4 if _dg(l11) >= 2 else 0)
            rplain.append("your income line is well supported")
        if _dg(l2) > 0:
            rc += 0.6
        jh = _house_of("Jupiter", d1)
        if jh and any(_aspects(jh, h, "Jupiter") or jh == h for h in (2, 11, 6)):
            rc += 1.0
            rplain.append("a protective, steadying hand is on your money")
        # a malefic IN the 6th classically defeats debts/enemies (upachaya)
        if any(_house_of(p, d1) == 6 for p in ("Mars", "Saturn", "Rahu", "Sun")):
            rc += 0.6
            rplain.append("pressure in obligations tends to get beaten down with effort")
        if _benefics_on(d1, 11):
            rc += 0.4
        r_level = "strong" if rc >= 2.2 else "some" if rc >= 1.0 else "thin"

        lean = ("recoverable" if rc - pr >= 0.8
                else "heavy" if pr - rc >= 1.2 else "contested")

        # what the debt tends to be ABOUT (a tendency, never a statement of fact)
        nature = None
        if _house_of(l12, d1) in (2, 11) or _malefics_on(d1, 12):
            nature = "spending"            # outflow outruns inflow
        if _house_of(l2, d1) in (6, 8, 12) or _house_of(l11, d1) in (6, 8, 12):
            nature = "shortfall"           # inflow too thin for the obligations
        if _house_of(l8, d1) in (2, 6, 11):
            nature = nature or "shared"    # other people's money (loans, joint)

        summary = (f"Debt pressure is {p_level}; capacity to clear it is {r_level} — "
                   f"the chart leans {lean}.")
        return {"available": True,
                "pressure": {"level": p_level, "score": round(pr, 2), "plain": pplain[:3]},
                "recovery": {"level": r_level, "score": round(rc, 2), "plain": rplain[:3]},
                "lean": lean, "nature": nature, "summary": summary}
    except Exception as e:
        return {"available": False, "error": str(e)[:160]}


def debt_timing(chart_data: dict, dashas: dict, birth_date: Optional[str] = None,
                today: Optional[str] = None) -> dict:
    """Next pressure window AND next relief window. Returns
    {available, pressure{best}, relief{best}, summary}."""
    pres = domain_convergence(chart_data, dashas, DEBT_PRESSURE_SPEC, birth_date=birth_date, today=today)
    rel = domain_convergence(chart_data, dashas, DEBT_RELIEF_SPEC, birth_date=birth_date, today=today)
    if not (pres.get("available") or rel.get("available")):
        return {"available": False}
    pb, rb = (pres.get("best") if pres.get("available") else None), (rel.get("best") if rel.get("available") else None)
    parts = []
    if pb:
        parts.append(f"Pressure peaks around {pb.get('year', pb['start'][:4])}.")
    if rb:
        parts.append(f"The best window for relief is around {rb.get('year', rb['start'][:4])}.")
    return {"available": True, "pressure": {"best": pb}, "relief": {"best": rb},
            "summary": " ".join(parts) or "No sharply-converging debt window ahead."}


# ── chapter-verdict package for the Ask /predict debt override ───────────────
# Honest by design: a LEAN + the relief window, never "you'll be debt-free".
# band ∈ MIXED|WEAK (never FAVORABLE).
def _debt_lang(language: str) -> str:
    b = str(language or "en").split("_")[0].split("-")[0].lower()
    return b if b in ("en", "es", "pt") else "en"


_DEBT_LINE = {
    "recoverable": {
        "en": "This reads as recoverable — your income line can carry it if you give it a plan. Steady, structured paydown is what turns that lean into a result.",
        "es": "Esto se lee como recuperable — tu línea de ingresos puede sostenerlo si le das un plan. Un pago constante y estructurado es lo que convierte esa inclinación en un resultado.",
        "pt": "Isto se lê como recuperável — sua linha de renda pode sustentar se você lhe der um plano. Pagamento constante e estruturado é o que transforma essa inclinação em resultado.",
    },
    "contested": {
        "en": "This reads as genuinely mixed — pressure and capacity are about even, so what you do now (a clear plan, no new obligations) decides which way it tips.",
        "es": "Esto se lee como genuinamente mixto — la presión y la capacidad están parejas, así que lo que hagas ahora (un plan claro, sin nuevas obligaciones) decide hacia dónde se inclina.",
        "pt": "Isto se lê como genuinamente misto — pressão e capacidade estão parelhas, então o que você faz agora (um plano claro, sem novas obrigações) decide para onde pende.",
    },
    "heavy": {
        "en": "The pressure here is heavy and the cushion is thin — treat restructuring or negotiating terms early as the smart play, not a last resort.",
        "es": "La presión aquí es fuerte y el colchón es delgado — trata reestructurar o negociar condiciones pronto como la jugada inteligente, no como último recurso.",
        "pt": "A pressão aqui é pesada e a margem é fina — trate reestruturar ou negociar condições cedo como a jogada inteligente, não como último recurso.",
    },
}
_DEBT_MOVE = {
    "en": "List every obligation, rank by interest and urgency, and talk to a qualified financial counsellor — relief is most workable {win}.",
    "es": "Lista cada obligación, ordénalas por interés y urgencia, y habla con un asesor financiero calificado — el alivio es más viable {win}.",
    "pt": "Liste cada obrigação, ordene por juros e urgência, e converse com um consultor financeiro qualificado — o alívio é mais viável {win}.",
}
_DEBT_MOVE_NOWIN = {
    "en": "List every obligation, rank by interest and urgency, and talk to a qualified financial counsellor — no single relief window stands out, so build steadily.",
    "es": "Lista cada obligación, ordénalas por interés y urgencia, y habla con un asesor financiero calificado — ninguna ventana de alivio destaca, así que avanza con constancia.",
    "pt": "Liste cada obrigação, ordene por juros e urgência, e converse com um consultor financeiro qualificado — nenhuma janela de alívio se destaca, então avance com constância.",
}
_DEBT_PEAK = {
    "en": " The squeeze is sharpest {peak} — avoid taking on new obligations then.",
    "es": " El apretón es más fuerte {peak} — evita asumir nuevas obligaciones entonces.",
    "pt": " O aperto é mais forte {peak} — evite assumir novas obrigações então.",
}
_DEBT_DISCLAIM = {
    "en": "This is not financial or legal advice — for collections, a lawsuit or bankruptcy, a qualified professional should handle the actual matter.",
    "es": "Esto no es asesoría financiera ni legal — para cobranzas, una demanda o una quiebra, un profesional calificado debe manejar el asunto real.",
    "pt": "Isto não é aconselhamento financeiro nem jurídico — para cobranças, um processo ou falência, um profissional qualificado deve conduzir o assunto real.",
}


def _when(L: str, yr) -> str:
    yr = str(yr).strip() if yr else ""
    if not yr:
        return ""
    return {"en": f"around {yr}", "es": f"alrededor de {yr}", "pt": f"por volta de {yr}"}[L]


def debt_verdict(lean: str, relief_year, peak_year=None, language: str = "en") -> dict:
    """CHAPTER-level debt verdict for the Ask /predict override. Never raises:
    {available, band, line, the_move, secondary_note, window_range}."""
    try:
        L = _debt_lang(language)
        lean = lean if lean in _DEBT_LINE else "contested"
        band = "WEAK" if lean == "heavy" else "MIXED"
        rel, peak = _when(L, relief_year), _when(L, peak_year)
        line = _DEBT_LINE[lean][L] + (_DEBT_PEAK[L].format(peak=peak) if peak else "")
        move = _DEBT_MOVE[L].format(win=rel) if rel else _DEBT_MOVE_NOWIN[L]
        return {"available": True, "band": band, "line": line, "the_move": move,
                "secondary_note": _DEBT_DISCLAIM[L],
                "window_range": rel or {"en": "in the period ahead", "es": "en el periodo que viene",
                                        "pt": "no período à frente"}[L]}
    except Exception as e:
        return {"available": False, "error": str(e)[:160]}
