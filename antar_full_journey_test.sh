#!/bin/bash
# ============================================================
# ANTAR — Full User Journey Test
# ============================================================
# Test subject: Feb 14, 1969, 11:50 AM, New Delhi, India
# Living in: India (IN)
#
# This script simulates a COMPLETE new user journey:
#   1. Create chart (onboarding)
#   2. Fetch dashboard (verify chart computed)
#   3. Fetch welcome signal (first impression)
#   4. Fetch daily signal
#   5. Ask: "what is happening with my business"
#   6. Follow-up: "when will things improve"
#   7. Follow-up: "what should I focus on right now"
#   8. Show what the user sees (plain_summary fields only)
#
# Run AFTER deploying patch_plain_english_v2.py
#
# Usage:
#   bash antar_full_journey_test.sh
# ============================================================

BASE_URL="https://antar-fastapi-production.up.railway.app"

echo "╔══════════════════════════════════════════════════════╗"
echo "║  ANTAR — Full User Journey Test                     ║"
echo "║  Subject: Feb 14, 1969 · 11:50 AM · New Delhi      ║"
echo "║  Date: $(date)                      ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ----------------------------------------------------------
# STEP 1: CREATE CHART (Onboarding)
# ----------------------------------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "▸ STEP 1: Create Chart — POST /api/v1/chart/create"
echo "  Name: Arjun"
echo "  DOB: 1969-02-14"
echo "  Time: 11:50 (24hr)"
echo "  City: New Delhi"
echo "  Country: IN"
echo "  Lives in: IN"
echo "  Gender: male"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

CREATE_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/chart/create" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Arjun",
    "name": "Arjun Test",
    "birth_date": "1969-02-14",
    "birth_time": "11:50",
    "birth_city": "New Delhi",
    "birth_country": "IN",
    "current_country": "IN",
    "gender": "male"
  }')

echo "  Response:"
echo "${CREATE_RESPONSE}" | python3 -m json.tool 2>/dev/null || echo "${CREATE_RESPONSE}"
echo ""

# Extract chart_id
CHART_ID=$(echo "${CREATE_RESPONSE}" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('chart_id', d.get('id', '')))
except:
    print('')
" 2>/dev/null)

if [ -z "$CHART_ID" ]; then
    echo "ERROR: Could not extract chart_id from response."
    echo "  Full response: ${CREATE_RESPONSE}"
    echo "  Aborting."
    exit 1
fi

echo "  ✅ Chart created: ${CHART_ID}"
echo ""

