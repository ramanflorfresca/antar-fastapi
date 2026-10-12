"""
antar_engine/immigration.py

Deterministic IMMIGRATION / settle-abroad engine. Answers, from the real chart:
  • STRUCTURE — does the chart actually carry a "live abroad long-term" pull?
    (4th = homeland/roots against 12th = foreign residence and 9th = fortune in
    distant lands; Rahu as the boundary-crosser; Saturn = delay, not denial.)
  • PHASE — is the running chapter RELEASING (9th/12th lords, Jupiter, a placed
    Rahu) or SLOW (6th/8th lords, Saturn pressing the foreign houses)?
  • TIMING — the next window worth pushing on, via the shared multi-system
    convergence (dasha + transits + Chara + Lal-Kitab varshphal).

HONESTY BY DESIGN: a visa/lottery/cap outcome is set by the authorities, never by
the chart. We give a STRUCTURE read + a TIMING window + "delay vs denial" — never
an approval prediction, never a promise. The chart supports the lawyer, it does
not replace one. LLM narrates only. v1 — calibrate against real outcomes.
"""
from __future__ import annotations

import re
from typing import Optional

from antar_engine.d10_career import SIGN_LORD, _sign_n_from
from antar_engine.relationships import (
    _dig, _house_of, _in_house, _malefics_on, _benefics_on, _aspects)
from antar_engine.domain_timing import domain_convergence

_MOVABLE = {"Aries", "Cancer", "Libra", "Capricorn"}
_FIXED = {"Taurus", "Leo", "Scorpio", "Aquarius"}

IMMIGRATION_SPEC = {
    "noun": "a move or settlement abroad",
    "houses": [9, 12, 4, 7],
    "activator_houses": [9, 12],
    "karakas": ["Rahu", "Jupiter", "Saturn"],
    "varsh_houses": [9, 12],
    "transit_grahas": ["Rahu", "Jupiter", "Saturn"],
    "transit_houses": [9, 12],
    "malefic_varsh": False,
    "varsh_weight": 1.4,
    "min_score": 2.0,
}

_IMM_RE = re.compile(
    r"immigra|h-?1b|\bh 1b\b|green ?card|\buscis\b|work permit|permanent residen|"
    r"citizenship|naturali[sz]|\bi-?485\b|\beb-?[1-5]\b|\bstem opt\b|\bopt (extension|status)\b|"
    r"deport|asylum|settle abroad|settle in (the )?(us|usa|states|america|canada|uk|australia)|"
    r"\bvisa\b|\bpr (visa|status|card)\b|"
    r"inmigraci|tarjeta verde|residencia permanente|ciudadan[ií]a|"
    r"imigra[cç]|\bvisto\b|cidadania")
_NOT_IMM_RE = re.compile(r"visa (card|debit|credit|gift)|(credit|debit|gift) visa")


def is_immigration_q(question) -> bool:
    """True for visa / immigration / status / settle-abroad questions (en/es/pt).
    A plain 'visit/travel' question is NOT immigration."""
    ql = (question or "").lower()
    if not ql or _NOT_IMM_RE.search(ql):
        return False
    return bool(_IMM_RE.search(ql))


