"""
antar_engine/loan.py

Deterministic LOAN-APPROVAL lane ("will I be able to get a loan / mortgage / financing?") —
a different question from debt PAYOFF (antar_engine/debt.py). Answers, from the real chart:
  • ACCESS — how open the chart is to other people's money: 11th (gain) and 2nd (own funds)
    lords placed well, Jupiter/Venus graces on the money houses; 2nd/11th lords sent into the
    6/8/12 trouble houses, Saturn/Rahu pressing 2/11, a debilitated 11th lord all tighten it.
  • PHASE — is the running Mahadasha/Antardasha a supportive one to APPLY in (2nd/11th lords,
    Jupiter, Venus) or a strained one (6th/8th/12th lords)?
  • TIMING — the next window to apply, via the shared multi-system convergence.

HONESTY BY DESIGN: a lender decides on credit, income and terms — never the chart. We give an
ACCESS lean + a PHASE + a window, never "you will be approved". LLM narrates only. v1.

Business funding / investor questions are NOT this lane (they keep the existing funding path):
`is_loan_q` skips any question about a startup, investors or raising capital.
"""
from __future__ import annotations

import re
from typing import Optional

from antar_engine.d10_career import SIGN_LORD, _sign_n_from
from antar_engine.relationships import _dig, _house_of, _benefics_on, _malefics_on, _aspects
from antar_engine.domain_timing import domain_convergence

LOAN_SPEC = {
    "noun": "borrowing and financing",
    "houses": [2, 11, 6, 8],
    "activator_houses": [2, 11],
    "karakas": ["Jupiter", "Venus", "Mercury"],
    "varsh_houses": [2, 11],
    "transit_grahas": ["Jupiter", "Venus"],
    "transit_houses": [2, 11],
    "malefic_varsh": False,
    "varsh_weight": 1.4,
    "min_score": 2.0,
}

_LOAN_RE = re.compile(
    r"(get|take|apply for|applying for|qualify for|be approved for|secure|obtain)\s+(a |an |my |the )?"
    r"(personal |home |car |student |bank )?(loan|mortgage|financing|credit line|line of credit)|"
    r"(loan|mortgage|financing)\s+(approval|approved|application)|approve (my|the) (loan|mortgage)|"
    r"(loan|mortgage|financing)( application)? (be |get |gets |is |will be )?(approved|accepted)|"
    r"approved for (a |an |my |the )?(personal |home |car |student |bank )?(loan|mortgage|financing)|"
    r"\bborrow\b|"
    r"pedir un pr[eé]stamo|conseguir un pr[eé]stamo|solicitar un (pr[eé]stamo|cr[eé]dito)|"
    r"aprueben (mi|el) (pr[eé]stamo|cr[eé]dito)|aprobar mi (pr[eé]stamo|hipoteca)|"
    r"pedir um empr[eé]stimo|conseguir um empr[eé]stimo|aprovar meu (empr[eé]stimo|financiamento)|"
    r"aprovem (o meu|meu) (empr[eé]stimo|financiamento)")
_BUSINESS_RE = re.compile(
    r"startup|my business|my company|investor|venture|raise (money|funds|capital)|funding round|seed|"
    r"mi negocio|mi empresa|inversionista|meu neg[oó]cio|minha empresa|investidor")


def is_loan_q(question) -> bool:
    """True for personal loan / mortgage / financing APPROVAL questions (en/es/pt). Business-funding
    questions stay on the funding path; paying a loan OFF is debt, not this lane."""
    ql = (question or "").lower()
    if not ql or _BUSINESS_RE.search(ql):
        return False
    return bool(_LOAN_RE.search(ql))


