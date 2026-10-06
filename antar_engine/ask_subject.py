"""
antar_engine/ask_subject.py

WHO is an Ask question about? Pure, deterministic, no LLM, never raises.

Ask used to answer every question from the ASKER's own chart, so "when will my son
get married?" returned the asker's own marriage timing. This resolver decides
whether the question is about the asker (`self`), one of the asker's saved People
(`person`), or cannot be told apart (`ambiguous`, e.g. two sons).

Rules
  * Match ONLY against the asker's own People list that the caller passes in -
    never a global/account chart lookup.
  * A mention only counts when the person/relation is the SUBJECT of the question
    ("how is Amik doing", "when will my son get married", "Amik's health"), not
    when they are context for the asker ("should I hire Amik", "my wife and I keep
    fighting", "does my boss like me") - those stay `self`.
  * "my own ...", "myself", "about me" => self always wins.
  * Names: accent-folded, possessive-stripped, spelling-variant normalised
    (Amik/Amick/Ameek/Amiq are one name). Relation words are matched with word
    boundaries in EN/ES/PT/Hinglish (so "childhood" never matches "child").
  * A relation word used as the subject with NO matching saved person returns
    subject='person' with person=None and missing=True so the caller can say
    "I don't have your son's chart yet" instead of answering from the asker's.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Optional

# ── canonical relations ───────────────────────────────────────────────────────
# surface phrase -> relation group (what the asker calls them)
_REL_WORDS: Dict[str, str] = {}


def _reg(group: str, *words: str) -> None:
    for w in words:
        _REL_WORDS[w] = group


_reg("child", "son", "daughter", "kid", "kids", "child", "children", "baby",
     "hijo", "hija", "hijos", "hijas", "bebe", "niño", "niña", "nino", "nina",
     "filho", "filha", "filhos", "filhas", "crianca", "criança",
     "beta", "beti", "bete", "bachcha", "bacha", "bachche", "bachhe", "ladka", "ladki", "putra")
_reg("partner", "wife", "husband", "spouse", "partner", "girlfriend", "boyfriend",
     "fiance", "fiancee", "fiancé", "fiancée", "esposa", "esposo", "marido", "mujer",
     "novia", "novio", "pareja", "namorada", "namorado", "parceiro", "parceira",
     "esposa", "patni", "pati", "biwi", "bivi", "shohar", "jeevansathi")
_reg("parent", "mom", "mother", "mum", "dad", "father", "parents", "mama", "papa",
     "madre", "padre", "mae", "mãe", "pai", "pais", "maa", "ma", "pitaji", "mummy", "daddy", "mataji")
_reg("sibling", "brother", "sister", "sibling", "siblings", "hermano", "hermana",
     "irmao", "irmão", "irma", "irmã", "bhai", "behen", "behan", "bhaiya", "didi")
_reg("friend", "friend", "friends", "amigo", "amiga", "amigos", "dost", "doste", "yaar")
_reg("boss", "boss", "manager", "supervisor", "jefe", "jefa", "chefe", "gerente")
_reg("employee", "employee", "colleague", "coworker", "co-worker", "empleado", "empleada",
     "funcionario", "funcionaria", "colega")
_reg("cofounder", "cofounder", "co-founder", "cofundador", "cofundadora")
_reg("advisor", "advisor", "adviser", "mentor", "coach", "consultant")
_reg("family", "cousin", "uncle", "aunt", "grandmother", "grandfather", "grandma", "grandpa",
     "primo", "prima", "tio", "tío", "tia", "tía", "abuela", "abuelo", "avo", "avó", "avô",
     "chacha", "mausi", "nani", "nana", "dada", "dadi", "in-laws", "inlaws")

# compat_type (People tab) -> relation groups it can satisfy
_COMPAT_GROUPS: Dict[str, set] = {
    "romantic": {"partner"}, "relationship": {"partner"}, "love": {"partner"},
    "marriage": {"partner"}, "spouse": {"partner"},
    "child": {"child"}, "parent": {"parent"},
    "family": {"sibling", "family", "parent", "child"},
    "friend": {"friend"},
    "cofounder": {"cofounder", "partner"}, "business": {"partner", "cofounder"},
    "advisor": {"advisor"},
    "boss-or-manager": {"boss"}, "boss": {"boss"}, "manager": {"boss"},
    "employee": {"employee"}, "worker": {"employee"},
}
# "partner" is also said of a business partner; a romantic-only person still satisfies it.

_SELF_OVERRIDE = re.compile(
    r"\b(my own|myself|about me|for me|mi propio|mi propia|meu proprio|minha propria|"
    r"mere apne|apne baare|apne bare|main khud|yo mismo|eu mesmo|eu mesma)\b")

_INTERROG = {"when", "will", "would", "is", "are", "does", "do", "did", "how", "how's",
             "what", "why", "where", "should", "can", "could", "has", "have", "was",
             "cuando", "cuándo", "sera", "será", "como", "cómo", "esta", "está", "va",
             "quando", "vai", "ira", "irá", "kab", "kaisa", "kaisi", "kaise", "kya",
             "que", "qué", "como", "tem", "tera"}
_AUX = {"is", "are", "will", "does", "did", "has", "was", "would", "be", "was", "va",
        "vai", "ira", "irá", "sera", "será", "esta", "está", "a", "o", "el", "la",
        "kab", "kya"}
_DETERMINERS = {"my", "mi", "mis", "meu", "minha", "meus", "minhas", "mera", "meri", "mere",
                "the", "el", "la", "o", "a", "los", "las", "os", "as", "our", "nuestro",
                "nuestra", "nosso", "nossa", "hamara", "hamari"}
_ABOUT_BEFORE = re.compile(
    r"\b(about|sobre|acerca de|a respeito de|regarding|de|del|do|da|dos|das|"
    r"what about|how about|and what about)\s*$")
_RELATIONAL_BEFORE = re.compile(
    r"\b(with|between|and|con|e|aur|se|y|without|sin|sem)\s*$")
_RELATIONSHIP_WORD_BEFORE = re.compile(
    r"\b(relationship|relation|relacion|relación|relacao|relação|rishta|rishte|bond|fight|"
    r"fighting|argument|argue|arguing|jhagda|pelea|briga)\b(\s+\w+){0,2}\s*$")
_OBJECT_AFTER = {"me", "us", "myself", "mine", "nos", "mim", "mujhe", "hume", "conmigo",
                 "comigo", "i", "yo", "eu", "main"}
_LIFE_AFTER = re.compile(
    r"^(\s+[\w']+){0,3}?\s+(get(ting)? married|marry|marriage|married|doing|health|healthy|"
    r"career|job|future|studies|study|exam|pass|recover|recovery|succeed|success|pregnan\w*|"
    r"baby|conceive|settle|business|money|luck|happy|sick|ill|surgery|migrate|divorce|"
    r"casar\w*|salud|trabajo|futuro|saude|emprego|shaadi|shadi|sehat|naukri|padhai|"
    r"kamyab|bimar|vida|carrera|carreira|negocio)\b")
_COMMON_WORD_NAMES = {"will", "mark", "bill", "rose", "grace", "hope", "joy", "art", "may",
                      "june", "summer", "dawn", "faith", "ray", "pat", "sue", "ben", "dan",
                      "jack", "jay", "sunny", "star", "sky", "ivy", "lily", "daisy", "amber",
                      "angel", "bob", "case", "chance", "christian", "dean", "earl", "frank",
                      "gene", "guy", "heath", "iris", "jade", "jean", "kit", "lee", "major",
                      "miles", "mike", "page", "pearl", "peace", "rich", "rob", "sandy", "wade"}


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower().replace("’", "'").replace("`", "'")


def norm_name(s: str) -> str:
    """Spelling-variant normaliser: Amik/Amick/Ameek/Amiq -> one key."""
    t = re.sub(r"[^a-z]", "", _fold(s))
    if not t:
        return ""
    t = t.replace("ck", "k").replace("q", "k").replace("ph", "f").replace("kh", "k")
    t = t.replace("ee", "i").replace("ie", "i").replace("oo", "u").replace("w", "v")
    t = re.sub(r"(.)\1+", r"\1", t)            # collapse doubled letters
    t = re.sub(r"h$", "", t)                   # Sarah/Sara
    t = re.sub(r"y$", "i", t)                  # Ami/Amy
    t = re.sub(r"([aeiou])h(?=[aeiou])", r"\1", t)
    return t


def _tokens(s: str) -> List[str]:
    return re.findall(r"[a-z0-9']+", s)


def _norm_people(people: Any) -> List[Dict[str, Any]]:
    """One entry per distinct chart_id_b, with every relation group it can satisfy."""
    out: Dict[str, Dict[str, Any]] = {}
    for p in (people or []):
        if not isinstance(p, dict):
            continue
        cid = str(p.get("chart_id_b") or p.get("chart_id") or "").strip()
        name = str(p.get("name_b") or p.get("name") or "").strip()
        if not cid or not name:
            continue
        rel = str(p.get("compat_type") or p.get("relation") or "").strip().lower()
        e = out.setdefault(cid, {"name": name, "chart_id": cid, "relations": set(),
                                 "compat_types": []})
        e["relations"] |= _COMPAT_GROUPS.get(rel, set())
        if rel and rel not in e["compat_types"]:
            e["compat_types"].append(rel)
    return list(out.values())


def _subject_focus(text: str, s: int, e: int) -> bool:
    """Is the mention at text[s:e] the SUBJECT of the question (not context)?"""
    before = text[:s]
    after = text[e:]
    btoks = _tokens(before)
    atoks = _tokens(after)[:6]
    # context for the asker -> not the subject
    if any(t in _OBJECT_AFTER for t in atoks):
        return False
    if re.match(r"^\s*(and|y|e|aur)\s+(i|me|yo|eu|main)\b", after):
        return False
    tail = " ".join(btoks[-4:])
    if _RELATIONSHIP_WORD_BEFORE.search(before.rstrip()[-40:] if before else ""):
        return False
    pre = list(btoks)
    while pre and pre[-1] in _DETERMINERS:
        pre.pop()
    pre_txt = " ".join(pre[-3:])
    if _RELATIONAL_BEFORE.search(pre_txt):
        return False
    # P1: possessive / ka-ki-ke
    if re.match(r"^('s|s'|\s+(ka|ki|ke)\b)", after) or re.match(r"^'", after):
        return True
    # P1b: "about X", "de mi hijo", "what about X"
    if _ABOUT_BEFORE.search(pre_txt):
        return True
    # P2: interrogative / auxiliary right before
    if not pre:
        return True        # question opens with the person: "Amik, how is ...?" / "My son will ..."
    if pre[-1] in _INTERROG:
        return True
    if len(pre) >= 2 and pre[-2] in _INTERROG and pre[-1] in _AUX:
        return True
    # P2b: verb-first Romance order, "va a casarse mi hija" / "vai se casar meu filho"
    if re.search(r"\b(casarse|se casa|se casara|casara|se casar|enfermarse|graduarse|"
                 r"recuperarse|se formar|se recuperar)\s*$", " ".join(pre[-3:])):
        return True
    # P3: followed by an own-life predicate
    if _LIFE_AFTER.search(after[:60]):
        return True
    return False


def _find_relations(text: str):
    """[(group, start, end)] of focused relation words, word-boundary matched."""
    hits = []
    for m in re.finditer(r"[a-z0-9][a-z0-9'\-]*", text):
        w = m.group(0).strip("'-")
        grp = _REL_WORDS.get(w)
        if not grp:
            continue
        # a bare relation word must be possessed ("my son", "mi hijo", "mera beta")
        pre = _tokens(text[:m.start()])
        if not pre or pre[-1] not in _DETERMINERS - {"the", "el", "la", "o", "a", "los", "las", "os", "as"}:
            # allow Hinglish/Spanish possessive after noun? keep strict: needs my/mi/meu/mera...
            if not (len(pre) >= 2 and pre[-2] in {"my", "mi", "meu", "minha", "mera", "meri", "mere"}):
                continue
        # "mama"/"nana" are ambiguous across groups: first registration wins; fine.
        hits.append((grp, m.start(), m.end()))
    # multiword: "business partner"
    for m in re.finditer(r"\bmy (business partner|co-founder|in-laws|mother-in-law|father-in-law)\b", text):
        g = "cofounder" if "founder" in m.group(1) else ("partner" if "partner" in m.group(1) else "family")
        hits.append((g, m.start(1), m.end(1)))
    return hits


def _find_names(text: str, orig: str, people: List[Dict[str, Any]]):
    """[(person_entry, start, end, full)] for names mentioned in the question."""
    hits = []
    orig_f = _fold(orig)
    for p in people:
        parts = [t for t in re.findall(r"[A-Za-zÀ-ÿ']+", _fold(p["name"]))]
        if not parts:
            continue
        full = " ".join(parts)
        first = parts[0]
        # full name (exact folded) first
        if len(parts) > 1:
            m = re.search(r"\b" + re.escape(full) + r"\b", text)
            if m:
                hits.append((p, m.start(), m.end(), True))
                continue
        key = norm_name(first)
        if not key or len(key) < 2:
            continue
        for m in re.finditer(r"[a-z][a-z']*", text):
            w = re.sub(r"('s|s')$", "", m.group(0))
            if norm_name(w) != key:
                continue
            if first in _COMMON_WORD_NAMES or w in _COMMON_WORD_NAMES:
                seg = orig[m.start():m.end()]
                if not seg[:1].isupper() or m.start() == 0:
                    continue
            hits.append((p, m.start(), m.start() + len(w), False))
            break
    return hits


def resolve_subject(question: str, asker_chart_id: str = "",
                    people: Optional[list] = None) -> Dict[str, Any]:
    """-> {subject: 'self'|'person'|'ambiguous', relation, person, candidates,
           confidence, missing}.  Never raises; any trouble => self."""
    self_res = {"subject": "self", "relation": None, "person": None, "candidates": [],
                "confidence": 1.0, "missing": False}
    try:
        orig = question or ""
        text = _fold(orig)
        if not text.strip() or _SELF_OVERRIDE.search(text):
            return self_res
        plist = [p for p in _norm_people(people) if p["chart_id"] != str(asker_chart_id or "")]

        # 1) names (strongest evidence), subject-focused only
        name_hits = []
        for p, s, e, full in _find_names(text, orig, plist):
            if _subject_focus(text, s, e):
                name_hits.append((p, full))
        if name_hits:
            full_hits = [p for p, f in name_hits if f]
            pool = full_hits or [p for p, _ in name_hits]
            uniq = {p["chart_id"]: p for p in pool}
            if len(uniq) == 1:
                p = next(iter(uniq.values()))
                rel = _relation_label(p, _first_rel(text))
                return {"subject": "person", "relation": rel,
                        "person": {"name": p["name"], "chart_id": p["chart_id"]},
                        "candidates": [], "confidence": 0.95 if name_hits else 0.8,
                        "missing": False}
            return _ambiguous(list(uniq.values()))

        # 2) relation words ("my son") against the asker's people of that kind
        rel_hits = [(g, s, e) for g, s, e in _find_relations(text)
                    if _subject_focus(text, s, e)]
        if rel_hits:
            groups = []
            for g, _, _ in rel_hits:
                if g not in groups:
                    groups.append(g)
            if len(groups) == 1:
                g = groups[0]
                cands = [p for p in plist if g in p["relations"]]
                if len(cands) == 1:
                    p = cands[0]
                    return {"subject": "person", "relation": g,
                            "person": {"name": p["name"], "chart_id": p["chart_id"]},
                            "candidates": [], "confidence": 0.85, "missing": False}
                if len(cands) >= 2:
                    return _ambiguous(cands, relation=g)
                return {"subject": "person", "relation": g, "person": None,
                        "candidates": [], "confidence": 0.7, "missing": True}
        return self_res
    except Exception:
        return self_res


def _first_rel(text: str) -> Optional[str]:
    for g, s, e in _find_relations(text):
        return g
    return None


def _relation_label(p: Dict[str, Any], said: Optional[str]) -> Optional[str]:
    if said and said in p["relations"]:
        return said
    for pref in ("partner", "child", "parent", "sibling", "friend", "boss", "employee",
                 "cofounder", "advisor", "family"):
        if pref in p["relations"]:
            return pref
    return said


def _ambiguous(cands: List[Dict[str, Any]], relation: Optional[str] = None) -> Dict[str, Any]:
    return {"subject": "ambiguous", "relation": relation, "person": None,
            "candidates": [{"name": c["name"], "chart_id": c["chart_id"]} for c in cands[:6]],
            "confidence": 0.5, "missing": False}
