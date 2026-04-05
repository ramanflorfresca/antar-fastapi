#!/bin/bash
# ============================================================
# ANTAR API — Curl Test Script for Raman
# ============================================================
# Tests the /predict endpoint with the same question shown in
# the "Ask Yogi" screenshots: "funding for startup is not 
# getting any positive feedback"
#
# Base URL: https://antar-fastapi-production.up.railway.app
# Test Chart: Ramandeep (Capricorn lagna, Pisces Moon, Revati)
# ============================================================

BASE_URL="https://antar-fastapi-production.up.railway.app"
CHART_ID="de02bb52-d43a-4b09-be25-b45a07bfbf8a"

echo "============================================"
echo "  ANTAR API TEST — Ask Yogi / Ask Antar"
echo "  Date: $(date)"
echo "============================================"
echo ""

# ----------------------------------------------------------
# TEST 1: Health check — is the server up?
# ----------------------------------------------------------
echo "▸ TEST 1: Server health check"
echo "  GET ${BASE_URL}/api/v1/dashboard/${CHART_ID}"
echo ""

curl -s -o /dev/null -w "  Status: %{http_code} | Time: %{time_total}s\n" \
  "${BASE_URL}/api/v1/dashboard/${CHART_ID}"

echo ""

# ----------------------------------------------------------
# TEST 2: Exact question from screenshot
# "funding for startup is not getting any positive feedback"
# This goes to POST /api/v1/predict
# ----------------------------------------------------------
echo "▸ TEST 2: Predict — Startup Funding Question (from screenshot)"
echo "  POST ${BASE_URL}/api/v1/predict"
echo "  Question: \"funding for startup is not getting any positive feedback\""
echo ""

RESPONSE_2=$(curl -s -X POST "${BASE_URL}/api/v1/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "chart_id": "'"${CHART_ID}"'",
    "question": "funding for startup is not getting any positive feedback",
    "language": "en",
    "conversation_history": []
  }')

echo "  --- RESPONSE ---"
echo "${RESPONSE_2}" | python3 -m json.tool 2>/dev/null || echo "${RESPONSE_2}"
echo ""

# ----------------------------------------------------------
# TEST 3: Follow-up with conversation history
# Simulates the user saying "yes a timeframe" after the 
# initial response (as shown in the screenshot)
# ----------------------------------------------------------
echo "▸ TEST 3: Follow-up — \"yes a timeframe\" (with conversation history)"
echo "  POST ${BASE_URL}/api/v1/predict"
echo ""

# Extract the prediction text from TEST 2 for conversation history
PREV_PREDICTION=$(echo "${RESPONSE_2}" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    # Try plain_summary first, then prediction
    print(d.get('plain_summary', d.get('prediction', 'Previous response not captured')))
except:
    print('Previous response not captured')
" 2>/dev/null)

RESPONSE_3=$(curl -s -X POST "${BASE_URL}/api/v1/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "chart_id": "'"${CHART_ID}"'",
    "question": "yes a timeframe",
    "language": "en",
    "conversation_history": [
      {"role": "user", "content": "funding for startup is not getting any positive feedback"},
      {"role": "assistant", "content": "'"$(echo "${PREV_PREDICTION}" | sed 's/"/\\"/g' | tr '\n' ' ')"'"}
    ]
  }')

echo "  --- RESPONSE ---"
echo "${RESPONSE_3}" | python3 -m json.tool 2>/dev/null || echo "${RESPONSE_3}"
echo ""

# ----------------------------------------------------------
# TEST 4: Third message — "yes" (explore what to focus on)
# ----------------------------------------------------------
echo "▸ TEST 4: Follow-up — \"yes\" (explore what to focus on during waiting)"
echo "  POST ${BASE_URL}/api/v1/predict"
echo ""

PREV_PREDICTION_3=$(echo "${RESPONSE_3}" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('plain_summary', d.get('prediction', 'Previous response not captured')))
except:
    print('Previous response not captured')
" 2>/dev/null)

RESPONSE_4=$(curl -s -X POST "${BASE_URL}/api/v1/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "chart_id": "'"${CHART_ID}"'",
    "question": "yes",
    "language": "en",
    "conversation_history": [
      {"role": "user", "content": "funding for startup is not getting any positive feedback"},
      {"role": "assistant", "content": "'"$(echo "${PREV_PREDICTION}" | sed 's/"/\\"/g' | tr '\n' ' ')"'"},
      {"role": "user", "content": "yes a timeframe"},
      {"role": "assistant", "content": "'"$(echo "${PREV_PREDICTION_3}" | sed 's/"/\\"/g' | tr '\n' ' ')"'"},
      {"role": "user", "content": "yes"}
    ]
  }')

echo "  --- RESPONSE ---"
echo "${RESPONSE_4}" | python3 -m json.tool 2>/dev/null || echo "${RESPONSE_4}"
echo ""

# ----------------------------------------------------------
# SUMMARY: Key fields to compare with screenshot
# ----------------------------------------------------------
echo "============================================"
echo "  COMPARISON CHECKLIST vs SCREENSHOT"
echo "============================================"
echo ""
echo "Screenshot says:"
echo "  1. Emphasis on persistence and strategic patience"
echo "  2. Energy is about refining pitch, building credibility"
echo "  3. Shift coming in next few months"
echo "  4. Focus on tangible progress / proof of concept"
echo "  5. Funding momentum from late May 2026 onward"
echo "  6. Groundwork turns into tangible discussions"
echo ""
echo "Check: Does our API response cover similar themes?"
echo "  - Timing window returned?"
echo "  - Confidence level?"
echo "  - Domain detected (career/funding/business)?"
echo "  - Action item practical and specific?"
echo ""

# Extract key fields for quick comparison
echo "--- KEY FIELDS FROM TEST 2 (initial question) ---"
echo "${RESPONSE_2}" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(f\"  confidence:     {d.get('confidence', 'N/A')}\")
    print(f\"  timing_window:  {d.get('timing_window', 'N/A')}\")
    print(f\"  all_domains:    {d.get('all_domains', 'N/A')}\")
    print(f\"  signal_line:    {d.get('signal_line', 'N/A')}\")
    print(f\"  action_item:    {d.get('action_item', 'N/A')}\")
    plain = d.get('plain_summary', '')
    if plain:
        print(f\"  plain_summary:  {plain[:200]}...\")
except Exception as e:
    print(f'  Parse error: {e}')
" 2>/dev/null

echo ""
echo "--- KEY FIELDS FROM TEST 3 (timeframe follow-up) ---"
echo "${RESPONSE_3}" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(f\"  confidence:     {d.get('confidence', 'N/A')}\")
    print(f\"  timing_window:  {d.get('timing_window', 'N/A')}\")
    print(f\"  all_domains:    {d.get('all_domains', 'N/A')}\")
    print(f\"  signal_line:    {d.get('signal_line', 'N/A')}\")
    plain = d.get('plain_summary', '')
    if plain:
        print(f\"  plain_summary:  {plain[:200]}...\")
except Exception as e:
    print(f'  Parse error: {e}')
" 2>/dev/null

echo ""
echo "============================================"
echo "  DONE"
echo "============================================"
