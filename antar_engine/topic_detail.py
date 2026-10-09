"""Topic depth: the analysis the Today / This month / This year / Life chapter views used to show,
filtered to ONE topic and attached to `GET /chart/{id}/topic-read` as `detail`.

Pure and deterministic: no network, no LLM. The route loads each source engine's payload ONCE per
request (daily signal, monthly deep-dive, annual plan, life arc) and every topic is cut from those
same dicts. Engine strings are kept as the engine wrote them; nothing is invented. A section with
nothing to say is None, and the whole `detail` is None when its engine had nothing.

ONE mapping table (DOMAIN_TOPICS) turns every engine's own domain word onto the seven topic keys;
a domain not listed (travel, legal, ...) is skipped. Items that carry no domain are matched on
words (_WORDS, en/es/pt/hinglish); an item that matches no topic at all is kept under `day`
rather than dropped, an item that clearly belongs to ANOTHER topic is left out.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Dict, List, Optional

from antar_engine import topic_copy as C

# ── the one domain table ─────────────────────────────────────────────────────
# Every engine's domain word -> the topic keys it informs. Lower-case; labels are normalised first.
DOMAIN_TOPICS: Dict[str, tuple] = {
    "money": ("money",), "wealth": ("money",), "finance": ("money",), "income": ("money",),
    "money & wealth": ("money",),
    "speculation": ("money", "business"), "risk & speculation": ("money", "business"),
    "work": ("career", "business"), "career": ("career",), "work & reputation": ("career", "business"),
    "business": ("business",), "venture": ("business",),
    "body": ("health",), "health": ("health",), "energy": ("health",),
    "mind": ("peace",), "spiritual": ("peace",), "inner life": ("peace",), "peace": ("peace",),
    "people": ("love", "family"), "relationship": ("love",), "relationships": ("love",), "love": ("love",),
    "family": ("family",), "home": ("family",), "home & property": ("family",),
}
# life-event categories on the long-view timeline
CATEGORY_TOPICS: Dict[str, tuple] = {
    "WORK": ("career", "business"), "CAREER": ("career",), "BUSINESS": ("business",),
    "WEALTH": ("money",), "MONEY": ("money",), "FINANCE": ("money",),
    "RELATIONSHIP": ("love",), "MARRIAGE": ("love",), "LOVE": ("love",),
    "HEALTH": ("health",), "FAMILY": ("family",), "CHILDREN": ("family",), "HOME": ("family",),
    "PROPERTY": ("family",),
}
RISK_KEYS = ("speculation",)   # a domain that means "go easy on risk"


def topics_for(domain) -> tuple:
    return DOMAIN_TOPICS.get(re.sub(r"\s+", " ", str(domain or "").strip().lower()), ())


# ── words (for items that carry no domain) ───────────────────────────────────
_WORDS = {
    "money": r"money|income|invoice|pric(?:e|ing)|pay(?:ment|out|ments)?\b|paid|salar|spend|expens|purchase|saving|"
             r"loan|debt|credit|invest|financ|wealth|cash|bet\b|bets\b|speculat|gambl|position|budget|profit|"
             r"dinero|ingres|factura|precio|pago|salario|gast|compra|ahorr|pr[eé]stamo|deuda|invers|riqueza|apuesta|especul|"
             r"dinheiro|renda|fatura|pre[cç]o|pagamento|sal[aá]rio|poupan|empr[eé]stimo|d[ií]vida|aposta|"
             r"paisa|paise|kharch|nivesh|udhaar|bhugtan|kamai|daav",
    "career": r"work|job|career|boss|promotion|pitch|meeting|interview|colleague|project|deadline|recogni|reputation|visible|"
              r"trabajo|empleo|carrera|jefe|ascenso|reuni[oó]n|proyecto|reconoc|reputaci|"
              r"trabalho|emprego|carreira|chefe|promo[cç][aã]o|reuni[aã]o|projeto|reputa[cç]|"
              r"kaam|naukri|pad\b",
    "business": r"business|client|customer|partner|deal\b|deals\b|contract|counterpart|venture|launch|negotiat|startup|sales|"
                r"negocio|cliente|socio|acuerdo|contrato|lanzamiento|negoci|ventas|empresa|"
                r"neg[oó]cio|parceiro|acordo|lan[cç]amento|vendas|vyapaar|vyapar|grahak|saajhedaar|sauda",
    "love": r"love|relationship|spouse|husband|wife|romanc|dating|marriage|intima|affection|"
            r"amor|pareja|espos|matrimonio|romance|relaci[oó]n|"
            r"namorad|casamento|relacionamento|pyaar|pyar|rishta|shaadi|patni|pati\b",
    "health": r"health|body|energy|exercise|movement|sleep|rest\b|diet|doctor|illness|pain|workout|"
              r"salud|cuerpo|energ[ií]a|ejercicio|dormir|sue[nñ]o|dieta|m[eé]dico|dolor|"
              r"sa[uú]de|corpo|exerc[ií]cio|sono|dor\b|sehat|sharir|neend|vyayam|dard",
    "peace": r"mind|mental|calm|stress|peace|anxiety|meditat|reflect|spiritual|inner|focus|intellectual|study|learn|"
             r"mente|calma|estr[eé]s|paz\b|ansiedad|meditar|esp[ií]ritu|interior|enfoque|estudi|"
             r"estresse|ansiedade|espiritual|foco|estud|shaanti|shanti|tanav|dhyaan|dhyan|chintan",
    "family": r"family|parent|mother|father|child|kids?\b|sibling|brother|sister|home\b|relative|elder|"
              r"familia|padre|madre|hij[oa]|hermano|hermana|hogar|casa\b|pariente|"
              r"fam[ií]lia|pai\b|m[aã]e\b|filh|irm[aã]o|irm[aã]\b|lar\b|parivar|maa\b|papa\b|bachch|bhai\b|behen|ghar\b",
}
_RX = {k: re.compile(r"\b(?:" + v + ")", re.I) for k, v in _WORDS.items()}


def relevance(text, topic: str) -> str:
    """'yes' = it speaks about this topic, 'other' = only about other topics, 'none' = generic."""
    t = str(text or "")
    if _RX[topic].search(t):
        return "yes"
    return "other" if any(rx.search(t) for k, rx in _RX.items() if k != topic) else "none"


_RISK_RX = re.compile(r"\brisk|speculat|gambl|\bbet\b|\bbets\b|hold off|riesgo|especul|apuesta|aposta|risco|jokhim|daav", re.I)

# strings that must never reach a reader as the engine wrote them
_JARGON = re.compile(
    r"\b(dasha|dasa|mahadasha|antardasha|pratyantar\w*|jaimini|vimsottari|vimshottari|chara|malefic\w*|"
    r"benefic\w*|transits?|gochar|karakas?|lagna|nakshatra|navamsa|dusthana|kendra|trikona|ascendant|"
    r"rahu|ketu|saturn|jupiter|mars|venus|mercury|d-?\d{1,2}|houses? \d+|\d+(?:st|nd|rd|th) house)\b", re.I)


def _s(v, cap: int = 600) -> Optional[str]:
    """A clean engine string, or None (empty / jargon / not text)."""
    if not isinstance(v, str):
        return None
    v = v.strip()
    if not v or len(v) > cap or _JARGON.search(v):
        return None
    return v


def _sentences(text) -> List[str]:
    return [x.strip() for x in re.split(r"(?<=[.!?])\s+", str(text or "")) if x.strip()]


def _nonempty(d: dict) -> Optional[dict]:
    return d if any(v not in (None, [], {}, "") for v in d.values()) else None


def _split_items(items, topic: str):
    """-> (for this topic, generic). Items that clearly belong to another topic are dropped."""
    mine, generic = [], []
    for it in items or []:
        t = _s(it, 300)
        if not t:
            continue
        r = relevance(t, topic)
        if r == "yes":
            mine.append(t)
        elif r == "none":
            generic.append(t)
    return mine, generic


# ── Right now (the daily signal) ─────────────────────────────────────────────
def _domain_for(topic: str, daily: dict) -> Optional[dict]:
    for d in daily.get("domains") or []:
        if isinstance(d, dict) and topic in topics_for(d.get("key")):
            return d
    return None


def risk_caution(topic: str, daily: Optional[dict]) -> Optional[str]:
    """The day's own sentence when it advises going easy on risk for this topic, else None.
    Structural first (a risk domain flagged caution that informs this topic, or this topic's domain on
    'caution'), then the engine's own text for it - never a sentence we wrote."""
    if not isinstance(daily, dict):
        return None
    dom = _domain_for(topic, daily)
    if dom and dom.get("state") == "caution":
        return _s(dom.get("line"))
    structural = any(
        isinstance(d, dict) and d.get("key") in RISK_KEYS and d.get("caution") and topic in topics_for(d.get("key"))
        for key in ("active_domains", "quiet_domains") for d in daily.get(key) or [])
    if not structural:
        return None
    for cand in [daily.get("headline"), daily.get("move")] + list(daily.get("friction_for") or []):
        t = _s(cand, 400)
        if t and _RISK_RX.search(t):
            return t
    return None


