#!/bin/bash
# ============================================================
# ANTAR — Full User Journey Test #2
# ============================================================
# Test subject: Nov 2, 1970, 6:02 AM, Siddipet, India
# Living in: India (IN)
# Age: 55
#
# Questions:
#   1. "what is happening with my businesses"
#   2. "when will i get funding for my startup business 
#       i have been trying since January 2025"
#   3. "when do i see a relief in income versus expenses"
#
# Usage:
#   bash antar_test_siddipet.sh
# ============================================================

BASE_URL="https://antar-fastapi-production.up.railway.app"

echo "╔══════════════════════════════════════════════════════╗"
echo "║  ANTAR — Full Journey Test #2                       ║"
echo "║  Subject: Nov 2, 1970 · 6:02 AM · Siddipet, India  ║"
echo "║  Date: $(date)                                      ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ----------------------------------------------------------
# STEP 1: CREATE CHART
# ----------------------------------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "▸ STEP 1: Create Chart — POST /api/v1/chart/create"
echo "  Name: Vikram"
echo "  DOB: 1970-11-02"
echo "  Time: 06:02 (24hr)"
echo "  City: Siddipet"
echo "  Country: IN"
echo "  Lives in: IN"
echo "  Gender: male"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

CREATE_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/chart/create" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Vikram",
    "name": "Vikram Test",
    "birth_date": "1970-11-02",
    "birth_time": "06:02",
    "birth_city": "Siddipet",
    "birth_country": "IN",
    "current_country": "IN",
    "gender": "male"
  }')

echo "  Response:"
echo "${CREATE_RESPONSE}" | python3 -m json.tool 2>/dev/null || echo "${CREATE_RESPONSE}"
echo ""

CHART_ID=$(echo "${CREATE_RESPONSE}" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('chart_id', d.get('id', '')))
except:
    print('')
" 2>/dev/null)

if [ -z "$CHART_ID" ]; then
    echo "ERROR: Could not extract chart_id. Aborting."
    exit 1
fi

echo "  ✅ Chart created: ${CHART_ID}"
echo ""

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
# STEP 2: DASHBOARD
# ----------------------------------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "▸ STEP 2: Dashboard — GET /api/v1/dashboard/${CHART_ID}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

DASH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/api/v1/dashboard/${CHART_ID}")
echo "  Status: ${DASH_STATUS}"
[ "$DASH_STATUS" = "200" ] && echo "  ✅ Dashboard loaded" || echo "  ⚠️  Dashboard returned ${DASH_STATUS}"
echo ""

# ----------------------------------------------------------
# STEP 3: WELCOME SIGNAL
# ----------------------------------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "▸ STEP 3: Welcome Signal — GET /api/v1/welcome/${CHART_ID}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# First call may trigger async generation — retry once
WELCOME_RESPONSE=$(curl -s "${BASE_URL}/api/v1/welcome/${CHART_ID}?language=en")
if echo "${WELCOME_RESPONSE}" | grep -q "Failed"; then
    echo "  ⏳ First call triggered generation, waiting 10s..."
    sleep 10
    WELCOME_RESPONSE=$(curl -s "${BASE_URL}/api/v1/welcome/${CHART_ID}?language=en")
fi

