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


# ── one balanced headline for an open window that also carries a caution ─────────────────────────
_CONFLICT_RX = re.compile(r"conflict|argument|fight|tension|friction|quarrel|dispute|sharp word|"
                          r"conflicto|discusi|tensi|conflito|disputa|tanaav|jhagd|behes", re.I)
_TIMING_RX = re.compile(r"sign|commit|decision|decid|rush|delay|timing|talk|message|negotiat|promise|"
                        r"firm|decisi|compromet|prisa|assin|decis|pressa|vaada|faisl|jaldi", re.I)


_MONEY_TOPICS = ("money", "business")
_HARD_RISK_RX = re.compile(r"\brisk|speculat|gambl|\bbet\b|\bbets\b|riesgo|especul|apuesta|aposta|risco|jokhim|daav", re.I)


def caution_kind(note: Optional[str], topic: str) -> str:
    """risk / conflict / timing / neutral for the caution's own text (the risk cue is the one the
    Right-now caution already uses; `relevance` keeps it to a sentence about this topic or no topic)."""
    t = str(note or "")
    if not t or relevance(t, topic) == "other":
        return "neutral"
    if _RISK_RX.search(t) and (topic in _MONEY_TOPICS or _HARD_RISK_RX.search(t)):
        return "risk"      # a bare "hold off" is timing advice outside money / business
    if _RISK_RX.search(t):
        return "timing"
    if _CONFLICT_RX.search(t):
        return "conflict"
    if _TIMING_RX.search(t):
        return "timing"
    return "neutral"


def _week_tail(note: Optional[str], lang: str) -> str:
    """', especially the week of October 10' from 'Week of October 10 - ...', else ''."""
    head = re.split(r"\s[\u2014\u2013-]\s", str(note or ""), maxsplit=1)[0].strip().rstrip(".")
    if not head or len(head) > 40 or not _WEEK_RX.match(head):
        return ""
    w = head[0].lower() + head[1:]
    return C.pick(C.BAL_TAIL, lang).format(when=C.pick(C.BAL_WEEK, lang).format(w=w))


def balanced(out: dict, lang: str, note: Optional[str], tail: str = "") -> dict:
    """Open window + caution -> ONE headline sentence ('Today, good for income and pricing, but careful
    with speculative moves.') and a Your move that agrees. The raw caution text stays in
    `detail.caution_note`. Returns a new dict."""
    topic, scale = out.get("topic"), out.get("scale")
    kind = caution_kind(note, topic)
    good = C.pick(C.BAL_GOOD, lang)[topic]
    care = C.pick(C.BAL_CARE, lang)[topic][kind]
    out = dict(out)
    out["claim"] = C.pick(C.BAL_JOIN, lang).format(
        lead=C.pick(C.SPAN_LEAD, lang)[scale], good=good, care=care, tail=tail)
    if out.get("your_move"):
        add = C.pick(C.KEEP_SMALL, lang) if kind == "risk" and topic in _MONEY_TOPICS else C.pick(C.BAL_MOVE, lang).format(care=care)
        if add not in out["your_move"] and not (kind == "risk" and topic in _MONEY_TOPICS and re.search(r"\b(bet|bets|apuesta|aposta|daav)\b", out["your_move"], re.I)):
            out["your_move"] = f"{out['your_move'].rstrip()} {add}"
    return out


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


# ── dates inside engine text (so advice that has already passed never reaches a reader) ──────────
_ISO_RX = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
_FROM_RX = re.compile(r"\b(after|from|since|starting|desde|despu[eé]s|depois|a partir)\b", re.I)
_WEEK_RX = re.compile(r"\bweek of\b|\bsemana del?\b|\bsemana de\b|\bsaptaah\b|\bhafte\b", re.I)
_MONTH_FORMS: Dict[str, int] = {}
for _l in ("en", "es", "pt", "hinglish"):
    for _i, _n in enumerate(C.FULL_MONTHS.get(_l, ())):
        _MONTH_FORMS[_n.lower()] = _i + 1
    for _i, _n in enumerate(C.MONTHS.get(_l, ())):
        _MONTH_FORMS.setdefault(_n.lower().rstrip("."), _i + 1)
_MONTH_ALT = "|".join(sorted((re.escape(m) for m in _MONTH_FORMS), key=len, reverse=True))
_DAY_RX = re.compile(rf"\b(?:({_MONTH_ALT})\.?\s+(\d{{1,2}})(?!\d)|(\d{{1,2}})(?:\s+de)?\s+({_MONTH_ALT})\b)", re.I)