def analyze_loan(chart_data: dict) -> dict:
    """Return {available, access{level,score,plain}, summary}. Never raises."""
    try:
        cd = chart_data if isinstance(chart_data, dict) else {}
        d1 = cd.get("planets") or {}
        lagna = ((cd.get("lagna") or {}).get("sign"))
        if not d1 or not lagna:
            return {"available": False}

        def _lord(h):
            return SIGN_LORD.get(_sign_n_from(lagna, h))

        l2, l11 = _lord(2), _lord(11)

        def _dg(p):
            return _dig(p, (d1.get(p) or {}).get("sign"))[0]

        sc, plain = 0.0, []
        if _dg(l11) > 0:
            sc += 0.9
            plain.append("your gains line is well supported")
        if _dg(l11) < 0:
            sc -= 0.8
        if _dg(l2) > 0:
            sc += 0.6
        if _house_of(l11, d1) in (1, 2, 5, 9, 11):
            sc += 0.8
            plain.append("income and fortune sit well together")
        if _house_of(l2, d1) in (1, 5, 9, 11):
            sc += 0.6
        for lord in (l2, l11):
            if _house_of(lord, d1) in (6, 8, 12):
                sc -= 0.9
        if _house_of(l2, d1) in (6, 8, 12) or _house_of(l11, d1) in (6, 8, 12):
            plain.append("savings or income get pulled toward obligations and outflow")
        for p in ("Jupiter", "Venus"):
            ph = _house_of(p, d1)
            if ph and any(ph == h or _aspects(ph, h, p) for h in (2, 11)):
                sc += 1.0 if p == "Jupiter" else 0.6
                plain.append("a steadying, generous hand is on your money" if p == "Jupiter"
                             else "goodwill around money and agreements")
        hard = [p for p in _malefics_on(d1, 2) + _malefics_on(d1, 11) if p in ("Saturn", "Rahu")]
        if hard:
            sc -= 0.5 * min(len(set(hard)), 2)
            plain.append("friction and delay around money matters")
        if _benefics_on(d1, 11):
            sc += 0.4
        level = "open" if sc >= 2.0 else "conditional" if sc >= 0.8 else "tight"
        return {"available": True,
                "access": {"level": level, "score": round(sc, 2), "plain": plain[:3]},
                "lords": {"l2": l2, "l11": l11, "l6": _lord(6), "l8": _lord(8), "l12": _lord(12)},
                "summary": f"Access to borrowed money reads {level}."}
    except Exception as e:
        return {"available": False, "error": str(e)[:160]}


def loan_phase(analysis: Optional[dict], dasha_str: Optional[str]) -> str:
    """'supportive' | 'strained' | 'mixed' for the RUNNING chain (MD-AD)."""
    try:
        lords = (analysis or {}).get("lords") or {}
        sup = {lords.get("l2"), lords.get("l11"), "Jupiter", "Venus"}
        blk = {lords.get("l6"), lords.get("l8"), lords.get("l12")} - sup
        parts = [x.strip().title() for x in str(dasha_str or "").replace("–", "-").split("-") if x.strip()][:2]
        s = sum(1 for p in parts if p in sup)
        b = sum(1 for p in parts if p in blk)
        return "supportive" if s > b else "strained" if b > s else "mixed"
    except Exception:
        return "mixed"


def loan_timing(chart_data: dict, dashas: dict, birth_date: Optional[str] = None,
                today: Optional[str] = None) -> dict:
    """Next window to apply — multi-system convergence. {available, windows[], best, summary}."""
    res = domain_convergence(chart_data, dashas, LOAN_SPEC, birth_date=birth_date, today=today)
    if not res.get("available"):
        return res
    best = res.get("best")
    res["summary"] = (f"The most workable window to apply is around {best.get('year', best['start'][:4])}."
                      if best else "No sharply-converging window ahead — no structural push flagged.")
    return res


# ── verdict package (Ask /predict) + lead phrase ─────────────────────────────
def _lang(language) -> str:
    b = str(language or "en").split("_")[0].split("-")[0].lower()
    return b if b in ("en", "es", "pt") else "en"


