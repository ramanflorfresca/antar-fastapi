#!/bin/bash
echo "=== DASHBOARD panchang fields ==="
curl -s "https://antar-fastapi-production.up.railway.app/api/v1/dashboard/de02bb52-d43a-4b09-be25-b45a07bfbf8a?language=es" | python3 -c "
import sys,json
d=json.load(sys.stdin)
print('panchanga_headline:', d.get('panchanga_headline',''))
print('day_quality:', d.get('day_quality',''))
print('do_today:', d.get('do_today',''))
print('dont_today:', d.get('dont_today',''))
print('moon_nak_today:', d.get('moon_nak_today',''))
print('rahu_kalam:', d.get('rahu_kalam',''))
print('abhijit:', d.get('abhijit',''))
print('dasha_remedy:', d.get('dasha_remedy','')[:100])
"

echo ""
echo "=== DAILY-WEEK first day ==="
curl -s "https://antar-fastapi-production.up.railway.app/api/v1/daily-week/de02bb52-d43a-4b09-be25-b45a07bfbf8a?tz_offset=-5" | python3 -c "
import sys,json
d=json.load(sys.stdin)
print('TOP KEYS:', list(d.keys())[:15])
days = d.get('days', d.get('week',[]))
if days:
    day = days[0] if isinstance(days,list) else list(days.values())[0]
    print('DAY KEYS:', list(day.keys()) if isinstance(day,dict) else 'not dict')
    if isinstance(day,dict):
        print('panchang:', day.get('panchang',day.get('panchanga',{})))
        print('tithi:', day.get('tithi',''))
        print('vara:', day.get('vara',''))
        print('do:', str(day.get('do',''))[:80])
        print('avoid:', str(day.get('avoid',''))[:80])
        print('energy:', day.get('energy_label',''))
" 2>/dev/null
