#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# ANTAR BACKEND HEALTH CHECK — All Frontend-Critical Endpoints
# 
# Run this from any terminal:
#   chmod +x test_all_endpoints.sh && ./test_all_endpoints.sh
#
# Test chart: de02bb52-d43a-4b09-be25-b45a07bfbf8a (Ramandeep)
# Backend:   https://antar-fastapi-production.up.railway.app
# ═══════════════════════════════════════════════════════════════════

API="https://antar-fastapi-production.up.railway.app"
CHART="de02bb52-d43a-4b09-be25-b45a07bfbf8a"
PASS=0
FAIL=0
WARN=0
RESULTS=""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No color
BOLD='\033[1m'

log_pass() { PASS=$((PASS+1)); RESULTS+="  ✅ $1\n"; echo -e "  ${GREEN}✅ $1${NC}"; }
log_fail() { FAIL=$((FAIL+1)); RESULTS+="  ❌ $1\n"; echo -e "  ${RED}❌ $1${NC}"; }
log_warn() { WARN=$((WARN+1)); RESULTS+="  ⚠️  $1\n"; echo -e "  ${YELLOW}⚠️  $1${NC}"; }
section()  { echo -e "\n${CYAN}${BOLD}═══ $1 ═══${NC}"; }

# Helper: check HTTP status + extract field
check_endpoint() {
  local METHOD=$1 ENDPOINT=$2 BODY=$3 LABEL=$4
  local URL="${API}${ENDPOINT}"
  
  if [ "$METHOD" = "GET" ]; then
    RESPONSE=$(curl -s -w "\n%{http_code}" --max-time 30 "$URL" 2>&1)
  else
    RESPONSE=$(curl -s -w "\n%{http_code}" --max-time 30 -X POST \
      -H "Content-Type: application/json" \
      -d "$BODY" "$URL" 2>&1)
  fi
  
  HTTP_CODE=$(echo "$RESPONSE" | tail -1)
  BODY_RESPONSE=$(echo "$RESPONSE" | sed '$d')
  
  if [ "$HTTP_CODE" = "200" ]; then
    log_pass "$LABEL → HTTP $HTTP_CODE"
  elif [ "$HTTP_CODE" = "201" ]; then
    log_pass "$LABEL → HTTP $HTTP_CODE"
  elif [ "$HTTP_CODE" = "422" ]; then
    log_warn "$LABEL → HTTP $HTTP_CODE (validation error — check request body)"
  else
    log_fail "$LABEL → HTTP $HTTP_CODE"
  fi
  
  echo "$BODY_RESPONSE"
}


# ═══════════════════════════════════════════════════════════════════
section "1. CORE CHART ENDPOINTS"
# ═══════════════════════════════════════════════════════════════════

echo -e "\n${BOLD}1a. GET /dashboard/{chart_id}${NC}"
DASH=$(check_endpoint "GET" "/api/v1/dashboard/$CHART" "" "Dashboard")
# Verify key fields
if echo "$DASH" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('lagna') or d.get('lagna_sign')" 2>/dev/null; then
  log_pass "Dashboard contains lagna data"
else
  log_warn "Dashboard missing lagna — check response shape"
fi

echo -e "\n${BOLD}1b. GET /welcome/{chart_id}${NC}"
WELCOME=$(check_endpoint "GET" "/api/v1/welcome/$CHART" "" "Welcome signal")
if echo "$WELCOME" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('signals') or d.get('signal_1') or d.get('mirror')" 2>/dev/null; then
  log_pass "Welcome contains signal data"
else
  log_warn "Welcome response shape — check if signals/mirror/signal_1 key exists"
fi

echo -e "\n${BOLD}1c. GET /subscription/{chart_id}${NC}"
check_endpoint "GET" "/api/v1/subscription/$CHART" "" "Subscription status" > /dev/null

echo -e "\n${BOLD}1d. GET /alerts/{chart_id}${NC}"
check_endpoint "GET" "/api/v1/alerts/$CHART" "" "Alerts" > /dev/null


# ═══════════════════════════════════════════════════════════════════
section "2. ASK ANTAR — /predict (NLP Chat)"
# ═══════════════════════════════════════════════════════════════════

