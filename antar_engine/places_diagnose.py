"""
antar_engine/places_diagnose.py
─────────────────────────────────────────────────────────────────────────────
PLACES — diagnostic-first relocation ("prescribe", not "leaderboard").

Owner's method (2026-09-28): don't make the user pick a concern and hand back
five near-identical far-flung cities. Read the chart FIRST — score the person's
CURRENT city across every life-area to find where they're actually STUCK (the
afflicted / low-support domains, which for someone still in their birthplace is
their natal setup), then prescribe places that specifically LIFT that problem
area, feasibility-first, with plain "this is stuck → this place improves it"
reasoning. "You can't outrun your dasha by moving, but the right place eases the
area your chart struggles with most."

This module owns the DIAGNOSIS (what's the problem). The endpoint reuses the
existing places scoring to build the PRESCRIPTION (which feasible place fixes it)
and reuses places_what_changes for the per-city relocation reasoning.

Plain-language throughout (no house numbers, no Sanskrit); a strip pass in the
endpoint is the backstop.
"""
from __future__ import annotations
from typing import Optional

from antar_engine.places_concern import score_city_for_concern, resolve_concern

# The life-areas we diagnose. Kept tight and non-overlapping so the "biggest
# problem" is a real signal, not a coin-flip between synonyms (business folds
# into career for the diagnosis; the prescription can still target either).
PROBLEM_CONCERNS = ["health", "career", "money", "love", "family", "peace"]

PROBLEM_LABEL = {
    "en": {"health": "health and energy", "career": "career and work",
           "money": "money and cash flow", "love": "love and partnership",
           "family": "home and family", "peace": "peace of mind"},
    "es": {"health": "salud y energía", "career": "carrera y trabajo",
           "money": "dinero y flujo de caja", "love": "amor y pareja",
           "family": "hogar y familia", "peace": "paz interior"},
    "pt": {"health": "saúde e energia", "career": "carreira e trabalho",
           "money": "dinheiro e fluxo de caixa", "love": "amor e parceria",
           "family": "lar e família", "peace": "paz de espírito"},
}

# A home-city score at/below this reads as "you're struggling with this here".
STUCK_MAX = 42
# A relocation only counts as a real fix if it beats the home city by this much.
MEANINGFUL_LIFT = 8


def _lang(language: Optional[str]) -> str:
    l = (language or "en").split("-")[0].lower()
    return l if l in ("en", "es", "pt") else "en"


def diagnose_home_city(chart: dict, home_city: Optional[dict], dasha_lords,
                       conditions: dict, all_lines: list) -> list[dict]:
    """Score the CURRENT city across life-areas. Returns worst-first:
      [{concern, score, tier}], lower score = where the person is most stuck.
    Empty list when there is no resolvable home city (caller falls back)."""
    if not home_city:
        return []
    out = []
    for cn in PROBLEM_CONCERNS:
        try:
            s = score_city_for_concern(
                chart, home_city, cn, dasha_lords=dasha_lords,
                conditions=conditions, all_lines=all_lines)
            sc = s.get("score")
            if isinstance(sc, (int, float)):
                out.append({"concern": cn, "score": float(sc),
                            "tier": s.get("tier")})
        except Exception:
            continue
    out.sort(key=lambda x: x["score"])
    return out


def rank_problems(home_scores: list[dict], best_lift_by_concern: dict) -> list[dict]:
    """Combine severity (how stuck at home) with fixability (how much a feasible
    move lifts it) → the problems worth acting on, worst/most-fixable first.
    `best_lift_by_concern` = {concern: improvement_over_home (>=0)}.
    A domain only ranks as an actionable problem when it's stuck AND a real lift
    exists (a domain that's weak everywhere isn't a 'move fixes it' story)."""
    ranked = []
    for row in home_scores:
        cn = row["concern"]
        lift = float(best_lift_by_concern.get(cn, 0.0))
        stuck = row["score"] <= STUCK_MAX or (row.get("tier") == "STRAIN")
        fixable = lift >= MEANINGFUL_LIFT
        if not (stuck and fixable):
            continue
        # Lead with the stuck area a FEASIBLE move helps MOST — lift is the point
        # (a place that barely improves your worst area is a weaker recommendation
        # than one that clearly lifts a genuinely stuck area). Severity is a
        # secondary weight so a deeply-stuck area still counts, and the tie-break.
        severity = max(0.0, STUCK_MAX - row["score"])
        ranked.append({**row, "lift": lift, "severity": severity,
                       "priority": lift + 0.5 * severity})
    ranked.sort(key=lambda x: (-x["priority"], -x["lift"]))
    return ranked


def diagnosis_line(lead: Optional[dict], home_name: str, is_birthplace: bool,
                   language: str) -> str:
    """The opening 'here's your problem' sentence (or the well-placed one)."""
    lang = _lang(language)
    home = home_name or {"en": "where you live now", "es": "donde vives ahora",
                         "pt": "onde você mora agora"}[lang]
    if not lead:
        return {
            "en": f"Your chart is broadly well-supported where you live — no single "
                  f"life-area is stuck in a way a move would clearly fix. Somewhere "
                  f"else can shift the emphasis, but nothing here is calling you away.",
            "es": f"Tu carta está bien sostenida donde vives — ninguna área concreta "
                  f"está tan bloqueada como para que una mudanza la arregle. Otro lugar "
                  f"puede cambiar el énfasis, pero nada aquí te empuja a irte.",
            "pt": f"Seu mapa está bem apoiado onde você mora — nenhuma área está tão "
                  f"travada que uma mudança resolveria. Outro lugar pode mudar a ênfase, "
                  f"mas nada aqui te empurra para partir.",
        }[lang]
    label = PROBLEM_LABEL[lang][lead["concern"]]
    if is_birthplace:
        stuck = {
            "en": f"Your {label} is where a move would help you most — it's under real "
                  f"strain, and because you still live where you were born, that's your "
                  f"chart running on its original setup, unrelieved.",
            "es": f"Tu {label} es el área con más tensión — y como sigues en tu lugar de "
                  f"nacimiento, es tu carta funcionando en su configuración original, sin alivio.",
            "pt": f"Sua {label} é a área sob mais tensão — e como você ainda está no lugar "
                  f"onde nasceu, é o seu mapa rodando na configuração original, sem alívio.",
        }[lang]
    else:
        stuck = {
            "en": f"Your {label} is where a move would help you most — it's under real "
                  f"strain, and {home} isn't giving it much support.",
            "es": f"Tu {label} es el área con más tensión, y {home} no le da mucho apoyo.",
            "pt": f"Sua {label} é a área sob mais tensão, e {home} não lhe dá muito apoio.",
        }[lang]
    fix = {
        "en": " The places below are chosen for one thing: they lift exactly this area.",
        "es": " Los lugares de abajo se eligen por una cosa: elevan justamente esta área.",
        "pt": " Os lugares abaixo são escolhidos por uma coisa: eles elevam justamente esta área.",
    }[lang]
    return stuck + fix


def fix_line(concern: str, language: str) -> str:
    """One plain line stating WHAT a fix-city does for the diagnosed problem."""
    lang = _lang(language)
    label = PROBLEM_LABEL[lang][concern]
    return {
        "en": f"Here your {label} gets support it doesn't have at home.",
        "es": f"Aquí tu {label} recibe un apoyo que no tiene en casa.",
        "pt": f"Aqui sua {label} recebe um apoio que não tem em casa.",
    }[lang]