def analyze_immigration(chart_data: dict) -> dict:
    """Return {available, structure{level,score,flags,plain,nature}, delay, hidden_obstacles,
    summary}. Never raises."""
    try:
        cd = chart_data if isinstance(chart_data, dict) else {}
        d1 = cd.get("planets") or {}
        lagna = ((cd.get("lagna") or {}).get("sign"))
        if not d1 or not lagna:
            return {"available": False}

        def _lord(h):
            return SIGN_LORD.get(_sign_n_from(lagna, h))

        l4, l9, l12, l8, l6 = _lord(4), _lord(9), _lord(12), _lord(8), _lord(6)
        h_l4, h_l9, h_l12 = _house_of(l4, d1), _house_of(l9, d1), _house_of(l12, d1)
        s_l4 = (d1.get(l4) or {}).get("sign")

        push, pull = 0.0, 0.0
        flags, plain = [], []

        # 4th lord tied to foreign soil / distant lands
        if h_l4 == 12:
            push += 2.0
            flags.append("4th lord in 12th")
            plain.append("the home base itself is tied to a life away from where you started")
        elif h_l4 == 9:
            push += 1.0
            flags.append("4th lord in 9th")
            plain.append("roots and fortune in far places pull together")
        # 12th ↔ 4th / 9th ↔ 12th links
        if h_l12 == 4 or l12 in _in_house(d1, 4):
            push += 0.8
            flags.append("12th lord on the 4th")
            plain.append("the pull of foreign places sits right on the home front")
        if h_l9 == 12 or h_l12 == 9:
            push += 1.0
            flags.append("9th–12th link")
            plain.append("fortune and foreign residence are linked")
        # Rahu, the boundary-crosser
        rh = _house_of("Rahu", d1)
        if rh in (12, 9):
            push += 1.0
            flags.append(f"Rahu in {rh}")
            plain.append("a strong pull toward the unfamiliar and across borders")
        elif rh in (7, 8):
            push += 0.6
            flags.append(f"Rahu in {rh}")
        # malefic pressure on the 4th = a push outward from the homeland
        m4 = [p for p in _malefics_on(d1, 4) if p != "Saturn"]
        if m4:
            push += min(0.4 * len(m4), 1.0)
            flags.append("pressure on the 4th")
        # home-pull (roots) subtracts
        b4 = _benefics_on(d1, 4)
        if b4:
            pull += min(0.4 * len(b4), 0.8)
        if h_l4 in (1, 4) and _dig(l4, s_l4)[0] >= 0:
            pull += 0.8
            plain.append("the home base is steady and well placed — a real pull to stay rooted")

        score = round(push - pull, 2)
        level = "strong" if score >= 2.5 else "some" if score >= 1.2 else "weak"

        # a long stay vs. a recurring move (only meaningful when there IS a pull)
        nature = None
        if level != "weak" and h_l4 in (12, 9):
            if s_l4 in _FIXED:
                nature = "settled"
            elif s_l4 in _MOVABLE:
                nature = "recurring"

        # Saturn = delay, not denial
        sh = _house_of("Saturn", d1)
        delay = bool(sh in (9, 12, 4) or _aspects(sh, 9, "Saturn") or _aspects(sh, 12, "Saturn"))
        # hidden obstacles — the 8th house: paperwork, status mismatches, surprises
        hidden = bool(_malefics_on(d1, 8) or _house_of(l8, d1) in (6, 8, 12))

        summary = (f"Pull to settle abroad is {level}"
                   + (f" ({nature} pattern)" if nature else "")
                   + ("; expect slow, repeated steps rather than one clean pass" if delay else "")
                   + ".")
        return {"available": True,
                "structure": {"level": level, "score": score, "flags": flags,
                              "plain": plain[:3], "nature": nature},
                "delay": delay, "hidden_obstacles": hidden,
                "lords": {"l4": l4, "l9": l9, "l12": l12, "l6": l6, "l8": l8},
                "summary": summary}
    except Exception as e:
        return {"available": False, "error": str(e)[:160]}


def _split_label(label: str):
    parts = [x.strip() for x in (label or "").replace("–", "-").split("-")]
    return [p for p in parts if p]


