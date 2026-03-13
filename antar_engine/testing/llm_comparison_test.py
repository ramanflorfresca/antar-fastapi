"""
llm_comparison_test.py
======================
Layer 4 — Compare Anthropic Claude Sonnet vs DeepSeek on identical Antar prompts.
Runs the SAME prompt through both APIs side-by-side and scores each response.

Scores each response on 5 dimensions (1-5):
  1. Astro accuracy    — does it reference the correct placements / dashas?
  2. Energy language   — no house numbers, no planet jargon, warm tone?
  3. Actionability     — ends with something the user can actually do?
  4. Conciseness       — under 200 words without losing substance?
  5. Personalisation   — feels specific to Sam K, not a generic reading?

Run:
    cd antarai
    pip install anthropic openai python-dotenv
    ANTHROPIC_API_KEY=sk-ant-... DEEPSEEK_API_KEY=... python llm_comparison_test.py

Optional flags:
    --prompt career|wealth|health|spiritual|grief  (default: all 5)
    --no-scores    (skip scoring, just print raw responses)
"""

import os
import sys
import argparse
import time
from datetime import date

# ── Path setup ────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
for candidate in [SCRIPT_DIR, os.path.join(SCRIPT_DIR, "antarai")]:
    if os.path.isdir(os.path.join(candidate, "antar_engine")):
        sys.path.insert(0, candidate)
        break

from dotenv import load_dotenv
load_dotenv()

parser = argparse.ArgumentParser()
parser.add_argument("--prompt", default="all")
parser.add_argument("--no-scores", action="store_true")
args = parser.parse_args()

ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")
DEEPSEEK_KEY  = os.getenv("DEEPSEEK_API_KEY", "")

if not ANTHROPIC_KEY:
    print("Set ANTHROPIC_API_KEY env var")
    sys.exit(1)
if not DEEPSEEK_KEY:
    print("Set DEEPSEEK_API_KEY env var")
    sys.exit(1)

# ── Build Sam K chart + LK context (same as production) ──────────────────────
print("Building Sam K chart context...")

try:
    from antar_engine.chart import calculate_chart
    from antar_engine import vimsottari, transits
    from antar_engine.lal_kitab import calculate_varshphal_chart, get_all_varshphal_remedies
    from antar_engine.lal_kitab_db import format_lk_context_from_stored
    from antar_engine.patra import build_patra_context, patra_to_context_block
    from antar_engine.karakas import psychological_profile

    chart_data = calculate_chart(
        birth_date="1970-11-02", birth_time="14:30",
        lat=19.0760, lng=72.8777, timezone="Asia/Kolkata", ayanamsa="lahiri",
    )
    dashas       = {"vimsottari": vimsottari.calculate(chart_data)}
    cur_transits = transits.calculate_transits(chart_data, target_date=None, ayanamsa_mode=1)
    profile_text = psychological_profile(chart_data)

    varshphal  = calculate_varshphal_chart(chart_data, age=55)
    all_rem    = get_all_varshphal_remedies(varshphal, max_planets=4)
    rem_summary = [{"planet": p, "name": r.name, "instructions": r.instructions,
                    "duration": r.duration, "significance": r.significance,
                    "materials": r.materials}
                   for p, rems in all_rem.items() for r in rems]

    lk_data = {
        "age": 55, "table_age": 56,
        "placements": varshphal.placements,
        "is_special_cycle": False,
        "remedies_summary": rem_summary,
    }
    lk_context    = format_lk_context_from_stored(lk_data, concern="career")
    patra = build_patra_context(
        birth_date="1970-11-02",
        user_profile={"marital_status": "married", "career_stage": "mid_career",
                      "financial_status": "stable", "birth_country": "IN",
                      "current_country": "IN", "countries_lived": []},
        primary_concern="career",
    )
    patra_ctx = patra_to_context_block(patra)
    print(f"  ✓ Chart built  |  Lagna: {chart_data['lagna']['sign']}  |  LK: Age 55 / RY 56")

except Exception as e:
    print(f"  Engine error: {e}")
    import traceback; traceback.print_exc()
    # Fall back to pre-built context for LLM-only testing
    chart_data   = None
    lk_context   = """LAL KITAB VARSHPHAL — Age 55 (running year 56):
  Sun: annual house 2    Moon: annual house 3    Mars: annual house 7
  Mercury: annual house 2  Jupiter: annual house 2  Venus: annual house 2
  Saturn: annual house 10  Rahu: annual house 9    Ketu: annual house 12
PRACTICES: Feed birds wheat at sunrise (Sun). Drink water from silver glass (Moon).
Donate red items Tuesdays (Mars). Donate black sesame Saturdays (Saturn)."""
    patra_ctx    = "Life stage: Mid-life consolidation · Age 55 · Career: mid_career · Country: IN"
    profile_text = "Libra ascendant with strong 1st house — leadership, justice, diplomacy."


