"""[work-fit 2026-10-12] Which kinds of work run WITH this chart and which run AGAINST it (D-1 10th + D-10 + D-9 + dasha, via d10_career.analyze_career), and — once the person says what they do —
which tier THEIR work falls in: strong fit / workable / against the grain.

This is a FIT read, never a promise (the closed business study showed outcomes don't track planet strength): a line against the grain can work with will, but is expected to under-return effort;
a strong-fit line still needs execution. Timing and the 'is the window open' answer stay with the topic engines. Deterministic, en + es, never raises.
"""
import re
from typing import Any, Dict, List, Optional

# bucket -> (keywords that put THEIR text in the bucket, substrings that find the bucket in the engine's ranked field names, plain name, hands-on?)
_BUCKETS = {
    "tech":      (("software", "saas", " ai ", "ai agent", "agents", "artificial", "app ", "platform", "startup", "tech", "coding", "developer", "data ", "automation", "fintech", "cloud", "cyber", "web", "digital"),
                  ("technology", "it /", "software", "digital", "coding", "startups"), "technology & software", False),
    "research":  (("research", "science", "lab", "biotech", "analysis", "analyst"), ("research", "science", "investigation"), "research & analysis", False),
    "media":     (("media", "content", "writing", "writer", "journalism", "podcast", "youtube", "publishing", "marketing", "communication", "brand"), ("media", "communication", "writing", "publishing"), "media & communication", False),
    "arts":      (("design", "art", "film", "music", "fashion", "beauty", "creative", "photography"), ("arts", "design", "creative", "luxury", "entertainment"), "design & creative work", False),
    "law_fin":   (("law", "legal", "lawyer", "finance", "fintech", "bank", "invest", "payments", "lending", "credit", "accounting", "audit", "insurance", "wealth"), ("law", "finance", "banking", "accounting"), "law & finance", False),
    "health":    (("health", "medical", "doctor", "nurse", "therapy", "wellness", "clinic", "psychology", "pharma", "healing"), ("medicine", "healing", "care", "psychology", "surgery"), "health & care", False),
    "education": (("teach", "education", "school", "tutor", "training", "academy", "course", "coaching"), ("teaching", "academia"), "teaching & coaching", False),
    "advisory":  (("consult", "advisor", "advisory", "strategy"), ("consulting", "advisory"), "advisory & consulting", False),
    "network":   (("community", "nonprofit", "ngo", "network", "social impact", "diplomacy", "relations"), ("network", "community", "humanitarian", "diplomacy", "relationships"), "networks & community", False),
    "gov":       (("government", "public sector", "politic", "civil service", "policy"), ("government", "politics", "administration", "authority", "governance"), "government & leadership roles", False),
    "trade":     (("trading", "trader", "wholesale", "import", "export", "commerce", "e-commerce", "ecommerce", "dropship"), ("commerce", "trade", "foreign", "international"), "trade & commerce", False),
    "food_hosp": (("food", "restaurant", "cafe", "coffee", "catering", "bakery", "bar ", "hotel", "hospitality", "flower", "florist", "grocery", "kitchen", "delivery"), ("food", "hospitality", "public-facing", "serving the public"), "food, flowers & hospitality", True),
    "retail_inv": (("retail", "shop", "store", "inventory", "boutique", "merchandise", "supermarket", "pharmacy shop"), ("retail", "inventory"), "retail & physical inventory", True),
    "ops_heavy": (("logistics", "transport", "manufactur", "factory", "construction", "warehouse", "fleet", "agricultur", "farming", "mining", "supply chain"), ("operations", "construction", "heavy industry", "manufacturing", "agriculture"), "operations-heavy businesses", True),
    "realestate": (("real estate", "property", "realtor", "developer of homes", "rental"), ("real estate",), "real estate", True),
}
_ES_NAME = {"technology & software": "tecnología y software", "research & analysis": "investigación y análisis", "media & communication": "medios y comunicación",
            "design & creative work": "diseño y trabajo creativo", "law & finance": "derecho y finanzas", "health & care": "salud y cuidado", "teaching & coaching": "enseñanza y coaching",
            "advisory & consulting": "asesoría y consultoría", "networks & community": "redes y comunidad", "government & leadership roles": "gobierno y roles de liderazgo",
            "trade & commerce": "comercio", "food, flowers & hospitality": "comida, flores y hospitalidad", "retail & physical inventory": "comercio minorista e inventario físico",
            "operations-heavy businesses": "negocios con mucha operación", "real estate": "bienes raíces"}
_ES_FIELD = {"technology & innovation": "tecnología e innovación", "science & research": "ciencia e investigación", "networks / community / humanitarian": "redes, comunidad y causas humanitarias",
             "law & diplomacy": "derecho y diplomacia", "communication & media": "comunicación y medios", "arts & design": "arte y diseño"}
