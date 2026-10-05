"""[partner-lean 2026-10-04] "Build alone or bring in a partner?" gets ONE answer from
the chart's partnership reading (domain_fit, 7th house), said in sentence one.

Live (Jaime, same chart, same question): one run "a partner could reduce that load",
the next "keep autonomy — a partner adds complexity". Nothing deterministic decided it.
Guardrail scope unchanged: shape/approach/timing, never "this partner will work".
"""
import re
from typing import Optional

_ALONE = re.compile(r"(?i)\b(alone|solo|sola|by myself|on my own|sozinh[oa]|akel[ea]|khud)\b")
_PARTNER = re.compile(r"(?i)\b(partners?|co-?founders?|socios?|socias?|s[oó]ci[oa]s?|cofundador\w*|"
                      r"parceir[oa]s?|saa?jhedaar\w*)\b")


def is_alone_or_partner(question: str) -> bool:
    q = question or ""
    return bool(_ALONE.search(q) and _PARTNER.search(q))


def partner_case(chart_data: dict, dashas: dict, running_lords: Optional[set] = None) -> str:
    """'partner_yes' / 'partner_yes_later' / 'partner_solo' / '' from domain_fit."""
    try:
        from antar_engine.domain_fit import assess_domain_fit
        r = assess_domain_fit(chart_data, dashas, "business partner", "business",
                              running_lords=running_lords or set())
    except Exception:
        return ""
    if (r or {}).get("domain") != "partnership":
        return ""
    if r.get("alignment") == "supported":
        return "partner_yes_later" if r.get("period_fit") == "caution" else "partner_yes"
    return "partner_solo"


PARTNER_DIRECTIVE = {
    "partner_yes": ("PARTNER QUESTION — THE ANSWER IS: BRING IN THE RIGHT PARTNER. The reading backs "
                    "shared ownership for them. Say why in plain words and what kind of partner "
                    "(someone who covers what they don't want to carry). `next` = a concrete step to "
                    "find or test that partner. Never advise staying solo."),
    "partner_yes_later": ("PARTNER QUESTION — THE ANSWER IS: THE RIGHT PARTNER, BUT TEST BEFORE YOU "
                          "SIGN. The reading backs a partner, but this is a hazy stretch for formal "
                          "commitments — try them on one project now, formalize equity later. `next` = "
                          "the trial project step. Never say stay solo, never say sign now."),
    "partner_solo": ("PARTNER QUESTION — THE ANSWER IS: KEEP IT YOURS FOR NOW. The reading doesn't "
                     "back shared ownership right now — get help by contract or hire, not as an "
                     "equity partner, and revisit later. `next` = the one thing to hand off by "
                     "contract. Never advise taking a partner now."),
}

PARTNER_OPENER = {
    "partner_yes": {
        "en": "{n}the reading backs bringing in the right partner — this is work you don't have to carry alone.",
        "es": "{n}la lectura respalda sumar al socio indicado — esto no tienes que cargarlo sin ayuda.",
        "pt": "{n}a leitura apoia trazer o sócio certo — isso você não precisa carregar sem ajuda.",
        "hi": "{n}reading sahi partner laane ka saath deti hai — yeh sab akele uthana zaroori nahi.",
    },
    "partner_yes_later": {
        "en": "{n}the reading backs the right partner — but test it on one project now and formalize it later, not in this hazy stretch.",
        "es": "{n}la lectura respalda al socio indicado — pero pruébalo en un proyecto ahora y formalízalo después, no en este tramo confuso.",
        "pt": "{n}a leitura apoia o sócio certo — mas teste em um projeto agora e formalize depois, não neste trecho nebuloso.",
        "hi": "{n}reading sahi partner ka saath deti hai — par abhi ek project pe aazmao, paperwork baad mein karo, is dhundhle daur mein nahi.",
    },
    "partner_solo": {
        "en": "{n}the reading says keep it yours for now — bring in help by contract, not as a partner.",
        "es": "{n}la lectura dice que por ahora lo mantengas tuyo — suma ayuda por contrato, no como socio.",
        "pt": "{n}a leitura diz para manter isso seu por enquanto — traga ajuda por contrato, não como sócio.",
        "hi": "{n}reading kehti hai abhi ise apne paas rakho — madad contract pe lo, partner bana ke nahi.",
    },
}

_R = re.compile(r"(?i)\bpartner|\bsocio|\bs[oó]cio|\bsolo\b|\balone\b|akel|sozinh|by yourself|"
                r"on your own|autonom|\bsin ayuda\b")
PARTNER_RESTATE = {k: _R for k in PARTNER_OPENER}