def text_dates(text, today: date) -> List[date]:
    """Calendar days named in a sentence ('before October 8', '8 de octubre', '2026-10-08')."""
    t, out = str(text or ""), []
    for y, m, d in _ISO_RX.findall(t):
        try:
            out.append(date(int(y), int(m), int(d)))
        except ValueError:
            pass
    for m1, d1, d2, m2 in _DAY_RX.findall(t):
        mon, day = _MONTH_FORMS.get((m1 or m2).lower().rstrip(".")), int(d1 or d2)
        if not mon:
            continue
        try:
            c = date(today.year, mon, day)
        except ValueError:
            continue
        out.append(c.replace(year=c.year + 1) if (today - c).days > 180 else c)
    return out


def is_past(text, today: date) -> bool:
    """True when every date the sentence names is already behind `today` (a 'Week of ...' lasts 6 more days).
    Text with no date, or one that points forward ('from October 8'), is never past."""
    ds = text_dates(text, today)
    if not ds or _FROM_RX.search(str(text or "")):
        return False
    last = max(ds) + (timedelta(days=6) if _WEEK_RX.search(str(text or "")) else timedelta(0))
    return last < today


def _window_span(w):
    if isinstance(w, dict):
        a, b = str(w.get("start") or "")[:10], str(w.get("end") or "")[:10]
        ds = [a, b]
    else:
        ds = _ISO_RX.findall(str(w or ""))
        ds = ["-".join(x) for x in ds]
    try:
        days = [date.fromisoformat(x) for x in ds if x]
    except ValueError:
        return None
    return (min(days), max(days)) if days else None


def _clean_window(w, today: date):
    """The focus window with nothing before today: None when it has ended, start clamped to today."""
    span = _window_span(w)
    if not span:
        return w or None
    s, e = span
    if e < today:
        return None
    s = max(s, today)
    return f"{s.isoformat()} – {e.isoformat()}" if s != e else s.isoformat()


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
    do_all = list(dict.fromkeys(do_m + do_g))   # topic-relevant first, then the day's general ones, once each
    out = {
        "do": do_all, "avoid": av_m,
        "day": _nonempty({"avoid": av_g}),
        "best_times": times["best"], "steer_clear": times["avoid"],
        "watch_for": wow if wow and relevance(wow, topic) == "yes" else None,
        "confidence": ({"level": conf.get("level"), "line": _s(conf.get("line"))}
                       if conf.get("level") and _s(conf.get("line")) else None),
        "domain": dom_out,
        "caution_note": risk_caution(topic, daily),
    }
    return _nonempty(out)