# ── System prompt (exact copy from main.py) ───────────────────────────────────
SYSTEM_PROMPT = (
    "You are Antar, an astrological life coach. "
    "Answer based only on the data provided. "
    "Never invent planetary positions, dashas, transits, or life events. "
    "Never give medical, financial, or legal advice. "
    "Be concise, warm, and practical. "
    "Never use house numbers in your response — translate everything to energy language."
)

# ── Test prompts ──────────────────────────────────────────────────────────────
PROMPTS = {
    "career": {
        "question": "I'm 55 and feeling stuck in my career. Should I take the new job offer or stay?",
        "concern":  "career",
    },
    "wealth": {
        "question": "Will my investment in real estate pay off this year? Is now a good time?",
        "concern":  "wealth",
    },
    "health": {
        "question": "I've been getting headaches and low energy. What does my chart say about health?",
        "concern":  "health",
    },
    "spiritual": {
        "question": "I feel like something big is ending in my life. Am I in a spiritual transition?",
        "concern":  "spiritual",
    },
    "grief": {
        "question": "I lost my father last year and I still can't move forward. What does my chart say?",
        "concern":  "grief",
    },
}

if args.prompt != "all":
    PROMPTS = {k: v for k, v in PROMPTS.items() if k == args.prompt}


def build_full_prompt(question, concern):
    """Build the same prompt structure as main.py's build_predict_prompt()"""
    lagna = (chart_data or {}).get("lagna", {}).get("sign", "Libra") if chart_data else "Libra"
    return f"""CHART: Libra Lagna (D-1)
Planets: Sun/Mercury/Jupiter/Venus in 1st, Moon in 2nd (Scorpio), Mars in 12th,
         Saturn in 7th (Aries), Rahu in 5th (Aquarius), Ketu in 11th (Leo)

{patra_ctx}

{lk_context}

PSYCHOLOGICAL PROFILE:
{profile_text[:300] if profile_text else 'Libra ascendant — diplomacy, justice, relationships.'}

CURRENT TRANSITS (Mar 2026):
Saturn transiting Aquarius (sade sati peak for Scorpio Moon)
Jupiter transiting Aries (house of partnerships)

CONCERN: {concern}
QUESTION: {question}

Respond in 3-4 paragraphs. Lead with the dominant theme for this year based on
the Lal Kitab Varshphal placements. End with ONE specific action they can take
this week. No house numbers. No Sanskrit terms unless explained."""


# ── LLM callers ───────────────────────────────────────────────────────────────
def call_anthropic(prompt):
    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    t0 = time.time()
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=800,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    elapsed = time.time() - t0
    text = msg.content[0].text
    tokens = msg.usage.input_tokens + msg.usage.output_tokens
    return text, elapsed, tokens


def call_deepseek(prompt):
    from openai import OpenAI
    client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com/v1/")
    t0 = time.time()
    resp = client.chat.completions.create(
        model="deepseek-chat",
        max_tokens=800,
        temperature=0.5,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
    )
    elapsed = time.time() - t0
    text   = resp.choices[0].message.content.strip()
    tokens = (resp.usage.prompt_tokens or 0) + (resp.usage.completion_tokens or 0)
    return text, elapsed, tokens


# ── Scoring ────────────────────────────────────────────────────────────────────
SCORE_CRITERIA = [
    ("Astro accuracy",  ["house 2", "house 3", "house 10", "house 9",
                          "wealth", "career", "fortune", "annual", "year 56",
                          "rahu", "saturn", "sun", "moon", "mars"]),
    ("Energy language", ["release", "expansion", "clarity", "flow", "energy",
                          "pressure", "growth", "presence", "foundation"]),
    ("Actionability",   ["this week", "today", "start", "commit", "practice",
                          "do", "begin", "take", "choose", "write"]),
    ("Conciseness",     None),   # special: word count
    ("Personalisation", ["55", "career", "india", "libra", "transition",
                          "life stage", "mid-life", "consolidation"]),
]

def score_response(text, question_concern):
    text_lower = text.lower()
    scores = {}

    for name, keywords in SCORE_CRITERIA:
        if name == "Conciseness":
            words = len(text.split())
            scores[name] = 5 if words < 150 else 4 if words < 200 else 3 if words < 260 else 2 if words < 350 else 1
        elif keywords:
            hits = sum(1 for kw in keywords if kw.lower() in text_lower)
            scores[name] = min(5, 1 + hits)

    # No house numbers penalty
    import re
    house_nums = re.findall(r'\bhouse\s+\d+\b|\b\d+(?:st|nd|rd|th)\s+house\b', text_lower)
    if house_nums:
        scores["Energy language"] = max(1, scores.get("Energy language", 3) - len(house_nums))

    total = sum(scores.values())
    return scores, total