def daily_detail(topic: str, daily: Optional[dict]) -> Optional[dict]:
    if not isinstance(daily, dict) or daily.get("fallback"):
        return None
    do_m, do_g = _split_items(daily.get("do_today"), topic)
    av_m, av_g = _split_items(daily.get("dont_today"), topic)
    dom = _domain_for(topic, daily)
    dom_out = None
    if dom and _s(dom.get("line")):
        dom_out = {"state": dom.get("state"), "state_label": dom.get("state_label"), "line": _s(dom.get("line"))}
        if dom.get("state") == "favorable":
            do_m.insert(0, dom_out["line"])
        elif dom.get("state") == "caution":
            av_m.insert(0, dom_out["line"])
    times: Dict[str, list] = {"best": [], "avoid": []}
    for w in daily.get("windows") or []:
        if isinstance(w, dict) and w.get("kind") in times and w.get("start") and w.get("end"):
            times[w["kind"]].append({"start": w["start"], "end": w["end"], "text": _s(w.get("text"), 300)})
    wow = _s(daily.get("wow"), 700)
    conf = daily.get("confidence") if isinstance(daily.get("confidence"), dict) else {}
    out = {
        "do": do_m, "avoid": av_m,
        "day": _nonempty({"do": do_g, "avoid": av_g}),
        "best_times": times["best"], "steer_clear": times["avoid"],
        "watch_for": wow if wow and relevance(wow, topic) == "yes" else None,
        "confidence": ({"level": conf.get("level"), "line": _s(conf.get("line"))}
                       if conf.get("level") and _s(conf.get("line")) else None),
        "domain": dom_out,
        "caution_note": risk_caution(topic, daily),
    }
    return _nonempty(out)


