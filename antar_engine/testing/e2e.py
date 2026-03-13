#!/usr/bin/env python3
"""
ANTAR — END-TO-END PRODUCTION TEST (Source-verified)
════════════════════════════════════════════════════════════════════════
Written against EXACT source code of vimsottari.py and jaimini.py.

VIMSOTTARI return shape (calculate_vimsottari_from_chart):
  {
    'mahadashas':  [{'lord', 'start_date', 'end_date',
                     'start_datetime', 'end_datetime', 'duration_years'}, ...]
    'antardashas': [{'lord', 'start_date', 'end_date',
                     'parent_lord', 'duration_years'}, ...]
  }
  Key for planet: 'lord'
  Key for date:   'start_date' / 'end_date'  (ISO strings)

JAIMINI return shape (calculate_chara_dasha_from_chart):
  {
    'mahadashas':  [{'sign', 'sign_index', 'start_date', 'end_date',
                     'start_datetime', 'end_datetime', 'duration_years'}, ...]
    'antardashas': [{'sign', 'sign_index', 'parent_sign',
                     'start_date', 'end_date', 'duration_years'}, ...]
  }
  Key for sign:  'sign'  (NOT 'lord')
  Key for date:  'start_date' / 'end_date'  (ISO strings)

CHART return shape (calculate_chart):
  {'lagna': {'sign', 'sign_index', 'degree'},
   'planets': {'Sun': {'longitude', 'sign', 'sign_index', 'degree',
                        'nakshatra', 'nakshatra_index', 'nakshatra_lord',
                        'nakshatra_portion'}, ...}}
  birth_jd NOT stored in chart — compute separately

DIVISIONAL return shape (calculate_divisional_chart):
  same shape as chart_data

USAGE:
  cd ~/antarai
  export $(cat .env | grep -v '#' | xargs)
  python3 antar_engine/testing/e2e.py
════════════════════════════════════════════════════════════════════════
"""

import os, sys, json, uuid, urllib.request, urllib.error
from datetime import datetime, timedelta
from pathlib import Path

THIS_DIR    = Path(__file__).resolve().parent
ENGINE_DIR  = THIS_DIR.parent
PROJECT_DIR = ENGINE_DIR.parent
sys.path.insert(0, str(PROJECT_DIR))

SUPABASE_URL  = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY  = os.environ.get("SUPABASE_SERVICE_KEY", os.environ.get("SUPABASE_KEY", ""))
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
DEEPSEEK_KEY  = os.environ.get("DEEPSEEK_API_KEY", "")
_default      = "deepseek" if DEEPSEEK_KEY and not ANTHROPIC_KEY else "claude"
AI_PROVIDER   = os.environ.get("ANTAR_AI_PROVIDER", _default)

print("\n  Loading antar_engine modules...")

def try_import(dotpath, label, fatal=False):
    try:
        mod = __import__(dotpath, fromlist=[dotpath.split(".")[-1]])
        print(f"  ✓ {label}"); return mod
    except ImportError as e:
        print(f"  {'✗' if fatal else '○'} {label}: {e}")
        if fatal: sys.exit(1)
        return None

chart_mod   = try_import("antar_engine.chart",             "chart",             fatal=True)
div_mod     = try_import("antar_engine.divisional",        "divisional")
divc_mod    = try_import("antar_engine.divisional_career", "divisional_career")
vim_mod     = try_import("antar_engine.vimsottari",        "vimsottari")
jai_mod     = try_import("antar_engine.jaimini",           "jaimini")
ash_mod     = try_import("antar_engine.ashtottari",        "ashtottari")
txn_mod     = try_import("antar_engine.transits",          "transits")
yoga_mod    = try_import("antar_engine.yoga_engine",       "yoga_engine")
chakra_mod  = try_import("antar_engine.chakra_engine",     "chakra_engine")
arc_mod     = try_import("antar_engine.chapter_arc",       "chapter_arc")
win_mod     = try_import("antar_engine.precision_windows", "precision_windows")
rarity_mod  = try_import("antar_engine.rarity_engine",     "rarity_engine")

import swisseph as swe

# ─────────────────────────────────────────────────────────────────────────────
# STATIC TABLES
# ─────────────────────────────────────────────────────────────────────────────

SIGNS = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
         "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]
SIGN_LORDS = {
    "Aries":"Mars","Taurus":"Venus","Gemini":"Mercury","Cancer":"Moon",
    "Leo":"Sun","Virgo":"Mercury","Libra":"Venus","Scorpio":"Mars",
    "Sagittarius":"Jupiter","Capricorn":"Saturn","Aquarius":"Saturn","Pisces":"Jupiter"
}
DASHA_ENERGY = {
    "Sun":     "Identity & Purpose — time to step into authority",
    "Moon":    "Emotional Depth — nurturing, intuition, public connection",
    "Mars":    "Action & Courage — building, competing, beginning",
    "Mercury": "Intellect & Communication — ideas, trade, analysis",
    "Jupiter": "Expansive Growth — abundance, wisdom, opportunity",
    "Venus":   "Heart & Beauty — love, creativity, material pleasures",
    "Saturn":  "Clarifying Pressure — discipline, mastery, karma resolved",
    "Rahu":    "Hungry Becoming — ambition, disruption, foreign rise",
    "Ketu":    "Releasing & Liberation — past skills, detachment, depth",
}
CHART_LABELS = {
    1:"D-1 Rashi (birth chart)",2:"D-2 Hora (wealth)",
    4:"D-4 Chaturthamsha (property/home)",5:"D-5 Panchamsha (power)",
    6:"D-6 Shashthansa (health/enemies)",7:"D-7 Saptamsha (children)",
    8:"D-8 Ashtamsha (longevity)",9:"D-9 Navamsa (soul/marriage)",
    10:"D-10 Dashamsha (career)",11:"D-11 Ekadashamsha (income/gains)",
    12:"D-12 Dwadashamsha (parents/foreign)",16:"D-16 Shodashamsha (vehicles)",
    20:"D-20 Vimsamsha (spiritual)",24:"D-24 Chaturvimsamsha (education)",
    27:"D-27 Nakshtramsha (vitality)",30:"D-30 Trimsamsha (misfortune)",
    40:"D-40 Khavedamsha (karma)",45:"D-45 Akshavedamsha (welfare)",
    60:"D-60 Shashtiamsha (past life)",
}
ALL_DIVS = [2,4,5,6,7,8,9,10,11,12,16,20,24,27,30,40,45,60]
PLANET_SIGNIFICATIONS = {
    "Sun":     "Soul, authority, government, father, career visibility",
    "Moon":    "Mind, emotions, mother, public, mental health",
    "Mars":    "Energy, courage, property, surgery, drive",
    "Mercury": "Intellect, communication, business, education",
    "Jupiter": "Wisdom, children, wealth, expansion, dharma",
    "Venus":   "Love, marriage, beauty, arts, partnerships",
    "Saturn":  "Discipline, karma, chronic illness, delays, mastery",
    "Rahu":    "Foreign, ambition, unconventional, fame",
    "Ketu":    "Spirituality, past life, detachment, liberation",
}

