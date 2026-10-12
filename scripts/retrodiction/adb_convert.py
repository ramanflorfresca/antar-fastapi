#!/usr/bin/env python3
"""
scripts/retrodiction/adb_convert.py — Astro-Databank XML export -> retrodiction CSVs.

Usage: python -I scripts/retrodiction/adb_convert.py <adb_export.xml> data/retrodiction

Writes people.csv and events.csv in the format scripts/retrodiction/run.py reads.
The ADB data is licensed (Astrodienst, time-limited; research_data is for astrological
research only, no record-level publication) — keep the XML and CSVs private
(data/retrodiction is gitignored). Needs pyswisseph.

Choices (fixed before looking at any result; changing them voids a run):
  people : Rodden AA or A, birth time + place present, Gregorian, born >= 1850,
           |lat| <= 66 (the harness uses Placidus houses, which fail at polar latitudes).
           Birth time is taken as UTC from ADB's jd_ut, so tz=0.
  events : only exact-day Gregorian dates (month/year-only dates are dropped).
           Work : Start Business -> business_start
           Work : New Career / New Job -> career_start
           Relationship : Marriage / Begin significant relationship -> relationship_began
           Relationship : Divorce dates / End significant relationship -> relationship_ended
"""
import csv, re, sys, collections
import xml.etree.ElementTree as ET
import swisseph as swe
SRC, OUT = sys.argv[1], sys.argv[2]
MAP = {"Work : Start Business": "business_start", "Work : New Career": "career_start",
       "Work : New Job": "career_start", "Relationship : Marriage": "relationship_began",
       "Relationship : Begin significant relationship": "relationship_began",
       "Relationship : Divorce dates": "relationship_ended",
       "Relationship : End significant relationship": "relationship_ended"}
def ll(s, pos, neg):
    m = re.fullmatch(r"(\d+)([a-z])(\d*)", s.strip())
    v = int(m.group(1)) + (int(m.group(3) or 0) / 60)
    return -v if m.group(2) == neg else v
stats = collections.Counter(); people = []; events = []
for _, el in ET.iterparse(SRC):
    if el.tag != "adb_entry": continue
    stats["entries"] += 1
    pid = el.get("adb_id"); pd = el.find("public_data")
    rr = (pd.findtext("roddenrating") or "").strip()
    bd = pd.find("bdata"); sb = bd.find("sbdate"); st = bd.find("sbtime"); pl = bd.find("place")
    evs = el.find("research_data/events")
    el_events = []
    if evs is not None:
        for e in evs.findall("event"):
            t = MAP.get(e.get("sevcode"))
            if not t: continue
            stats["mapped_events_all"] += 1
            d = e.find("event_data/sbdate")
            if d is None or d.get("ccalendar") != "g" or int(d.get("iday") or 0) == 0 or int(d.get("imonth") or 0) == 0:
                stats["event_dropped_imprecise"] += 1; continue
            el_events.append((t, f"{int(d.get('iyear')):04d}-{int(d.get('imonth')):02d}-{int(d.get('iday')):02d}"))
    el.clear()
    if rr not in ("AA", "A"): stats["not_AA_A"] += 1; continue
    if st is None or not st.get("jd_ut") or pl is None or sb.get("ccalendar") != "g": stats["no_time_or_place"] += 1; continue
    if int(sb.get("iyear")) < 1850: stats["born_pre1850"] += 1; continue
    if abs(ll(pl.get("slati"), "n", "s")) > 66: stats["polar_lat"] += 1; continue
    y, mo, d, h = swe.revjul(float(st.get("jd_ut")))
    hh = int(round(h * 60)); y2, mo2, d2 = int(y), int(mo), int(d)
    if hh >= 1440: hh -= 1440; d2 += 1  # rare rounding; refined below
    people.append(dict(id=pid, date=f"{y2:04d}-{mo2:02d}-{d2:02d}", time=f"{hh//60:02d}:{hh%60:02d}", tz=0,
                       lat=round(ll(pl.get("slati"), "n", "s"), 4), lon=round(ll(pl.get("slong"), "e", "w"), 4), rating=rr))
    for t, dt in el_events: events.append(dict(person=pid, type=t, date=dt, tol_days=92))
    stats["usable_people"] += 1
    if el_events: stats["people_with_mapped_events"] += 1
for n, rows, keys in (("people", people, ["id","date","time","tz","lat","lon","rating"]), ("events", events, ["person","type","date","tol_days"])):
    w = csv.DictWriter(open(f"{OUT}/{n}.csv", "w", newline=""), keys); w.writeheader(); w.writerows(rows)
print(dict(stats)); print(collections.Counter(e["type"] for e in events))