# ── Next 30 days (the monthly deep-dive) ─────────────────────────────────────
def month_detail(topic: str, m: Optional[dict]) -> Optional[dict]:
    if not isinstance(m, dict):
        return None

    def keep_action(a) -> bool:
        if not isinstance(a, dict) or not _s(a.get("action")):
            return False
        tp = topics_for(a.get("domain"))
        return (topic in tp) if tp else relevance(a["action"], topic) == "yes"

    def keep_text(t) -> Optional[str]:
        t = _s(t, 500)
        return t if t and relevance(t, topic) != "other" else None

    focus = None
    for d in m.get("active_domains") or []:
        if isinstance(d, dict) and (topic in topics_for(d.get("key")) or topic in topics_for(d.get("label"))):
            focus = {"window": d.get("window") or None, "careful": bool(d.get("caution"))}
            break
    hl = []
    for h in m.get("highlights") or []:
        if not (isinstance(h, dict) and _s(h.get("text"))):
            continue
        tp = topics_for(h.get("domain"))
        if (topic in tp) if tp else relevance(h["text"], topic) == "yes":
            hl.append({"domain": h.get("domain"), "text": _s(h["text"])})
    out = {
        "theme": _s(m.get("month_theme")),
        "overview": " ".join(x for x in _sentences(m.get("overview")) if _s(x) and relevance(x, topic) == "yes") or None,
        "best_week": keep_text(m.get("best_week")),
        "caution_week": keep_text(m.get("caution_week")),
        "priority_actions": [{"action": _s(a["action"]), "domain": a.get("domain")}
                             for a in (m.get("priority_actions") or []) if keep_action(a)],
        "highlights": hl,
        "focus": focus,
        "remedies": [r for r in (m.get("remedies") or []) if isinstance(r, dict) and _s(r.get("practice"))],
        "mantra": _s(m.get("monthly_mantra")),
        "energy_level": m.get("energy_level") if isinstance(m.get("energy_level"), str) else None,
    }
    return _nonempty(out)


# ── Your year (the annual plan) ──────────────────────────────────────────────
def year_detail(topic: str, y: Optional[dict]) -> Optional[dict]:
    if not isinstance(y, dict):
        return None
    strong, caution = [], []
    for e in y.get("events") or []:
        if isinstance(e, dict) and topic in topics_for(e.get("domain")) and _s(e.get("text")):
            row = {"when": e.get("date_label"), "text": _s(e["text"])}
            if (e.get("polarity") or 0) > 0:
                strong.append(row)
            elif (e.get("polarity") or 0) < 0:
                caution.append(row)
    arc = next((a for a in (y.get("arcs") or []) if isinstance(a, dict) and topic in topics_for(a.get("key"))), None)
    peak = next((v for k, v in (y.get("peak_windows") or {}).items()
                 if isinstance(v, dict) and topic in topics_for(k) and _s(v.get("signal"))), None)
    keyed = [{"when": c.get("date"), "text": _s(c.get("event"))} for c in (y.get("critical_dates") or [])
             if isinstance(c, dict) and _s(c.get("event")) and relevance(c["event"], topic) == "yes"]

    def pick(lst):
        return [t for t in (_s(x, 300) for x in lst or []) if t and relevance(t, topic) == "yes"]

    out = {
        "theme": _s(y.get("year_theme")),
        "summary": " ".join(x for x in _sentences(y.get("year_summary")) if _s(x) and relevance(x, topic) == "yes") or None,
        "strong": strong,
        "caution": caution,
        "peak": {"months": peak.get("months"), "text": _s(peak.get("signal"))} if peak else None,
        "trend": {"trend": arc.get("trend"), "when": arc.get("when")} if arc and arc.get("when") else None,
        "key_months": keyed,
        "prioritise": pick(y.get("build_this_year")),
        "protect": pick(y.get("protect_this_year")),
        "release": pick(y.get("release_this_year")),
        "mantra": _s(y.get("year_mantra")),
    }
    return _nonempty(out)