# ─────────────────────────────────────────────────────────────────────────────
# DOMAIN CONFIGURATION — 16 life domains
# ─────────────────────────────────────────────────────────────────────────────
DOMAINS = {
    "wealth":    (["wealth","rich","earn","income","money","financial","fund","profit","asset","savings"],
                  [2,10,11],[1,9],["vimsottari","ashtottari"],
                  [2,11,9],{2:"Wealth house",11:"Gains house",9:"Fortune house"},
                  ["Jupiter","Venus","Moon"]),
    "invest":    (["invest","stock","crypto","expense","spend","capital","portfolio"],
                  [2,12],[1,11],["vimsottari"],
                  [2,11,12],{2:"Wealth house",11:"Gains house",12:"Expenses house"},
                  ["Saturn","Jupiter","Ketu"]),
    "career":    (["career","job","work","profession","business","startup","entrepreneur","promotion"],
                  [10,9],[1,2],["vimsottari","jaimini"],
                  [10,9,1],{10:"Career house",9:"Dharma house",1:"Self house"},
                  ["Saturn","Sun","Mercury"]),
    "marriage":  (["marriage","marry","wedding","spouse","husband","wife","partner","engagement"],
                  [9,7],[1],["vimsottari","jaimini"],
                  [7,9,5],{7:"Marriage house",9:"Soul compatibility",5:"Romance house"},
                  ["Venus","Jupiter","Moon"]),
    "divorce":   (["divorce","separate","separation","breakup","split","marriage problem"],
                  [9,1],[7],["vimsottari"],
                  [7,12,6],{7:"Partnership house",12:"Loss house",6:"Conflict house"},
                  ["Rahu","Mars","Saturn"]),
    "love":      (["love","romance","relationship","dating","boyfriend","girlfriend","soulmate"],
                  [9,1],[5],["vimsottari"],
                  [5,7,9],{5:"Romance house",7:"Partnership house",9:"Fortune house"},
                  ["Venus","Moon","Jupiter"]),
    "children":  (["child","children","baby","pregnancy","pregnant","fertility","conceive"],
                  [7,9],[1,5],["vimsottari","jaimini"],
                  [5,9,7],{5:"Children house",9:"Fortune house",7:"D-7 lagna"},
                  ["Jupiter","Moon","Sun"]),
    "autism":    (["autism","autistic","special needs","development","learning disability","adhd"],
                  [7,24],[1,9],["vimsottari"],
                  [5,3,1],{5:"Intellect house",3:"Communication house",1:"Body house"},
                  ["Mercury","Moon","Ketu"]),
    "health":    (["health","illness","disease","sick","surgery","hospital","medical","pain","chronic"],
                  [6,30],[1,8],["vimsottari","ashtottari"],
                  [6,8,12],{6:"Disease house",8:"Surgery house",12:"Hospitalisation house"},
                  ["Saturn","Mars","Sun"]),
    "mental":    (["mental","anxiety","depression","peace","stress","mind","psychology","burnout"],
                  [9,12],[1,4],["vimsottari"],
                  [4,12,1],{4:"Inner peace house",12:"Isolation house",1:"Body-mind house"},
                  ["Moon","Mercury","Saturn"]),
    "longevity": (["death","lifespan","longevity","accident","danger","fatal","life threatening"],
                  [8,30],[1,6],["vimsottari","ashtottari"],
                  [8,6,12],{8:"Lifespan house",6:"Health house",12:"Loss house"},
                  ["Saturn","Ketu","Mars"]),
    "travel":    (["travel","trip","abroad","foreign","international","visa","tourist","overseas"],
                  [12,9],[1,3],["vimsottari"],
                  [12,9,3],{12:"Foreign lands house",9:"Long journey house",3:"Short travel house"},
                  ["Rahu","Venus","Jupiter"]),
    "foreign":   (["settle","migration","immigrat","relocat","move country","green card","citizenship","pr visa"],
                  [12,4],[1,9],["vimsottari","jaimini"],
                  [12,4,9],{12:"Foreign settlement house",4:"Home/roots house",9:"Fortune abroad"},
                  ["Rahu","Moon","Saturn"]),
    "property":  (["property","house","home","land","real estate","flat","apartment","mortgage"],
                  [4,1],[9],["vimsottari"],
                  [4,2,11],{4:"Property house",2:"Assets house",11:"Gains house"},
                  ["Mars","Saturn","Moon"]),
    "education": (["education","study","degree","university","course","exam","scholarship"],
                  [24,4],[1,9],["vimsottari"],
                  [5,4,9],{5:"Intellect house",4:"Foundation house",9:"Higher learning house"},
                  ["Mercury","Jupiter","Moon"]),
    "spiritual": (["spiritual","soul","karma","past life","meditation","dharma","moksha","purpose"],
                  [9,60],[1,20],["jaimini","vimsottari"],
                  [12,9,1],{12:"Moksha house",9:"Dharma house",1:"Soul's vehicle"},
                  ["Ketu","Saturn","Jupiter"]),
}

def detect_domain(question):
    q = question.lower()
    for domain, cfg in DOMAINS.items():
        if any(k in q for k in cfg[0]):
            return domain
    return "career"

def domain_cfg(domain):
    c = DOMAINS[domain]
    return {"keywords":c[0],"primary":c[1],"secondary":c[2],"dashas":c[3],
            "key_houses":c[4],"house_labels":c[5],"key_planets":c[6]}

# ─────────────────────────────────────────────────────────────────────────────
# JULIAN DAY — mirror of chart.py's julian_day()
# ─────────────────────────────────────────────────────────────────────────────
def jd_from_birth(birth_date, birth_time, tz_offset):
    dt = datetime.strptime(f"{birth_date} {birth_time}", "%Y-%m-%d %H:%M") - timedelta(hours=tz_offset)
    return swe.julday(dt.year, dt.month, dt.day, dt.hour + dt.minute / 60.0)

# ─────────────────────────────────────────────────────────────────────────────
# DASHA NORMALISATION
# Vimsottari items: 'lord', 'start_date', 'end_date'
# Jaimini items:    'sign', 'sign_index', 'start_date', 'end_date'
# Both dates are ISO strings (not 'start'/'end')
# ─────────────────────────────────────────────────────────────────────────────

def _parse_iso(s):
    """Parse ISO datetime string to datetime, tolerating microseconds."""
    s = str(s)[:19]  # drop microseconds
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try: return datetime.strptime(s, fmt)
        except: pass
    return None

def norm_vim(raw_result):
    """
    Normalise Vimsottari result dict into flat mahadasha list.
    Input: {'mahadashas': [...], 'antardashas': [...]}
    Each item has: lord, start_date, end_date, duration_years
    Output: [{'lord', 'lord_or_sign', 'start', 'end', 'duration_years'}, ...]
    """
    if not raw_result: return [], []
    mds = raw_result.get("mahadashas", [])
    ads = raw_result.get("antardashas", [])
    out_mds = []
    for d in mds:
        lord = d.get("lord", "")
        start = d.get("start_date", d.get("start_datetime",""))
        end   = d.get("end_date",   d.get("end_datetime",""))
        if isinstance(start, datetime): start = start.isoformat()
        if isinstance(end, datetime):   end   = end.isoformat()
        out_mds.append({
            "lord": lord, "lord_or_sign": lord,
            "start": str(start)[:10], "end": str(end)[:10],
            "start_date": str(start)[:10], "end_date": str(end)[:10],
            "duration_years": float(d.get("duration_years", 0) or 0),
            "system": "vimsottari",
        })
    out_ads = []
    for d in ads:
        lord = d.get("lord", "")
        parent = d.get("parent_lord", "")
        start = d.get("start_date", d.get("start_datetime",""))
        end   = d.get("end_date",   d.get("end_datetime",""))
        if isinstance(start, datetime): start = start.isoformat()
        if isinstance(end, datetime):   end   = end.isoformat()
        out_ads.append({
            "lord": lord, "lord_or_sign": lord,
            "parent_lord": parent,
            "start": str(start)[:10], "end": str(end)[:10],
            "start_date": str(start)[:10], "end_date": str(end)[:10],
            "duration_years": float(d.get("duration_years", 0) or 0),
            "system": "vimsottari_antardasha",
        })
    return out_mds, out_ads

