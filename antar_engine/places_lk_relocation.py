"""
antar_engine/places_lk_relocation.py
─────────────────────────────────────────────────────────────────────────────
PLACES — Layer 3: Lal Kitab relocation findings.

The relocation step (places_relocation.compute_relocated_chart) already
re-casts every planet's house for a candidate city (birth date/time are
unchanged; only the place moves the lagna, and with it each planet's house).

This layer reads those re-cast houses through two founder-locked Lal Kitab
lenses and reports ONLY what changes between the natal placement and the city:

  • karmic-debt houses (rin)  — LK_KARMIC_DEBTS
  • a planet's own house (pakka ghar) — PAKKA_GHAR

Output is verdict-free, planet-as-actor, NO house numbers, NO Sanskrit terms.
Each finding's `text` is composed here and is expected to be passed through the
Places strip layer by the caller (apply_user_facing_strips, source=
"curated_static"), consistent with the rest of /places/concern.
"""

from __future__ import annotations

from antar_engine.lk_trigger import PAKKA_GHAR

try:
    from antar_engine.lal_kitab_engine import LK_KARMIC_DEBTS
except Exception:                                       # pragma: no cover
    LK_KARMIC_DEBTS = {}


def _debt_houses() -> dict:
    """Parse 'Sun_6_or_12' -> {'Sun': {6, 12}} from the founder debt table."""
    out: dict[str, set] = {}
    for key in LK_KARMIC_DEBTS:
        parts = str(key).split("_")
        planet = parts[0]
        hs = {int(p) for p in parts[1:] if p.isdigit()}
        if hs:
            out.setdefault(planet, set()).update(hs)
    return out


_DEBT = _debt_houses()


def _lang(language) -> str:
    base = str(language or "en").split("_")[0].split("-")[0].lower()
    return base if base in ("en", "es", "pt") else "en"


# shift -> (polarity, {lang: template}).  {p} = planet, as actor.
# No house numbers, no Sanskrit; verdict-free framing.
_FRAMES = {
    "debt_lifted": ("supportive", {
        "en": "Here {p} steps off a long-standing weight it carries in your "
              "birth map — this ground asks less of it.",
        "es": "Aquí {p} se libera de un peso que arrastra en tu carta natal — "
              "este lugar le exige menos.",
        "pt": "Aqui {p} se livra de um peso que carrega no seu mapa natal — "
              "este lugar lhe exige menos.",
    }),
    "debt_taken": ("strain", {
        "en": "Here {p} picks up a weight it doesn't carry at home — this "
              "ground asks more care of it.",
        "es": "Aquí {p} asume un peso que no lleva en casa — este lugar le "
              "pide más cuidado.",
        "pt": "Aqui {p} assume um peso que não carrega em casa — este lugar "
              "lhe pede mais cuidado.",
    }),
    "came_home": ("supportive", {
        "en": "Here {p} settles onto its own ground — it works with "
              "noticeably less friction in this place.",
        "es": "Aquí {p} se asienta en su propio terreno — funciona con "
              "bastante menos fricción en este lugar.",
        "pt": "Aqui {p} se assenta no seu próprio terreno — funciona com bem "
              "menos atrito neste lugar.",
    }),
    "left_home": ("strain", {
        "en": "Here {p} steps off its own ground — it loses some of the ease "
              "it has at home.",
        "es": "Aquí {p} deja su propio terreno — pierde algo de la soltura que "
              "tiene en casa.",
        "pt": "Aqui {p} deixa o seu próprio terreno — perde parte da leveza "
              "que tem em casa.",
    }),
}

# Supportive shifts surface first; debt outranks home within each polarity.
_PRIORITY = {"debt_lifted": 0, "came_home": 1, "debt_taken": 2, "left_home": 3}


def lk_relocation_findings(relocation: dict, language: str = "en",
                           limit: int = 3) -> list[dict]:
    """
    Layer-3 LK findings for one relocated city.

    Args:
        relocation: a places_relocation.compute_relocated_chart() result.
        language:   en | es | pt (anything else degrades to en).
        limit:      max findings to return (default 3).

    Returns a (possibly empty) list of:
        {"planet": str, "shift": str, "polarity": "supportive"|"strain",
         "text": str}
    Empty when the relocation chart is unavailable or nothing changes.
    """
    if not relocation or not relocation.get("_available"):
        return []
    moved = relocation.get("relocated_planet_houses") or {}
    if not moved:
        return []

    L = _lang(language)
    findings: list[dict] = []
    for planet, mv in moved.items():
        nat_h = mv.get("natal_house")
        rel_h = mv.get("relocated_house")
        if nat_h is None or rel_h is None:
            continue
        try:
            nat_h, rel_h = int(nat_h), int(rel_h)
        except (TypeError, ValueError):
            continue

        debt_h = _DEBT.get(planet, set())
        home_h = set(PAKKA_GHAR.get(planet, []))

        shift = None
        # A debt change is the louder signal; check it before the home change.
        if nat_h in debt_h and rel_h not in debt_h:
            shift = "debt_lifted"
        elif nat_h not in debt_h and rel_h in debt_h:
            shift = "debt_taken"
        elif nat_h not in home_h and rel_h in home_h:
            shift = "came_home"
        elif nat_h in home_h and rel_h not in home_h:
            shift = "left_home"
        if not shift:
            continue

        polarity, frames = _FRAMES[shift]
        findings.append({
            "planet": planet,
            "shift": shift,
            "polarity": polarity,
            "text": frames[L].format(p=planet),
        })

    findings.sort(key=lambda f: (_PRIORITY.get(f["shift"], 9), f["planet"]))
    return findings[:limit]