echo "${WELCOME_RESPONSE}" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    if 'signal_1' in d:
        s1 = d.get('signal_1', {})
        s2 = d.get('signal_2', {})
        s3 = d.get('signal_3', {})
        print(f\"  Mirror:  {s1.get('body', s1.get('headline', 'N/A'))[:150]}\")
        print(f\"  Chapter: {str(s2.get('events', s2.get('body', s2.get('headline', 'N/A'))))[:150]}\")
        print(f\"  Signal:  {s3.get('body', s3.get('headline', 'N/A'))[:150]}\")
    elif 'detail' in d:
        print(f\"  ⚠️  {d['detail']}\")
    else:
        print(f\"  {json.dumps(d, indent=2)[:300]}\")
except Exception as e:
    print(f'  Parse error: {e}')
" 2>/dev/null
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
except Exception as e:
    print(f'  Error: {e}')
" 2>/dev/null
echo ""

# ============================================================
# HELPER: Display what user sees + run quality checks
# ============================================================
show_response() {
    local RESP="$1"
    local QNUM="$2"
    local QTEXT="$3"

    echo ""
    echo "  ┌─────────────────────────────────────────────┐"
    echo "  │  WHAT THE USER SEES IN CHAT                 │"
    echo "  └─────────────────────────────────────────────┘"
    echo ""

    echo "${RESP}" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    sig = d.get('signal_line', '')
    why = d.get('why_this', '')
    ps = d.get('plain_summary', '')
    ai = d.get('action_item', '')
    tw = d.get('timing_window', '')
    cf = d.get('signal_confidence', d.get('confidence', ''))
    dom = d.get('all_domains', [])

    if sig:
        print(f'  ✦ {sig}')
        print()
    if why:
        print(f'  WHY: {why}')
        print()
    print(f'  {ps}')
    print()
    if cf or dom:
        badges = []
        if cf: badges.append(f'{str(cf).upper()} CONFIDENCE')
        for dd in dom: badges.append(dd.upper())
        print(f'  [{\\"  ·  \\".join(badges)}]')
    if tw:
        print(f'  ◎ {tw}')
    if ai:
        print()
        print(f'  YOUR MOVE: {ai}')
except Exception as e:
    print(f'  Error: {e}')
" 2>/dev/null

    echo ""
    echo "  ── Quality Checks ──"
    echo "${RESP}" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    ps = d.get('plain_summary', '')
    ai = d.get('action_item', '')
    sl = d.get('signal_line', '')
    tw = d.get('timing_window', '')
    why = d.get('why_this', '')

    # Check 1: No trailing questions
    ends_q = ps.rstrip().endswith('?')
    print(f\"    {'❌' if ends_q else '✅'} No trailing question\")

    # Check 2: No jargon
    banned = ['Mahadasha', 'Antardasha', 'Atmakaraka', 'Navamsa', 'Amatyakaraka', 'Darakaraka']
    found = [b for b in banned if b.lower() in ps.lower()]
    print(f\"    {'❌ ' + ','.join(found) if found else '✅'} Zero jargon\")

    # Check 3: No planet names
    planets = ['Saturn', 'Rahu', 'Mars', 'Jupiter', 'Venus', 'Mercury', 'Ketu']
    found_p = [p for p in planets if p in ps]
    print(f\"    {'❌ ' + ','.join(found_p) if found_p else '✅'} No planet names in summary\")

    # Check 4: No long cycles
    long_cycles = ['18-year', '19-year', '20-year', 'until 2044', 'until 2043', 'until 2045']
    found_lc = [lc for lc in long_cycles if lc in ps]
    print(f\"    {'❌ ' + ','.join(found_lc) if found_lc else '✅'} No long cycles (>5yr) in summary\")

    # Check 5: WHY present
    has_why = bool(why and len(why) > 10)
    print(f\"    {'✅' if has_why else '❌'} WHY field present\")

    # Check 6: WHY in first sentence of plain_summary
    first_sent = ps.split('.')[0] if ps else ''
    age_refs = ['55', '50s', 'at your age', 'at this stage', 'chapter', 'phase of life']
    has_why_in_summary = any(ref in first_sent.lower() for ref in age_refs)
    print(f\"    {'✅' if has_why_in_summary else '⚠️ '} WHY in first sentence of summary\")

    # Check 7: Action item starts with verb
    has_verb = ai and ai[0].isupper() and ' ' in ai
    print(f\"    {'✅' if has_verb else '⚠️ '} Action starts with verb: {ai[:60]}...\")

    # Check 8: Signal line under 15 words
    sl_words = len(sl.split()) if sl else 0
    print(f\"    {'✅' if sl_words < 15 else '❌'} Signal line: {sl_words} words\")

    # Check 9: Timing specific
    vague = ['soon', 'in the coming months', 'in the future', 'eventually']
    tw_vague = any(v in (tw or '').lower() for v in vague)
    print(f\"    {'❌' if tw_vague else '✅'} Timing specific: {tw}\")

    # Check 10: No past dates
    import re
    past_months = ['January 2025', 'February 2025', 'March 2025', 'April 2025',
                   'May 2025', 'June 2025', 'July 2025', 'August 2025',
                   'September 2025', 'October 2025', 'November 2025', 'December 2025',
                   'January 2026', 'February 2026', 'March 2026']
    found_past = [pm for pm in past_months if pm in ps]
    print(f\"    {'❌ ' + ','.join(found_past) if found_past else '✅'} No past dates in summary\")

except Exception as e:
    print(f'    Error: {e}')
" 2>/dev/null
    echo ""
}

# ----------------------------------------------------------
# STEP 5: Q1 — "what is happening with my businesses"
# ----------------------------------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "▸ STEP 5: Ask Antar — \"what is happening with my businesses\""
echo "  POST /api/v1/predict"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

Q1="what is happening with my businesses"

R1=$(curl -s -X POST "${BASE_URL}/api/v1/predict" \
  -H "Content-Type: application/json" \
  -d "{
    \"chart_id\": \"${CHART_ID}\",
    \"question\": \"${Q1}\",
    \"language\": \"en\",
    \"conversation_history\": []
  }")

show_response "$R1" "1" "$Q1"

# Extract plain_summary for conversation history
PS1=$(echo "${R1}" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('plain_summary', d.get('prediction', ''))[:500])
except:
    print('')
" 2>/dev/null)
PS1_ESC=$(echo "${PS1}" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read().strip()))" 2>/dev/null)

# ----------------------------------------------------------
# STEP 6: Q2 — "when will i get funding..."
# ----------------------------------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "▸ STEP 6: Follow-up — \"when will i get funding for my"
echo "  startup business i have been trying since January 2025\""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

Q2="when will i get funding for my startup business i have been trying since January 2025"

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

show_response "$R2" "2" "$Q2"

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
# STEP 7: Q3 — "when do i see a relief in income vs expenses"
# ----------------------------------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "▸ STEP 7: Follow-up — \"when do i see a relief in"
echo "  income versus expenses\""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

Q3="when do i see a relief in income versus expenses"

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

show_response "$R3" "3" "$Q3"

# ----------------------------------------------------------
# SUMMARY
# ----------------------------------------------------------
echo "╔══════════════════════════════════════════════════════╗"
echo "║  TEST COMPLETE                                      ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "  Chart ID: ${CHART_ID}"
echo "  (Save this — reuse for future tests)"
echo ""
echo "  ── REPETITION CHECK ──"
echo "  Compare the three responses below."
echo "  Q1 should set the landscape."
echo "  Q2 should go deeper into funding specifically."
echo "  Q3 should go deeper into cash flow specifically."
echo "  If all three sound the same → depth ladder not working."
echo ""

echo "  ── SIGNAL LINES ──"
echo "${R1}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"  Q1: {d.get('signal_line','N/A')}\")" 2>/dev/null
echo "${R2}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"  Q2: {d.get('signal_line','N/A')}\")" 2>/dev/null
echo "${R3}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"  Q3: {d.get('signal_line','N/A')}\")" 2>/dev/null
echo ""

echo "  ── ACTION ITEMS (should be DIFFERENT each turn) ──"
echo "${R1}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"  Q1: {d.get('action_item','N/A')[:80]}\")" 2>/dev/null
echo "${R2}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"  Q2: {d.get('action_item','N/A')[:80]}\")" 2>/dev/null
echo "${R3}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"  Q3: {d.get('action_item','N/A')[:80]}\")" 2>/dev/null
echo ""

echo "  ── WHY FIELDS ──"
echo "${R1}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"  Q1: {d.get('why_this','(missing)')[:100]}\")" 2>/dev/null
echo "${R2}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"  Q2: {d.get('why_this','(missing)')[:100]}\")" 2>/dev/null
echo "${R3}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"  Q3: {d.get('why_this','(missing)')[:100]}\")" 2>/dev/null
echo ""

# Save full JSON
echo "${R1}" | python3 -m json.tool > /tmp/antar_siddipet_q1.json 2>/dev/null
echo "${R2}" | python3 -m json.tool > /tmp/antar_siddipet_q2.json 2>/dev/null
echo "${R3}" | python3 -m json.tool > /tmp/antar_siddipet_q3.json 2>/dev/null
echo "  Full JSON saved to /tmp/antar_siddipet_q1/q2/q3.json"
echo ""
echo "  Done."