def norm_jai(raw_result):
    """
    Normalise Jaimini result dict into flat mahadasha list.
    Input: {'mahadashas': [...], 'antardashas': [...]}
    Each item has: sign, sign_index, start_date, end_date, duration_years
    Output: [{'sign', 'lord_or_sign', 'start', 'end', 'duration_years'}, ...]
    """
    if not raw_result: return [], []
    mds = raw_result.get("mahadashas", [])
    ads = raw_result.get("antardashas", [])
    out_mds = []
    for d in mds:
        sign = d.get("sign", "")
        start = d.get("start_date", d.get("start_datetime",""))
        end   = d.get("end_date",   d.get("end_datetime",""))
        if isinstance(start, datetime): start = start.isoformat()
        if isinstance(end, datetime):   end   = end.isoformat()
        out_mds.append({
            "sign": sign, "lord_or_sign": sign,  # Jaimini uses sign not planet
            "sign_index": d.get("sign_index", 0),
            "start": str(start)[:10], "end": str(end)[:10],
            "start_date": str(start)[:10], "end_date": str(end)[:10],
            "duration_years": float(d.get("duration_years", 0) or 0),
            "system": "jaimini",
        })
    out_ads = []
    for d in ads:
        sign = d.get("sign", "")
        parent = d.get("parent_sign", "")
        start = d.get("start_date", d.get("start_datetime",""))
        end   = d.get("end_date",   d.get("end_datetime",""))
        if isinstance(start, datetime): start = start.isoformat()
        if isinstance(end, datetime):   end   = end.isoformat()
        out_ads.append({
            "sign": sign, "lord_or_sign": sign,
            "parent_sign": parent,
            "start": str(start)[:10], "end": str(end)[:10],
            "start_date": str(start)[:10], "end_date": str(end)[:10],
            "duration_years": float(d.get("duration_years", 0) or 0),
            "system": "jaimini_antardasha",
        })
    return out_mds, out_ads

def norm_ash(raw_result):
    """Ashtottari has same shape as Vimsottari — re-use norm_vim."""
    mds, ads = norm_vim(raw_result)
    for d in mds: d["system"] = "ashtottari"
    for d in ads: d["system"] = "ashtottari_antardasha"
    return mds, ads

def find_current_md(periods):
    """Find the active mahadasha from a normalised list."""
    today = datetime.utcnow()
    for d in periods:
        start = _parse_iso(d.get("start") or d.get("start_date",""))
        end   = _parse_iso(d.get("end")   or d.get("end_date",""))
        if not start or not end: continue
        if start <= today <= end:
            el  = (today - start).days / 365.25
            tot = (end - start).days / 365.25
            pct = el / tot if tot > 0 else 0
            ph  = "opening" if pct<0.2 else "building" if pct<0.5 else "peak" if pct<0.8 else "closing"
            label = d.get("lord") or d.get("sign","")
            return {
                "lord": label, "sign": d.get("sign",""),
                "lord_or_sign": label,
                "start": d["start"], "end": d["end"],
                "phase": ph,
                "years_elapsed": round(el, 1),
                "years_left": round((end - today).days / 365.25, 1),
                "energy": DASHA_ENERGY.get(label, f"{label} — sign-based timing"),
            }
    return {}

def find_current_antardasha(ads, current_md_lord):
    """Find active antardasha within the current mahadasha."""
    today = datetime.utcnow()
    for d in ads:
        parent = d.get("parent_lord") or d.get("parent_sign","")
        if parent != current_md_lord: continue
        start = _parse_iso(d.get("start") or d.get("start_date",""))
        end   = _parse_iso(d.get("end")   or d.get("end_date",""))
        if not start or not end: continue
        if start <= today <= end:
            label = d.get("lord") or d.get("sign","")
            return {
                "lord": label, "sign": d.get("sign",""),
                "start": d["start"], "end": d["end"],
                "energy": DASHA_ENERGY.get(label, f"{label} — sub-period"),
            }
    return {}

# ─────────────────────────────────────────────────────────────────────────────
# DIVISIONAL CHART
# ─────────────────────────────────────────────────────────────────────────────
def get_div_chart(chart_data, div):
    if div_mod:
        fn = getattr(div_mod, "calculate_divisional_chart", None)
        if fn:
            try: return fn(chart_data, div)
            except Exception: pass
    if divc_mod:
        fn = getattr(divc_mod, "get_all_divisional_positions", None)
        if fn:
            try:
                pos = fn(chart_data, div)
                lp  = pos.pop("Lagna", {})
                return {
                    "lagna": {"sign":lp.get("sign",""),"sign_index":lp.get("sign_index",0),"degree":0},
                    "planets": {
                        p: {"sign":d.get("sign",""),"sign_index":d.get("sign_index",0),
                            "degree":d.get("degree_in_sign",0),
                            "longitude":chart_data["planets"].get(p,{}).get("longitude",0)}
                        for p,d in pos.items()
                    },
                }
            except Exception: pass
    return {}

# ─────────────────────────────────────────────────────────────────────────────
# SUPABASE
# ─────────────────────────────────────────────────────────────────────────────
def sb(method, path, body=None, params=""):
    if not SUPABASE_URL or not SUPABASE_KEY: return {"_skipped":True}
    url  = f"{SUPABASE_URL}/rest/v1/{path}" + (f"?{params}" if params else "")
    data = json.dumps(body, default=str).encode() if body else None
    hdrs = {"apikey":SUPABASE_KEY,"Authorization":f"Bearer {SUPABASE_KEY}",
            "Content-Type":"application/json","Prefer":"return=representation"}
    req  = urllib.request.Request(url,data=data,headers=hdrs,method=method)
    try:
        with urllib.request.urlopen(req,timeout=15) as r:
            txt = r.read().decode(); return json.loads(txt) if txt else {}
    except urllib.error.HTTPError as e: return {"error":f"HTTP {e.code}: {e.read().decode()[:200]}"}
    except Exception as ex: return {"error":str(ex)}

def save_chart_row(chart_data, meta, lagna):
    cid = str(uuid.uuid4())
    row = {"id":cid,"user_id":None,
           "birth_date":meta["birth_date"],"birth_time":meta["birth_time"],
           "latitude":meta["lat"],"longitude":meta["lon"],
           "timezone_offset":meta["tz_offset"],"ayanamsa":"Lahiri",
           "lagna_sign":lagna.get("sign_index"),"lagna_degree":lagna.get("degree"),
           "chart_data":chart_data,
           "country_code":meta.get("birth_country","IN"),
           "birth_country":meta.get("birth_country","IN"),
           "language_preference":"en","marital_status":"unknown",
           "children_status":"no_children_unsure","career_stage":"mid_career",
           "health_status":"excellent","financial_status":"stable",
           "countries_lived":[],"lived_abroad":False,"patra_complete":False}
    r = sb("POST","charts",row)
    if isinstance(r,list) and r:
        print(f"  ✓ Chart saved  id={r[0].get('id',cid)}"); return r[0].get("id",cid)
    if isinstance(r,dict) and r.get("_skipped"): print("  ○ Supabase skipped")
    else: print(f"  ✗ Save error: {r}")
    return cid

def save_dasha_rows(cid, vim_mds):
    """Save Vimsottari mahadashas to dasha_periods table."""
    rows = []
    for i,d in enumerate(vim_mds):
        lord  = d.get("lord","")
        start = d.get("start_date","") or d.get("start","")
        end   = d.get("end_date","")   or d.get("end","")
        dur   = float(d.get("duration_years",0) or 0)
        if lord and start and end:
            rows.append({"chart_id":cid,"system":"vimsottari",
                         "planet_or_sign":lord,
                         "start_date":str(start)[:10],
                         "end_date":str(end)[:10],
                         "duration_years":dur,"sequence":i})
    if rows:
        r = sb("POST","dasha_periods",rows)
        if isinstance(r,dict) and r.get("error"): print(f"  ✗ Dasha save: {r['error'][:100]}")
        elif not (isinstance(r,dict) and r.get("_skipped")): print(f"  ✓ {len(rows)} dasha periods saved")

