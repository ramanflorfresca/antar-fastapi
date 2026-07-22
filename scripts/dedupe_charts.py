"""
scripts/dedupe_charts.py
Collapse duplicate charts onto one row per person.  SOFT delete only.

    ./venv311/bin/python scripts/dedupe_charts.py            # dry run
    ./venv311/bin/python scripts/dedupe_charts.py --apply

First run (2026-07-22) took the live base from 179 charts to 92. Most were
test/QA copies of the same few birth moments (one had nine, another eight).

Nothing is hard-deleted. Rows are marked deleted_at and given
parent_chart_id -> the keeper, so every table that referenced them still
resolves and the whole operation is reversible.

Two rules stop it destroying real data, both learned from this base:

  * SAME BIRTH MINUTE IS NOT THE SAME PERSON. One cluster held a Chilean and a
    Colombian born the same minute. Clusters are split on distinct signed-in
    users and on birth places more than 300km apart.
  * A COUNTRY CENTROID IS A PLACEHOLDER, NOT A PLACE. Comparing it by distance
    split one man into two people (his centroid row sits 360km from his real
    city), and ranking it as a valid geocode kept the placeholder over the real
    birth city. Centroid rows carry no location and group with anything sharing
    the birth minute.

Keeper priority: signed-in user > real geocode > has birth_city > protected >
has activity > most recent.
"""
import os, math, json
from dotenv import load_dotenv; load_dotenv("/Users/ramandeepsinghchadha/antarai/.env")
from supabase import create_client
from collections import defaultdict
APPLY = "--apply" in sys.argv
sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
CENTROIDS = {(20.5937,78.9629),(4.5709,-74.2973),(37.0902,-95.7129),(35.8617,104.1954)}

def km(a,b):
    (la1,lo1),(la2,lo2)=a,b
    p=math.pi/180
    return 12742*math.asin(min(1,math.sqrt(0.5-math.cos((la2-la1)*p)/2 +
        math.cos(la1*p)*math.cos(la2*p)*(1-math.cos((lo2-lo1)*p))/2)))

rows,page=[],0
while True:
    d=(sb.table("charts").select(
        "id,name,first_name,user_id,guest_session_id,birth_date,birth_time,birth_city,"
        "latitude,longitude,created_at,deleted_at,protected,daily_wow_cache,parent_chart_id"
    ).range(page*1000,page*1000+999).execute().data) or []
    rows+=d
    if len(d)<1000: break
    page+=1
live=[r for r in rows if not r.get("deleted_at")]

g=defaultdict(list)
for r in live: g[(r["birth_date"], str(r.get("birth_time"))[:5])].append(r)

def is_centroid(r):
    """A country centroid is a PLACEHOLDER, not a birth place.

    It must never act like a location: comparing it by distance split one
    person into two (Shashi's centroid row sits 360km from his Hyderabad rows),
    and ranking it as a valid geocode kept the placeholder over the real city.
    """
    try:
        lat,lng=float(r.get("latitude")),float(r.get("longitude"))
    except Exception:
        return True
    return any(abs(lat-c[0])<0.01 and abs(lng-c[1])<0.01 for c in CENTROIDS)


def split(cluster):
    """Same birth minute is NOT the same person. Split on distinct signed-in
    users, and on birth places too far apart to be a geocoding difference."""
    groups=[]
    for r in cluster:
        placed=False
        for grp in groups:
            u1={x.get("user_id") for x in grp if x.get("user_id")}
            u2=r.get("user_id")
            if u2 and u1 and u2 not in u1: continue
            # Placeholder coords carry no location information, so they group
            # with anything sharing the same birth minute rather than forcing a
            # split on a distance that means nothing.
            if not (is_centroid(r) or is_centroid(grp[0])):
                try:
                    d=km((float(grp[0]["latitude"]),float(grp[0]["longitude"])),
                         (float(r["latitude"]),float(r["longitude"])))
                except Exception: d=0
                if d>300: continue
            grp.append(r); placed=True; break
        if not placed: groups.append([r])
    return groups

def score(r):
    on_centroid=is_centroid(r)
    # A real birth place outranks the `protected` flag. Keeping a placeholder
    # because it happened to be flagged is precisely the corruption this
    # cleanup exists to remove.
    return (bool(r.get("user_id")), not on_centroid,
            bool((r.get("birth_city") or "").strip()), bool(r.get("protected")),
            bool(r.get("daily_wow_cache")), str(r.get("created_at") or ""))

keep_n=drop=0; plan=[]
for key,cluster in sorted(g.items()):
    for grp in split(cluster):
        keep_n+=1
        if len(grp)==1: continue
        grp=sorted(grp,key=score,reverse=True)
        keeper,losers=grp[0],grp[1:]
        drop+=len(losers)
        plan.append((key,keeper,losers))

print(f"{'APPLYING' if APPLY else 'DRY RUN'}")
print(f"live now {len(live)}  ->  after cleanup {len(live)-drop}   (soft-deleting {drop})")
print(f"distinct people identified: {keep_n}\n")
for key,keeper,losers in plan[:12]:
    who=keeper.get("name") or keeper.get("first_name") or "-"
    print(f"{key[0]} {key[1]}  KEEP {keeper['id'][:8]} {str(who)[:12]:13} "
          f"lat={keeper.get('latitude')} city={keeper.get('birth_city')} "
          f"user={'Y' if keeper.get('user_id') else '-'}  drop {len(losers)}")
if APPLY:
    for key,keeper,losers in plan:
        for l in losers:
            sb.table("charts").update(
                {"deleted_at":"now()","parent_chart_id":keeper["id"]}).eq("id",l["id"]).execute()
    print("\napplied. every dropped row keeps parent_chart_id -> its keeper, and is")
    print("soft-deleted only, so nothing that referenced it is orphaned.")

print("\n=== SAFETY CHECKS ===")
# 1. any signed-in user's chart being dropped?
dropped_with_user = [l for _,k,ls in plan for l in ls if l.get("user_id")]
print(f"1. signed-in users' charts in the drop list: {len(dropped_with_user)}")
for l in dropped_with_user:
    print("     !!", l["id"][:8], l.get("name"), l.get("user_id"))
# 2. the two different people born the same minute
for key,keeper,losers in plan:
    if key[0]=="2001-03-28":
        print("2. Santiago/Cali cluster -> KEEP", keeper["id"][:8], keeper.get("birth_city"),
              "drop", [l["id"][:8] for l in losers])
        break
else:
    print("2. Santiago/Cali cluster: correctly SPLIT into separate people (never compared)")
# 3. Shashi
for key,keeper,losers in plan:
    if key[0]=="1970-11-02":
        print(f"3. Shashi -> KEEP {keeper['id'][:8]} lat={keeper.get('latitude')} "
              f"city={keeper.get('birth_city')}  (dropping {len(losers)})")
# 4. every keeper still resolves
print(f"4. keepers total {len({k['id'] for _,k,_ in plan})}, "
      f"losers total {len({l['id'] for _,_,ls in plan for l in ls})}, overlap "
      f"{len({k['id'] for _,k,_ in plan} & {l['id'] for _,_,ls in plan for l in ls})}")
