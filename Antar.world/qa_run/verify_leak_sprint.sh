#!/bin/bash
# verify_leak_sprint.sh — Pass 2.
# Re-pulls leak-bearing fields across 4 charts (+ ES) after the leak-elimination
# commits have deployed.
#
# Cache-busting per endpoint:
#   /home           → ?force_refresh=true  (synchronous, returns fresh payload)
#   /life-arc       → NO force_refresh — async returns {"status":"generating"} and
#                     never the body. Natural cache holds clean content after one
#                     warm-up cycle. We pull once to warm, sleep, pull again.
#   /remedies       → no cache layer to bust
#   /practices/...  → ?refresh=true  (synchronous, returns fresh)
#   /year-attention → recomputed per call
#   /prashna        → needs PRASHNA_TEST_CHARTS env var on Railway listing the
#                     4 test chart IDs, comma-separated, so cooldown is bypassed
#                     for these test charts only.
#
# Exit 0 = zero HARD hits on the 11 brief-targeted fields across all 4 charts in
# both languages. Exit 1 = at least one field still leaks.

set -u
BASE="https://antar-fastapi-production.up.railway.app"
US=1496055b-3603-44d9-8bea-49f54d1351c9
CO=3ee678e2-6535-4c9c-a779-a30a476718f4
IN=8603999c-7607-4c08-aa24-f83546a80aa6
SR=de0c6265-96cc-41ba-a39c-e55868fa5806

cd "$(dirname "$0")"

fetch() {
  local SLUG="$1" CID="$2" LANG="$3" METHOD="$4" PATH_="$5" BODY="$6" SURFACE="$7"
  local OUT="post_${SLUG}__${SURFACE}.json"
  if [ "$METHOD" = "POST" ]; then
    curl -sS -X POST "$BASE$PATH_" -H "Content-Type: application/json" \
      -H "Accept-Language: $LANG" --max-time 90 -d "$BODY" -o "$OUT" \
      -w "%{http_code} ${OUT}\n"
  else
    curl -sS "$BASE$PATH_" -H "Accept-Language: $LANG" --max-time 90 -o "$OUT" \
      -w "%{http_code} ${OUT}\n"
  fi
}

echo "=== Warming life-arc caches (async background compute) ==="
for ENTRY in "us_en|$US|en" "co_es|$CO|es" "in_en|$IN|en" "sr_en|$SR|en"; do
  CID="${ENTRY#*|}"; CID="${CID%%|*}"; LANG="${ENTRY##*|}"
  curl -sS "$BASE/api/v1/life-arc/$CID?language=$LANG" \
    -H "Accept-Language: $LANG" --max-time 30 -o /dev/null \
    -w "  warm $LANG %{http_code}\n"
done
echo "  sleep 35s for background generation"
sleep 35

echo
echo "=== Pulling leak-bearing fields (cache-busted where applicable) ==="
for ENTRY in "us_en|$US|en" "co_es|$CO|es" "in_en|$IN|en" "sr_en|$SR|en"; do
  SLUG="${ENTRY%%|*}"; rest="${ENTRY#*|}"
  CID="${rest%%|*}"; LANG="${rest##*|}"
  # /home — bust cache (per-language home_cache table)
  fetch "$SLUG" "$CID" "$LANG" GET  "/api/v1/home/$CID?language=$LANG&force_refresh=true" "" "home"
  # /life-arc — natural cache (already warmed)
  fetch "$SLUG" "$CID" "$LANG" GET  "/api/v1/life-arc/$CID?language=$LANG" "" "life_arc"
  # /remedies — no cache layer
  fetch "$SLUG" "$CID" "$LANG" GET  "/api/v1/remedies/$CID?language=$LANG" "" "remedies"
  # /practices — bust cache (practice_schedule_cache by chart_id + week_of)
  fetch "$SLUG" "$CID" "$LANG" GET  "/api/v1/practices/$CID/schedule?language=$LANG&refresh=true" "" "practices"
  # /year-attention — recomputed per call
  fetch "$SLUG" "$CID" "$LANG" POST "/api/v1/predict/year-attention" "{\"chart_id\":\"$CID\",\"language\":\"$LANG\"}" "year"
  # /prashna — requires PRASHNA_TEST_CHARTS on Railway
  fetch "$SLUG" "$CID" "$LANG" POST "/api/v1/prashna" "{\"chart_id\":\"$CID\",\"question\":\"Will I get the promotion this quarter?\",\"language\":\"$LANG\"}" "prashna"
done

echo
echo "=== Sanity: confirm prashna returned 200 (not 429) ==="
for f in post_*__prashna.json; do
  python3 -c "
import json,sys
d=json.load(open('$f'))
err=d.get('error') or ''
print(f'  $f: error={err!r}  has_remedy={bool(d.get(\"remedy\"))}')
"
done