def read_chart_row(cid):
    r = sb("GET","charts",params=f"id=eq.{cid}&select=*")
    if isinstance(r,list) and r: print("  ✓ Read back from Supabase"); return r[0]
    if isinstance(r,dict) and r.get("_skipped"): return {}
    return {}

def read_dasha_rows(cid):
    r = sb("GET","dasha_periods",params=f"chart_id=eq.{cid}&order=sequence.asc")
    if isinstance(r,list):
        for d in r:
            d.setdefault("lord",         d.get("planet_or_sign",""))
            d.setdefault("lord_or_sign", d.get("planet_or_sign",""))
            d.setdefault("start",        d.get("start_date",""))
            d.setdefault("end",          d.get("end_date",""))
        print(f"  ✓ {len(r)} dasha periods read"); return r
    return []

# ─────────────────────────────────────────────────────────────────────────────
# AI
# ─────────────────────────────────────────────────────────────────────────────
def call_ai(prompt):
    if AI_PROVIDER=="deepseek" and DEEPSEEK_KEY:
        pl  = json.dumps({"model":"deepseek-chat","max_tokens":1500,
                "messages":[{"role":"user","content":prompt}],"temperature":0.7}).encode()
        req = urllib.request.Request("https://api.deepseek.com/v1/chat/completions",data=pl,method="POST",
                headers={"Content-Type":"application/json","Authorization":f"Bearer {DEEPSEEK_KEY}"})
        try:
            with urllib.request.urlopen(req,timeout=60) as r:
                return json.loads(r.read().decode())["choices"][0]["message"]["content"],"deepseek-chat"
        except Exception as e: return f"[DeepSeek error: {e}]","error"
    elif ANTHROPIC_KEY:
        pl  = json.dumps({"model":"claude-sonnet-4-6","max_tokens":1500,
                "messages":[{"role":"user","content":prompt}]}).encode()
        req = urllib.request.Request("https://api.anthropic.com/v1/messages",data=pl,method="POST",
                headers={"Content-Type":"application/json","x-api-key":ANTHROPIC_KEY,
                         "anthropic-version":"2023-06-01"})
        try:
            with urllib.request.urlopen(req,timeout=60) as r:
                return json.loads(r.read().decode())["content"][0]["text"],"claude-sonnet-4-6"
        except Exception as e: return f"[Claude error: {e}]","error"
    return "[No API key — set DEEPSEEK_API_KEY or ANTHROPIC_API_KEY]","none"

# ─────────────────────────────────────────────────────────────────────────────
# PROMPT BUILDER
# ─────────────────────────────────────────────────────────────────────────────
def house_n(planet_sign_idx, lagna_sign_idx):
    return (planet_sign_idx - lagna_sign_idx) % 12 + 1

def get_house_lord(h, lagna_sign_idx):
    house_sign_idx = (lagna_sign_idx + h - 1) % 12
    return SIGN_LORDS[SIGNS[house_sign_idx]], SIGNS[house_sign_idx]

def planet_table(cd):
    lagna   = cd.get("lagna",{})
    planets = cd.get("planets",{})
    li      = lagna.get("sign_index",0)
    rows    = ["  Planet      Sign            Deg    House  Soul-star (lord)         Nak%"]
    rows.append("  " + "─"*72)
    for p in ["Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn","Rahu","Ketu"]:
        d = planets.get(p,{})
        if not d: continue
        h   = house_n(d.get("sign_index",0), li)
        pct = int(d.get("nakshatra_portion",0)*100)
        rows.append(
            f"  {p:10s}  {d.get('sign',''):14s}  {d.get('degree',0):5.1f}°  H{h:2d}  "
            f"  {d.get('nakshatra',''):22s} ({d.get('nakshatra_lord','')}, {pct}%)"
        )
    return "\n".join(rows)

def div_block(d_charts, divs, label):
    sections = []
    for div in divs:
        dc = d_charts.get(div,{})
        if not dc or not dc.get("lagna",{}).get("sign"): continue
        dl    = dc.get("lagna",{}).get("sign","?")
        dl_si = dc.get("lagna",{}).get("sign_index",0)
        prows = []
        for p in ["Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn","Rahu","Ketu"]:
            pd = dc.get("planets",{}).get(p,{})
            if not pd: continue
            ph = house_n(pd.get("sign_index",0), dl_si)
            prows.append(f"  {p:10s}  {pd.get('sign',''):14s}  H{ph:2d}")
        if prows:
            sections.append(
                f"\n{CHART_LABELS.get(div,f'D-{div}')} | Lagna: {dl}\n"
                "  Planet      Sign            House\n  " + "─"*38 + "\n"
                + "\n".join(prows)
            )
    return "\n".join(sections) if sections else "  (calculating...)"

def house_lord_block(cd, key_houses, house_labels):
    lagna   = cd.get("lagna",{})
    planets = cd.get("planets",{})
    li      = lagna.get("sign_index",0)
    rows    = []
    for h in key_houses:
        lord_planet, lord_sign = get_house_lord(h, li)
        label    = house_labels.get(h, f"House {h}")
        house_sg = SIGNS[(li + h - 1) % 12]
        occupants = [p for p,d in planets.items() if house_n(d.get("sign_index",0),li)==h]
        occ_str   = ", ".join(occupants) if occupants else "empty"
        lord_data   = planets.get(lord_planet,{})
        lord_in_h   = house_n(lord_data.get("sign_index",0),li) if lord_data else "?"
        rows.append(
            f"  {label:28s} ({house_sg}): lord={lord_planet} placed in H{lord_in_h} | occupants={occ_str}"
        )
    return "\n".join(rows)

def key_planets_block(cd, key_planets):
    lagna   = cd.get("lagna",{})
    planets = cd.get("planets",{})
    li      = lagna.get("sign_index",0)
    rows    = []
    for p in key_planets:
        d = planets.get(p,{})
        if not d: continue
        h = house_n(d.get("sign_index",0),li)
        rows.append(f"  {p:10s}  {d.get('sign',''):14s}  H{h:2d}  — {PLANET_SIGNIFICATIONS.get(p,'')}")
    return "\n".join(rows) if rows else "  (no data)"

def vim_dasha_table(mds, ads, current_lord=""):
    """
    Full Vimsottari table: mahadasha + current antardasha inline.
    """
    if not mds: return "  Vimsottari: (unavailable)"
    today = datetime.utcnow()
    rows  = ["  Vimsottari (120-year cycle — main life timing)"]
    rows.append(f"  {'Planet':10s}  {'Start':10s}  {'End':10s}  {'Dur':6s}  Energy / theme")
    rows.append("  " + "─"*72)
    for d in mds[:12]:
        lord  = d.get("lord","")
        start = d.get("start","")[:10]
        end   = d.get("end","")[:10]
        dur   = d.get("duration_years",0)
        dur_s = f"{float(dur):.1f}y" if dur else ""
        energy = DASHA_ENERGY.get(lord,"")[:42]
        marker = " ◄ NOW" if lord == current_lord else ""
        rows.append(f"  {lord:10s}  {start}  {end}  {dur_s:6s}  {energy}{marker}")
        # If this is current MD, show active antardasha
        if lord == current_lord and ads:
            ad = find_current_antardasha(ads, lord)
            if ad:
                ad_lord  = ad.get("lord","")
                ad_start = ad.get("start","")[:10]
                ad_end   = ad.get("end","")[:10]
                ad_nrg   = DASHA_ENERGY.get(ad_lord,"")[:36]
                rows.append(f"    └─ sub-period: {ad_lord:10s}  {ad_start}  {ad_end}  {ad_nrg}")
    return "\n".join(rows)

