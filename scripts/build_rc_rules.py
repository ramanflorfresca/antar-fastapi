"""
Build antar_engine/data/lk_roop_chand_rules.json from the four reader outputs
(DATA_rc_rules_{A,B,C,D}_*.json: Roop Chand's text decomposed into atomic rules).

Steps (fixed, no judgement calls hidden here):
  1. drop sensitive rules (death, longevity, disease, harm to relatives, occult) and rules with no effect text
  2. turn 'rising sign is X' unparsed clauses into {"lagna_sign": X}
  3. drop every rule that still has an unparsed clause (it could never apply) -> backlog file, not shipped
  4. drop exact duplicates
  5. drop rules that the text contradicts under IDENTICAL conditions (same kind, planet, houses, requires, one good
     and one bad): the text gives no way to choose, so the engine stays silent
Usage: python scripts/build_rc_rules.py [data_dir]
"""
import json
import os
import re
import sys

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn",
         "Aquarius", "Pisces"]
KEEP = ("id", "kind", "planet", "houses", "annual_houses", "requires", "tone", "topics", "effect", "effect_es", "ages",
        "remedy", "remedy_es", "line", "clarity")


def convert_lagna(clause):
    if "unparsed" not in clause:
        return clause
    m = re.search(r"(?:rising sign|lagna sign|lagan sign|ascendant)\D{0,12}(" + "|".join(SIGNS) + ")", clause["unparsed"], re.I)
    return {"lagna_sign": m.group(1).capitalize()} if m else clause


def build(data_dir):
    raw = []
    for x in "ABCD":
        raw += json.load(open(os.path.join(data_dir, f"DATA_rc_rules_{x}_2026-10-13.json")))["rules"]
    stats = {"raw": len(raw)}
    rules = [r for r in raw if not r.get("sensitive") and (r.get("effect") or "").strip() not in ("", "(omitted)")]
    stats["after_sensitive"] = len(rules)
    for r in rules:
        r["requires"] = [convert_lagna(c) for c in r.get("requires", [])]
    # an effect that carries its own condition ("if the entrance faces south...") has a condition we cannot check
    cond = re.compile(r"\b(if|when|unless|provided|only if|whenever|in case)\b", re.I)
    embedded = [r for r in rules if cond.search(r["effect"])]
    stats["dropped_embedded_condition"] = len(embedded)
    rules = [r for r in rules if not cond.search(r["effect"])]
    backlog = [r for r in rules if any("unparsed" in c for c in r["requires"])]
    rules = [r for r in rules if not any("unparsed" in c for c in r["requires"])]
    stats["unparsed_backlog"] = len(backlog)
    seen, uniq = set(), []
    for r in rules:
        key = (r["kind"], r.get("planet"), tuple(r.get("houses") or ()), tuple(r.get("annual_houses") or ()),
               json.dumps(r["requires"], sort_keys=True), r["tone"], r["effect"])
        if key not in seen:
            seen.add(key)
            uniq.append(r)
    stats["after_dedupe"] = len(uniq)
    # contradiction = same conditions, same TOPIC, one good and one bad. Remove that topic from the clashing rules
    # (a rule is dropped only when no topic is left), so a placement good for money and bad for marriage survives.
    def gkey(r):
        return (r["kind"], r.get("planet"), tuple(r.get("houses") or ()), tuple(r.get("annual_houses") or ()),
                json.dumps(r["requires"], sort_keys=True))
    tones = {}
    for r in uniq:
        for t in r.get("topics") or ["other"]:
            tones.setdefault((gkey(r), t), set()).add(r["tone"])
    clash = {k for k, v in tones.items() if {"good", "bad"} <= v}
    final = []
    for r in uniq:
        topics = [t for t in (r.get("topics") or ["other"]) if (gkey(r), t) not in clash or r["tone"] not in ("good", "bad")]
        if topics:
            final.append({**r, "topics": topics})
    stats["clashing_topic_groups"] = len(clash)
    stats["dropped_as_contradictory"] = len(uniq) - len(final)
    stats["final"] = len(final)
    stats["by_kind"] = {k: sum(1 for r in final if r["kind"] == k) for k in ("natal", "annual")}
    return [{k: r.get(k) for k in KEEP} for r in final], backlog, stats


