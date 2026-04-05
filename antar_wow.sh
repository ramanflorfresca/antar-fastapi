#!/bin/bash
# ============================================================
# ANTAR — Welcome Signal WOW Test
# ============================================================
# Tests the 3-signal welcome experience for a specific chart.
# Retries every 5 seconds until the signal generates.
#
# The 3 signals:
#   Signal 1 — THE MIRROR: Character insight from lagna + moon + nakshatra
#   Signal 2 — THE PROOF: Past events the chart predicted (proof loop)
#   Signal 3 — THE SIGNAL: What to watch for in next 60-90 days
#
# Logic sources:
#   Signal 1: Lagna sign + Moon sign + Moon nakshatra + Atmakaraka
#   Signal 2: Dasha transitions over last 5-10 years mapped to life events
#   Signal 3: Current dasha + upcoming transit + Varshphal activation
#
# Usage:
#   bash antar_test_wow.sh <chart_id>
#   bash antar_test_wow.sh   (defaults to Siddipet chart)
# ============================================================

BASE_URL="https://antar-fastapi-production.up.railway.app"

# Use provided chart_id or default to Siddipet
CHART_ID="${1:-de20689b-6da5-45bc-b81e-0c9c82d57d02}"

echo "╔══════════════════════════════════════════════════════╗"
echo "║  ANTAR — Welcome Signal WOW Test                    ║"
echo "║  Chart: ${CHART_ID:0:20}...                         ║"
echo "║  Date: $(date)                                      ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── Get chart basics first ────────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "▸ Chart Profile"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

DASH=$(curl -s "${BASE_URL}/api/v1/dashboard/${CHART_ID}")
echo "${DASH}" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(f'  Name:      {d.get(\"first_name\", \"N/A\")}')
    print(f'  Lagna:     {d.get(\"lagna\", \"N/A\")}')
    print(f'  Moon:      {d.get(\"moon_sign\", \"N/A\")}')
    print(f'  Nakshatra: {d.get(\"moon_nakshatra\", \"N/A\")}')
    print(f'  Sun:       {d.get(\"sun_sign\", \"N/A\")}')
    print(f'  Dasha:     {d.get(\"dasha\", \"N/A\")}')
    print(f'  Country:   {d.get(\"current_country\", \"N/A\")}')
except:
    print('  Could not load dashboard')
" 2>/dev/null
echo ""

# ── Fetch welcome signal with retry ──────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "▸ Welcome Signal — GET /api/v1/welcome/${CHART_ID}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

MAX_RETRIES=6
RETRY_WAIT=5
ATTEMPT=0
WELCOME=""

