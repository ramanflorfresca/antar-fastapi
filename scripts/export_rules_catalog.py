"""Write a readable catalog of every library rule (CSV): what it says, which conditions must hold in the chart, when it
happens, which line it belongs to. Open it in a spreadsheet; edit via antar_engine/data/rule_overrides.json."""
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from antar_engine import book_rules, combo_rules
from antar_engine.rule_describe import describe
from antar_engine.reading_library import line_of

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "antar_engine", "data")


def rows():
    for fname, system in (("book_rules.json", None), ("book_rules_kp.json", "KP (internal, off)"), ("book_rules_varsha.json", "Solar return (not applied yet)"), ("book_rules_market.json", "Market timing (off)")):
        for r in json.load(open(os.path.join(DATA, fname))).get("rules", []):
            sysname = system or ("Same for everyone (transit only)" if combo_rules.is_impersonal(r) else
                                 ("Jaimini line" if line_of(r) == "jaimini" else "Vimshottari line"))
            yield [r["id"], book_rules.label(r), sysname, r.get("tone"), ",".join(r.get("topics") or []),
                   describe(r.get("requires")), describe(r.get("activation")) if r.get("activation") else "(standing: always true once natal conditions hold)",
                   r.get("effect"), r.get("remedy") or "", r.get("clarity"), r.get("line")]


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/antarai/Antar.world/RULES_CATALOG.csv")
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "book", "system_line", "tone", "topics", "chart_must_have", "when_it_happens", "user_sees", "remedy", "clarity", "book_line"])
        n = 0
        for row in rows():
            w.writerow(row)
            n += 1
    print(n, "rules ->", out)
