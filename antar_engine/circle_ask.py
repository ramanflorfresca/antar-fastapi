"""
antar_engine/circle_ask.py - pair-aware Ask: "When should Aarav and I sign?"

Deterministic, no LLM, no new astrology: a question that names someone in the asker's CIRCLE
(an active pair - never a private Person, which keeps today's behaviour) together with a joint
marker ("and I", "we", "together"...) and a topic is answered from that pair's shared windows
(circle_overlap), i.e. the same dated overlap the Between-us page shows. When the two charts do
not overlap the answer says so; no window is made up. Any doubt -> None, and Ask carries on
exactly as before.
"""
from __future__ import annotations

import re
from datetime import date
from typing import List, Optional

from antar_engine import circle_copy as CC
from antar_engine import topic_copy as C
from antar_engine.ask_subject import _fold, norm_name

# a joint marker, accent-folded (EN / ES / PT / Hinglish)
_JOINT = re.compile(
    r"\b(and i|and me|me and|i and|with me|with us|we|us|our|together|"
    r"y yo|yo y|conmigo|nosotros|nosotras|nos|juntos|juntas|nuestro|nuestra|"
    r"e eu|eu e|comigo|nos dois|nós|juntos|nosso|nossa|"
    r"aur main|main aur|mere saath|hum|humein|hume|saath|hamara|hamare)\b")

# topic words (folded). Order matters: first hit wins.
_TOPIC_WORDS = (
    ("business", r"sign|contract|deal|agreement|partnership|launch|firmar|contrato|acuerdo|assinar|contrato|negocio|business|sauda|hastakshar"),
    ("money", r"money|pay|loan|invest|price|buy|sell|dinero|pagar|prestamo|inversion|comprar|vender|dinheiro|pagar|emprestimo|investir|paisa|paise|udhaar|nivesh"),
    ("career", r"work|job|career|project|hire|trabajo|empleo|carrera|proyecto|trabalho|emprego|carreira|projeto|kaam|naukri"),
    ("love", r"love|marry|wedding|relationship|heart|talk|amor|boda|casar|relacion|casamento|casar|namoro|pyaar|shaadi|dil"),
    ("family", r"family|home|house|move|familia|casa|mudar|mudanca|parivaar|ghar"),
    ("health", r"health|doctor|surgery|salud|medico|saude|sehat"),
    ("peace", r"peace|calm|paz|sukoon|shanti"),
)


def topic_of(question: str) -> Optional[str]:
    t = _fold(question or "")
    for topic, pat in _TOPIC_WORDS:
        if re.search(r"\b(" + pat + r")", t):
            return topic
    return None


def detect(question: str, partners: List[dict]) -> Optional[dict]:
    """-> {partner, topic} or None. `partners` = [{chart_id, name}] of ACTIVE pairs only.
    Exactly one partner named, one joint marker, one recognised topic; otherwise None."""
    t = _fold(question or "")
    if not t.strip() or not _JOINT.search(t):
        return None
    hits = []
    for p in partners or []:
        n = norm_name(p.get("name") or "")
        if n and len(n) >= 2 and re.search(r"\b" + re.escape(_fold(p["name"]).strip().split(" ")[0]) + r"\b", t):
            hits.append(p)
    if len(hits) != 1:
        return None
    topic = topic_of(question)
    return {"partner": hits[0], "topic": topic} if topic else None


def answer(name: str, topic: str, pages: dict, lang: str) -> dict:
    """Ask payload from the pair's shared pages {"month": page, "season": page} (circle_overlap.build_page)."""
    lang = CC.lang_of(lang)
    label = C.LABEL[lang][topic].lower()
    best = care = None
    for scale in ("month", "season"):
        tp = next((x for x in (pages.get(scale) or {}).get("topics", []) if x["topic"] == topic), None)
        if not tp:
            continue
        if tp["best"] and best is None:
            best = tp["best"][0]
        if tp["care"] and care is None:
            care = tp["care"][0]
    if best:
        why = " ".join(best["reasoning"]["bullets"][:1])
        read = CC.pick(CC.ASK_BEST, lang).format(topic=label, name=name, range=best["label"], why=why).strip()
        if care:
            read += " " + CC.pick(CC.ASK_CARE, lang).format(range=care["label"])
    else:
        read = CC.pick(CC.ASK_NONE, lang).format(topic=label, name=name)
        if care:
            read += " " + CC.pick(CC.ASK_CARE, lang).format(range=care["label"])
    return {"mode": "explore", "read": read, "next": CC.pick(CC.ASK_NEXT, lang), "locked": False,
            "subject": {"name": name, "relation": "circle", "chart_available": True, "pair": True},
            "window": ({"start": best["start"], "end": best["end"], "label": best["label"]} if best else None)}
