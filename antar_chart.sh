#!/bin/bash
# ============================================================
# ANTAR — Interactive CLI Chat (Ask Antar Simulator)
# ============================================================
# Simulates the web chat experience from your terminal.
# Type questions, see responses as the user would.
# Conversation history is maintained across turns.
#
# Usage:
#   bash antar_chat.sh <chart_id>
#   bash antar_chat.sh   (prompts for chart_id)
#
# Commands:
#   Type any question → sends to /predict
#   /new              → clear conversation history
#   /info             → show chart details
#   /raw              → show last raw prediction
#   /quit or /exit    → exit
# ============================================================

BASE_URL="https://antar-fastapi-production.up.railway.app"

# Get chart_id
if [ -n "$1" ]; then
    CHART_ID="$1"
else
    echo ""
    echo "  ╔═══════════════════════════════════════╗"
    echo "  ║  ANTAR — Interactive Chat             ║"
    echo "  ╚═══════════════════════════════════════╝"
    echo ""
    echo "  Enter chart_id (or 'new' to create a chart):"
    read -p "  > " CHART_ID
    
    if [ "$CHART_ID" = "new" ]; then
        echo ""
        read -p "  First name: " FIRST_NAME
        read -p "  Birth date (YYYY-MM-DD): " BIRTH_DATE
        read -p "  Birth time (HH:MM 24hr): " BIRTH_TIME
        read -p "  Birth city: " BIRTH_CITY
        read -p "  Birth country (IN/US/GB): " BIRTH_COUNTRY
        read -p "  Lives in now (IN/US/GB): " CURRENT_COUNTRY
        read -p "  Gender (male/female): " GENDER
        
        echo ""
        echo "  Creating chart..."
        CREATE_RESP=$(curl -s -X POST "${BASE_URL}/api/v1/chart/create" \
          -H "Content-Type: application/json" \
          -d "{
            \"first_name\": \"${FIRST_NAME}\",
            \"name\": \"${FIRST_NAME}\",
            \"birth_date\": \"${BIRTH_DATE}\",
            \"birth_time\": \"${BIRTH_TIME}\",
            \"birth_city\": \"${BIRTH_CITY}\",
            \"birth_country\": \"${BIRTH_COUNTRY}\",
            \"current_country\": \"${CURRENT_COUNTRY}\",
            \"gender\": \"${GENDER}\"
          }")
        
        CHART_ID=$(echo "${CREATE_RESP}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('chart_id',''))" 2>/dev/null)
        
        if [ -z "$CHART_ID" ]; then
            echo "  ERROR: Chart creation failed"
            echo "  ${CREATE_RESP}"
            exit 1
        fi
        
        echo "${CREATE_RESP}" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f\"  Chart: {d.get('chart_id', '')[:20]}...\")