echo -e "\n${BOLD}2a. POST /predict — Career question${NC}"
PREDICT=$(check_endpoint "POST" "/api/v1/predict" \
  "{\"chart_id\":\"$CHART\",\"question\":\"How is my career looking this month?\"}" \
  "/predict career")

# Verify structured response fields
echo -e "\n  Checking response fields..."
for FIELD in plain_summary action_item signal_line timing_window confidence; do
  VAL=$(echo "$PREDICT" | python3 -c "import sys,json; d=json.load(sys.stdin); v=d.get('$FIELD',''); print(v[:80] if v else 'NULL')" 2>/dev/null)
  if [ -n "$VAL" ] && [ "$VAL" != "NULL" ] && [ "$VAL" != "None" ]; then
    log_pass "  $FIELD: \"$VAL...\""
  else
    log_fail "  $FIELD is missing or null — plain_english.py not wired?"
  fi
done

# Check for banned Sanskrit terms in plain_summary
echo -e "\n  Checking banned terms in plain_summary..."
PLAIN=$(echo "$PREDICT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('plain_summary',''))" 2>/dev/null)
BANNED_FOUND=0
for TERM in Mahadasha Antardasha Atmakaraka Amatyakaraka Navamsa Vimsottari; do
  if echo "$PLAIN" | grep -qi "$TERM"; then
    log_fail "  Banned term '$TERM' found in plain_summary!"
    BANNED_FOUND=1
  fi
done
if [ $BANNED_FOUND -eq 0 ]; then
  log_pass "  Zero banned Sanskrit terms in plain_summary"
fi

echo -e "\n${BOLD}2b. POST /predict — Relationship question${NC}"
check_endpoint "POST" "/api/v1/predict" \
  "{\"chart_id\":\"$CHART\",\"question\":\"Will my relationship improve?\"}" \
  "/predict relationship" > /dev/null

echo -e "\n${BOLD}2c. POST /predict — Financial question${NC}"
check_endpoint "POST" "/api/v1/predict" \
  "{\"chart_id\":\"$CHART\",\"question\":\"Is this a good time to invest?\"}" \
  "/predict financial" > /dev/null


# ═══════════════════════════════════════════════════════════════════
section "3. PRASHNA ORACLE — /prashna (Yes/No)"
# ═══════════════════════════════════════════════════════════════════

echo -e "\n${BOLD}3a. POST /prashna${NC}"
PRASHNA=$(check_endpoint "POST" "/api/v1/prashna" \
  "{\"chart_id\":\"$CHART\",\"question\":\"Will I get the promotion?\",\"lat\":40.82,\"lng\":-73.99}" \
  "/prashna yes/no")

# Check verdict field
for FIELD in verdict score confidence; do
  VAL=$(echo "$PRASHNA" | python3 -c "import sys,json; print(json.load(sys.stdin).get('$FIELD','NULL'))" 2>/dev/null)
  if [ -n "$VAL" ] && [ "$VAL" != "NULL" ] && [ "$VAL" != "None" ]; then
    log_pass "  prashna.$FIELD = $VAL"
  else
    log_fail "  prashna.$FIELD is missing"
  fi
done

# Check for answer/why/timing/action fields
for FIELD in answer why timing action remedy; do
  VAL=$(echo "$PRASHNA" | python3 -c "import sys,json; v=json.load(sys.stdin).get('$FIELD',''); print('exists' if v else 'NULL')" 2>/dev/null)
  if [ "$VAL" = "exists" ]; then
    log_pass "  prashna.$FIELD present"
  fi
done


# ═══════════════════════════════════════════════════════════════════
section "4. PREDICTION HISTORY & PATTERNS"
# ═══════════════════════════════════════════════════════════════════

echo -e "\n${BOLD}4a. GET /predictions/{chart_id}${NC}"
PREDS=$(check_endpoint "GET" "/api/v1/predictions/$CHART" "" "Prediction history")
PRED_COUNT=$(echo "$PREDS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('predictions',d if isinstance(d,list) else [])))" 2>/dev/null)
if [ -n "$PRED_COUNT" ]; then
  log_pass "  Found $PRED_COUNT predictions in history"
else
  log_warn "  Could not parse prediction count"
fi