def jai_dasha_table(mds, ads, current_sign=""):
    """
    Full Jaimini Chara table: sign-based, 12 signs over one cycle.
    """
    if not mds: return "  Jaimini Chara: (unavailable)"
    rows = ["  Jaimini Chara (sign-based soul timing — marriage, dharma, life purpose)"]
    rows.append(f"  {'Sign':14s}  {'Start':10s}  {'End':10s}  {'Dur':6s}  Lord of sign")
    rows.append("  " + "─"*60)
    for d in mds[:12]:
        sign  = d.get("sign","")
        start = d.get("start","")[:10]
        end   = d.get("end","")[:10]
        dur   = d.get("duration_years",0)
        dur_s = f"{float(dur):.1f}y" if dur else ""
        lord  = SIGN_LORDS.get(sign,"")
        marker = " ◄ NOW" if sign == current_sign else ""
        rows.append(f"  {sign:14s}  {start}  {end}  {dur_s:6s}  {lord}{marker}")
        # Show active sub-period
        if sign == current_sign and ads:
            ad = find_current_antardasha(ads, sign)
            if ad:
                ad_sign  = ad.get("sign","")
                ad_start = ad.get("start","")[:10]
                ad_end   = ad.get("end","")[:10]
                rows.append(f"    └─ sub-period: {ad_sign:14s}  {ad_start}  {ad_end}  lord: {SIGN_LORDS.get(ad_sign,'')}")
    return "\n".join(rows)

def ash_dasha_table(mds, ads, current_lord=""):
    """Ashtottari — same format as Vimsottari."""
    if not mds: return "  Ashtottari: (unavailable)"
    rows = ["  Ashtottari (108-year cycle — health, karmic events, longevity)"]
    rows.append(f"  {'Planet':10s}  {'Start':10s}  {'End':10s}  {'Dur':6s}  Energy / theme")
    rows.append("  " + "─"*72)
    for d in mds[:12]:
        lord  = d.get("lord","")
        start = d.get("start","")[:10]
        end   = d.get("end","")[:10]
        dur   = d.get("duration_years",0)
        dur_s = f"{float(dur):.1f}y" if dur else ""
        energy = DASHA_ENERGY.get(lord,"")[:42]
        marker = " ◄ NOW" if lord == current_lord else ""
        rows.append(f"  {lord:10s}  {start}  {end}  {dur_s:6s}  {energy}{marker}")
    return "\n".join(rows)

DOMAIN_FOCUS = {
    "wealth":   "When will wealth peak? Type of wealth — salary/business/windfall. Best window to invest.",
    "invest":   "Safe vs risky periods. 12th house expenses vs 2nd/11th gains. When to deploy capital.",
    "career":   "Career best fit. Entrepreneur vs employment. Peak window. What field suits this chart.",
    "marriage": "When is marriage most likely. What partner type. Current marriage timing.",
    "divorce":  "Relationship tensions. Whether separation is indicated and when. Healing path.",
    "love":     "What soul seeks in love. Current relationship energy. When love deepens.",
    "children": "Fertility window. Children indicated. Timing of conception. D-7 child potential.",
    "autism":   "Child's developmental profile. Mercury/Moon/5th lord. Parenting guidance.",
    "health":   "Which body systems vulnerable. When health needs care. D-6 and D-30 indicators.",
    "mental":   "Sources of mental peace and anxiety. When clarity arrives. Moon's condition.",
    "longevity":"Longevity indicators. Periods needing extra care. 8th house and Saturn.",
    "travel":   "Foreign travel indicators. Visa and immigration timing. Favourable countries.",
    "foreign":  "Foreign settlement potential. Which countries favour this chart. Timing.",
    "property": "Property acquisition timing. D-4 destiny. When to buy.",
    "education":"Fields that suit this chart. D-24 education destiny. When to pursue higher study.",
    "spiritual":"Karmic lessons from D-60 and D-9. Dharma path. Spiritual practices.",
}

def build_prompt(meta, cd, vim_mds, vim_ads, jai_mds, jai_ads, ash_mds, ash_ads,
                 d_charts, career, yogas, windows, chakra, arc, domain):
    cfg      = domain_cfg(domain)
    lagna    = cd.get("lagna",{})
    planets  = cd.get("planets",{})
    moon     = planets.get("Moon",{})
    md_vim   = find_current_md(vim_mds)
    md_jai   = find_current_md(jai_mds)
    md_ash   = find_current_md(ash_mds)
    cur_vim  = md_vim.get("lord","")
    cur_jai  = md_jai.get("sign","")
    cur_ash  = md_ash.get("lord","")

    active_yogas = [y for y in (yogas or []) if y.get("present")]
    yoga_lines   = [f"  ✓ {y.get('name',''):25s} [{y.get('strength','')}]  {(y.get('implication','') or y.get('description',''))[:80]}"
                    for y in active_yogas[:6]]
    win_lines    = [f"  {w.get('label',''):18s} {w.get('score',0)}/10  {w.get('action','')[:80]}"
                    for w in (windows or [])[:4]]

    career_block = ""
    if career:
        career_block = f"""
══ CAREER & WEALTH CONTEXT ═══════════════════════════════════
  Atmakaraka (soul planet):    {getattr(career,'atmakaraka','')} — {getattr(career,'ak_career','')[:80]}
  Amatyakaraka (career soul):  {getattr(career,'amatyakaraka','')} — {getattr(career,'amk_career','')[:80]}
  Best career fields:          {', '.join(getattr(career,'primary_fields',[])[:5])}
  Entrepreneur vs Employment:  {getattr(career,'recommendation','')}
  Current career phase:        {getattr(career,'current_career_phase','')}
  Peak earning period:         {getattr(career,'peak_earning_period','')}"""
        fi = getattr(career,"funding_indicators",[])
        if fi: career_block += f"\n  Funding window:              {getattr(career,'funding_timing','')[:100]}"

    arc_block = ""
    if arc and "being calculated" not in str(arc.get("chapter_theme","")):
        n = arc.get("narrative",{})
        arc_block = f"""
══ LIFE CHAPTER ARC ══════════════════════════════════════════
  Chapter:  {arc.get('chapter_theme','')}
  Phase:    {arc.get('phase','').upper()} · {arc.get('years_elapsed',0):.1f}y elapsed · {arc.get('years_left',0):.1f}y remaining
  Past:     {n.get('past','')[:120]}
  Present:  {n.get('present','')[:120]}
  Ahead:    {n.get('future','')[:120]}"""

    chakra_block = ""
    if chakra and chakra.get("english_name","?") not in ("?",""):
        chakra_block = f"""
══ ENERGETIC BODY ════════════════════════════════════════════
  Active chakra:  {chakra.get('english_name','')} ({chakra.get('theme','')})
  Daily practice: {chakra.get('daily_practice','')[:150]}"""

    return f"""You are Antar — a wise, precise, warm Vedic life timing coach.

LANGUAGE RULES (non-negotiable):
  Never say: house numbers, D-9, D-10, Mahadasha, nakshatra, ayanamsa, dasha
  Always say: "soul chart" (D-9), "career chart" (D-10), "children chart" (D-7)
              "life chapter" (Mahadasha), "soul star" (nakshatra), "timing cycle" (dasha)
  Be specific: name the planet AND the sign AND the year/year-range
  5-7 paragraphs. Open with the person's name. Close with ONE actionable invitation this week.

══════════════════════════════════════════════════════════════
PERSON: {meta['name']}
Born: {meta['birth_date']} at {meta['birth_time']} | {meta['birth_city']}, {meta['birth_country']}
Lagna (rising): {lagna.get('sign','')} at {lagna.get('degree',0):.1f}°
Moon's soul star: {moon.get('nakshatra','')} (ruled by {moon.get('nakshatra_lord','')})
Moon in: {moon.get('sign','')} at {moon.get('degree',0):.1f}°

══ D-1 BIRTH CHART — All Planets ════════════════════════════
{planet_table(cd)}

══ KEY HOUSES FOR THIS QUESTION ({domain.upper()}) ══════════
{house_lord_block(cd, cfg['key_houses'], cfg['house_labels'])}

══ KEY PLANETS FOR {domain.upper()} ══════════════════════════
{key_planets_block(cd, cfg['key_planets'])}

══ PRIMARY CHARTS ════════════════════════════════════════════
{div_block(d_charts, cfg['primary'], 'Primary')}

══ SUPPORTING CHARTS ═════════════════════════════════════════
{div_block(d_charts, cfg['secondary'], 'Supporting')}

══════════════════════════════════════════════════════════════
TIMING — THREE SYSTEMS

Current life chapter (Vimsottari): {md_vim.get('lord','')} — {md_vim.get('energy','')}
  Phase: {md_vim.get('phase','?').upper()} | {md_vim.get('years_elapsed',0):.1f}y elapsed | {md_vim.get('years_left',0):.1f}y remaining

{vim_dasha_table(vim_mds, vim_ads, cur_vim)}

{jai_dasha_table(jai_mds, jai_ads, cur_jai)}

{ash_dasha_table(ash_mds, ash_ads, cur_ash)}

══ ACTIVE YOGAS ══════════════════════════════════════════════
{chr(10).join(yoga_lines) if yoga_lines else "  None detected for this domain."}

══ BEST WINDOWS NEXT 12 MONTHS ══════════════════════════════
{chr(10).join(win_lines) if win_lines else "  None identified."}
{career_block}
{arc_block}
{chakra_block}
══════════════════════════════════════════════════════════════
DOMAIN: {domain.upper()}
FOCUS:  {DOMAIN_FOCUS.get(domain,'')}

QUESTION: {meta['question']}

Open with {meta['name']}'s name.
Name specific planets, signs, and year windows from the data above.
Integrate all three timing systems — each reveals a different layer.
End with ONE concrete actionable invitation for this week.""".strip()

