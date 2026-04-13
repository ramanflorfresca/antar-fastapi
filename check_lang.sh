#!/bin/bash
echo "=== Testing language=es is actually received ==="
curl -s "https://antar-fastapi-production.up.railway.app/api/v1/practices/de02bb52-d43a-4b09-be25-b45a07bfbf8a/schedule?language=es" \
  | python3 -c "
import sys,json
d=json.load(sys.stdin)
s=d.get('schedule',{})
pp=s.get('primary_practice',{})
mot=s.get('mantra_of_the_day',{})
print('locale:', s.get('locale'))
print('energy_label:', pp.get('energy_label'))
print('why:', pp.get('why','')[:100])
print('what:', pp.get('what','')[:100])
print('practice_why:', pp.get('practice_why','')[:100])
print('convergence_summary:', s.get('convergence_summary','')[:100])
print('mantra affirmation:', mot.get('affirmation','')[:100])
print('mantra_text:', mot.get('mantra_text','')[:80])
"