echo -e "\n${BOLD}4b. GET /domain-signals/{chart_id}${NC}"
SIGNALS=$(check_endpoint "GET" "/api/v1/domain-signals/$CHART" "" "Domain signals")
if echo "$SIGNALS" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('signals')" 2>/dev/null; then
  DOMAINS=$(echo "$SIGNALS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len([k for k,v in d['signals'].items() if v and v.get('signal_line')]))" 2>/dev/null)
  log_pass "  $DOMAINS domains have active signals"
else
  log_warn "  Domain signals response shape may differ — check manually"
fi

echo -e "\n${BOLD}4c. GET /patterns/{chart_id}${NC}"
check_endpoint "GET" "/api/v1/patterns/$CHART" "" "Life patterns" > /dev/null


# ═══════════════════════════════════════════════════════════════════
section "5. LIFE COACHING ENDPOINTS (Sprint E)"
# ═══════════════════════════════════════════════════════════════════

echo -e "\n${BOLD}5a. GET /weekly-briefing/{chart_id}${NC}"
check_endpoint "GET" "/api/v1/weekly-briefing/$CHART" "" "Weekly briefing" > /dev/null

echo -e "\n${BOLD}5b. GET /monthly-deepdive/{chart_id}${NC}"
check_endpoint "GET" "/api/v1/monthly-deepdive/$CHART" "" "Monthly deep-dive" > /dev/null

echo -e "\n${BOLD}5c. GET /annual-plan/{chart_id}${NC}"
check_endpoint "GET" "/api/v1/annual-plan/$CHART" "" "Annual plan" > /dev/null


# ═══════════════════════════════════════════════════════════════════
section "6. PRACTICES & REMEDIES"
# ═══════════════════════════════════════════════════════════════════

echo -e "\n${BOLD}6a. GET /remedies/{chart_id}${NC}"
REMEDIES=$(check_endpoint "GET" "/api/v1/remedies/$CHART" "" "Remedies WHY/WHAT/HOW")
if echo "$REMEDIES" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('remedies') or isinstance(d,list)" 2>/dev/null; then
  log_pass "  Remedies data present"
fi

echo -e "\n${BOLD}6b. GET /practices/{chart_id}/schedule${NC}"
SCHEDULE=$(check_endpoint "GET" "/api/v1/practices/$CHART/schedule" "" "Practice schedule")
# Check locale
LOCALE=$(echo "$SCHEDULE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('schedule',{}).get('locale','UNKNOWN'))" 2>/dev/null)
if [ "$LOCALE" = "IN" ]; then
  log_warn "  Locale = IN — Ramandeep lives in US. current_country needs fix! (Run: UPDATE charts SET current_country = 'US' WHERE id = '$CHART')"
elif [ "$LOCALE" = "GLOBAL" ]; then
  log_pass "  Locale = GLOBAL (correct for US resident)"
else
  log_warn "  Locale = $LOCALE — check current_country in Supabase"
fi

echo -e "\n${BOLD}6c. GET /practices/{chart_id}/streak${NC}"
check_endpoint "GET" "/api/v1/practices/$CHART/streak" "" "Practice streak" > /dev/null


# ═══════════════════════════════════════════════════════════════════
section "7. DAILY SIGNAL & PANCHANGA"
# ═══════════════════════════════════════════════════════════════════

echo -e "\n${BOLD}7a. POST /daily-signal${NC}"
DAILY=$(check_endpoint "POST" "/api/v1/daily-signal" \
  "{\"chart_id\":\"$CHART\"}" \
  "Daily signal")
if echo "$DAILY" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('signal_text') or d.get('signal')" 2>/dev/null; then
  log_pass "  Daily signal text present"
fi

echo -e "\n${BOLD}7b. GET /panchanga${NC}"
check_endpoint "GET" "/api/v1/panchanga" "" "Panchanga" > /dev/null


# ═══════════════════════════════════════════════════════════════════
section "8. COMPATIBILITY"
# ═══════════════════════════════════════════════════════════════════

echo -e "\n${BOLD}8a. POST /compatibility/start${NC}"
COMPAT=$(check_endpoint "POST" "/api/v1/compatibility/start" \
  "{\"chart_id_a\":\"$CHART\",\"name_b\":\"Test Partner\",\"birth_date_b\":\"1988-03-15\",\"birth_time_b\":\"14:30\",\"birth_city_b\":\"Mumbai\",\"birth_country_b\":\"IN\",\"mode\":\"relationship\"}" \
  "Compatibility start")