# ── Stretch + life chapter (the life arc) ────────────────────────────────────
def _event_topics(ev: dict) -> tuple:
    return CATEGORY_TOPICS.get(str(ev.get("category") or "").upper(), ()) or topics_for(ev.get("domain"))


def _node(topic: str, n: dict) -> Optional[dict]:
    evs = [{"title": _s(e.get("title")), "when": e.get("window_label"), "likelihood": e.get("conviction_label")}
           for e in (n.get("events") or []) if isinstance(e, dict) and topic in _event_topics(e) and _s(e.get("title"))]
    text = f"{n.get('title') or ''} {n.get('body') or ''}"
    if not evs and relevance(text, topic) != "yes":
        return None
    if not (_s(n.get("title")) or _s(n.get("body"), 900)):
        return None
    return {"start": n.get("start"), "end": n.get("end"), "title": _s(n.get("title")), "body": _s(n.get("body"), 900),
            "when": n.get("when_label"), "events": evs}


def cycle_detail(topic: str, scale: str, arc: Optional[dict], today: date) -> Optional[dict]:
    """scale 'season' = the current stretch, 'chapter' = the whole current life chapter."""
    if not isinstance(arc, dict):
        return None
    nodes = [n for n in (arc.get("cycle_timeline") or []) if isinstance(n, dict)]
    now_node = next((n for n in nodes if n.get("kind") == "now"), None)
    horizon = (today + timedelta(days=365)).isoformat()
    months = []
    for e in arc.get("predicted_events") or []:
        if not isinstance(e, dict) or topic not in _event_topics(e) or not _s(e.get("title")):
            continue
        ws = str(e.get("window_start") or (e.get("window") or {}).get("start") or "")[:10]
        if ws and today.isoformat() <= ws <= horizon:
            months.append({"title": _s(e["title"]), "when": e.get("window_label"), "likelihood": e.get("conviction_label")})
    if scale == "season":
        out = {
            "story": _s(arc.get("gist"), 700),
            "tightest_stretch": _node(topic, now_node) if now_node else None,
            "ahead": [a for a in (_node(topic, n) for n in nodes if n.get("kind") == "sub_chapter") if a],
            "next_months": months,
        }
    else:
        span = arc.get("arc") if isinstance(arc.get("arc"), dict) else {}
        out = {
            "story": _s(arc.get("verdict"), 900),
            "began": span.get("began_label"), "ends": span.get("end_label"),
            "ahead": [a for a in (_node(topic, n) for n in nodes if n.get("kind") in ("turn", "new_chapter")) if a],
        }
    return _nonempty(out)


def build_detail(topic: str, scale: str, src: dict, today: date) -> Optional[dict]:
    """The `detail` object for one topic at one scale, or None. Never raises."""
    try:
        if scale == "today":
            return daily_detail(topic, src.get("daily"))
        if scale == "month":
            return month_detail(topic, src.get("month"))
        if scale == "year":
            return year_detail(topic, src.get("year"))
        if scale in ("season", "chapter"):
            return cycle_detail(topic, scale, src.get("arc"), today)
    except Exception:
        return None
    return None


def reconcile(out: dict, daily: Optional[dict], lang: str) -> dict:
    """Right-now read vs the day's own advice. When the day says go easy on risk for this topic,
    `detail.caution_note` carries that sentence and Your move says so too (the open-window claim
    stays: the window is open, the bet is what stays small). Returns a new dict; never raises."""
    try:
        if out.get("scale") != "today":
            return out
        note = risk_caution(out.get("topic"), daily)
        if not note:
            return out
        out = dict(out)
        out["detail"] = dict(out.get("detail") or {}, caution_note=note)
        if out.get("tone") == "open" and out.get("your_move"):
            add = C.pick(C.KEEP_SMALL, out.get("language") or "en")
            if add not in out["your_move"]:
                out["your_move"] = f"{out['your_move'].rstrip()} {add}"
        return out
    except Exception:
        return out