while [ $ATTEMPT -lt $MAX_RETRIES ]; do
    ATTEMPT=$((ATTEMPT + 1))
    echo "  Attempt ${ATTEMPT}/${MAX_RETRIES}..."
    
    WELCOME=$(curl -s "${BASE_URL}/api/v1/welcome/${CHART_ID}?language=en")
    
    # Check if it's a success (has signal_1 or headline)
    HAS_SIGNAL=$(echo "${WELCOME}" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    if 'signal_1' in d or 'headline' in d:
        print('YES')
    else:
        print('NO')
except:
    print('NO')
" 2>/dev/null)
    
    if [ "$HAS_SIGNAL" = "YES" ]; then
        echo "  ✅ Welcome signal received!"
        echo ""
        break
    else
        if [ $ATTEMPT -lt $MAX_RETRIES ]; then
            echo "  ⏳ Still generating... waiting ${RETRY_WAIT}s"
            sleep $RETRY_WAIT
        else
            echo "  ❌ Failed after ${MAX_RETRIES} attempts"
            echo "  Response: ${WELCOME}"
            echo ""
            echo "  This chart may need the welcome signal cache cleared."
            echo "  Try: DELETE FROM welcome_signals WHERE chart_id = '${CHART_ID}';"
            exit 1
        fi
    fi
done

# ── Display the 3 signals ────────────────────────────────────
echo "${WELCOME}" | python3 -c "
import sys, json

try:
    d = json.load(sys.stdin)
except:
    print('  ERROR: Could not parse response')
    sys.exit(1)

# ── SIGNAL 1: THE MIRROR ──────────────────────────────────
print('  ┌─────────────────────────────────────────────┐')
print('  │  SIGNAL 1 — THE MIRROR                      │')
print('  │  Source: Lagna + Moon + Nakshatra + AK       │')
print('  └─────────────────────────────────────────────┘')
print()

s1 = d.get('signal_1', {})
if s1:
    print(f'  Type:     {s1.get(\"type\", \"N/A\")}')
    hl = s1.get('headline', '')
    if hl:
        print(f'  Headline: {hl}')
    body = s1.get('body', '')
    if body:
        print(f'  Body:     {body}')
    print()
    print('  LOGIC: This signal comes from the combination of:')
    print('    - Lagna (rising sign) = how you show up in the world')
    print('    - Moon sign = your emotional nature')  
    print('    - Moon nakshatra = your deepest behavioral pattern')
    print('    - Atmakaraka = your soul\\'s core mission')
    print('  It should feel personal and slightly uncomfortable — like')
    print('  someone seeing a truth about you that you rarely say out loud.')
else:
    hl = d.get('headline', '')
    body = d.get('summary', '')
    if hl: print(f'  Headline: {hl}')
    if body: print(f'  Body:     {body}')

print()

# ── SIGNAL 2: THE PROOF ──────────────────────────────────
print('  ┌─────────────────────────────────────────────┐')
print('  │  SIGNAL 2 — THE PROOF                       │')
print('  │  Source: Dasha transitions mapped to events  │')
print('  └─────────────────────────────────────────────┘')
print()

s2 = d.get('signal_2', {})
if s2:
    print(f'  Type:     {s2.get(\"type\", \"N/A\")}')
    
    events = s2.get('events', [])
    if events:
        for i, ev in enumerate(events):
            print(f'  Event {i+1}:')
            print(f'    Chapter:  {ev.get(\"chapter\", \"N/A\")}')
            print(f'    Period:   {ev.get(\"period\", \"N/A\")}')
            print(f'    Age:      {ev.get(\"age\", \"N/A\")}')
            print(f'    Question: {ev.get(\"question\", \"N/A\")}')
            print(f'    Meaning:  {ev.get(\"meaning\", \"N/A\")}')
            print()
    
    thread = s2.get('thread', '')
    if thread:
        print(f'  Thread:   {thread}')
    
    body = s2.get('body', '')
    if body and not events:
        print(f'  Body:     {body}')
    
    timing = s2.get('timing', '')
    if timing:
        print(f'  Timing:   {timing}')
    
    print()
    print('  LOGIC: This signal comes from:')
    print('    - Dasha transitions in the last 5-10 years')
    print('    - Major life chapters (Mahadasha/Antardasha shifts)')
    print('    - Each event maps to a specific dasha period')
    print('  The user should think \"how did it know that happened?\"')
    print('  This builds trust before any future predictions.')
else:
    print('  (Signal 2 not in response)')

print()

# ── SIGNAL 3: THE SIGNAL ──────────────────────────────────
print('  ┌─────────────────────────────────────────────┐')
print('  │  SIGNAL 3 — THE SIGNAL                      │')
print('  │  Source: Current dasha + transit + Varshphal │')
print('  └─────────────────────────────────────────────┘')
print()

s3 = d.get('signal_3', {})
if s3:
    print(f'  Type:     {s3.get(\"type\", \"N/A\")}')
    print(f'  Headline: {s3.get(\"headline\", \"N/A\")}')
    print(f'  Body:     {s3.get(\"body\", \"N/A\")}')
    print(f'  Domain:   {s3.get(\"domain\", \"N/A\")}')
    print(f'  Watch:    {s3.get(\"watch_for\", \"N/A\")}')
    print()
    print('  LOGIC: This signal comes from:')
    print('    - Current Vimsottari dasha + Antardasha activation')
    print('    - Slow planet transits (Saturn, Jupiter, Rahu) in next 60-90 days')
    print('    - Varshphal (annual chart) year lord placement')
    print('    - Jaimini Chara Dasha current sign activation')
    print('  It should name a specific domain, specific date range,')
    print('  and one concrete thing to watch for or do.')
else:
    action = d.get('action', '')
    sig_type = d.get('signal_type', '')
    if action: print(f'  Action:   {action}')
    if sig_type: print(f'  Type:     {sig_type}')

print()

# ── WOW QUALITY CHECK ──────────────────────────────────────
print('  ┌─────────────────────────────────────────────┐')
print('  │  WOW QUALITY CHECKS                         │')
print('  └─────────────────────────────────────────────┘')
print()

# Check 1: Signal 1 is personal (not generic)
s1_body = s1.get('body', '') if s1 else d.get('summary', '')
generic_phrases = ['your chart shows', 'astrologically', 'the stars', 'cosmic', 'universe']
is_generic = any(p in s1_body.lower() for p in generic_phrases)
print(f'  {\"❌\" if is_generic else \"✅\"} Signal 1 is personal (not generic astro-speak)')

# Check 2: Signal 2 has past events with specific years
has_events = bool(s2.get('events', []))
has_years = any(str(y) in str(s2) for y in range(2015, 2026))
print(f'  {\"✅\" if has_events else \"⚠️ \"} Signal 2 has past event questions')
print(f'  {\"✅\" if has_years else \"⚠️ \"} Signal 2 references specific years')

# Check 3: Signal 3 has domain + future date + action
has_domain = bool(s3.get('domain', ''))
has_watch = bool(s3.get('watch_for', ''))
s3_body = s3.get('body', '')
has_future = any(m in s3_body for m in ['April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December', '2026', '2027'])
print(f'  {\"✅\" if has_domain else \"❌\"} Signal 3 has a specific domain')
print(f'  {\"✅\" if has_future else \"⚠️ \"} Signal 3 has a future date')
print(f'  {\"✅\" if has_watch else \"❌\"} Signal 3 has a watch_for action')

# Check 4: No jargon
all_text = str(d)
jargon = ['Mahadasha', 'Antardasha', 'Navamsa', 'Atmakaraka']
found_jargon = [j for j in jargon if j in all_text]
print(f'  {\"❌ \" + \",\".join(found_jargon) if found_jargon else \"✅\"} Zero jargon across all signals')

# Check 5: Age appropriate
print(f'  ℹ️  Manual check: Are the events age-appropriate for a 55-year-old?')

print()
" 2>/dev/null

# ── Save raw response ────────────────────────────────────────
echo "${WELCOME}" | python3 -m json.tool > /tmp/antar_wow_test.json 2>/dev/null
echo "  Full JSON saved to /tmp/antar_wow_test.json"
echo ""
echo "  Done."