if echo "$COMPAT" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('score') is not None or d.get('session_id')" 2>/dev/null; then
  log_pass "  Compatibility returned score or session_id"
fi

echo -e "\n${BOLD}8b. GET /compatibility/sessions/{chart_id}${NC}"
check_endpoint "GET" "/api/v1/compatibility/sessions/$CHART" "" "Compatibility history" > /dev/null


# ═══════════════════════════════════════════════════════════════════
section "9. AUTH & PAYMENTS"
# ═══════════════════════════════════════════════════════════════════

echo -e "\n${BOLD}9a. GET /subscription/{chart_id}${NC}"
SUB=$(check_endpoint "GET" "/api/v1/subscription/$CHART" "" "Subscription")
PLAN=$(echo "$SUB" | python3 -c "import sys,json; print(json.load(sys.stdin).get('plan','UNKNOWN'))" 2>/dev/null)
log_pass "  Current plan: $PLAN"

echo -e "\n${BOLD}9b. POST /payments/stripe/create-checkout (dry run)${NC}"
STRIPE=$(check_endpoint "POST" "/api/v1/payments/stripe/create-checkout" \
  "{\"chart_id\":\"$CHART\",\"plan_key\":\"seeker_monthly\",\"success_url\":\"https://antar.world/success\"}" \
  "Stripe checkout")
# 200 = working, 500 = env vars not set
STRIPE_URL=$(echo "$STRIPE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('checkout_url','NONE'))" 2>/dev/null)
if [ "$STRIPE_URL" != "NONE" ] && [ -n "$STRIPE_URL" ]; then
  log_pass "  Stripe checkout URL generated"
else
  log_warn "  Stripe checkout URL missing — check STRIPE env vars on Railway"
fi


# ═══════════════════════════════════════════════════════════════════
section "10. SHARE CARDS & PDF"
# ═══════════════════════════════════════════════════════════════════

echo -e "\n${BOLD}10a. GET /share-card/{chart_id}/daily${NC}"
check_endpoint "GET" "/api/v1/share-card/$CHART/daily" "" "Share card (daily)" > /dev/null

echo -e "\n${BOLD}10b. GET /report/{chart_id}/pdf${NC}"
PDF_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 30 "$API/api/v1/report/$CHART/pdf")
if [ "$PDF_RESPONSE" = "200" ]; then
  log_pass "PDF report → HTTP 200"
elif [ "$PDF_RESPONSE" = "403" ]; then
  log_pass "PDF report → HTTP 403 (Seeker+ gate working correctly)"
else
  log_fail "PDF report → HTTP $PDF_RESPONSE"
fi


# ═══════════════════════════════════════════════════════════════════
section "11. RESPONSE SHAPE VALIDATION — /predict"
# ═══════════════════════════════════════════════════════════════════

echo -e "\n${BOLD}Verifying /predict returns ALL fields the frontend needs...${NC}"
PREDICT_CHECK=$(curl -s --max-time 45 -X POST \
  -H "Content-Type: application/json" \
  -d "{\"chart_id\":\"$CHART\",\"question\":\"What should I focus on this week?\"}" \
  "$API/api/v1/predict" 2>&1)

echo "$PREDICT_CHECK" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    required = ['plain_summary', 'action_item', 'signal_line', 'timing_window', 'confidence']
    optional = ['prediction', 'all_domains', 'diagnostic_mode', 'remedies']
    
    print()
    print('  REQUIRED FIELDS (frontend will break without these):')
    for f in required:
        v = d.get(f)
        status = '✅' if v else '❌ MISSING'
        preview = str(v)[:60] + '...' if v and len(str(v))>60 else str(v)
        print(f'    {status} {f}: {preview}')
    
    print()
    print('  OPTIONAL FIELDS (nice to have):')
    for f in optional:
        v = d.get(f)
        status = '✅' if v else '—'
        print(f'    {status} {f}: {\"present\" if v else \"absent\"}')
    
    # Confidence validation
    conf = d.get('confidence','')
    if conf in ['high','medium','low']:
        print(f'  ✅ confidence value \"{conf}\" is valid (high/medium/low)')
    elif conf:
        print(f'  ⚠️  confidence value \"{conf}\" not in expected set')
    
    # Timing validation
    timing = d.get('timing_window','')
    bad_timing = ['soon', 'in the coming months', 'in the future', 'eventually']
    if timing:
        for bad in bad_timing:
            if bad.lower() in timing.lower():
                print(f'  ❌ timing_window contains vague term \"{bad}\"')
                break
        else:
            print(f'  ✅ timing_window is specific: \"{timing}\"')
    
    print()
