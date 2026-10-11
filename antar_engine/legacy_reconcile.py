"""[legacy-reconcile 2026-10-11] Make the OLD Today / This Month / This Year fields agree with the new `decision` block.

The decision blocks are composed from the structured engine fields and are internally consistent. The older prose
fields on the same payloads were written by other layers and could still contradict them (live, 2026-10-11):

  Today   headline / highlight lead with "a journey far from home" while the decision (and the evidence engine) lead
          with work and income; do_today says "take the short trip" on a day the decision says work; moon_nakshatra
          says Swati while the signals (and the decision) say Chitra; todays_nudge says "say yes to the new thing"
          next to a timed move.
  Month   priority_actions still offer advice whose date has passed ("cap your exposure before October 8" on Oct 11).
  Year    theme "a year of expansion" next to year_theme "guard your speculative bets"; year_summary "your money is
          the strong axis" next to an event "money comes under pressure".

When a decision block exists, the decision wins: these helpers overwrite or filter the conflicting legacy fields
IN PLACE. Deterministic, idempotent, never raises, and a field is only changed when the decision gives a truthful
replacement (otherwise it is left alone). English-only filters (do/don't, domain labels) skip other languages
rather than guess."""
from __future__ import annotations

import re
from datetime import date, datetime

# decision `evidence.chosen` key -> the do/don't domains that agree with it
_AGREES = {
    "work": {"work", "authority", "learning"}, "network": {"money", "work", "authority"}, "money": {"money"},
    "father": {"travel", "spiritual", "learning", "authority"}, "body": {"health"}, "relationship": {"relationship"},
    "family": {"family", "home"}, "travel": {"travel"}, "home": {"home", "family"},
}
_PRIMARY = {"work": "work", "network": "money", "money": "money", "father": "spiritual", "body": "health",
            "relationship": "relationship", "family": "family", "travel": "travel", "home": "home"}
_LABEL_HINT = {"work": "work", "network": "money", "money": "money", "father": "travel", "body": "health",
               "relationship": "relationship", "family": "family", "travel": "travel", "home": "home"}


def _first_sentence(s: str) -> str:
    s = (s or "").strip()
    m = re.match(r"(.+?[.!?])(\s|$)", s)
    return m.group(1).strip() if m else s


# day_energy.key is THE day-level source (daily_v2.day_energy; the app reads only it for the chips). The LLM-authored
# verdict_label / verdict_emoji and the older strength / score / direction / is_friction_day are internals that can
# disagree with it ("High" + score 10 on a lighter-touch day). Map every one of them from the key.
_VERDICT = {
    "steady":   {"emoji": "\u25c6", "strength": "high",   "band": (7, 10), "en": "Good",    "es": "Bueno"},
    "light":    {"emoji": "\u25cf", "strength": "medium", "band": (4, 6),  "en": "Neutral", "es": "Neutro"},
    "friction": {"emoji": "\u26a0", "strength": "low",    "band": (0, 3),  "en": "Caution", "es": "Precauci\u00f3n"},
}