# Extract key chart details
echo "  Chart Summary:"
echo "${CREATE_RESPONSE}" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(f\"    Lagna:      {d.get('lagna', 'N/A')}\")
    print(f\"    Moon Sign:  {d.get('moon_sign', 'N/A')}\")
    print(f\"    Nakshatra:  {d.get('moon_nakshatra', 'N/A')}\")
    print(f\"    Sun Sign:   {d.get('sun_sign', 'N/A')}\")
    print(f\"    Dasha:      {d.get('current_dasha', 'N/A')}\")
except:
    print('    (could not parse)')
" 2>/dev/null
echo ""

# ----------------------------------------------------------
# STEP 2: DASHBOARD (Verify chart computed)
# ----------------------------------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "▸ STEP 2: Dashboard — GET /api/v1/dashboard/${CHART_ID}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

DASH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/api/v1/dashboard/${CHART_ID}")
echo "  Status: ${DASH_STATUS}"

if [ "$DASH_STATUS" = "200" ]; then
    echo "  ✅ Dashboard loaded — chart data, jaimini, lal kitab all computed"
else
    echo "  ⚠️  Dashboard returned ${DASH_STATUS}"
fi
echo ""

# ----------------------------------------------------------
# STEP 3: WELCOME SIGNAL (First impression)
# ----------------------------------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "▸ STEP 3: Welcome Signal — GET /api/v1/welcome/${CHART_ID}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

WELCOME_RESPONSE=$(curl -s "${BASE_URL}/api/v1/welcome/${CHART_ID}?language=en")
WELCOME_STATUS=$(echo "${WELCOME_RESPONSE}" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    if 'signal_1' in d:
        print('3-signal format')
        s1 = d.get('signal_1', {})
        s2 = d.get('signal_2', {})
        s3 = d.get('signal_3', {})
        print(f\"  Mirror:  {s1.get('body', s1.get('headline', 'N/A'))[:120]}...\")
        print(f\"  Chapter: {s2.get('body', s2.get('headline', 'N/A'))[:120]}...\")
        print(f\"  Signal:  {s3.get('body', s3.get('headline', 'N/A'))[:120]}...\")
    elif 'headline' in d:
        print('old format')
        print(f\"  Headline: {d.get('headline', 'N/A')}\")
        print(f\"  Summary:  {d.get('summary', 'N/A')[:120]}...\")
    elif 'status' in d:
        print(f\"  Status: {d.get('status')} — signal may still be generating\")
    else:
        print(json.dumps(d, indent=2)[:300])
except Exception as e:
    print(f'  Parse error: {e}')
" 2>/dev/null)
echo "  ${WELCOME_STATUS}"
echo ""

# ----------------------------------------------------------
# STEP 4: DAILY SIGNAL
# ----------------------------------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "▸ STEP 4: Daily Signal — POST /api/v1/daily-signal"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

DAILY_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/daily-signal" \
  -H "Content-Type: application/json" \
  -d "{\"chart_id\": \"${CHART_ID}\", \"language\": \"en\"}")

echo "${DAILY_RESPONSE}" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(f\"  Signal: {d.get('signal_text', 'N/A')[:200]}\")
    print(f\"  Moon:   {d.get('moon_nakshatra', 'N/A')}\")
    p = d.get('panchanga', {})
    print(f\"  Tithi:  {p.get('tithi', 'N/A')}\")
    print(f\"  Yoga:   {p.get('yoga', 'N/A')}\")
except Exception as e:
    print(f'  Error: {e}')
" 2>/dev/null
echo ""

# ----------------------------------------------------------
# STEP 5: ASK ANTAR — "what is happening with my business"
# ----------------------------------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "▸ STEP 5: Ask Antar — \"what is happening with my business\""
echo "  POST /api/v1/predict"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

Q1="what is happening with my business"

R1=$(curl -s -X POST "${BASE_URL}/api/v1/predict" \
  -H "Content-Type: application/json" \
  -d "{
    \"chart_id\": \"${CHART_ID}\",
    \"question\": \"${Q1}\",
    \"language\": \"en\",
    \"conversation_history\": []
  }")

echo "  ┌─────────────────────────────────────────────┐"
echo "  │  WHAT THE USER SEES IN CHAT                 │"
echo "  └─────────────────────────────────────────────┘"
echo ""
echo "${R1}" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    sig = d.get('signal_line', '')
    ps = d.get('plain_summary', '')
    ai = d.get('action_item', '')
    tw = d.get('timing_window', '')
    cf = d.get('signal_confidence', d.get('confidence', ''))
    dom = d.get('all_domains', [])
    
    if sig:
        print(f'  ✦ {sig}')
        print()
    print(f'  {ps}')
    print()
    if cf or dom:
        badges = []
        if cf: badges.append(f'{str(cf).upper()} CONFIDENCE')
        for dd in dom: badges.append(dd.upper())
        print(f'  [{\"  ·  \".join(badges)}]')
    if tw:
        print(f'  ◎ {tw}')
    if ai:
        print()
        print(f'  YOUR MOVE: {ai}')
except Exception as e:
    print(f'  Error parsing: {e}')
    print(sys.stdin.read()[:500] if hasattr(sys.stdin, 'read') else '')
" 2>/dev/null

echo ""
echo ""

# Extract plain_summary for conversation history
PS1=$(echo "${R1}" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('plain_summary', d.get('prediction', ''))[:500])
except:
    print('')
" 2>/dev/null)

# ----------------------------------------------------------
# STEP 6: FOLLOW-UP — "when will things improve"
# ----------------------------------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "▸ STEP 6: Follow-up — \"when will things improve\""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

Q2="when will things improve"

# Escape the previous response for JSON
PS1_ESC=$(echo "${PS1}" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read().strip()))" 2>/dev/null)

R2=$(curl -s -X POST "${BASE_URL}/api/v1/predict" \
  -H "Content-Type: application/json" \
  -d "{
    \"chart_id\": \"${CHART_ID}\",
    \"question\": \"${Q2}\",
    \"language\": \"en\",
    \"conversation_history\": [
      {\"role\": \"user\", \"content\": \"${Q1}\"},
      {\"role\": \"assistant\", \"content\": ${PS1_ESC}}
    ]
  }")

echo "  ┌─────────────────────────────────────────────┐"
echo "  │  WHAT THE USER SEES IN CHAT                 │"
echo "  └─────────────────────────────────────────────┘"
echo ""
echo "${R2}" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    sig = d.get('signal_line', '')
    ps = d.get('plain_summary', '')
    ai = d.get('action_item', '')
    tw = d.get('timing_window', '')
    cf = d.get('signal_confidence', d.get('confidence', ''))
    dom = d.get('all_domains', [])
    
    if sig:
        print(f'  ✦ {sig}')
        print()
    print(f'  {ps}')
    print()
    if cf or dom:
        badges = []
        if cf: badges.append(f'{str(cf).upper()} CONFIDENCE')
        for dd in dom: badges.append(dd.upper())
        print(f'  [{\"  ·  \".join(badges)}]')
    if tw:
        print(f'  ◎ {tw}')
    if ai:
        print()
        print(f'  YOUR MOVE: {ai}')
except Exception as e:
    print(f'  Error parsing: {e}')
" 2>/dev/null

echo ""
echo ""

# Extract for next conversation turn
PS2=$(echo "${R2}" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('plain_summary', d.get('prediction', ''))[:500])
except:
    print('')
" 2>/dev/null)
PS2_ESC=$(echo "${PS2}" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read().strip()))" 2>/dev/null)

# ----------------------------------------------------------
# STEP 7: FOLLOW-UP — "what should I focus on right now"
# ----------------------------------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "▸ STEP 7: Follow-up — \"what should I focus on right now\""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

Q3="what should I focus on right now"

R3=$(curl -s -X POST "${BASE_URL}/api/v1/predict" \
  -H "Content-Type: application/json" \
  -d "{
    \"chart_id\": \"${CHART_ID}\",
    \"question\": \"${Q3}\",
    \"language\": \"en\",
    \"conversation_history\": [
      {\"role\": \"user\", \"content\": \"${Q1}\"},
      {\"role\": \"assistant\", \"content\": ${PS1_ESC}},
      {\"role\": \"user\", \"content\": \"${Q2}\"},
      {\"role\": \"assistant\", \"content\": ${PS2_ESC}}
    ]
  }")

echo "  ┌─────────────────────────────────────────────┐"
echo "  │  WHAT THE USER SEES IN CHAT                 │"
echo "  └─────────────────────────────────────────────┘"
echo ""
echo "${R3}" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    sig = d.get('signal_line', '')
    ps = d.get('plain_summary', '')
    ai = d.get('action_item', '')
    tw = d.get('timing_window', '')
    cf = d.get('signal_confidence', d.get('confidence', ''))
    dom = d.get('all_domains', [])
    
    if sig:
        print(f'  ✦ {sig}')
        print()
    print(f'  {ps}')
    print()
    if cf or dom:
        badges = []
        if cf: badges.append(f'{str(cf).upper()} CONFIDENCE')
        for dd in dom: badges.append(dd.upper())
        print(f'  [{\"  ·  \".join(badges)}]')
    if tw:
        print(f'  ◎ {tw}')
    if ai:
        print()
        print(f'  YOUR MOVE: {ai}')
except Exception as e:
    print(f'  Error parsing: {e}')
" 2>/dev/null

echo ""
echo ""

# ----------------------------------------------------------
# SUMMARY
# ----------------------------------------------------------
echo "╔══════════════════════════════════════════════════════╗"
echo "║  TEST COMPLETE                                      ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "  Chart ID: ${CHART_ID}"
echo "  (Save this — you can reuse it for future tests)"
echo ""
echo "  QUALITY CHECKS:"
echo "  ─────────────────────────────────────────────"
echo ""

# Run quality checks on all 3 responses
for i in 1 2 3; do
    eval "RESP=\$R${i}"
    eval "QUES=\$Q${i}"
    echo "  Q${i}: \"${QUES}\""
    echo "${RESP}" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    ps = d.get('plain_summary', '')
    ai = d.get('action_item', '')
    sl = d.get('signal_line', '')
    tw = d.get('timing_window', '')
    
    # Check 1: No trailing questions
    ends_q = ps.rstrip().endswith('?')
    print(f\"    {'❌' if ends_q else '✅'} No trailing question in plain_summary\")
    
    # Check 2: No jargon
    banned = ['Mahadasha', 'Antardasha', 'Atmakaraka', 'Navamsa', 'Amatyakaraka', 'Darakaraka', 'Gnatikaraka']
    found = [b for b in banned if b.lower() in ps.lower()]
    print(f\"    {'❌ Found: ' + ','.join(found) if found else '✅'} Zero jargon in plain_summary\")
    
    # Check 3: Action item starts with verb
    has_verb = ai and ai[0].isupper() and ' ' in ai
    print(f\"    {'✅' if has_verb else '⚠️ '} Action item starts with verb: {ai[:60]}...\")
    
    # Check 4: Signal line under 15 words
    sl_words = len(sl.split()) if sl else 0
    print(f\"    {'✅' if sl_words < 15 else '❌'} Signal line: {sl_words} words — {sl}\")
    
    # Check 5: Timing window is specific
    vague = ['soon', 'in the coming months', 'in the future', 'eventually']
    tw_vague = any(v in (tw or '').lower() for v in vague)
    print(f\"    {'❌' if tw_vague else '✅'} Timing window specific: {tw}\")
    
    print()
except Exception as e:
    print(f'    Parse error: {e}')
    print()
" 2>/dev/null
done

echo "  ─────────────────────────────────────────────"
echo "  TIMING INVERSION CHECK (the bug we fixed):"
echo "  ─────────────────────────────────────────────"
echo ""
echo "  Look at the plain_summary for Q2 (\"when will things improve\")."
echo "  If plain_summary says something like \"now is your best window\""
echo "  but the timing_window says a future date → BUG STILL EXISTS."
echo "  If plain_summary says \"things shift at [date], until then [bridge]\" → FIXED."
echo ""

# Save full JSON responses for debugging
echo "${R1}" | python3 -m json.tool > /tmp/antar_test_q1_full.json 2>/dev/null
echo "${R2}" | python3 -m json.tool > /tmp/antar_test_q2_full.json 2>/dev/null
echo "${R3}" | python3 -m json.tool > /tmp/antar_test_q3_full.json 2>/dev/null
echo "  Full JSON responses saved to:"
echo "    /tmp/antar_test_q1_full.json"
echo "    /tmp/antar_test_q2_full.json"
echo "    /tmp/antar_test_q3_full.json"
echo ""
echo "  Done."
