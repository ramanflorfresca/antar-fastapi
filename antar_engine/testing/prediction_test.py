"""
prediction_test.py — production-identical prediction test for Sam K.
Run: PYTHONPATH=/Users/ramandeepsinghchadha/antarai python antar_engine/testing/prediction_test.py
"""
import os, sys, requests
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from supabase import create_client
from antar_engine import chart as chart_module, transits, karakas, patra, timing_engine
from antar_engine.predictions import build_layered_predictions, predictions_to_context_block, detect_concern
from antar_engine.prompt_builder import build_predict_prompt
from antar_engine.astrological_rules import run_all_rules, rules_to_context_block

SAM_K_BIRTH_DATE = "1970-11-02"
QUESTION = "What is happening in my life right now and what should I focus on in the coming months?"

sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_ROLE_KEY'])

# ── 1. Load chart ─────────────────────────────────────────
print("Loading Sam K chart from DB...")
row = sb.table("charts").select("*").eq("birth_date", SAM_K_BIRTH_DATE).order("created_at").limit(1).execute().data[0]
chart_id = row["id"]
print(f"  {chart_id[:8]}  lagna={row.get('lagna_sign')}")

stored = row["chart_data"]
lagna_si = stored["lagna"]["sign_index"]
for pd in stored["planets"].values():
    if "house" not in pd:
        pd["house"] = ((pd.get("sign_index", 0) - lagna_si) % 12) + 1
birth_time = (row.get("birth_time") or "06:02")[:5]
fresh = chart_module.calculate_chart(birth_date=row["birth_date"], birth_time=birth_time,
    lat=row["latitude"], lng=row["longitude"], tz_offset=row["timezone_offset"], ayanamsa="lahiri")
stored["birth_jd"] = fresh["birth_jd"]
chart_data = stored

# ── 2. Load dashas ────────────────────────────────────────
print("Loading dashas...")
raw = sb.table("dasha_periods").select("*").eq("chart_id", chart_id).order("sequence").execute()
dashas = {"vimsottari": [], "jaimini": [], "ashtottari": []}
for r in raw.data:
    s = r.get("system", "vimsottari")
    if s in dashas:
        dashas[s].append({"lord_or_sign": r["planet_or_sign"], "planet_or_sign": r["planet_or_sign"],
            "start": str(r["start_date"])[:10], "end": str(r["end_date"])[:10],
            "duration_years": r["duration_years"], "level": r["type"]})
print(f"  vim={len(dashas['vimsottari'])} jai={len(dashas['jaimini'])} ash={len(dashas['ashtottari'])}")

# ── 3. Transits ───────────────────────────────────────────
tr_list = transits.calculate_transits(chart_data)
tr_dict = {t["planet"]: t for t in tr_list}
transit_summary = "  |  ".join(f"{t['planet']} in {t.get('transit_sign','?')} H{t.get('transit_house','?')}" for t in tr_list)
print(f"Transits: {transit_summary[:120]}")

# ── 4. Concern + Patra ────────────────────────────────────
concern = detect_concern(QUESTION)
print(f"Concern: {concern}")
user_profile = {"marital_status": row.get("marital_status","unknown"),
    "children_status": row.get("children_status","unknown"),
    "career_stage": row.get("career_stage","mid_career"),
    "health_status": row.get("health_status","good"),
    "financial_status": row.get("financial_status","stable"),
    "birth_country": row.get("birth_country","India"),
    "current_country": row.get("country_code","IN"),
    "countries_lived": row.get("countries_lived",[])}
patra_obj = patra.build_patra_context(row["birth_date"], user_profile, concern)
patra_ctx = patra.patra_to_context_block(patra_obj)
print(f"  life_stage={patra_obj.life_stage_name}  age={patra_obj.age}")

# ── 5. Timing signals (predictions.py) ───────────────────
pred = build_layered_predictions(user_id=row.get("user_id"), chart_data=chart_data,
    dashas=dashas, current_transits=tr_list, life_events=[], supabase=None, concern=concern)
pred_ctx = predictions_to_context_block(pred, chart_data, concern)
print(f"  timing signals={pred['total_signals']}  confidence={pred.get('highest_confidence',0):.0%}")

# ── 6. Astrological rule signals (the real moat) ─────────
rules_result = run_all_rules(chart_data, dashas, tr_list, concern)
rules_ctx = rules_to_context_block(rules_result, concern)
print(f"  rules fired={rules_result['total_rules_fired']}  has_confluence={rules_result['has_confluence']}")
print(f"  karakas: AK={rules_result['karakas'].get('AK')}  AmK={rules_result['karakas'].get('AmK')}  DK={rules_result['karakas'].get('DK')}")
print(f"  dominant domain: {rules_result['dominant_domain']}")

# ── 7. Profile + timing text ──────────────────────────────
try: profile_text = karakas.psychological_profile(chart_data)
except: profile_text = "Libra rising. Moon in Scorpio. AK Venus — soul of relationship and creativity."

try: timing_text = timing_engine.timing_insights(chart_data, dashas)
except Exception as e: timing_text = ""; print(f"  timing error: {e}")

# ── 8. Build full prompt ──────────────────────────────────
print("\nBuilding prompt...")
prompt = build_predict_prompt(
    question=QUESTION, chart_data=chart_data, dashas=dashas, life_events=[],
    profile=profile_text, transit_summary=transit_summary,
    country_context="India — family-oriented, career-focused society.",
    timing_text=timing_text, nation_insight="", language="en",
    predictions_context=pred_ctx, concern=concern,
    country_code=row.get("country_code", "IN"),
    patra_context=patra_ctx, desh_context="", dkp_block="",
)
# Append rule signals — this is what makes responses specific
prompt += f"\n\n{rules_ctx}"

print(f"  Prompt: {len(prompt)} chars / ~{len(prompt)//4} tokens")

# ── 9. Call DeepSeek ──────────────────────────────────────
print("\n" + "="*60)
print("ANTAR'S RESPONSE (with astrological rules):")
print("="*60 + "\n")

key = os.environ.get("DEEPSEEK_API_KEY", "")
r = requests.post("https://api.deepseek.com/v1/chat/completions",
    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    json={"model": "deepseek-chat", "max_tokens": 1500,
          "messages": [{"role": "user", "content": prompt}]}, timeout=90)
resp = r.json()
if "error" in resp:
    print(f"DeepSeek error: {resp['error']}"); sys.exit(1)

print(resp["choices"][0]["message"]["content"])
print(f"\nTokens: {resp.get('usage',{})}")