_LINE = {
    "open": {
        "en": "Your chart is open to borrowing — but a lender decides on your credit, income and terms, not on timing.",
        "es": "Tu carta está abierta al financiamiento — pero quien decide es el prestamista, según tu crédito, ingresos y condiciones, no el momento.",
        "pt": "Seu mapa está aberto a crédito — mas quem decide é o credor, pelo seu histórico, renda e condições, não pelo momento.",
    },
    "conditional": {
        "en": "Borrowing reads as conditional — possible with strong preparation and modest terms, not something to lean on.",
        "es": "Pedir prestado se lee condicional — posible con buena preparación y condiciones modestas, no algo en lo que apoyarse.",
        "pt": "Pegar crédito se lê condicional — possível com boa preparação e condições modestas, não algo em que se apoiar.",
    },
    "tight": {
        "en": "Access to borrowed money reads tight — treat a loan as the harder route and strengthen your own cushion first.",
        "es": "El acceso a dinero prestado se lee ajustado — trata un préstamo como la ruta más difícil y fortalece primero tu propio colchón.",
        "pt": "O acesso a dinheiro emprestado se lê apertado — trate um empréstimo como o caminho mais difícil e fortaleça primeiro sua própria reserva.",
    },
}
_PHASE = {
    "supportive": {"en": " This stretch is a workable one to apply.",
                   "es": " Esta etapa es buena para solicitar.",
                   "pt": " Esta fase é boa para solicitar."},
    "strained": {"en": " This stretch is better for preparing than for applying.",
                 "es": " Esta etapa es mejor para prepararte que para solicitar.",
                 "pt": " Esta fase é melhor para se preparar do que para solicitar."},
    "mixed": {"en": "", "es": "", "pt": ""},
}
_MOVE = {
    "en": "Check your credit report, document your income, and borrow only what a lean month can repay — the best window to apply is {win}.",
    "es": "Revisa tu reporte de crédito, documenta tus ingresos y pide solo lo que un mes flojo puede pagar — la mejor ventana para solicitar es {win}.",
    "pt": "Confira seu relatório de crédito, documente sua renda e peça só o que um mês fraco consegue pagar — a melhor janela para solicitar é {win}.",
}
_MOVE_NOWIN = {
    "en": "Check your credit report, document your income, and borrow only what a lean month can repay — no single window stands out, so prepare steadily.",
    "es": "Revisa tu reporte de crédito, documenta tus ingresos y pide solo lo que un mes flojo puede pagar — ninguna ventana destaca, así que prepárate con constancia.",
    "pt": "Confira seu relatório de crédito, documente sua renda e peça só o que um mês fraco consegue pagar — nenhuma janela se destaca, então prepare-se com constância.",
}
_DISCLAIM = {
    "en": "This is not financial advice — a lender decides on your actual credit, income and terms.",
    "es": "Esto no es asesoría financiera — el prestamista decide según tu crédito, ingresos y condiciones reales.",
    "pt": "Isto não é aconselhamento financeiro — o credor decide pelo seu crédito, renda e condições reais.",
}


def loan_verdict(level: str, phase: str, best_year, language: str = "en", caution: str = "") -> dict:
    """Never raises: {available, band, line, the_move, secondary_note, window_range}.
    band is MIXED|WEAK — never FAVORABLE (a lender's decision is not ours to promise)."""
    try:
        L = _lang(language)
        level = level if level in _LINE else "conditional"
        yr = str(best_year).strip() if best_year else ""
        win = {"en": f"around {yr}", "es": f"alrededor de {yr}", "pt": f"por volta de {yr}"}[L] if yr else ""
        line = _LINE[level][L] + _PHASE.get(phase, _PHASE["mixed"])[L] + (" " + caution if caution else "")
        return {"available": True, "band": "WEAK" if level == "tight" else "MIXED", "line": line,
                "the_move": _MOVE[L].format(win=win) if win else _MOVE_NOWIN[L],
                "secondary_note": _DISCLAIM[L],
                "window_range": win or {"en": "in the period ahead", "es": "en el periodo que viene",
                                        "pt": "no período à frente"}[L]}
    except Exception as e:
        return {"available": False, "error": str(e)[:160]}


def loan_lead_phrase(level: str, language: str = "en") -> str:
    """One-sentence Ask lead — a lean on ACCESS, never 'Yes/Likely/No'."""
    try:
        t = _LINE[level if level in _LINE else "conditional"][_lang(language)]
        return t
    except Exception:
        return ""
