"""
antar_research/life_context_qa.py  —  READ-ONLY QA for life_context accessor.

Covers the brief's Section 5 checklist:
  [1] marital_status flipped single<->married changes the relationship framing
      (a married user is NEVER told to "find someone").
  [2] career_stage=running_business surfaces funding/entrepreneurial framing;
      studying does NOT.
  [3] has_context=False -> every surface still renders a clean neutral read
      (no crash, no "undefined", empty prompt block).
  [4] onboarding-written values (life_*) reach get_life_context and win over
      the patra schema defaults.

Run:  cd ~/antarai && source venv311/bin/activate && python antar_research/life_context_qa.py
No DB writes. Optionally validates against live charts if --live is passed.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from antar_engine.life_context import get_life_context, life_context_to_prompt_block

PASS, FAIL = "PASS", "FAIL"
_results = []

def check(name, cond, detail=""):
    _results.append((PASS if cond else FAIL, name, detail))
    print(f"  [{PASS if cond else FAIL}] {name}" + (f"  — {detail}" if detail else ""))


def test_marital_flip():
    print("\n[1] marital flip single <-> married")
    single = get_life_context(chart_record={"marital_status": "single"})
    married = get_life_context(chart_record={"marital_status": "married"})
    check("single -> 'single'", single["marital_status"] == "single", single["marital_status"])
    check("married -> 'married'", married["marital_status"] == "married", married["marital_status"])
    b_single = life_context_to_prompt_block(single).lower()
    b_married = life_context_to_prompt_block(married).lower()
    check("single block invites meeting/finding", "find" in b_single or "meeting" in b_single)
    check("married block NEVER says find a partner",
          "find a partner" not in b_married and "find someone" not in b_married)
    check("married block deepens partnership", "deepen" in b_married)


def test_career_framing():
    print("\n[2] running_business funding framing vs studying")
    biz = get_life_context(chart_record={"career_stage": "entrepreneur"})
    study = get_life_context(chart_record={"career_stage": "student"})
    check("entrepreneur -> running_business", biz["career_stage"] == "running_business", biz["career_stage"])
    check("student -> studying", study["career_stage"] == "studying", study["career_stage"])
    b_biz = life_context_to_prompt_block(biz).lower()
    b_study = life_context_to_prompt_block(study).lower()
    check("running_business surfaces FUNDING", "funding" in b_biz)
    check("studying does NOT surface funding", "funding" not in b_study)


def test_absent_neutral():
    print("\n[3] has_context=False -> clean neutral")
    # Empty record, all-default patra record, and missing row all -> neutral.
    empty = get_life_context(chart_record={})
    defaults = get_life_context(chart_record={
        "career_stage": "mid_career", "marital_status": "unknown",
        "children_status": "no_children_unsure", "health_status": "excellent",
        "financial_status": "stable", "life_work": None,
        "life_relationship": None, "life_kids": None})
    missing = get_life_context(chart_id="does-not-exist", supabase=None)
    for label, lc in (("empty", empty), ("all-default", defaults), ("missing", missing)):
        check(f"{label}: has_context False", lc["has_context"] is False, str(lc))
        block = life_context_to_prompt_block(lc)
        check(f"{label}: prompt block empty", block == "", repr(block[:40]))
        check(f"{label}: no 'undefined'/'none' leak",
              "undefined" not in block.lower())


def test_onboarding_wins_over_defaults():
    print("\n[4] onboarding life_* wins over patra defaults")
    # Mirrors the 3 real onboarded charts in prod.
    onboarded = get_life_context(chart_record={
        "life_work": "building", "life_relationship": "partnered", "life_kids": "none",
        "career_stage": "mid_career", "marital_status": "unknown",
        "children_status": "no_children_unsure", "health_status": "excellent",
        "financial_status": "stable"})
    check("life_work 'building' -> running_business (not default 'job')",
          onboarded["career_stage"] == "running_business", onboarded["career_stage"])
    check("life_relationship 'partnered' -> relationship",
          onboarded["marital_status"] == "relationship", onboarded["marital_status"])
    check("life_kids 'none' -> no", onboarded["children_status"] == "no", onboarded["children_status"])
    check("has_context True", onboarded["has_context"] is True)
    # Real patra value must still win when present (de0c6265: in_relationship).
    real = get_life_context(chart_record={
        "marital_status": "in_relationship", "career_stage": "mid_career",
        "children_status": "no_children_unsure"})
    check("real patra in_relationship -> relationship", real["marital_status"] == "relationship")
    check("default career with no life_work -> None (neutral)", real["career_stage"] is None)


def test_live(supabase):
    print("\n[LIVE] validating against real charts")
    fixtures = {
        "1496055b-3603-44d9-8bea-49f54d1351c9": {"career_stage": "running_business",
            "marital_status": "relationship", "children_status": "no"},
        "6b7ab7b0-97ed-40fb-82b0-7e7b9b430c16": {"marital_status": "married",
            "children_status": "yes"},
        "7c38b6b7-30f7-4ef1-8576-e571f9b7bd6e": {"marital_status": "single",
            "children_status": "no"},
        "de0c6265-96cc-41ba-a39c-e55868fa5806": {"marital_status": "relationship"},
    }
    for cid, expect in fixtures.items():
        lc = get_life_context(cid, supabase=supabase)
        for k, v in expect.items():
            check(f"{cid[:8]} {k}=={v}", lc.get(k) == v, f"got {lc.get(k)}")


def main():
    print("=" * 60)
    print("life_context QA")
    print("=" * 60)
    test_marital_flip()
    test_career_framing()
    test_absent_neutral()
    test_onboarding_wins_over_defaults()

    if "--live" in sys.argv:
        try:
            from supabase import create_client
            env = {}
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            for line in open(os.path.join(base, ".env")):
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, val = line.split("=", 1)
                    env[k] = val.strip().strip('"').strip("'")
            sb = create_client(env["SUPABASE_URL"],
                               env.get("SUPABASE_SERVICE_ROLE_KEY") or env["SUPABASE_KEY"])
            test_live(sb)
        except Exception as e:
            print(f"  [skip] live tests: {e}")

    fails = [r for r in _results if r[0] == FAIL]
    print("\n" + "=" * 60)
    print(f"{len(_results) - len(fails)}/{len(_results)} passed")
    if fails:
        print("FAILURES:")
        for _, n, d in fails:
            print(f"  - {n}: {d}")
        sys.exit(1)
    print("ALL GREEN")


if __name__ == "__main__":
    main()
