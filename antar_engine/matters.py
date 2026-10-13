"""[matters 2026-10-13] "Your matters": the two or three decisions a person keeps coming back to, found from what they
actually ask, with the next real window for each.

Why: a daily read is generic until the product knows what the person is deciding. Their Ask history already says so. This
turns it into a short ranked list, deterministically (no model call, no astrology invented):

  1. take the last 90 days of questions; count each distinct question once per day (a repeated tap is not a new decision);
  2. drop horizon checks that are not decisions ("what should I focus on today", "how is my week ahead", ...);
  3. group what is left by topic family (money / career / business / love / health / home / abroad) and by subject, using a
     small concept lexicon plus word overlap, so "when will my income increase" and "is January a good time to raise prices"
     land together;
  4. score each group: every distinct question counts, decision-shaped ones ("should I", "when", "is it a good time") count
     more, recent ones count more (21-day half-life style decay). A group needs two different questions or three different
     days to count at all;
  5. title it from the person's own repeated words when they repeat a phrase, else from the concept, else from the topic;
  6. attach the next real window for the topic from the Windows feed (one timing source) and the move from the latest answer.

Pure functions. Never raises on odd rows. The endpoint supplies the rows and the feed."""
from __future__ import annotations

import hashlib
import math
import re
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

WINDOW_DAYS = 90
HALF_LIFE_DAYS = 21.0
MIN_DISTINCT_QUESTIONS = 2
MIN_DISTINCT_DAYS = 3

_FAMILY = {"finance": "money", "speculation": "money", "wealth": "money", "funding": "money", "loss": "money",
           "career": "career", "business": "business", "love": "love", "marriage": "love", "divorce": "love",
           "health": "health", "property": "home", "foreign": "abroad"}
_FAMILY_LABEL = {"en": {"money": "Money", "career": "Your career", "business": "Your business", "love": "A relationship",
                        "health": "Your health", "home": "Your home", "abroad": "A move abroad"},
                 "es": {"money": "El dinero", "career": "Tu carrera", "business": "Tu negocio", "love": "Una relación",
                        "health": "Tu salud", "home": "Tu casa", "abroad": "Mudarte al extranjero"}}
_TOPIC_FOR_FEED = {"money": "money", "career": "career", "business": "business", "love": "love", "health": "health"}

_STOP = set("""a an and are as at be been but by can could did do does for from had has have how i if in into is it its just me my
of on or our should so than that the their them then there these they this to up us was we were what when where which who whom
why will with would you your yours am about any some very really also too more most much many one two get got let lets want
need like going go now today tomorrow tonight week month year next last this soon later time good best right still ever
el la los las un una y o de del en es que por para con mi mis tu tus se lo le les su sus como cuando cual debo puedo hoy
manana semana mes ano proximo ultimo bueno mejor momento""".split())
_GENERIC = re.compile(
    r"(?i)(^\s*(how|what)('s| is| are| does| do| will)\b.*\b(today|tomorrow|tonight|this week|this month|this year|next month|next \d+ (days|weeks|months)|week ahead)\b|"
    r"focus on (today|at work|this week)|how is (my|the) (week|day|tomorrow)|how('s| is) tomorrow|week ahead|"
    r"how (does|is) (this|my|the) (month|year|week)|which week this month|strongest (money|work|career|love|health) window|"
    r"what should i (do|focus on) (today|this week|this month)|how is my (health|career|love life|money) (looking|going)|"
    r"how does the year ahead|what('s| is) today|cómo (está|va) (mi|el) (semana|día|año|mes)|qué debo (hacer|enfocar) hoy)")
_DECISION = re.compile(r"(?i)^\s*(should i|should we|when (is|will|do|can|should)|is (it|this|that|now|january|february|march|april|may|"
                       r"june|july|august|september|october|november|december)|can i|do i|how (do|should) i|which\b|¿debo|¿cuándo|¿es buen)")

