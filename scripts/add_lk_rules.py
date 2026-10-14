"""Append reader-written Lal Kitab rules (Antar LK format) to lk_roop_chand_rules.json, with the same fixed filters:
no planet names / jargon / character labels in the effect, no exact duplicates, nothing sensitive.
Usage: python scripts/add_lk_rules.py Antar.world/RULES_book_lk_sure_shot_2026-10-14.json"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.build_rc_rules import PLANET_RE, JARGON_RE, LABEL_RE

PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "antar_engine", "data", "lk_roop_chand_rules.json")


def key(r):
    return (r.get("kind"), r.get("planet"), tuple(r.get("houses") or ()), tuple(r.get("annual_houses") or ()),
            json.dumps(r.get("requires", []), sort_keys=True), r.get("tone"), r.get("effect"))


def add(src):
    base = json.load(open(PATH))
    have = {key(r) for r in base["rules"]}
    ids = {r["id"] for r in base["rules"]}
    st = {"read": 0, "added": 0, "dup": 0, "wording": 0, "no_effect": 0}
    for r in json.load(open(src)).get("rules", []):
        st["read"] += 1
        en = (r.get("effect") or "").strip()
        if not en or r.get("sensitive") or r.get("drop"):
            st["no_effect"] += 1
            continue
        if PLANET_RE.search(en) or JARGON_RE.search(en) or LABEL_RE.search(en):
            st["wording"] += 1
            continue
        if re.search(r"\b(if|unless|provided)\b", en, re.I):      # conditional on conduct or events we cannot see
            st["conditional"] = st.get("conditional", 0) + 1
            continue
        if r["id"] in ids or key(r) in have:
            st["dup"] += 1
            continue
        ids.add(r["id"]); have.add(key(r))
        base["rules"].append(r)
        st["added"] += 1
    json.dump(base, open(PATH, "w"), indent=0, ensure_ascii=False)
    return st


if __name__ == "__main__":
    print(add(sys.argv[1]))
