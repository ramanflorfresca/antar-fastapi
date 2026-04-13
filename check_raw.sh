#!/bin/bash
echo "=== Raw top-level keys ==="
curl -s "https://antar-fastapi-production.up.railway.app/api/v1/practices/de02bb52-d43a-4b09-be25-b45a07bfbf8a/schedule?language=es" \
  | python3 -c "
import sys,json
raw = sys.stdin.read()
print('RAW (first 300):', raw[:300])
print()
try:
    d=json.loads(raw)
    print('TOP KEYS:', list(d.keys()))
    s=d.get('schedule',{})
    print('SCHEDULE TYPE:', type(s).__name__)
    print('SCHEDULE KEYS:', list(s.keys()) if isinstance(s,dict) else s)
except Exception as e:
    print('JSON ERROR:', e)
"