def verdict(p: dict, language: str = "en") -> list:
    """Make verdict_label / verdict_emoji / strength / score / direction / is_friction_day agree with day_energy."""
    changed: list = []
    try:
        de = p.get("day_energy") if isinstance(p, dict) else None
        v = _VERDICT.get((de or {}).get("key"))
        if not v:
            return changed
        lang = language if language in ("en", "es") else "en"

        def _set(k, val):
            if p.get(k) != val:
                p[k] = val
                changed.append(k)
        _set("verdict_label", v[lang])
        _set("verdict_emoji", v["emoji"])
        _set("strength", v["strength"])
        _set("is_friction_day", de["key"] == "friction")
        lo, hi = v["band"]
        try:
            sc = int(p.get("score"))
        except (TypeError, ValueError):
            sc = None
        if sc is None or not (lo <= sc <= hi):
            sc = max(lo, min(hi, sc if sc is not None else (lo + hi) // 2))
            _set("score", sc)
        if de.get("score") != sc:
            de["score"] = sc
            changed.append("day_energy.score")
        if de["key"] == "friction" and p.get("direction") == "positive":
            _set("direction", "negative")
        elif de["key"] == "steady" and p.get("direction") == "negative":
            _set("direction", "positive")
    except Exception:
        pass
    return changed


# Saturday / Sunday: LLM-written prose that sends you to a decision-maker, client or senior contact "before noon" is a
# weekday line. Replace it with the weekend read the decision block already gives (prepare today, send Monday).
_WK_PROSE = re.compile(r"(?i)decision-?maker|\bclient\b|senior contact|someone with authority|authority and deals|reach out|"
                       r"before noon|before midday|push forward|make the ask|"
                       r"tomador de decisiones|cliente|contacto clave|alguien con autoridad|autoridad|antes del mediod|"
                       r"llama o escribe|contacta|haz la petici")
# a weekday money action: negotiating / closing / signing is not a Sunday move
_WK_DEAL = re.compile(r"(?i)negotiat|put a number on the table|close the deal|\bsign\b|"
                      r"negoci|pon un n[u\u00fa]mero|cerrar el trato|firma")
# one DIFFERENT sentence per field — the same line in five places reads as a bug when two of them sit on one screen
_WK = {
    "en": {
        "wow": "A quiet day for visibility \u2014 use it to prepare, and let Monday be the day you ask.",
        "observa": "Notice what you would want to put in front of someone senior; write it down today and keep it for Monday.",
        "senal": "Today is better for preparing than pitching: draft the ask now, make it Monday.",
        "sub": "Quiet for visibility \u2014 prepare today, ask on Monday.",
        "do_ask": "Draft the ask you'll make on Monday \u2014 prepare it today, hold it until then.",
        "do_num": "Write down the number and terms you'd put on the table on Monday \u2014 don't negotiate today.",
    },
    "es": {
        "wow": "Un d\u00eda tranquilo para la visibilidad: \u00fasalo para preparar, y deja el lunes para pedir.",
        "observa": "Fíjate en lo que querrías poner delante de alguien con peso; an\u00f3talo hoy y gu\u00e1rdalo para el lunes.",
        "senal": "Hoy conviene preparar m\u00e1s que proponer: redacta la petici\u00f3n ahora y hazla el lunes.",
        "sub": "Tranquilo para la visibilidad: prepara hoy, pide el lunes.",
        "do_ask": "Redacta lo que pedir\u00e1s el lunes: prep\u00e1ralo hoy y gu\u00e1rdalo hasta entonces.",
        "do_num": "Anota la cifra y las condiciones que pondr\u00edas sobre la mesa el lunes: hoy no negocies.",
    },
}
_WK_FIELD = {"wow": "wow", "observa_hoy_text": "observa", "senal_de_hoy": "senal", "signal": "senal", "energy": "senal",
             "verdict_subline": "sub"}
_WK_LIST_FIELDS = ("haz_hoy", "aligned_for")


def weekend_prose(p: dict, language: str = "en") -> list:
    """On a weekend with a work/network lead, replace weekday-only contact / deal prose in the older fields."""
    changed: list = []
    try:
        from antar_engine.today_decision import _is_weekend
        if not isinstance(p, dict) or language not in _WK or not _is_weekend(p):
            return changed
        if not any(k in ("work", "network") for k in ((p.get("evidence") or {}).get("chosen") or [])):
            return changed
        tx = _WK[language]
        weekday = lambda x: isinstance(x, str) and (_WK_PROSE.search(x) or _WK_DEAL.search(x))
        for k, key in _WK_FIELD.items():
            v = p.get(k)
            if isinstance(v, str) and v and v != tx[key] and weekday(v):
                p[k] = tx[key]
                changed.append(k)
        for k in _WK_LIST_FIELDS:
            v = p.get(k)
            if isinstance(v, list) and any(weekday(x) for x in v):
                out, used = [], set()
                for x in v:
                    if weekday(x):
                        key = "do_ask" if _WK_PROSE.search(x) else "do_num"
                        if key not in used:
                            out.append(tx[key])
                            used.add(key)
                    else:
                        out.append(x)
                if out != v:
                    p[k] = out
                    changed.append(k)
    except Exception:
        pass
    return changed


def today(p: dict, dec: dict, language: str = "en", do_by_domain: dict | None = None) -> list:
    """Align the Today payload `p` with its decision block `dec`. Returns the names of the fields changed."""
    changed: list = []
    try:
        if not isinstance(p, dict) or not isinstance(dec, dict):
            return changed
        changed += verdict(p, language)
        changed += weekend_prose(p, language)

        def _set(k, v):
            if v and p.get(k) != v:
                p[k] = v
                changed.append(k)

        # headline / highlight / the "move" trio: the decision's lead, not the older engine's lead domain
        _set("headline", _first_sentence(dec.get("prediction")))
        _set("highlight", dec.get("move"))
        for k in ("todays_nudge", "move", "el_movimiento"):
            if k in p or k == "move":
                _set(k, dec.get("move"))

        # the Moon's star: the signals row is computed from the live Moon; the older field can lag a nakshatra
        for sg in (p.get("signals") or []):
            if sg.get("key") == "nakshatra" and sg.get("value"):
                nak = str(sg["value"]).split("·")[0].strip()
                if nak and p.get("moon_nakshatra") != nak:
                    p["moon_nakshatra"] = nak
                    changed.append("moon_nakshatra")
                break

        if language != "en":
            return changed

        chosen = [k for k in ((p.get("evidence") or {}).get("chosen") or []) if k in _AGREES][:2]
        if not chosen:
            return changed

        # headline domain chips: lead with what the decision leads with
        hd = p.get("headline_domains")
        if isinstance(hd, list) and hd:
            hints = [_LABEL_HINT[k] for k in chosen]
            order = sorted(range(len(hd)), key=lambda i: (
                min([n for n, h in enumerate(hints) if h in str(hd[i]).lower()] or [99]), i))
            new = [hd[i] for i in order]
            if new != hd:
                p["headline_domains"] = new
                changed.append("headline_domains")

        # Do list: keep only items whose domain agrees with the lead; never leave the list empty
        if do_by_domain:
            rev = {v["do"]: k for k, v in do_by_domain.items()}
            allowed = set().union(*(_AGREES[k] for k in chosen))
            do, why = list(p.get("do_today") or []), list(p.get("do_today_why") or [])
            if do and all(x in rev for x in do):
                keep = [i for i, x in enumerate(do) if rev[x] in allowed]
                if len(keep) != len(do):
                    if keep:
                        p["do_today"] = [do[i] for i in keep]
                        if len(why) == len(do):
                            p["do_today_why"] = [why[i] for i in keep]
                    else:
                        prim = (do_by_domain.get(_PRIMARY[chosen[0]]) or {}).get("do")
                        if prim:
                            p["do_today"] = [prim]
                            p["do_today_why"] = [""] if len(why) == len(do) else why
                    changed.append("do_today")
    except Exception:
        pass
    return changed


# ---------------------------------------------------------------- Month
_MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
     "november", "december"], 1)}
