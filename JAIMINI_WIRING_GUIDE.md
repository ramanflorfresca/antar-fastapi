# Jaimini Engine v2.0 — Manual Wiring Guide

Imports are auto-patched. Wire these 5 points manually in main.py.

## Find your insertion points:
```bash
grep -n "chart/create\|def create_chart" main.py
grep -n "def predict\|build_complete_context\|/api/v1/predict" main.py
grep -n "welcome\|def get_welcome" main.py
grep -n "prashna\|def prashna" main.py
grep -n "dashboard\|def get_dashboard" main.py
```

## 1. CHART CREATION — after chart insert to Supabase:
```python
try:
    build_and_store_jaimini(
        chart_id=chart_id,
        lagna_sign=lagna_sign_index,
        planets_dict=planets_for_db,
        d9_planets_dict=d9_planets_for_db,
        birth_date_str=birth_date,
        supabase_client=supabase,
    )
except Exception as e:
    logger.error(f"Jaimini v2 failed: {e}")
```

## 2. PREDICT — after Layer 2 (Dasha) in context builder:
```python
jaimini_block = format_jaimini_context_from_stored(chart_data)
context += jaimini_block
context += "\n" + score_jaimini_convergence(chart_data, concern_domain) + "\n"
```

## 3. WELCOME — replace old generate_welcome_signal() call:
```python
result = await generate_welcome_signal_v2(
    chart_data=chart.data,
    birth_date=chart.data.get("birth_date"),
    anthropic_client=anthropic,
)
```

## 4. PRASHNA — after main verdict, add triple-lock:
```python
try:
    q_map = {"marriage":"marriage","love":"marriage","investment":"investment",
             "wealth":"investment","lawsuit":"lawsuit","legal":"lawsuit",
             "abroad":"foreign","travel":"foreign","visa":"foreign"}
    q_type = next((v for k,v in q_map.items() if k in question.lower()), None)
    if q_type:
        jc = jaimini_prashna_check(chart_data, q_type, lagna_sign_index)
        if jc.get("jaimini_verdict"):
            confidence_score += 20
            verdict_reasons.extend(jc.get("reasons", []))
except Exception as e:
    logger.error(f"Jaimini prashna failed: {e}")
```

## 5. DASHBOARD — add to response dict:
```python
jd = chart_data.get("jaimini_data", {})
if isinstance(jd, str):
    jd = json.loads(jd) if jd else {}
response["jaimini"] = {
    "karakas": jd.get("karakas", []),
    "arudha_lagna": jd.get("arudha_lagna", {}),
    "upapada_lagna": jd.get("upapada_lagna", {}),
    "karakamsa": jd.get("karakamsa", {}),
    "current_md": jd.get("current_md"),
    "current_ad": jd.get("current_ad"),
    "predictions": jd.get("predictions", []),
}
```