# concept lexicon: token -> concept id. Words that mean the same decision land together.
_CONCEPT = {}
for cid, words in {
    "income": "income incomes revenue earn earning earnings salary pay raise raises price prices pricing charge charging fee fees "
              "ingresos ingreso precio precios cobrar sueldo".split(),
    "clients": "client clients customer customers proposal proposals deal deals sale sales lead leads quote cliente clientes propuesta".split(),
    "investors": "investor investors fundraise fundraising funding pitch equity cofounder cofounders partner partners "
                 "inversor inversionistas socio socios".split(),
    "markets": "invest investing investment stock stocks shares gold crypto bitcoin trading bet betting lottery gamble casino "
               "acciones oro apuesta apuestas".split(),
    "launch": "launch launching positioning platform product startup agents niche brand lanzar lanzamiento".split(),
    "job": "job jobs offer offers resign quit promotion hire hiring fire firing boss team employee trabajo empleo ascenso".split(),
    "home": "house home rent lease apartment move moving relocate buy mudanza casa renta".split(),
}.items():
    for w in words:
        _CONCEPT[w] = cid
_CONCEPT_LABEL = {"en": {"markets": "Investing and trading", "income": "Income and pricing", "clients": "Clients and proposals", "investors": "Investors and partners",
                         "launch": "Launching your product", "job": "Your job", "home": "Your home"},
                  "es": {"markets": "Inversi\u00f3n y trading", "income": "Ingresos y precios", "clients": "Clientes y propuestas", "investors": "Inversores y socios",
                         "launch": "Lanzar tu producto", "job": "Tu trabajo", "home": "Tu casa"}}
_NG_STOP = set("fits fit achieve achieving help helps make makes work works best better suited type kind highest level potential position "
               "answer english please new".split())
_UPPER = {"ai", "api", "seo", "crm", "saas", "b2b", "b2c", "kyc"}
_TOK = re.compile(r"[a-záéíóúñü0-9]+")


def _lang(language) -> str:
    return "es" if str(language or "en").lower().startswith("es") else "en"


def norm(q: Any) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", str(q or "").lower())).strip()


def tokens(q: Any) -> List[str]:
    return [t for t in _TOK.findall(norm(q)) if t not in _STOP and len(t) > 1]


def is_generic(q: Any) -> bool:
    return bool(_GENERIC.search(str(q or "")))


def decision_shaped(q: Any) -> bool:
    return bool(_DECISION.search(str(q or "")))


def family_of(domain: Any) -> Optional[str]:
    return _FAMILY.get(str(domain or "").lower())


def _day(created) -> Optional[date]:
    try:
        return datetime.fromisoformat(str(created).replace("Z", "+00:00")).date()
    except (ValueError, TypeError):
        return None


def _concepts(toks: List[str]) -> set:
    return {_CONCEPT[t] for t in toks if t in _CONCEPT}


def _similar(a_t: set, a_c: set, b_t: set, b_c: set) -> bool:
    if a_c & b_c:
        return True
    if not a_t or not b_t:
        return False
    inter = len(a_t & b_t)
    return inter >= 2 or inter / float(len(a_t | b_t)) >= 0.4


def _ngram_label(questions: List[str], lg: str) -> str:
    """A phrase the person repeats (2-3 words appearing in >= 3 of their questions), in their own words."""
    seqs = [[t for t in tokens(q) if t not in _NG_STOP] for q in questions]
    counts: Counter = Counter()
    for seq in seqs:
        seen = set()
        for n in (3, 2):
            for i in range(len(seq) - n + 1):
                g = tuple(seq[i:i + n])
                if g not in seen:
                    seen.add(g)
                    counts[g] += 1
    best = None
    for g, c in counts.items():
        if c < (3 if len(g) == 3 else 4):
            continue
        key = (len(g), c)
        if best is None or key > best[0]:
            best = (key, g)
    if not best:
        return ""
    words = [w.upper() if w in _UPPER else w for w in best[1]]
    s = " ".join(words)
    return (s[:1].upper() + s[1:]) if lg == "en" else (s[:1].upper() + s[1:])


