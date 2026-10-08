"""
antar_engine/compatibility_types.py

The ONE list of relationship types the "add a person" flow offers, with the order,
the group each belongs to, and a user-facing label in the reader's language.

Everything here is a view over the engine's own tables (compatibility_reasons holds
the types, their weights and their labels). A type appears in this list only if the
backend can actually compute it, and tests/test_compat_types_catalog.py fails if the
list, the engine tables, the wording or the languages ever drift apart.

No scoring lives here.
"""
from __future__ import annotations

from antar_engine import compatibility_reasons as _R

# The owner's eleven choices first, in this order; then the older types that are
# still live (stored sessions keep reading and displaying under them).
# "business" is not listed: business_partner is the same reading under the same
# label, so offering both would show two identical "Business partner" rows.
TYPE_ORDER = (
    "mother", "father", "daughter", "son", "girlfriend", "boyfriend", "husband", "wife",
    "employee", "business_partner", "cofounder", "friend",
    "spouse", "sibling", "family", "romantic", "parent", "child", "advisor", "boss-or-manager",
)
OWNER_FIRST = TYPE_ORDER[:12]
NOT_LISTED = ("business",)

# Headings the add flow groups the choices under: Parent (mother, father), Kids (son,
# daughter), Spouse (husband, wife), Partner (girlfriend, boyfriend) ...
TYPE_GROUP = {
    "mother": "parent", "father": "parent", "parent": "parent",
    "daughter": "kids", "son": "kids", "child": "kids",
    "sibling": "family", "family": "family",
    "husband": "spouse", "wife": "spouse", "spouse": "spouse",
    "girlfriend": "partner", "boyfriend": "partner", "romantic": "partner",
    "employee": "work", "business_partner": "work", "cofounder": "work",
    "boss-or-manager": "work", "business": "work",
    "friend": "friends", "advisor": "guidance",
}

GROUP_LABELS = {
    "parent":   {"en": "Parent", "es": "Padre o madre", "pt": "Pai ou mãe", "hinglish": "Mummy / Papa"},
    "kids":     {"en": "Kids", "es": "Hijos", "pt": "Filhos", "hinglish": "Bachche"},
    "spouse":   {"en": "Spouse", "es": "Cónyuge", "pt": "Cônjuge", "hinglish": "Pati / Patni"},
    "partner":  {"en": "Partner", "es": "Pareja", "pt": "Parceiro(a)", "hinglish": "Partner"},
    "family":   {"en": "Family", "es": "Familia", "pt": "Família", "hinglish": "Parivaar"},
    "work":     {"en": "Work", "es": "Trabajo", "pt": "Trabalho", "hinglish": "Kaam"},
    "friends":  {"en": "Friends", "es": "Amistades", "pt": "Amizades", "hinglish": "Dost"},
    "guidance": {"en": "Guidance", "es": "Guía", "pt": "Orientação", "hinglish": "Margdarshan"},
}


def group_label(group: str, language="en") -> str:
    lang = _R.label_lang(language)
    return GROUP_LABELS[group][lang]


# Types whose add flow asks "what position?" (free text, display only).
NEEDS_POSITION = ("employee",)


def is_romantic(compat_type: str) -> bool:
    """True when the reading is a romantic one (girlfriend / boyfriend / spouse and
    the older 'romantic'). It does NOT mean marriage factors are used: only spouse and
    the older 'romantic' use those (see compatibility_reasons.uses_marriage_kutas)."""
    return _R.engine_reason(compat_type) in ("romantic", "spouse")


def types_directory(language: str = "en") -> list:
    """[{id, label, group, romantic, needs_role, needs_position}] in display order."""
    out = []
    for tid in TYPE_ORDER:
        out.append({
            "id": tid,
            "label": _R.label_for(tid, language),
            "group": TYPE_GROUP[tid],
            "group_label": group_label(TYPE_GROUP[tid], language),
            "romantic": is_romantic(tid),
            "needs_role": bool(_R.REASON_DEFINITIONS[tid]["needs_role"]),
            "needs_position": tid in NEEDS_POSITION,
        })
    return out


# person_links.relation has a database CHECK on its twelve original values, so the
# one newer type that has no relation of its own is stored under the relation whose
# engine reads it, with its id kept in relation_detail. (mother, father, son,
# daughter, girlfriend and boyfriend already store under parent/child/romantic.)
STORED_RELATION = {"business_partner": "business"}