# ── Main comparison loop ──────────────────────────────────────────────────────
all_scores = {"anthropic": [], "deepseek": []}
DIVIDER = "═" * 70

for prompt_name, prompt_config in PROMPTS.items():
    question = prompt_config["question"]
    concern  = prompt_config["concern"]
    full_prompt = build_full_prompt(question, concern)

    print(f"\n{DIVIDER}")
    print(f"  PROMPT: {prompt_name.upper()} — {question[:60]}...")
    print(f"{DIVIDER}")

    # ── Anthropic ──────────────────────────────────────────────────────────────
    print(f"\n  ┌─ ANTHROPIC (Claude Sonnet 4.5)")
    try:
        ant_text, ant_time, ant_tokens = call_anthropic(full_prompt)
        ant_scores, ant_total = score_response(ant_text, concern)
        all_scores["anthropic"].append(ant_total)

        print(f"  │  Time: {ant_time:.1f}s  |  Tokens: {ant_tokens}")
        print(f"  │  Words: {len(ant_text.split())}")
        if not args.no_scores:
            for k, v in ant_scores.items():
                bar = "▓" * v + "░" * (5 - v)
                print(f"  │  {k:<20} {bar} {v}/5")
        print(f"  │")
        print(f"  │  RESPONSE:")
        for line in ant_text.split("\n"):
            print(f"  │  {line}")
    except Exception as e:
        print(f"  │  ERROR: {e}")
        all_scores["anthropic"].append(0)

    # ── DeepSeek ──────────────────────────────────────────────────────────────
    print(f"\n  ┌─ DEEPSEEK (deepseek-chat)")
    try:
        ds_text, ds_time, ds_tokens = call_deepseek(full_prompt)
        ds_scores, ds_total = score_response(ds_text, concern)
        all_scores["deepseek"].append(ds_total)

        print(f"  │  Time: {ds_time:.1f}s  |  Tokens: {ds_tokens}")
        print(f"  │  Words: {len(ds_text.split())}")
        if not args.no_scores:
            for k, v in ds_scores.items():
                bar = "▓" * v + "░" * (5 - v)
                print(f"  │  {k:<20} {bar} {v}/5")
        print(f"  │")
        print(f"  │  RESPONSE:")
        for line in ds_text.split("\n"):
            print(f"  │  {line}")
    except Exception as e:
        print(f"  │  ERROR: {e}")
        all_scores["deepseek"].append(0)

    # ── Head-to-head ──────────────────────────────────────────────────────────
    if not args.no_scores and all_scores["anthropic"] and all_scores["deepseek"]:
        a = all_scores["anthropic"][-1]
        d = all_scores["deepseek"][-1]
        winner = "ANTHROPIC" if a > d else "DEEPSEEK" if d > a else "TIE"
        print(f"\n  ▶  {prompt_name}: {winner}  (Anthropic {a}/25  vs  DeepSeek {d}/25)")

    time.sleep(1)  # rate limit courtesy


# ── Final scorecard ───────────────────────────────────────────────────────────
print(f"\n{DIVIDER}")
print(f"  FINAL SCORECARD")
print(f"{DIVIDER}")

ant_total = sum(all_scores["anthropic"])
ds_total  = sum(all_scores["deepseek"])
n         = max(len(all_scores["anthropic"]), 1)
max_score = n * 25

print(f"  Anthropic (Claude Sonnet 4.5):  {ant_total}/{max_score}  avg {ant_total/n:.1f}/25")
print(f"  DeepSeek  (deepseek-chat):       {ds_total}/{max_score}  avg {ds_total/n:.1f}/25")
print()

if ant_total > ds_total:
    diff = ant_total - ds_total
    print(f"  ▶  ANTHROPIC wins by {diff} points")
    print(f"     Consider: higher quality at ~$0.003/call vs DeepSeek ~$0.0003/call")
    print(f"     For Antar: if quality gap > 15%, switch to Anthropic for /predict")
elif ds_total > ant_total:
    diff = ds_total - ant_total
    print(f"  ▶  DEEPSEEK wins by {diff} points")
    print(f"     Cheaper AND better for this use case. Keep DeepSeek.")
else:
    print(f"  ▶  TIE — keep DeepSeek (10× cheaper at same quality)")

print()
print(f"  COST NOTE (per 1000 /predict calls, ~800 tokens each):")
print(f"    DeepSeek:  ~$0.24  (input $0.14/M + output $0.28/M)")
print(f"    Anthropic: ~$3.20  (Sonnet 4.5: $3/M input + $15/M output)")
print(f"    Ratio:     ~13× more expensive for Anthropic")
print(f"{DIVIDER}\n")