def _tone_of(lords: list, chart_data: dict) -> str:
    """'releasing' | 'slow' | 'mixed' for a dasha chain, from the chart's own lords."""
    cd = chart_data or {}
    d1 = cd.get("planets") or {}
    lagna = ((cd.get("lagna") or {}).get("sign"))
    if not lagna or not lords:
        return "mixed"

    def _lord(h):
        return SIGN_LORD.get(_sign_n_from(lagna, h))

    l9, l12, l6, l8 = _lord(9), _lord(12), _lord(6), _lord(8)
    rahu_placed = _house_of("Rahu", d1) in (9, 12, 7, 11)
    sat_h = _house_of("Saturn", d1)
    sat_presses = bool(sat_h in (9, 12) or _aspects(sat_h, 9, "Saturn") or _aspects(sat_h, 12, "Saturn"))
    support = {l9, l12, "Jupiter"} | ({"Rahu"} if rahu_placed else set())
    block = ({l6, l8} | ({"Saturn"} if sat_presses else set())) - support
    sup = sum(1 for p in lords if p in support)
    blk = sum(1 for p in lords if p in block)
    if sup > blk:
        return "releasing"
    if blk > sup:
        return "slow"
    return "mixed"


def immigration_phase(chart_data: dict, dasha_str: Optional[str]) -> str:
    """Tone of the RUNNING chapter. dasha_str like 'Rahu-Jupiter' (MD-AD)."""
    return _tone_of(_split_label(dasha_str or ""), chart_data)


def immigration_timing(chart_data: dict, dashas: dict, birth_date: Optional[str] = None,
                       today: Optional[str] = None) -> dict:
    """Next windows worth pushing on (or waiting through) — multi-system convergence,
    each tagged releasing/slow/mixed. Returns {available, windows[], best, summary}."""
    res = domain_convergence(chart_data, dashas, IMMIGRATION_SPEC, birth_date=birth_date, today=today)
    if not res.get("available"):
        return res
    for w in res.get("windows", []):
        w["tone"] = _tone_of(_split_label(w.get("label", "")), chart_data)
    # prefer the best RELEASING window; a slow window is not a window to push on
    good = [w for w in res.get("windows", []) if w.get("tone") != "slow"]
    best = max(good, key=lambda w: w.get("score", 0)) if good else None
    res["best"] = best
    if best:
        res["summary"] = (f"The most workable window to push is around "
                          f"{best.get('year', best['start'][:4])} — {len(best['systems'])} systems line up.")
    else:
        res["summary"] = "No sharply-converging window ahead — no structural push flagged."
    return res


# ── chapter-verdict package for the Ask /predict immigration override ────────
# Honest by design: NEVER an approval prediction. band ∈ MIXED|WEAK (never
# FAVORABLE — a visa decision is the authority's, not ours).
def _imm_lang(language: str) -> str:
    b = str(language or "en").split("_")[0].split("-")[0].lower()
    return b if b in ("en", "es", "pt") else "en"