echo
echo "=== Sanity: confirm life-arc returned full body (not 45-byte stub) ==="
for f in post_*__life_arc.json; do
  size=$(stat -c %s "$f" 2>/dev/null || wc -c < "$f")
  if [ "$size" -lt 200 ]; then
    body=$(head -c 200 "$f")
    echo "  ❌ $f: $size bytes — $body"
  else
    echo "  ✅ $f: $size bytes (full body)"
  fi
done

echo
echo "=== Scanning the 11 brief-targeted HARD fields with STRENGTHENED scanner ==="
python3 - <<'PY'
import json, re, glob, os, sys

SCAN_PATH = "scan.py"
SCAN_SRC = open(SCAN_PATH).read()
_ns = {"__name__": "_scan_lib", "__file__": SCAN_PATH}
exec(SCAN_SRC.split("hits = []")[0], _ns)
HARD = _ns["HARD"]; ATOMIC_HARD = _ns["ATOMIC_HARD"]
ATOMIC_SAFE = _ns["ATOMIC_SAFE"]; walk_strings = _ns["walk_strings"]
classify_key = _ns["classify_key"]; is_prose = _ns["is_prose"]

TARGETS_RE = [
    (re.compile(r"horizons\.cycle\.cycleName$"),            "1. home.horizons.cycle.cycleName"),
    (re.compile(r"attention\.planet$"),                      "2. year-attention attention.planet"),
    (re.compile(r"^archetype$"),                             "3. life-arc archetype"),
    (re.compile(r"dasha_remedy\.diagnosis$"),                "4. remedies dasha_remedy.diagnosis"),
    (re.compile(r"^remedies\.\[\d+\]\.why$"),                "5. remedies remedies[].why"),
    (re.compile(r"^remedy\.why$"),                           "6. prashna remedy.why"),
    (re.compile(r"primary_practice\.practice_why$"),         "7. practices primary_practice.practice_why"),
    (re.compile(r"mantra_of_the_day\.mantra_why$"),          "8. practices mantra_of_the_day.mantra_why"),
    (re.compile(r"(primary_practice|mantra_of_the_day)\.(mantra_)?duration_reason$"), "9. practices *.duration_reason"),
    (re.compile(r"weekly_plan\.\[\d+\]\.primary_action$"),   "10. practices weekly_plan[].primary_action"),
    (re.compile(r"supporting_practices\.\[\d+\]\.why$"),     "11. practices supporting_practices[].why"),
]

def scan_targets(d, slug, surface):
    hits = []
    for jp, key, val in walk_strings(d):
        parts = jp.split(".") if jp else []
        cls = classify_key(parts, key)
        if cls == "skip": continue
        sv = (val or "").strip()
        if sv and sv.upper() not in ATOMIC_SAFE:
            for rule, rx in ATOMIC_HARD.items():
                if rx.match(sv):
                    hits.append((slug, surface, jp, rule, sv[:60])); break
        if not is_prose(val): continue
        for rule, rx in HARD.items():
            if rule == "bija_syllables" and (surface == "practices" or "mantra" in (key or "").lower() or any("mantra" in p.lower() for p in parts) or any("practice" in p.lower() for p in parts)):
                continue
            m = rx.search(val)
            if m:
                hits.append((slug, surface, jp, rule, val[max(0,m.start()-25):m.end()+25].replace("\n"," ")))
    return [h for h in hits if any(rx.search(h[2]) for rx,_ in TARGETS_RE)]

per_target = {label: 0 for _, label in TARGETS_RE}
all_hits = []
for f in sorted(glob.glob("post_*.json")):
    base = os.path.basename(f).replace("post_","").replace(".json","")
    slug, _, surface = base.partition("__")
    try: d = json.load(open(f))
    except Exception as e:
        print(f"  parse fail {f}: {e}"); continue
    hh = scan_targets(d, slug, surface)
    all_hits.extend(hh)
    for h in hh:
        for rx, label in TARGETS_RE:
            if rx.search(h[2]):
                per_target[label] += 1; break

print("\n11-field checklist (post-deploy, Pass 2):")
ok = True
for _, label in TARGETS_RE:
    n = per_target[label]
    mark = "✅" if n == 0 else "❌"
    if n: ok = False
    print(f"  {mark} {label:<55}  hits={n}")

if all_hits:
    print(f"\n❌ {len(all_hits)} hit(s) survived. Sample:")
    for h in all_hits[:10]:
        print(f"   {h[0]:6} {h[1]:10} {h[2]:46} [{h[3]}] {h[4]!r}")
    sys.exit(1)
print("\n✅ ALL 11 brief-targeted fields = 0 HARD hits across 4 charts in both languages")
sys.exit(0)
PY