_BEFORE = re.compile(r"(?i)\b(?:before|by|until|through|ahead of)\s+(" + "|".join(_MONTHS) + r")\s+(\d{1,2})\b")


def month(p: dict, dec: dict, today_d: date | None = None) -> list:
    """Drop priority_actions whose own deadline has already passed (the decision block already skips them)."""
    changed: list = []
    try:
        if not isinstance(p, dict) or not isinstance(dec, dict):
            return changed
        today_d = today_d or datetime.utcnow().date()
        acts = p.get("priority_actions")
        if not isinstance(acts, list):
            return changed
        keep = []
        for a in acts:
            t = (a.get("action") if isinstance(a, dict) else str(a)) or ""
            past = False
            for m in _BEFORE.finditer(t):
                try:
                    if date(today_d.year, _MONTHS[m.group(1).lower()], int(m.group(2))) < today_d:
                        past = True
                except ValueError:
                    pass
            if not past:
                keep.append(a)
        if len(keep) != len(acts):
            p["priority_actions"] = keep
            changed.append("priority_actions")
    except Exception:
        pass
    return changed


# ---------------------------------------------------------------- Year
def year(p: dict, dec: dict, language: str = "en") -> list:
    """The decision's arc-derived read replaces the theme / summary prose that contradicts it."""
    changed: list = []
    try:
        if not isinstance(p, dict) or not isinstance(dec, dict):
            return changed
        pred, holds, brk = dec.get("prediction"), dec.get("holds"), dec.get("breaks")
        if not (pred and holds and brk):
            return changed
        for k in ("theme", "year_theme"):
            if k in p and p.get(k) != pred:
                p[k] = pred
                changed.append(k)
        # two producers named the year's character differently (yearly_v2 "Expansion" vs the plan's dasha-lord enum
        # "transformation"): the plan's canonical enum wins
        yq = p.get("year_quality")
        if isinstance(yq, str) and yq.strip() and "quality" in p and str(p.get("quality")).lower() != yq.strip().lower():
            p["quality"] = yq.strip().capitalize()
            changed.append("quality")
        summary = f"{pred} {holds} {brk}"
        if "year_summary" in p and p.get("year_summary") != summary:
            p["year_summary"] = summary
            changed.append("year_summary")
        # the "switched-on forces" line ("expand") is the opposite of a year with a pressured arc
        arcs = p.get("arcs") or []
        if "active" in p and any(a.get("trend") in ("pressure", "falling") for a in arcs):
            p["active"] = ""
            changed.append("active")
    except Exception:
        pass
    return changed