# ── Next 30 days (the monthly deep-dive) ─────────────────────────────────────
def month_detail(topic: str, m: Optional[dict], today: Optional[date] = None) -> Optional[dict]:
    if not isinstance(m, dict):
        return None
    today = today or date.today()

    def keep_action(a) -> bool:
        if not isinstance(a, dict) or not _s(a.get("action")) or is_past(a.get("action"), today):
            return False
        tp = topics_for(a.get("domain"))
        return (topic in tp) if tp else relevance(a["action"], topic) == "yes"

    def keep_text(t) -> Optional[str]:
        t = _s(t, 500)
        return t if t and relevance(t, topic) != "other" and not is_past(t, today) else None

    focus = None
    for d in m.get("active_domains") or []:
        if isinstance(d, dict) and (topic in topics_for(d.get("key")) or topic in topics_for(d.get("label"))):
            focus = {"window": _clean_window(d.get("window"), today), "careful": bool(d.get("caution"))}
            if not focus["window"] and not focus["careful"]:
                focus = None
            break
    hl = []
    for h in m.get("highlights") or []:
        if not (isinstance(h, dict) and _s(h.get("text"))) or is_past(h.get("text"), today):
            continue
        tp = topics_for(h.get("domain"))
        if (topic in tp) if tp else relevance(h["text"], topic) == "yes":
            hl.append({"domain": h.get("domain"), "text": _s(h["text"])})
    out = {
        "theme": _s(m.get("month_theme")),
        "overview": " ".join(x for x in _sentences(m.get("overview")) if _s(x) and relevance(x, topic) == "yes" and not is_past(x, today)) or None,
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
def _merge_when(rows: List[dict]) -> List[dict]:
    """One row per `when`: the texts of rows sharing a date are joined, a text already contained in
    another is dropped."""
    out: Dict[str, dict] = {}
    for r in rows:
        k = str(r.get("when") or "").strip().lower()
        if k not in out:
            out[k] = dict(r, _texts=[r["text"]])
            continue
        have = out[k]["_texts"]
        t = r["text"]
        n = lambda x: x.lower().rstrip(" .!?")
        if any(n(t) in n(h) for h in have):
            continue
        have[:] = [h for h in have if n(h) not in n(t)] + [t]
    return [dict({kk: vv for kk, vv in r.items() if kk != "_texts"}, text=" ".join(r["_texts"])) for r in out.values()]


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
    keyed = _merge_when([{"when": c.get("date"), "text": _s(c.get("event"))} for c in (y.get("critical_dates") or [])
                         if isinstance(c, dict) and _s(c.get("event")) and relevance(c["event"], topic) == "yes"])
    strong, caution = _merge_when(strong), _merge_when(caution)

    def pick(lst):
        return [t for t in (_s(x, 300) for x in lst or []) if t and relevance(t, topic) == "yes"]

    out = {
        "theme": _s(y.get("year_theme")),
        "summary": " ".join(x for x in _sentences(y.get("year_summary")) if _s(x) and relevance(x, topic) == "yes") or None,
        "strong": strong or None,
        "caution": caution or None,
        "peak": {"months": peak.get("months"), "text": _s(peak.get("signal"))} if peak else None,
        "trend": {"trend": arc.get("trend"), "when": arc.get("when")} if arc and arc.get("when") else None,
        "key_months": keyed or None,
        "prioritise": pick(y.get("build_this_year")) or None,
        "protect": pick(y.get("protect_this_year")) or None,
        "release": pick(y.get("release_this_year")) or None,
        "mantra": _s(y.get("year_mantra")),
    }
    return _nonempty(out)


# ── Stretch + life chapter (the life arc) ────────────────────────────────────
def _event_topics(ev: dict) -> tuple:
    return CATEGORY_TOPICS.get(str(ev.get("category") or "").upper(), ()) or topics_for(ev.get("domain"))


def _window_months(topic: str, feed: Optional[dict], today: date, lang: str) -> List[dict]:
    """The topic's own dated windows for the next 12 months (the Windows feed's list) as plain rows."""
    if not isinstance(feed, dict):
        return []
    horizon = (today + timedelta(days=365)).isoformat()
    area = C.pick(C.AREA, lang).get(topic)
    out = []
    for tr in feed.get("tracks") or []:
        if not (isinstance(tr, dict) and tr.get("topic") == topic and area):
            continue
        for w in tr.get("windows") or []:
            try:
                s_, e_ = date.fromisoformat(w["start"]), date.fromisoformat(w["end"])
            except (KeyError, ValueError, TypeError):
                continue
            if w["end"] < today.isoformat() or w["start"] > horizon or w.get("kind") not in ("open", "care"):
                continue
            fmt = (lambda d: C.day_label(d, lang)) if s_.year == e_.year == today.year else (lambda d: C.day_label_y(d, lang))
            out.append({"title": C.pick(C.WINDOW_ITEM, lang)[w["kind"]].format(area=area),
                        "when": fmt(s_) if s_ == e_ else f"{fmt(s_)} – {fmt(e_)}",
                        "likelihood": None, "start": max(w["start"], today.isoformat())})
    return out


def _node(topic: str, n: dict, generic: bool = False) -> Optional[dict]:
    evs = [{"title": _s(e.get("title")), "when": e.get("window_label"), "likelihood": e.get("conviction_label")}
           for e in (n.get("events") or []) if isinstance(e, dict) and topic in _event_topics(e) and _s(e.get("title"))]
    text = f"{n.get('title') or ''} {n.get('body') or ''}"
    rel = relevance(text, topic)
    if not evs and rel != "yes" and not (generic and rel == "none"):
        return None
    if not (_s(n.get("title")) or _s(n.get("body"), 900)):
        return None
    body = _s(n.get("body"), 900)
    if body and body.endswith(":"):   # the engine's sentence trails off into a list we do not carry
        body = " ".join(_sentences(body)[:-1]) or None
    return {"start": n.get("start"), "end": n.get("end"), "title": _s(n.get("title")), "body": body,
            "when": n.get("when_label"), "events": evs}


def _ahead(topic: str, nodes: List[dict], today: date, kinds: tuple) -> List[dict]:
    """What is coming: the later stretches of the arc (generic ones included, other topics' left out), plus
    the running one only when it carries an event for this topic."""
    out = []
    for n in nodes:
        if n.get("kind") not in kinds or str(n.get("end") or "")[:10] < today.isoformat():
            continue
        a = _node(topic, n, generic=True)
        if a and (str(n.get("start") or "")[:10] > today.isoformat() or a["events"]):
            out.append(a)
    return out


def cycle_detail(topic: str, scale: str, arc: Optional[dict], today: date,
                 feed: Optional[dict] = None, lang: str = "en") -> Optional[dict]:
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
            months.append({"title": _s(e["title"]), "when": e.get("window_label"), "likelihood": e.get("conviction_label"),
                           "start": ws})
    months = sorted(months + _window_months(topic, feed, today, lang), key=lambda m: m.get("start") or "")[:8]
    if scale == "season":
        out = {
            "story": _s(arc.get("gist"), 700),
            "tightest_stretch": _node(topic, now_node) if now_node else None,
            "ahead": _ahead(topic, nodes, today, ("sub_chapter", "turn")),
            "next_months": months or None,
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
            return month_detail(topic, src.get("month"), today)
        if scale == "year":
            return year_detail(topic, src.get("year"))
        if scale in ("season", "chapter"):
            return cycle_detail(topic, scale, src.get("arc"), today, src.get("feed"), src.get("lang") or "en")
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
        if out.get("tone") == "open" and out.get("claim"):   # one balanced sentence; the raw caution stays in the detail
            return balanced(out, out.get("language") or "en", note)
        if out.get("tone") == "steady" and out.get("claim"):   # the claim says it too, in the day's own words
            area = C.pick(C.AREA, out.get("language") or "en")[out["topic"]]
            out["claim"] = C.pick(C.LEAD_JOIN, out.get("language") or "en").format(
                lead=C.pick(C.SPAN_LEAD, out.get("language") or "en")["today"],
                core=C.pick(C.TODAY_CAUTION_CORE, out.get("language") or "en").format(area=area))
            if note not in out["claim"]:
                out["claim"] = f"{out['claim'].rstrip()} {note}"
        return out
    except Exception:
        return out


def reconcile_year(out: dict, lang: str) -> dict:
    """The year claim vs the year's own caution stretch. A steady claim ('nothing sharp is pulling')
    cannot sit beside a demanding month in the detail: the claim names that month, and the engine's
    sentence for it rides in `detail.caution_note`. An open / care year keeps its claim and gains a
    short 'Watch <month>.' Returns a new dict; never raises."""
    try:
        det = out.get("detail") or {}
        cau = next((c for c in det.get("caution") or [] if c.get("when") and c.get("text")), None)
        if out.get("scale") != "year" or not cau:
            return out
        out = dict(out)
        out["detail"] = dict(det, caution_note=cau["text"])
        if out.get("tone") == "steady":
            area = C.pick(C.AREA, lang)[out["topic"]]
            core = C.pick(C.YEAR_CAUTION_CORE, lang).format(area=area, when=cau["when"])
            out["claim"] = C.pick(C.LEAD_JOIN, lang).format(lead=C.pick(C.SPAN_LEAD, lang)["year"], core=core)
            out["why"] = out.get("why") or ""
        elif out.get("tone") == "open":
            return balanced(out, lang, cau["text"], C.pick(C.BAL_TAIL, lang).format(when=cau["when"]))
        else:
            tail = C.pick(C.YEAR_CAUTION_TAIL, lang).format(when=cau["when"])
            if tail not in out.get("claim", ""):
                out["claim"] = f"{out['claim'].rstrip()} {tail}"
        return out
    except Exception:
        return out


def reconcile_month(out: dict, lang: str) -> dict:
    """The 30-day claim vs the month's own caution week. When the monthly read flags a demanding
    week for this topic, the claim says so with the engine's own sentence ('Week of October 9 - ...').
    A steady claim ('nothing sharp') is replaced; an open / care claim keeps itself and gains the
    sentence. Returns a new dict; never raises."""
    try:
        det = out.get("detail") or {}
        note = det.get("caution_week")
        careful = (det.get("focus") or {}).get("careful")
        if out.get("scale") != "month" or not note or not (careful or relevance(note, out.get("topic")) == "yes"):
            return out
        out = dict(out)
        out["detail"] = dict(det, caution_note=note)
        if out.get("tone") == "steady":
            area = C.pick(C.AREA, lang)[out["topic"]]
            core = C.pick(C.MONTH_CAUTION_CORE, lang).format(area=area)
            out["claim"] = C.pick(C.LEAD_JOIN, lang).format(lead=C.pick(C.SPAN_LEAD, lang)["month"], core=core)
        if out.get("tone") == "open":
            return balanced(out, lang, note, _week_tail(note, lang))
        if note not in out.get("claim", ""):
            out["claim"] = f"{out['claim'].rstrip()} {note}"
        return out
    except Exception:
        return out