def build(rows: List[Dict[str, Any]], feed: Optional[dict] = None, language: str = "en", today: Optional[date] = None,
          limit: int = 3) -> Dict[str, Any]:
    lg = _lang(language)
    today = today or datetime.now(timezone.utc).date()
    items = []                                   # distinct (normalised question, day)
    seen = set()
    for r in rows or []:
        q = str(r.get("question") or "").strip()
        d = _day(r.get("created_at"))
        fam = family_of(r.get("domain"))
        if not q or not d or not fam or is_generic(q):
            continue
        age = (today - d).days
        if age < 0 or age > WINDOW_DAYS:
            continue
        key = (norm(q), d)
        if key in seen:
            continue
        seen.add(key)
        toks = tokens(q)
        items.append({"q": q, "d": d, "age": age, "fam": fam, "toks": set(toks), "con": _concepts(toks), "row": r,
                      "dec": decision_shaped(q)})
    items.sort(key=lambda x: x["d"], reverse=True)
    clusters: List[Dict[str, Any]] = []
    for it in items:
        home = None
        for c in clusters:
            if c["fam"] == it["fam"] and any(_similar(it["toks"], it["con"], o["toks"], o["con"]) for o in c["items"]):
                home = c
                break
        if home is None:
            home = {"fam": it["fam"], "items": []}
            clusters.append(home)
        home["items"].append(it)
    matters = []
    for c in clusters:
        its = c["items"]
        distinct_q = len({norm(i["q"]) for i in its})
        distinct_days = len({i["d"] for i in its})
        if distinct_q < MIN_DISTINCT_QUESTIONS and distinct_days < MIN_DISTINCT_DAYS:
            continue
        score = sum((1.5 if i["dec"] else 1.0) * math.pow(0.5, i["age"] / HALF_LIFE_DAYS) for i in its)
        questions = [i["q"] for i in its]
        title, src = _ngram_label(questions, lg), "your words"
        if not title:
            src = "topic words"
            con = Counter(k for i in its for k in i["con"])
            top = con.most_common(1)
            title = _CONCEPT_LABEL[lg].get(top[0][0]) if top else ""
        if not title:
            title, src = _FAMILY_LABEL[lg][c["fam"]], "topic"
        latest = max(its, key=lambda i: i["d"])
        row = latest["row"]
        mid = hashlib.sha1(f"{c['fam']}|{title.lower()}".encode()).hexdigest()[:10]
        if src == "topic":                 # nothing specific to name: a broad topic ranks below a named matter
            score *= 0.6
        matters.append({"id": mid, "title": title, "title_source": src, "topic": c["fam"], "asks": len(its), "days": distinct_days,
                        "last_asked": latest["d"].isoformat(), "score": round(score, 3),
                        "latest_question": latest["q"], "samples": list(dict.fromkeys(questions))[:3],
                        "move": next((str(i["row"].get("action_item") or "").strip() for i in sorted(its, key=lambda x: x["d"], reverse=True)
                                      if str(i["row"].get("action_item") or "").strip()), ""),
                        "next": _next_window(feed, c["fam"], lg)})
    merged: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for m in matters:                      # two groups that ended up with the same title are one matter
        k = (m["topic"], m["title"].lower())
        if k in merged:
            a = merged[k]
            a["asks"] += m["asks"]
            a["days"] = max(a["days"], m["days"])
            a["score"] = round(a["score"] + m["score"], 3)
            a["samples"] = list(dict.fromkeys(a["samples"] + m["samples"]))[:3]
            if m["last_asked"] > a["last_asked"]:
                a.update(last_asked=m["last_asked"], latest_question=m["latest_question"], move=m["move"] or a["move"])
        else:
            merged[k] = m
    matters = sorted(merged.values(), key=lambda m: m["score"], reverse=True)
    top = matters[:max(1, int(limit or 3))]
    return {"version": "matters-1", "matters": top, "empty": not top,
            "prompt": ("¿Qué estás decidiendo ahora mismo?" if lg == "es" else "What are you deciding right now?")}


def _next_window(feed: Optional[dict], family: str, lg: str) -> Optional[Dict[str, Any]]:
    """The next real window for the matter's topic from the Windows feed (the one timing source): the open stretch now or
    next, plus the next care stretch."""
    topic = _TOPIC_FOR_FEED.get(family)
    if not topic or not feed:
        return None
    ws = []
    for t in feed.get("tracks") or []:
        if t.get("topic") != topic:
            continue
        for w in t.get("windows") or []:
            try:
                s, e = date.fromisoformat(str(w["start"])[:10]), date.fromisoformat(str(w["end"])[:10])
            except (KeyError, ValueError):
                continue
            if w.get("kind") in ("open", "care"):
                ws.append((s, e, w["kind"]))
    if not ws:
        return None
    ws.sort()
    today = date.fromisoformat(str(feed.get("as_of") or date.today().isoformat())[:10])
    op = next(((s, e) for s, e, k in ws if k == "open" and e > today), None)
    ca = next(((s, e) for s, e, k in ws if k == "care" and e > today), None)
    out: Dict[str, Any] = {}
    if op:
        out["open"] = {"start": op[0].isoformat(), "end": op[1].isoformat()}
    if ca:
        out["care"] = {"start": ca[0].isoformat(), "end": ca[1].isoformat()}
    return out or None