PLANET_RE = re.compile(r"\b(sun|moon|mars|mercury|jupiter|venus|saturn|rahu|ketu|sol|luna|marte|mercurio|j[uú]piter|saturno)\b", re.I)
JARGON_RE = re.compile(r"\b(dasha|lagna|lagan|karaka|yoga|pakka|cell|house|native|zodiac|aries|taurus|gemini|cancer|leo|virgo|libra|scorpio|sagittarius|capricorn|aquarius|pisces)\b", re.I)


# character labels, not guidance: the product speaks to serious people about decisions, so these never ship
LABEL_RE = re.compile(r"\b(perverse|vile|thie(f|ves)|cheat\w*|liar|lies|lying|immoral|criminal|wicked|evil|sinful|lustful|"
                      r"debauch\w*|rogue|rascal|scoundrel|cruel\w*|selfish|blasphem\w*|ill[- ]intent\w*|ill-intended|"
                      r"degenerate|pervert\w*|shameless|lazy|greedy|avaricious|miser\w*|hypocrit\w*|fraud\w*|"
                      r"defame\w*|disgrace\w*|barbar\w*|stupid|fool\w*|ugly|mean-minded)\b", re.I)


def apply_effects(final, data_dir):
    """Second stage: replace each effect/remedy with its editorial plain-language version (en + es), drop what the
    editors dropped, and drop anything that still names a planet or uses technical words."""
    items = {}
    for k in (1, 2, 3, 4):
        items.update(json.load(open(os.path.join(data_dir, f"DATA_rc_effects_{k}_2026-10-13.json")))["items"])
    out, stats = [], {"edited": 0, "dropped_by_editor": 0, "dropped_planet_or_jargon": 0, "missing_edit": 0}
    for r in final:
        it = items.get(r["id"])
        if it is None:
            stats["missing_edit"] += 1
            continue
        if it.get("drop") or not (it.get("en") or "").strip():
            stats["dropped_by_editor"] += 1
            continue
        text_en, text_es = it["en"].strip(), (it.get("es") or "").strip()
        if LABEL_RE.search(text_en):
            stats["dropped_character_label"] = stats.get("dropped_character_label", 0) + 1
            continue
        if PLANET_RE.search(text_en) or JARGON_RE.search(text_en):
            stats["dropped_planet_or_jargon"] += 1
            continue
        rem_en, rem_es = (it.get("remedy_en") or "").strip() or None, (it.get("remedy_es") or "").strip() or None
        if rem_en and (PLANET_RE.search(rem_en) or JARGON_RE.search(rem_en)):
            rem_en = rem_es = None
        if text_es and PLANET_RE.search(text_es):
            text_es = ""
        r = dict(r, effect=text_en, effect_es=text_es or None, remedy=rem_en, remedy_es=rem_es)
        out.append(r)
        stats["edited"] += 1
    return out, stats


if __name__ == "__main__":
    data_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/antarai/Antar.world")
    final, backlog, stats = build(data_dir)
    if os.path.exists(os.path.join(data_dir, "DATA_rc_effects_4_2026-10-13.json")):
        final, stats2 = apply_effects(final, data_dir)
        stats.update({"stage2": stats2, "final_after_editorial": len(final)})
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "antar_engine", "data",
                       "lk_roop_chand_rules.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump({"source": "Pt. Roop Chand Joshi, Text Book of Lal Kitab (five classics), decomposed 2026-10-13",
               "rules": final}, open(out, "w"), indent=0, ensure_ascii=False)
    json.dump({"rules": backlog}, open(os.path.join(data_dir, "DATA_rc_rules_unparsed_backlog_2026-10-13.json"), "w"),
              indent=0, ensure_ascii=False)
    print(json.dumps(stats, indent=1))