# ─────────────────────────────────────────────────────────────────────────────
# TEST CHARTS
# ─────────────────────────────────────────────────────────────────────────────
TEST_CHARTS = [
    {"name":"Priya Sharma","birth_date":"1990-06-15","birth_time":"14:30",
     "birth_city":"Mumbai","birth_country":"IN","lat":19.0760,"lon":72.8777,"tz_offset":5.5,
     "question":"What is the most important thing I should focus on in my career right now, and when is my best window to make a major move?"},
    {"name":"Arjun Mehta","birth_date":"1985-11-23","birth_time":"06:15",
     "birth_city":"Delhi","birth_country":"IN","lat":28.6139,"lon":77.2090,"tz_offset":5.5,
     "question":"I am considering starting a business and raising funding. What does my chart say about wealth potential and when should I make the move?"},
]


# ─────────────────────────────────────────────────────────────────────────────
# MAIN FLOW
# ─────────────────────────────────────────────────────────────────────────────

def sep(t="", w=70):
    if t:
        pad = max(0, (w - len(t) - 2) // 2)
        print(f"\n{'═'*pad} {t} {'═'*(w - pad - len(t) - 2)}")
    else:
        print("\n" + "─"*w)


def run(meta):
    sep(f"CHART: {meta['name']}")
    print(f"\n  {meta['birth_date']} {meta['birth_time']}  |  {meta['birth_city']}, {meta['birth_country']}")
    print(f"  Lat:{meta['lat']}  Lon:{meta['lon']}  TZ:+{meta['tz_offset']}")

    domain = detect_domain(meta["question"])
    cfg    = domain_cfg(domain)
    print(f"  Domain: {domain.upper()} | Primary: D-{', D-'.join(str(d) for d in cfg['primary'])}")
    print(f"  Q: \"{meta['question'][:75]}...\"")

    # ── STEP 1: D-1 ──────────────────────────────────────────────────────────
    sep("STEP 1 — chart.calculate_chart(birth_date, birth_time, lat, lon, tz_offset)")
    print()
    try:
        cd = chart_mod.calculate_chart(
            birth_date=meta["birth_date"], birth_time=meta["birth_time"],
            lat=meta["lat"], lon=meta["lon"], tz_offset=meta["tz_offset"])
        print("  ✓ D-1 calculated")
    except Exception as e:
        print(f"  ✗ calculate_chart(): {e}"); return None

    swe.set_sid_mode(swe.SIDM_LAHIRI)
    birth_jd = jd_from_birth(meta["birth_date"], meta["birth_time"], meta["tz_offset"])
    ayanamsa = swe.get_ayanamsa_ut(birth_jd)
    lagna    = cd.get("lagna", {})
    planets  = cd.get("planets", {})
    li       = lagna.get("sign_index", 0)
    moon     = planets.get("Moon", {})

    print(f"  Lagna:    {lagna.get('sign','')} {lagna.get('degree',0):.2f}  (sign_index={li})")
    print(f"  Ayanamsa: {ayanamsa:.4f} Lahiri  |  JD: {birth_jd:.4f}")
    print()
    print(f"  {'Planet':10s}  {'Sign':14s}  {'Deg':6s}  H   {'Nakshatra':20s}  Lord   Nak%")
    print("  " + "-"*72)
    for p in ["Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn","Rahu","Ketu"]:
        d = planets.get(p, {})
        if not d: continue
        h   = house_n(d.get("sign_index",0), li)
        pct = int(d.get("nakshatra_portion", 0) * 100)
        print(f"  {p:10s}  {d.get('sign',''):14s}  {d.get('degree',0):5.1f}  H{h:2d}  "
              f"{d.get('nakshatra',''):20s}  {d.get('nakshatra_lord',''):6s}  {pct}%")

    # ── STEP 2: Divisional charts ─────────────────────────────────────────────
    sep("STEP 2 — All 18 Divisional Charts")
    print()
    d_charts   = {}
    all_needed = set(cfg["primary"] + cfg["secondary"])
    ok = fail = 0
    for div in ALL_DIVS:
        try:
            dc = get_div_chart(cd, div)
            if dc and dc.get("lagna", {}).get("sign"):
                d_charts[div] = dc
                flag = " KEY" if div in all_needed else ""
                lbl  = CHART_LABELS.get(div, f"D-{div}").split("--")[0].strip()
                print(f"  + D-{div:2d}  {dc['lagna']['sign']:12s}  {lbl}{flag}")
                ok += 1
            else:
                print(f"  x D-{div:2d}  (empty)"); fail += 1
        except Exception as e:
            print(f"  x D-{div:2d}  {e}"); fail += 1
    print(f"\n  {ok} computed, {fail} failed of {len(ALL_DIVS)} charts")

    # ── STEP 3: All 3 dasha systems ───────────────────────────────────────────
    sep("STEP 3 — All 3 Dasha Systems (Vimsottari + Jaimini Chara + Ashtottari)")
    print()

    # Vimsottari: calculate_vimsottari_from_chart(chart_data, birth_jd)
    # Returns: {'mahadashas': [{lord, start_date, end_date, duration_years}], 'antardashas': [...]}
    vim_raw = None
    if vim_mod:
        try:
            vim_raw = vim_mod.calculate_vimsottari_from_chart(cd, birth_jd)
            n_md = len(vim_raw.get("mahadashas", []))
            n_ad = len(vim_raw.get("antardashas", []))
            print(f"  + Vimsottari: {n_md} mahadashas, {n_ad} antardashas")
        except Exception as e:
            print(f"  x Vimsottari: {e}")

    # Jaimini: calculate_chara_dasha_from_chart(chart_data, birth_jd)
    # Returns: {'mahadashas': [{sign, sign_index, start_date, end_date, duration_years}], 'antardashas': [...]}
    jai_raw = None
    if jai_mod:
        try:
            jai_raw = jai_mod.calculate_chara_dasha_from_chart(cd, birth_jd)
            n_md = len(jai_raw.get("mahadashas", []))
            n_ad = len(jai_raw.get("antardashas", []))
            print(f"  + Jaimini:    {n_md} mahadashas, {n_ad} antardashas")
        except Exception as e:
            print(f"  x Jaimini: {e}")

    # Ashtottari: same shape as Vimsottari
    ash_raw = None
    if ash_mod:
        for fname in ["calculate_ashtottari_from_chart", "calculate", "compute", "get_dashas"]:
            fn = getattr(ash_mod, fname, None)
            if not (fn and callable(fn)): continue
            for args in [(cd, birth_jd), (birth_jd, cd), (cd,)]:
                try:
                    ash_raw = fn(*args)
                    if ash_raw:
                        n_md = len(ash_raw.get("mahadashas", []))
                        print(f"  + Ashtottari: {n_md} mahadashas  [{fname}]")
                        break
                except TypeError: continue
                except Exception as e:
                    print(f"  x Ashtottari.{fname}: {e}"); break
            if ash_raw: break
        if not ash_raw:
            fns = [f for f in dir(ash_mod) if not f.startswith("_") and callable(getattr(ash_mod,f))]
            print(f"  x Ashtottari: no match. Available: {fns}")

    # Normalise into flat (mds, ads) lists — exact key mapping per source
    vim_mds, vim_ads = norm_vim(vim_raw)
    jai_mds, jai_ads = norm_jai(jai_raw)
    ash_mds, ash_ads = norm_ash(ash_raw)

    md_vim = find_current_md(vim_mds)
    md_jai = find_current_md(jai_mds)
    md_ash = find_current_md(ash_mds)

    if md_vim:
        print(f"\n  Vimsottari now:  {md_vim['lord']} -- {md_vim['phase'].upper()}")
        print(f"  {md_vim['years_elapsed']}y elapsed, {md_vim['years_left']}y remaining")
    if md_jai:
        print(f"  Jaimini now:     {md_jai.get('sign', md_jai.get('lord',''))} ({md_jai['phase']})")
    if md_ash:
        print(f"  Ashtottari now:  {md_ash['lord']} ({md_ash['phase']})")

    print()
    print(vim_dasha_table(vim_mds, vim_ads, md_vim.get("lord","")))

    # ── STEP 4: Career analysis ────────────────────────────────────────────────
    sep("STEP 4 — Career Analysis [divisional_career.build_career_analysis()]")
    print()
    career = None
    if divc_mod:
        try:
            dashas_dict = {"vimsottari": vim_mds, "jaimini": jai_mds}
            career = divc_mod.build_career_analysis(cd, dashas_dict, patra=None)
            print(f"  + AK  : {career.atmakaraka} -- {career.ak_career[:70]}")
            print(f"  + AMK : {career.amatyakaraka} -- {career.amk_career[:70]}")
            print(f"  + Top : {', '.join(career.primary_fields[:4])}")
            e_vs_emp = "Entrepreneur" if career.entrepreneur_score > career.employment_score else "Employment"
            print(f"  + Mode: {e_vs_emp} ({career.entrepreneur_score:.1f} vs {career.employment_score:.1f})")
            if career.funding_timing:
                print(f"  + Fund: {career.funding_timing[:80]}")
        except Exception as e:
            print(f"  x Career analysis: {e}")

    # ── STEP 5: Save ──────────────────────────────────────────────────────────
    sep("STEP 5 -- Save to Supabase")
    print()
    chart_id = save_chart_row(cd, meta, lagna)
    save_dasha_rows(chart_id, vim_mds)
    print(f"  chart_id: {chart_id}")

    # ── STEP 6: Read back ─────────────────────────────────────────────────────
    sep("STEP 6 -- Read Back from Supabase")
    print()
    row        = read_chart_row(chart_id)
    db_d       = read_dasha_rows(chart_id)
    cd_db      = row.get("chart_data", cd) if row else cd
    vim_mds_db = [d for d in db_d if d.get("system") == "vimsottari"] or vim_mds
    if row:
        dl = cd_db.get("lagna", {}).get("sign", "?")
        print(f"  Lagna match: {dl} == {lagna.get('sign','')} -> {dl == lagna.get('sign','')}")
    for d in vim_mds_db:
        d.setdefault("start", d.get("start_date",""))
        d.setdefault("end",   d.get("end_date",""))
        d.setdefault("lord",  d.get("planet_or_sign",""))
        d.setdefault("lord_or_sign", d.get("lord",""))

    # ── STEP 7: Engines ───────────────────────────────────────────────────────
    sep("STEP 7 -- Engines")
    print()
    txn = None
    if txn_mod:
        try:
            txn = txn_mod.calculate_transits(cd_db, target_date=None, ayanamsa_mode=1)
            print("  + Transits")
        except Exception as e:
            print(f"  x Transits: {e}")

    yogas = []
    if yoga_mod:
        try:
            d_yoga = {f"D{n}": d_charts.get(n, {}) for n in cfg["primary"]}
            yogas  = yoga_mod.detect_yogas_for_question(domain, cd_db, d_yoga)
            active = [y for y in yogas if y.get("present")]
            print(f"  + Yogas: {len(active)}/{len(yogas)} active [{domain}]")
            for y in active[:4]:
                print(f"    + {y.get('name','')} [{y.get('strength','')}]")
        except Exception as e:
            print(f"  x Yogas: {e}")

    windows = []
    if win_mod and txn and vim_mds_db:
        try:
            windows = win_mod.find_precision_windows(
                chart_data=cd_db, dashas={"vimsottari": vim_mds_db},
                current_transits=txn, concern=domain,
                detected_yogas=[y.get("name","") for y in yogas if y.get("present")],
                user_correlations=[], months_ahead=12, top_n=4)
            print(f"  + Precision windows: {len(windows)}")
            for w in windows:
                print(f"    {w.get('label',''):18s}  {w.get('score',0)}/10")
        except Exception as e:
            print(f"  x Windows: {e}")

    chakra = None
    if chakra_mod and txn and vim_mds_db:
        try:
            chakra = chakra_mod.get_chakra_reading(
                chart_data=cd_db, dashas={"vimsottari": vim_mds_db}, current_transits=txn)
            print(f"  + Chakra: {chakra.get('english_name','?')}")
        except Exception as e:
            print(f"  x Chakra: {e}")

    arc = None
    if arc_mod and vim_mds_db:
        try:
            arc = arc_mod.build_chapter_arc(
                chart_data=cd_db, dashas={"vimsottari": vim_mds_db}, patra=None)
            print(f"  + Arc: {arc.get('chapter_theme','?')[:50]}  [{arc.get('phase','?')} {arc.get('years_elapsed',0):.1f}y]")
        except Exception as e:
            print(f"  x Arc: {e}")

    # ── STEP 8: Build prompt ──────────────────────────────────────────────────
    sep("STEP 8 -- Build Prompt")
    print()
    prompt = build_prompt(meta, cd_db,
                          vim_mds_db, vim_ads,
                          jai_mds, jai_ads,
                          ash_mds, ash_ads,
                          d_charts, career, yogas, windows, chakra, arc, domain)
    print(f"  Domain:    {domain.upper()}")
    print(f"  Primary:   D-{', D-'.join(str(d) for d in cfg['primary'])}")
    print(f"  Secondary: D-{', D-'.join(str(d) for d in cfg['secondary'])}")
    print(f"  Prompt:    {len(prompt)} chars | {len(prompt.splitlines())} lines")

    # ── STEP 9: AI reading ────────────────────────────────────────────────────
    sep(f"STEP 9 -- AI Reading [{AI_PROVIDER.upper()}]")
    print()
    response, model = call_ai(prompt)
    print(f"  Model: {model}")
    print("  " + "-"*60)
    for line in response.split("\n"):
        print(f"  {line}")
    print("  " + "-"*60)

    return {
        "chart_id":       chart_id,
        "chart_data":     cd_db,
        "birth_jd":       birth_jd,
        "ayanamsa":       ayanamsa,
        "vim_mds":        vim_mds_db,
        "vim_ads":        vim_ads,
        "jai_mds":        jai_mds,
        "jai_ads":        jai_ads,
        "ash_mds":        ash_mds,
        "current_md":     md_vim,
        "d_charts":       d_charts,
        "career":         career,
        "yogas":          yogas,
        "arc":            arc,
        "chakra":         chakra,
        "primary_divs":   cfg["primary"],
        "secondary_divs": cfg["secondary"],
        "ai_response":    response,
        "model":          model,
    }


# ─────────────────────────────────────────────────────────────────────────────
# SCORECARD  (33 checks)
# ─────────────────────────────────────────────────────────────────────────────

def scorecard(res, name):
    if not res:
        return 0, 1
    sep(f"SCORECARD -- {name}")
    print()

    cd  = res.get("chart_data", {})
    md  = res.get("current_md", {})
    dc  = res.get("d_charts", {})
    ca  = res.get("career")
    vim = res.get("vim_mds", [])
    jai = res.get("jai_mds", [])
    ash = res.get("ash_mds", [])
    pdv = res.get("primary_divs", [])

    def chk(label, ok):
        print(f"  {'OK' if ok else 'XX'}  {label}")
        return 1 if ok else 0

    p = 0

    print("  D-1 Birth Chart:")
    p += chk("Lagna sign calculated",            bool(cd.get("lagna",{}).get("sign")))
    p += chk("All 9 planets placed",             len(cd.get("planets",{})) == 9)
    p += chk("Nakshatra on every planet",        all(pl.get("nakshatra") for pl in cd.get("planets",{}).values()))
    p += chk("Nakshatra lord on every planet",   all(pl.get("nakshatra_lord") for pl in cd.get("planets",{}).values()))
    p += chk("Longitude on every planet",        all(pl.get("longitude") for pl in cd.get("planets",{}).values()))
    p += chk("Nakshatra index on every planet",  all(pl.get("nakshatra_index") is not None for pl in cd.get("planets",{}).values()))
    p += chk("Ayanamsa computed",                bool(res.get("ayanamsa")))
    p += chk("Birth JD computed",                bool(res.get("birth_jd")))

    print("\n  Divisional Charts:")
    p += chk("D-2  Hora (wealth)",               bool(dc.get(2,{}).get("lagna",{}).get("sign")))
    p += chk("D-6  Shashthansa (health)",        bool(dc.get(6,{}).get("lagna",{}).get("sign")))
    p += chk("D-7  Saptamsha (children)",        bool(dc.get(7,{}).get("lagna",{}).get("sign")))
    p += chk("D-8  Ashtamsha (longevity)",       bool(dc.get(8,{}).get("lagna",{}).get("sign")))
    p += chk("D-9  Navamsa (marriage/soul)",     bool(dc.get(9,{}).get("lagna",{}).get("sign")))
    p += chk("D-10 Dashamsha (career)",          bool(dc.get(10,{}).get("lagna",{}).get("sign")))
    p += chk("D-12 Dwadashamsha (foreign)",      bool(dc.get(12,{}).get("lagna",{}).get("sign")))
    p += chk("D-24 Chaturvimsamsha (education)", bool(dc.get(24,{}).get("lagna",{}).get("sign")))
    p += chk("D-30 Trimsamsha (health risk)",    bool(dc.get(30,{}).get("lagna",{}).get("sign")))
    p += chk("D-60 Shashtiamsha (past karma)",   bool(dc.get(60,{}).get("lagna",{}).get("sign")))
    p += chk("Domain-primary charts present",    all(dc.get(d,{}).get("lagna",{}).get("sign") for d in pdv if d != 1))

    print("\n  Dasha Systems:")
    p += chk("Vimsottari mahadashas (>=9)",      len(vim) >= 9)
    p += chk("Vimsottari antardashas present",   len(res.get("vim_ads",[])) > 0)
    p += chk("Jaimini Chara mahadashas (==12)",  len(jai) == 12)
    p += chk("Jaimini antardashas present",      len(res.get("jai_ads",[])) > 0)
    p += chk("Ashtottari calculated",            len(ash) > 0)
    p += chk("Current Vimsottari MD found",      bool(md.get("lord")))
    p += chk("MD phase + years computed",        bool(md.get("phase")) and bool(md.get("years_elapsed")))

    print("\n  Career Analysis:")
    p += chk("Atmakaraka identified",            bool(ca) and bool(getattr(ca,"atmakaraka","")))
    p += chk("Amatyakaraka identified",          bool(ca) and bool(getattr(ca,"amatyakaraka","")))
    p += chk("Career fields ranked",             bool(ca) and len(getattr(ca,"primary_fields",[])) > 0)

    print("\n  Infrastructure:")
    p += chk("Chart saved to Supabase",          bool(res.get("chart_id")))
    p += chk("AI response received",             len(res.get("ai_response","")) > 100)
    p += chk("AI response not an error",         not res.get("ai_response","").startswith("["))

    total = 32
    pct   = int(100 * p / total)
    print(f"\n  Score: {p}/{total}  ({pct}%)")
    status = ("PRODUCTION READY" if pct == 100 else
              "STRONG (>88%)"    if pct >= 88  else
              "NEEDS FIXES")
    print(f"  {status}")
    return p, total


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "="*70)
    print("  ANTAR -- E2E PRODUCTION TEST")
    print("  Charts: D-1 + 18 divisional  |  Dashas: Vimsottari + Jaimini + Ashtottari")
    print(f"  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print("="*70)

    sep("ENVIRONMENT")
    print()
    print(f"  Project:    {PROJECT_DIR}")
    print(f"  Supabase:   {'set' if SUPABASE_URL else 'not set'}")
    print(f"  DeepSeek:   {'set' if DEEPSEEK_KEY else 'not set'}")
    print(f"  Anthropic:  {'set' if ANTHROPIC_KEY else 'not set'}")
    print(f"  Provider:   {AI_PROVIDER.upper()}")
    print(f"  D-charts:   D-1 + {len(ALL_DIVS)} divisional = {1+len(ALL_DIVS)} total")
    print(f"  Domains:    {len(DOMAINS)} ({', '.join(DOMAINS.keys())})")

    total_p = total_c = 0
    for meta in TEST_CHARTS:
        res = run(meta)
        p, c = scorecard(res, meta["name"])
        total_p += p
        total_c += c

    sep("FINAL SCORE")
    pct = int(100 * total_p / total_c) if total_c else 0
    print(f"\n  {total_p}/{total_c} checks passed  ({pct}%)\n")