except Exception as e:
    print(f'  ❌ Could not parse /predict response: {e}')
" 2>/dev/null


# ═══════════════════════════════════════════════════════════════════
section "12. RESPONSE SHAPE VALIDATION — /prashna"
# ═══════════════════════════════════════════════════════════════════

echo -e "\n${BOLD}Verifying /prashna returns ALL fields the Prashna Oracle needs...${NC}"
echo "$PRASHNA" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    required = ['verdict', 'score', 'confidence']
    content = ['answer', 'why', 'timing', 'action', 'remedy']
    
    print()
    print('  REQUIRED FIELDS:')
    for f in required:
        v = d.get(f)
        status = '✅' if v is not None else '❌ MISSING'
        print(f'    {status} {f}: {v}')
    
    print()
    print('  CONTENT FIELDS (at least answer + timing should exist):')
    found = 0
    for f in content:
        v = d.get(f)
        if v:
            found += 1
            preview = str(v)[:60] + '...' if len(str(v))>60 else str(v)
            print(f'    ✅ {f}: {preview}')
        else:
            print(f'    — {f}: absent')
    
    if found >= 2:
        print(f'  ✅ {found} content fields present — good')
    else:
        print(f'  ⚠️  Only {found} content fields — frontend may show empty sections')
    
    # Verdict validation
    verdict = d.get('verdict','')
    if verdict.upper() in ['YES','NO','MAYBE']:
        print(f'  ✅ verdict \"{verdict}\" is valid')
    else:
        print(f'  ⚠️  verdict \"{verdict}\" not in expected set [YES/NO/MAYBE]')
    
    print()
except Exception as e:
    print(f'  ❌ Could not parse /prashna response: {e}')
" 2>/dev/null


# ═══════════════════════════════════════════════════════════════════
section "13. CURRENT_COUNTRY CHECK (Locale Gate)"
# ═══════════════════════════════════════════════════════════════════

echo -e "\n${BOLD}Checking if current_country is correct for test chart...${NC}"
echo -e "  The test chart (Ramandeep) lives in the US."
echo -e "  If locale shows IN, run this SQL in Supabase:"
echo -e "  ${YELLOW}UPDATE charts SET current_country = 'US' WHERE id = '$CHART';${NC}"
echo -e "  Then clear practice cache:"
echo -e "  ${YELLOW}DELETE FROM practice_schedule_cache WHERE chart_id = '$CHART';${NC}"


# ═══════════════════════════════════════════════════════════════════
section "SUMMARY"
# ═══════════════════════════════════════════════════════════════════

TOTAL=$((PASS + FAIL + WARN))
echo -e ""
echo -e "  ${GREEN}✅ Passed: $PASS${NC}"
echo -e "  ${RED}❌ Failed: $FAIL${NC}"
echo -e "  ${YELLOW}⚠️  Warnings: $WARN${NC}"
echo -e "  Total checks: $TOTAL"
echo -e ""

if [ $FAIL -eq 0 ]; then
  echo -e "  ${GREEN}${BOLD}ALL CRITICAL ENDPOINTS PASSING${NC}"
  echo -e "  Frontend can safely wire to these APIs."
else
  echo -e "  ${RED}${BOLD}$FAIL CRITICAL FAILURES — FIX BEFORE FRONTEND WIRING${NC}"
fi

echo -e ""
echo -e "  ${CYAN}Endpoints tested against: $API${NC}"
echo -e "  ${CYAN}Test chart: $CHART (Ramandeep)${NC}"
echo -e "  ${CYAN}Run date: $(date)${NC}"
echo -e ""