print(f\"  Lagna: {d.get('lagna', '')}\")
print(f\"  Moon: {d.get('moon_sign', '')}\")
print(f\"  Dasha: {d.get('current_dasha', '')}\")
intent = d.get('signup_intent')
if intent:
    print()
    print(f\"  TELEPATHIC INTENT:\")
    print(f\"  {intent.get('personalized_wow', '')}\")
" 2>/dev/null
    fi
fi

# Temp files for conversation history
HISTORY_FILE="/tmp/antar_chat_history_${CHART_ID:0:8}.json"
LAST_RAW="/tmp/antar_chat_last_raw.json"

# Initialize empty history
echo "[]" > "$HISTORY_FILE"

# Get chart info
DASH=$(curl -s "${BASE_URL}/api/v1/dashboard/${CHART_ID}" 2>/dev/null)
CHART_NAME=$(echo "$DASH" | python3 -c "import sys,json; print(json.load(sys.stdin).get('first_name','User'))" 2>/dev/null)
CHART_LAGNA=$(echo "$DASH" | python3 -c "import sys,json; print(json.load(sys.stdin).get('lagna','?'))" 2>/dev/null)
CHART_DASHA=$(echo "$DASH" | python3 -c "import sys,json; print(json.load(sys.stdin).get('dasha','?'))" 2>/dev/null)
CHART_MOON=$(echo "$DASH" | python3 -c "import sys,json; print(json.load(sys.stdin).get('moon_sign','?'))" 2>/dev/null)

echo ""
echo "  ╔═══════════════════════════════════════════════════╗"
echo "  ║  Ask Antar — Interactive Chat                     ║"
echo "  ╠═══════════════════════════════════════════════════╣"
echo "  ║  ${CHART_NAME} · ${CHART_LAGNA} · ${CHART_MOON} · ${CHART_DASHA}"
echo "  ║  Chart: ${CHART_ID:0:20}..."
echo "  ╠═══════════════════════════════════════════════════╣"
echo "  ║  Commands: /new /info /raw /quit                  ║"
echo "  ╚═══════════════════════════════════════════════════╝"
echo ""

TURN=0

while true; do
    # Prompt
    echo -n "  You: "
    read -r QUESTION
    
    # Handle commands
    case "$QUESTION" in
        /quit|/exit|/q)
            echo ""
            echo "  Session ended. ${TURN} turns."
            echo "  Chart: ${CHART_ID}"
            exit 0
            ;;
        /new)
            echo "[]" > "$HISTORY_FILE"
            TURN=0
            echo "  ── Conversation cleared ──"
            echo ""
            continue
            ;;
        /info)
            echo ""
            echo "  Name:    ${CHART_NAME}"
            echo "  Lagna:   ${CHART_LAGNA}"
            echo "  Moon:    ${CHART_MOON}"
            echo "  Dasha:   ${CHART_DASHA}"
            echo "  Chart:   ${CHART_ID}"
            echo "  Turn:    ${TURN}"
            echo ""
            continue
            ;;
        /raw)
            if [ -f "$LAST_RAW" ]; then
                echo ""
                echo "  ── Last Raw Prediction (first 2000 chars) ──"
                python3 -c "
import json
with open('${LAST_RAW}') as f:
    d = json.load(f)
print(d.get('prediction', '(empty)')[:2000])
" 2>/dev/null
                echo ""
                echo "  ── End Raw ──"
            else
                echo "  No previous response."
            fi
            echo ""
            continue
            ;;
        "")
            continue
            ;;
    esac
    
    TURN=$((TURN + 1))
    
    # Build conversation history JSON
    HISTORY=$(cat "$HISTORY_FILE")
    
    # Show loading
    echo "  ✦ Reading your chart..."
    
    # Make the API call
    RESPONSE=$(curl -s --max-time 120 -X POST "${BASE_URL}/api/v1/predict" \
      -H "Content-Type: application/json" \
      -d "{
        \"chart_id\": \"${CHART_ID}\",
        \"question\": $(python3 -c "import json; print(json.dumps('${QUESTION}'))" 2>/dev/null),
        \"language\": \"en\",
        \"conversation_history\": ${HISTORY}
      }")
    
    # Save raw response
    echo "${RESPONSE}" > "$LAST_RAW"
    
    # Display response
    echo ""
    echo "${RESPONSE}" | python3 -c "
import sys, json

try:
    d = json.load(sys.stdin)
except:
    print('  ERROR: Could not parse response')
    sys.exit(0)

sig = d.get('signal_line', '')
why = d.get('why_this', '')
ps = d.get('plain_summary', '')
ai = d.get('action_item', '')
tw = d.get('timing_window', '')
cf = d.get('signal_confidence', d.get('confidence', ''))
dom = d.get('all_domains', [])
bn = d.get('bridge_practice_note', '')

# Signal line
if sig:
    print(f'  ✦ {sig}')
    print()

# WHY
if why:
    print(f'  WHY: {why}')
    print()

# Summary
if ps:
    # Word wrap at ~70 chars
    words = ps.split()
    line = '  '
    for w in words:
        if len(line) + len(w) + 1 > 72:
            print(line)
            line = '  ' + w
        else:
            line += (' ' if len(line) > 2 else '') + w
    if line.strip():
        print(line)
    print()

# Badges
if cf or dom:
    badges = []
    if cf: badges.append(f'{str(cf).upper()} CONFIDENCE')
    for dd in dom: badges.append(dd.upper())
    print(f'  [{\"  ·  \".join(badges)}]')

# Timing
if tw:
    print(f'  ◎ {tw}')

# Bridge practice note
if bn:
    print(f'  ♢ {bn}')

# Action
if ai:
    print()
    print(f'  YOUR MOVE: {ai}')

print()
print('  ─────────────────────────────────────────')
" 2>/dev/null
    
    # Update conversation history
    PLAIN=$(echo "${RESPONSE}" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('plain_summary', d.get('prediction', ''))[:500])
except:
    print('')
" 2>/dev/null)
    
    # Append this turn to history
    python3 -c "
import json

with open('${HISTORY_FILE}') as f:
    history = json.load(f)

history.append({'role': 'user', 'content': $(python3 -c "import json; print(json.dumps('${QUESTION}'))" 2>/dev/null)})
history.append({'role': 'assistant', 'content': $(echo "${PLAIN}" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read().strip()))" 2>/dev/null)})

# Keep last 8 messages (4 turns)
if len(history) > 8:
    history = history[-8:]

with open('${HISTORY_FILE}', 'w') as f:
    json.dump(history, f)
" 2>/dev/null
    
    echo ""
done