_IMM_LINE = {
    "weak": {
        "en": "Your chart doesn't show a strong pull to build a long-term life abroad — treat this as one route among several, and weigh a path nearer home or a points-based country seriously.",
        "es": "Tu carta no muestra una fuerte inclinación a construir una vida a largo plazo en el extranjero — trátalo como una ruta entre varias, y considera en serio un camino más cerca de casa o un país con sistema de puntos.",
        "pt": "Seu mapa não mostra uma forte inclinação a construir uma vida de longo prazo no exterior — trate isto como uma rota entre várias, e considere a sério um caminho mais perto de casa ou um país com sistema de pontos.",
    },
    "slow": {
        "en": "A life abroad is supported by your chart, but this stretch reads as slow rather than closed — a delay, not a denial. Expect repeated steps, not one clean pass.",
        "es": "Tu carta respalda una vida en el extranjero, pero esta etapa se lee lenta más que cerrada — una demora, no una negativa. Espera pasos repetidos, no un solo trámite limpio.",
        "pt": "Seu mapa sustenta uma vida no exterior, mas esta fase se lê lenta, não fechada — um atraso, não uma negativa. Espere passos repetidos, não uma passagem limpa.",
    },
    "releasing": {
        "en": "A life abroad is supported by your chart and the current stretch is a workable one to push — but approvals are decided by the rules and the draw, not by timing.",
        "es": "Tu carta respalda una vida en el extranjero y la etapa actual es buena para avanzar — pero las aprobaciones las deciden las reglas y el sorteo, no el momento.",
        "pt": "Seu mapa sustenta uma vida no exterior e a fase atual é boa para avançar — mas as aprovações são decididas pelas regras e pelo sorteio, não pelo momento.",
    },
    "mixed": {
        "en": "A life abroad is supported by your chart; the current stretch is neither a clear push nor a clear wait — prepare steadily and let the next window do the heavy lifting.",
        "es": "Tu carta respalda una vida en el extranjero; la etapa actual no es ni un claro impulso ni una clara espera — prepárate con constancia y deja que la próxima ventana haga el trabajo pesado.",
        "pt": "Seu mapa sustenta uma vida no exterior; a fase atual não é nem um claro impulso nem uma clara espera — prepare-se com constância e deixe a próxima janela fazer o trabalho pesado.",
    },
}
_IMM_MOVE = {
    "en": "Keep your status and paperwork impeccable and work with an immigration attorney — the next window to push is {win}.",
    "es": "Mantén tu estatus y tus documentos impecables y trabaja con un abogado de inmigración — la próxima ventana para avanzar es {win}.",
    "pt": "Mantenha seu status e seus documentos impecáveis e trabalhe com um advogado de imigração — a próxima janela para avançar é {win}.",
}
_IMM_MOVE_NOWIN = {
    "en": "Keep your status and paperwork impeccable and work with an immigration attorney — no single window stands out, so prepare steadily.",
    "es": "Mantén tu estatus y tus documentos impecables y trabaja con un abogado de inmigración — ninguna ventana destaca, así que prepárate con constancia.",
    "pt": "Mantenha seu status e seus documentos impecáveis e trabalhe com um advogado de imigração — nenhuma janela se destaca, então prepare-se com constância.",
}
_IMM_CHECK = {
    "en": " Double-check every document line by line — small mismatches are where surprises hide.",
    "es": " Revisa cada documento línea por línea — las pequeñas discrepancias son donde se esconden las sorpresas.",
    "pt": " Confira cada documento linha por linha — pequenas divergências são onde as surpresas se escondem.",
}
_IMM_DISCLAIM = {
    "en": "This is not legal or immigration advice — rules, caps and lotteries are set by the authorities, and an immigration attorney should handle the actual case.",
    "es": "Esto no es asesoría legal ni migratoria — las reglas, cupos y sorteos los fijan las autoridades, y un abogado de inmigración debe llevar el caso real.",
    "pt": "Isto não é aconselhamento jurídico nem migratório — regras, cotas e sorteios são definidos pelas autoridades, e um advogado de imigração deve conduzir o caso real.",
}


def immigration_verdict(level: str, phase: str, hidden_obstacles: bool, best_year,
                        language: str = "en") -> dict:
    """CHAPTER-level immigration verdict for the Ask /predict override. Never raises:
    {available, band, line, the_move, secondary_note, window_range, key}."""
    try:
        L = _imm_lang(language)
        if level == "weak":
            key = "weak"
        else:
            key = phase if phase in ("slow", "releasing") else "mixed"
        band = "WEAK" if key == "weak" else "MIXED"
        yr = str(best_year).strip() if best_year else ""
        win = {"en": f"around {yr}", "es": f"alrededor de {yr}", "pt": f"por volta de {yr}"}[L] if yr else ""
        line = _IMM_LINE[key][L] + (_IMM_CHECK[L] if hidden_obstacles and key != "weak" else "")
        move = _IMM_MOVE[L].format(win=win) if win else _IMM_MOVE_NOWIN[L]
        return {"available": True, "band": band, "line": line, "the_move": move,
                "secondary_note": _IMM_DISCLAIM[L],
                "window_range": win or {"en": "in the period ahead", "es": "en el periodo que viene",
                                        "pt": "no período à frente"}[L],
                "key": key}
    except Exception as e:
        return {"available": False, "error": str(e)[:160]}
