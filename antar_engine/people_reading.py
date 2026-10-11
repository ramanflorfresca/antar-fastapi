"""[people-reading 2026-10-11] The reading STAGE of a saved connection, for the My connections list / sheet.

A connection is a reading of the two people: how they fit (layer 1, always), who leads what and what works / doesn't for the work
they are building (layer 2, "How to work with X" — generated when the user says what they are building together) and each person's
current cycle and when their timing lines up (layer 3 — generated when the user adds the product / pitch). The list endpoint used to
send only a score + badge, so the app could not tell a connection that has its roles read from one that has not, nor point the user at
the step that produces it. This is a pure, cheap reduction of the three stored layers — no LLM, no recompute.

  stage      highest layer that exists (1 | 2 | 3)
  has_roles  layer 2 exists  ("who should lead what" read)
  has_timing layer 3 exists  ("current cycles" read)
  headline   first sentence of layer 1, English only (the stored text has no other language; a wrong-language line is worse than none)
  next_step  "add_context" (tell us what you are building -> layer 2) | "add_product" (add the product / pitch -> layer 3) | None
  roles_auto cofounder / business: the deterministic who-leads-what read (partner_roles) is always present; add_context then SHARPENS it
"""
from __future__ import annotations

import re
from typing import Optional

_PLACEHOLDER_A = re.compile(r"\bPerson A\b")
_PLACEHOLDER_B = re.compile(r"\bPerson B\b")


def _first_sentence(text: str, cap: int = 200) -> str:
    t = re.sub(r"[*#_`>]+", "", str(text or "")).strip()
    t = re.sub(r"\s+", " ", t)
    m = re.match(r"(.+?[.!?])(\s|$)", t)
    s = (m.group(1) if m else t).strip()
    return s if len(s) <= cap else s[: cap - 1].rstrip() + "…"


_ROLE_TYPES = ("cofounder", "business", "employee", "boss", "boss-or-manager", "manager", "advisor", "mentor")


def stage(layer1, layer2, layer3, name_b: str = "", lang: str = "en", compat_type: str = "") -> dict:
    """The reading-stage dict for one saved session. Never raises."""
    try:
        has3 = bool(str(layer3 or "").strip())
        # a cofounder / business-partner reading always carries the deterministic who-leads-what read (partner_roles), whether or not the
        # longer written layer 2 exists; the next step then only SHARPENS it with what they are building
        has_l2 = bool(str(layer2 or "").strip())
        has2 = has_l2 or (compat_type or "") in _ROLE_TYPES
        head = None
        if (lang or "en").split("-")[0].lower() == "en" and str(layer1 or "").strip():
            head = _first_sentence(layer1)
            head = _PLACEHOLDER_A.sub("You", head)
            if name_b:
                head = _PLACEHOLDER_B.sub(str(name_b).strip(), head)
            head = head or None
        return {"stage": 3 if has3 else 2 if has2 else 1, "has_roles": has2, "has_timing": has3, "headline": head,
                "next_step": None if (has_l2 and has3) else ("add_product" if has_l2 else "add_context"),
                "roles_auto": (compat_type or "") in _ROLE_TYPES}
    except Exception:
        return {"stage": 1, "has_roles": False, "has_timing": False, "headline": None, "next_step": "add_context"}
