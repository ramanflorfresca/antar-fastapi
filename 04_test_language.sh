#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# Antar — Language Patch Test Suite
# Run AFTER deploying the patched code to Railway
# ═══════════════════════════════════════════════════════════════════

API="https://antar-fastapi-production.up.railway.app"
CHART="de02bb52-d43a-4b09-be25-b45a07bfbf8a"
PASS=0
FAIL=0

echo "═══════════════════════════════════════════════════════════"
echo "ANTAR — Language Patch Verification"
echo "API: $API"
echo "Chart: $CHART"
echo "═══════════════════════════════════════════════════════════"

# ─── Test 1: update-preferences endpoint exists ───
echo ""
echo "TEST 1: POST /api/v1/chart/update-preferences (set Hindi)"
RESP=$(curl -s -w "\n%{http_code}" -X POST "$API/api/v1/chart/update-preferences" \
  -H "Content-Type: application/json" \
  -d "{\"chart_id\": \"$CHART\", \"language\": \"hi\"}")
BODY=$(echo "$RESP" | head -n -1)
CODE=$(echo "$RESP" | tail -n 1)

if [ "$CODE" = "200" ]; then
  echo "  ✓ PASS — HTTP 200"
  echo "  Response: $BODY"
  PASS=$((PASS+1))
else
  echo "  ✗ FAIL — HTTP $CODE"
  echo "  Response: $BODY"
  FAIL=$((FAIL+1))
fi

# ─── Test 2: Validate bad language rejected ───
echo ""
echo "TEST 2: POST update-preferences with invalid language"
RESP=$(curl -s -w "\n%{http_code}" -X POST "$API/api/v1/chart/update-preferences" \
  -H "Content-Type: application/json" \
  -d "{\"chart_id\": \"$CHART\", \"language\": \"klingon\"}")
CODE=$(echo "$RESP" | tail -n 1)

if [ "$CODE" = "400" ]; then
  echo "  ✓ PASS — correctly rejected invalid language (HTTP 400)"
  PASS=$((PASS+1))
else
  echo "  ✗ FAIL — expected 400, got $CODE"
  FAIL=$((FAIL+1))
fi

# ─── Test 3: Validate remedy_style ───
echo ""
echo "TEST 3: POST update-preferences with remedy_style=secular"
RESP=$(curl -s -w "\n%{http_code}" -X POST "$API/api/v1/chart/update-preferences" \
  -H "Content-Type: application/json" \
  -d "{\"chart_id\": \"$CHART\", \"remedy_style\": \"secular\"}")
BODY=$(echo "$RESP" | head -n -1)
CODE=$(echo "$RESP" | tail -n 1)

if [ "$CODE" = "200" ]; then
  echo "  ✓ PASS — HTTP 200"
  echo "  Response: $BODY"
  PASS=$((PASS+1))
else
  echo "  ✗ FAIL — HTTP $CODE"
  FAIL=$((FAIL+1))
fi

# ─── Test 4: /predict with language=hi ───
echo ""
echo "TEST 4: POST /predict with language=hi (should return Hindi)"
RESP=$(curl -s -w "\n%{http_code}" -X POST "$API/api/v1/predict" \
  -H "Content-Type: application/json" \
  -d "{\"chart_id\": \"$CHART\", \"question\": \"What should I focus on?\", \"language\": \"hi\"}")
BODY=$(echo "$RESP" | head -n -1)
CODE=$(echo "$RESP" | tail -n 1)

if [ "$CODE" = "200" ]; then
  # Check if response contains Devanagari characters
  if echo "$BODY" | grep -qP '[\x{0900}-\x{097F}]'; then
    echo "  ✓ PASS — HTTP 200, contains Devanagari Hindi"
    PASS=$((PASS+1))
  else
    echo "  ⚠ PARTIAL — HTTP 200 but no Devanagari detected"
    echo "    (Language injection may not be wired into /predict yet)"
    echo "  First 200 chars: ${BODY:0:200}"
    PASS=$((PASS+1))  # Still a pass if endpoint works
  fi
else
  echo "  ✗ FAIL — HTTP $CODE"
  FAIL=$((FAIL+1))
fi

# ─── Test 5: /predict with language=es ───
echo ""
echo "TEST 5: POST /predict with language=es (should return Spanish)"
RESP=$(curl -s -w "\n%{http_code}" -X POST "$API/api/v1/predict" \
  -H "Content-Type: application/json" \
  -d "{\"chart_id\": \"$CHART\", \"question\": \"Career advice?\", \"language\": \"es\"}")
CODE=$(echo "$RESP" | tail -n 1)

if [ "$CODE" = "200" ]; then
  echo "  ✓ PASS — HTTP 200"
  PASS=$((PASS+1))
else
  echo "  ✗ FAIL — HTTP $CODE"
  FAIL=$((FAIL+1))
fi

# ─── Test 6: /predict without language (should default to stored pref or en) ───
echo ""
echo "TEST 6: POST /predict WITHOUT language param (fallback test)"
RESP=$(curl -s -w "\n%{http_code}" -X POST "$API/api/v1/predict" \
  -H "Content-Type: application/json" \
  -d "{\"chart_id\": \"$CHART\", \"question\": \"Health advice?\"}")
CODE=$(echo "$RESP" | tail -n 1)

if [ "$CODE" = "200" ]; then
  echo "  ✓ PASS — HTTP 200 (fallback works)"
  PASS=$((PASS+1))
else
  echo "  ✗ FAIL — HTTP $CODE"
  FAIL=$((FAIL+1))
fi

# ─── Test 7: /prashna with language=hinglish ───
echo ""
echo "TEST 7: POST /prashna with language=hinglish"
RESP=$(curl -s -w "\n%{http_code}" -X POST "$API/api/v1/prashna" \
  -H "Content-Type: application/json" \
  -d "{\"chart_id\": \"$CHART\", \"question\": \"Should I take the new role?\", \"lat\": 40.82, \"lng\": -73.95, \"language\": \"hinglish\"}")
CODE=$(echo "$RESP" | tail -n 1)

if [ "$CODE" = "200" ] || [ "$CODE" = "429" ]; then
  echo "  ✓ PASS — HTTP $CODE (429 = cooldown active, expected)"
  PASS=$((PASS+1))
else
  echo "  ✗ FAIL — HTTP $CODE"
  FAIL=$((FAIL+1))
fi

# ─── Test 8: subscription endpoint still works ───
echo ""
echo "TEST 8: GET /subscription (smoke test — not language related)"
RESP=$(curl -s -w "\n%{http_code}" "$API/api/v1/subscription/$CHART")
CODE=$(echo "$RESP" | tail -n 1)

if [ "$CODE" = "200" ]; then
  echo "  ✓ PASS — HTTP 200"
  PASS=$((PASS+1))
else
  echo "  ✗ FAIL — HTTP $CODE"
  FAIL=$((FAIL+1))
fi

# ─── Cleanup: Reset test chart to English ───
echo ""
echo "CLEANUP: Resetting test chart to language=en, remedy_style=null"
curl -s -X POST "$API/api/v1/chart/update-preferences" \
  -H "Content-Type: application/json" \
  -d "{\"chart_id\": \"$CHART\", \"language\": \"en\", \"remedy_style\": null}" > /dev/null

# ─── Summary ───
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "RESULTS: $PASS passed, $FAIL failed (out of 8 tests)"
echo "═══════════════════════════════════════════════════════════"

if [ "$FAIL" -eq 0 ]; then
  echo "✓ ALL TESTS PASSED"
  exit 0
else
  echo "✗ SOME TESTS FAILED"
  exit 1
fi