_TX = {
    "en": {"strong": "Strong fit", "workable": "Workable", "against": "Against the grain", "unknown": "",
           "why_strong": "{what} sits in a lane your chart favours most.", "why_workable": "{what} is workable, but it isn't where your chart stands out.",
           "why_against": "{what} runs against your chart's grain: it is {mode}. It can still work with will, but expect it to under-return the effort you put in.",
           "mode_hands": "a hands-on, operations-heavy kind of work", "caveat": "This is a fit read, not a guarantee: strong fit still needs execution, and a low-fit line can work with will.",
           "best_h": "Strongest lanes for you", "uphill_h": "Uphill for you"},
    "es": {"strong": "Buen encaje", "workable": "Viable", "against": "A contracorriente", "unknown": "",
           "why_strong": "{what} está en una de las áreas que más favorece tu carta.", "why_workable": "{what} es viable, pero no es donde tu carta destaca.",
           "why_against": "{what} va a contracorriente de tu carta: es {mode}. Aun así puede funcionar con voluntad, pero espera que rinda menos que el esfuerzo que le pones.",
           "mode_hands": "un trabajo práctico y con mucha operación", "caveat": "Es una lectura de encaje, no una garantía: un buen encaje aún necesita ejecución, y una línea de bajo encaje puede funcionar con voluntad.",
           "best_h": "Tus áreas más fuertes", "uphill_h": "Cuesta arriba para ti"},
}


def buckets_of(text: Any) -> List[str]:
    """Every bucket the person's words touch (a 'fintech app' is both tech and finance), strongest match first."""
    t = " " + re.sub(r"[^a-z0-9áéíóúñ/&\- ]", " ", str(text or "").lower()) + " "
    def has(k):          # word-start match (so "art" does not fire inside "startup"); short keywords ("ai", "ngo", "bar") must also end on a word boundary
        k = k.strip()
        return bool(re.search(r"(?<![a-z0-9áéíóúñ])" + re.escape(k) + (r"(?![a-z0-9áéíóúñ])" if len(k) <= 3 else ""), t))
    hits = [(sum(1 for k in kws if has(k)), b) for b, (kws, _f, _n, _h) in _BUCKETS.items()]
    return [b for n, b in sorted(hits, key=lambda x: -x[0]) if n]


def bucket_of(text: Any) -> Optional[str]:
    bs = buckets_of(text)
    return bs[0] if bs else None


def _rank_of(careers: List[dict], bucket: str) -> Optional[int]:
    subs = _BUCKETS[bucket][1]
    for i, c in enumerate(careers):
        f = str(c.get("field") or "").lower()
        if any(s in f for s in subs):
            return i
    return None


def fit(careers: List[dict], what: Any = "", lang: str = "en") -> Optional[dict]:
    """careers: analyze_career()['careers'] (ranked {field, weight}). `what`: the person's own words (optional). None when there is no ranking."""
    careers = [c for c in (careers or []) if isinstance(c, dict) and c.get("field")]
    if not careers:
        return None
    lang = "es" if lang == "es" else "en"
    tx = _TX[lang]
    fl = (lambda f: _ES_FIELD.get(f, f)) if lang == "es" else (lambda f: f)
    best = [fl(c["field"]) for c in careers[:3]]
    uphill = []
    for b, (_k, _f, name, hands) in _BUCKETS.items():
        if hands and _rank_of(careers, b) is None:
            uphill.append(_ES_NAME.get(name, name) if lang == "es" else name)
    out = {"best_label": tx["best_h"], "best": best, "uphill_label": tx["uphill_h"], "uphill": uphill[:4], "workable": [fl(c["field"]) for c in careers[3:6]],
           "tier": None, "label": None, "why": None, "caveat": tx["caveat"]}
    what = str(what or "").strip()
    bs = buckets_of(what) if what else []
    if not bs:
        return out
    # MODE over sector: a hands-on / perishable / operations-heavy line is against the grain unless the chart puts that lane in its TOP three — even when it is wrapped in "tech"
    # (the software layer doesn't remove the daily-logistics drag). Otherwise a line touching several lanes takes its BEST-ranked one; unranked non-hands-on work is just workable.
    ranks = {b: _rank_of(careers, b) for b in bs}
    hands = [b for b in bs if _BUCKETS[b][3]]
    if hands and all(ranks[b] is None or ranks[b] > 2 for b in hands):
        tier = "against"
    else:
        ranked = [r for r in ranks.values() if r is not None]
        tier = "strong" if ranked and min(ranked) <= 2 else "workable"
    out["tier"], out["label"] = tier, tx[tier]
    out["why"] = tx["why_" + tier].format(what=what, mode=tx["mode_hands"])
    return out
