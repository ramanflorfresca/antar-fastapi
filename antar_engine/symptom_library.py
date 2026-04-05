"""
ANTAR — 12-Channel Diagnostic Engine (Master Architecture)
============================================================
5-Layer Blood Work × 12 Strategic Instruments × Weighted Convergence

Layer 1: BLUEPRINT    — Natal D1 + Jaimini DNA (permanent potential)
Layer 2: INFRASTRUCTURE — D-Charts (D10 career, D9 alliance, D2 wealth)
Layer 3: CLOCK        — Vimsottari Dasha + LK sleeping/Rin (active season)
Layer 4: TRAFFIC      — Live transits via Swiss Ephemeris (real-time pressure)
Layer 5: ANNUAL AGENDA — Varshphal + Muntha (12-month mission)

Convergence weights: Dasha 40%, Transits 30%, D-Charts 20%, Varshphal 10%

Deploy: cp symptom_library.py antar_engine/symptom_library.py
"""

import json
import math
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Import LK advanced functions for on-the-fly computation
try:
    from antar_engine.lal_kitab_advanced import detect_sleeping_planets, detect_enemy_houses, calculate_comprehensive_rin
    HAS_LK_ADVANCED = True
except ImportError:
    HAS_LK_ADVANCED = False


try:
    import swisseph as swe
    HAS_SWE = True
except ImportError:
    swe = None
    HAS_SWE = False

# ═══════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════

SIGNS = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
         "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]

SIGN_LORD_NAMES = {
    0:"Mars",1:"Venus",2:"Mercury",3:"Moon",4:"Sun",
    5:"Mercury",6:"Venus",7:"Mars",8:"Jupiter",9:"Saturn",
    10:"Saturn",11:"Jupiter"
}

PID = {"Sun":0,"Moon":1,"Mars":2,"Mercury":3,"Jupiter":4,"Venus":5,"Saturn":6,"Rahu":7,"Ketu":8}
SWE_IDS = {"Sun":0,"Moon":1,"Mercury":2,"Venus":3,"Mars":4,"Jupiter":5,"Saturn":6}

EXALT = {0:0,1:1,2:9,3:5,4:3,5:11,6:6}
DEBIL = {0:6,1:7,2:3,3:11,4:9,5:5,6:0}
OWN   = {0:[4],1:[3],2:[0,7],3:[2,5],4:[8,11],5:[1,6],6:[9,10]}
MALEFICS = {"sun","mars","saturn","rahu","ketu"}

ENERGY = {
    "Sun":"Authority Signal","Moon":"Emotional Radar","Mars":"Action Drive",
    "Mercury":"Processing Speed","Jupiter":"Growth Amplifier",
    "Venus":"Magnetism Field","Saturn":"Structural Load",
    "Rahu":"Ambition Engine","Ketu":"Intuition Compass",
}

# 12 Strategic Instruments (houses are deprecated in UI)
INSTRUMENTS = {
    1: {"key":"vitals",       "label":"SYSTEM VITALS",     "name":"Health & Identity",
        "checklist":"Lagna Lord (D1) + Transit over Lagna + AK health"},
    2: {"key":"reserves",     "label":"CAPITAL RESERVES",   "name":"Wealth & Savings",
        "checklist":"2L (D1+D2) + Jupiter strength + LK 2nd house audit"},
    3: {"key":"action",       "label":"ACTION CAPACITY",    "name":"Courage & Initiative",
        "checklist":"3L + Natal Mars + Transit pressure on execution"},
    4: {"key":"property",     "label":"REAL ESTATE RADAR",  "name":"Home & Property",
        "checklist":"4L + Moon/Venus strength + Property Yoga convergence"},
    5: {"key":"creation",     "label":"CREATION ENGINE",    "name":"Children & Intelligence",
        "checklist":"5L + PK (Putrakaraka) + Intelligence nodes"},
    6: {"key":"conflict",     "label":"CONFLICT SHIELD",    "name":"Enemies & Legal",
        "checklist":"6L + Natal Saturn + Litigation risk + Operational debt"},
    7: {"key":"alliance",     "label":"ALLIANCE SYNC",      "name":"Marriage & Partners",
        "checklist":"7L (D1+D9) + DK (Darakaraka) + Partnership resonance"},
    8: {"key":"runway",       "label":"CAPITAL RUNWAY",     "name":"Funding & Transformation",
        "checklist":"8L + Rahu + External Equity/Funding + Legacy assets"},
    9: {"key":"fortune",      "label":"FORTUNE VECTOR",     "name":"Luck & Foreign",
        "checklist":"9L + Jupiter + Global reach + Sovereign Wisdom"},
    10:{"key":"authority",    "label":"AUTHORITY ENGINE",   "name":"Career & Status",
        "checklist":"10L (D1+D10) + AmK + Boardroom status"},
    11:{"key":"revenue",      "label":"REVENUE PIPELINE",   "name":"Income & Network",
        "checklist":"11L + Gains Yogas + Network monetization"},
    12:{"key":"global",       "label":"GLOBAL VECTOR",      "name":"Foreign & Expenses",
        "checklist":"12L + Foreign Exit potential + Burn/Loss audit"},
}

# Convergence weights per Master Architecture
WEIGHTS = {"dasha": 0.40, "transit": 0.30, "dchart": 0.20, "varshphal": 0.10}

DOMAIN_VOCABULARY = {
    "career":       {"tone":"chairman","instruction":"Speak like a Chairman. Use: leverage, positioning, mandate, visibility window. Never astrology terms.","nouns":["authority","positioning","visibility","leverage","mandate"]},
    "wealth":       {"tone":"cfo","instruction":"Speak like a CFO. Use: runway, overhead, burn rate, capital deployment. Never astrology terms.","nouns":["runway","overhead","equity","burn rate","capital"]},
    "relationship": {"tone":"mediator","instruction":"Speak like a Conflict Mediator. Use: alignment, sync, convergence, resonance. Never astrology terms.","nouns":["alignment","sync","convergence","stability","resonance"]},
    "health":       {"tone":"physician","instruction":"Speak like an Executive Physician. Use: vitals, reserves, capacity, recovery. Never astrology terms.","nouns":["vitals","reserves","resilience","recovery","capacity"]},
    "legal":        {"tone":"counsel","instruction":"Speak like General Counsel. Use: exposure, leverage, liability, positioning. Never astrology terms.","nouns":["exposure","leverage","liability","positioning","terms"]},
    "general":      {"tone":"advisor","instruction":"Speak like a trusted strategic advisor. Clear, direct, no astrology terms.","nouns":["momentum","clarity","direction","energy","timing"]},
    "finance":      {"tone":"cfo","instruction":"Speak like a CFO. Use: runway, burn rate, capital deployment. Never astrology terms.","nouns":["runway","overhead","equity","burn rate","capital"]},
    "property":     {"tone":"advisor","instruction":"Speak like a real estate strategist. Use: asset, equity, timing, market position. Never astrology terms.","nouns":["asset","equity","location","timing","market"]},
    "education":    {"tone":"advisor","instruction":"Speak like an academic advisor. Use: capacity, timing, preparation, positioning. Never astrology terms.","nouns":["capacity","preparation","timing","positioning","merit"]},
    "children":     {"tone":"advisor","instruction":"Speak like a family planning advisor. Use: timing, readiness, conditions, window. Never astrology terms.","nouns":["timing","readiness","conditions","window","preparation"]},
    "foreign":      {"tone":"advisor","instruction":"Speak like a relocation strategist. Use: vector, corridor, window, positioning. Never astrology terms.","nouns":["vector","corridor","window","positioning","transition"]},
}

LIFE_EVENTS = [
    {"id":"buying_house","name":"Buying a Home","houses":[4,2],"planets":["Mars","Moon"],"label":"PROPERTY ACQUISITION"},
    {"id":"buying_car","name":"Buying a Vehicle","houses":[4,2],"planets":["Venus"],"label":"VEHICLE ACQUISITION"},
    {"id":"marriage","name":"Marriage","houses":[7,2],"planets":["Venus"],"label":"MARRIAGE WINDOW"},
    {"id":"having_children","name":"Having Children","houses":[5,2],"planets":["Jupiter"],"label":"FERTILITY WINDOW"},
    {"id":"job_change","name":"Job Change","houses":[10,6],"planets":["Saturn","Sun"],"label":"CAREER TRANSITION"},
    {"id":"starting_business","name":"Starting a Business","houses":[10,7],"planets":["Mercury","Rahu"],"label":"VENTURE LAUNCH"},
    {"id":"legal_case","name":"Legal Matter","houses":[6,7],"planets":["Saturn","Mars"],"label":"LEGAL POSITIONING"},
    {"id":"moving_abroad","name":"Relocating Abroad","houses":[12,9],"planets":["Rahu","Moon"],"label":"RELOCATION WINDOW"},
    {"id":"moving_city","name":"Moving / Relocation","houses":[4,3,12],"planets":["Moon"],"label":"RELOCATION SIGNAL"},
    {"id":"inheritance","name":"Inheritance / Windfall","houses":[8,2,11],"planets":["Jupiter"],"label":"WINDFALL WINDOW"},
    {"id":"higher_education","name":"Higher Education","houses":[4,9,5],"planets":["Jupiter","Mercury"],"label":"EDUCATION WINDOW"},
    {"id":"health_crisis","name":"Health Alert","houses":[6,8,1],"planets":["Mars","Saturn"],"label":"HEALTH ALERT"},
    {"id":"debt_clearance","name":"Debt Clearance","houses":[6,12],"planets":["Saturn"],"label":"DEBT RESOLUTION"},
    {"id":"investment","name":"Investment Window","houses":[5,11,2],"planets":["Jupiter","Rahu"],"label":"INVESTMENT WINDOW"},
    {"id":"promotion","name":"Promotion / Rise","houses":[10,11],"planets":["Sun","Jupiter"],"label":"RISE WINDOW"},
    {"id":"separation","name":"Separation Risk","houses":[7,12],"planets":["Rahu","Ketu"],"label":"SEPARATION SIGNAL"},
]


# ═══════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════

def _sj(d):
    if isinstance(d,str):
        try: return json.loads(d)
        except: return {}
    return d if isinstance(d,dict) else {}

def _si(n):
    if isinstance(n, int): return n % 12
    if isinstance(n, float): return int(n) % 12
    if isinstance(n, str) and n in SIGNS: return SIGNS.index(n)
    if isinstance(n, str):
        # Try case-insensitive match
        nl = n.lower().strip()
        for i, s in enumerate(SIGNS):
            if s.lower() == nl:
                return i
        # Try parsing as number
        try:
            return int(n) % 12
        except (ValueError, TypeError):
            pass
    if isinstance(n, dict):
        # Handle {"sign": 9} or {"sign_name": "Capricorn"} or {"sign": "Capricorn"}
        v = n.get("sign", n.get("sign_name", n.get("sign_idx", n.get("index", 0))))
        return _si(v)
    return 0

def _fp(cd,nm):
    for pid,pd in cd.get("planets",{}).items():
        if isinstance(pd,dict) and pd.get("name","").lower()==nm.lower(): return pd
    return None

def _hl(cd,h):
    lg=cd.get("lagna_sign",cd.get("lagna",0))
    if isinstance(lg,dict):
        lg = lg.get("sign", lg.get("sign_name", lg.get("index", 0)))
    if isinstance(lg,str): lg=_si(lg)
    if isinstance(lg,float): lg=int(lg)
    if not isinstance(lg,int): lg=0
    return SIGN_LORD_NAMES.get((lg+h-1)%12,"Saturn")

def _exalt(pd):
    if not pd: return False
    return EXALT.get(PID.get(pd.get("name",""),-1))==pd.get("sign",-1)

def _own(pd):
    if not pd: return False
    return pd.get("sign",-1) in OWN.get(PID.get(pd.get("name",""),-1),[])

def _debil(pd):
    if not pd: return False
    return DEBIL.get(PID.get(pd.get("name",""),-1))==pd.get("sign",-1)

def _retro(pd):
    if not pd: return False
    s=pd.get("daily_speed",pd.get("speed",0))
    return isinstance(s,(int,float)) and s<0

def _combust(pd,cd):
    if not pd: return False
    sun=_fp(cd,"Sun")
    if not sun: return False
    diff=abs(pd.get("longitude",0)-sun.get("longitude",0))
    if diff>180: diff=360-diff
    return diff<{"Moon":12,"Mars":17,"Mercury":14,"Jupiter":11,"Venus":10,"Saturn":15}.get(pd.get("name",""),15)

def _strong(pd): return _exalt(pd) or _own(pd)
def _weak(pd,cd):
    if not pd: return True
    return _retro(pd) or _combust(pd,cd) or _debil(pd)

def _lc(cd,h1,h2):
    a=_fp(cd,_hl(cd,h1)); b=_fp(cd,_hl(cd,h2))
    if not a or not b: return False
    sa,sb=a.get("sign",-1),b.get("sign",-1)
    if sa==sb: return True
    d=(sb-sa)%12
    return d in [0,4,8] or (12-d) in [4,8]

def _mih(cd,h):
    for pid,pd in cd.get("planets",{}).items():
        if isinstance(pd,dict) and pd.get("name","").lower() in MALEFICS and pd.get("house")==h: return True
    return False

def _bih(cd,h):
    for pid,pd in cd.get("planets",{}).items():
        if isinstance(pd,dict) and pd.get("name","").lower() in {"jupiter","venus","mercury"} and pd.get("house")==h: return True
    return False

def _pd(ds):
    if not ds or "-" not in str(ds): return ("","")
    p=str(ds).split("-"); return (p[0].strip(), p[1].strip() if len(p)>1 else "")

def _karakas(jd):
    jd=_sj(jd); k=jd.get("karakas",jd.get("chara_karakas",{}))
    if isinstance(k,list):
        d={}
        for i in k:
            if isinstance(i,dict): d[i.get("role",i.get("karaka",""))]=i.get("planet",i.get("name",""))
        return d
    return k if isinstance(k,dict) else {}


# ═══════════════════════════════════════════════════════════════════
# JAIMINI INTELLIGENCE FUNCTIONS
# Rashi Drishti, Argala, AL/UL/KL, Chara Dasha, Predictive Rules
# ═══════════════════════════════════════════════════════════════════

def _rashi_drishti(sign_idx):
    """Jaimini sign-based aspects. Movable→Fixed(except adjacent), Fixed→Movable(except adjacent), Dual→Dual."""
    t = sign_idx % 3
    if t == 0:  # Movable: aspects all Fixed except adjacent
        adj = (sign_idx + 1) % 12
        return [s for s in [1,4,7,10] if s != adj]
    elif t == 1:  # Fixed: aspects all Movable except adjacent
        adj = (sign_idx - 1) % 12
        return [s for s in [0,3,6,9] if s != adj]
    else:  # Dual: aspects other Duals
        return [s for s in [2,5,8,11] if s != sign_idx]


def _sign_aspects_house(sign_idx, house_num, natal_lagna):
    """Does this sign (by Rashi Drishti) aspect the given house?"""
    if isinstance(natal_lagna, dict):
        natal_lagna = natal_lagna.get("sign", natal_lagna.get("sign_name", 0))
    if isinstance(natal_lagna, str):
        natal_lagna = _si(natal_lagna)
    if not isinstance(natal_lagna, int):
        natal_lagna = 0
    target_sign = (natal_lagna + house_num - 1) % 12
    return target_sign in _rashi_drishti(sign_idx)


def _check_argala(cd, house_num):
    """
    Argala: planets in 2nd, 4th, 11th from a house SUPPORT it.
    Virodhargala: planets in 12th, 10th, 3rd OBSTRUCT the argala.
    5th house = secondary argala, obstructed by 9th.
    Returns net support count.
    """
    lg = _si(cd.get("lagna_sign", cd.get("lagna", 0)))

    support = 0
    obstruct = 0

    # Primary argala pairs: (support_offset, obstruction_offset)
    argala_pairs = [(2, 12), (4, 10), (11, 3)]
    # Secondary: (5, 9)

    for sup_off, obs_off in argala_pairs:
        sup_house = ((house_num - 1 + sup_off) % 12) + 1
        obs_house = ((house_num - 1 + obs_off) % 12) + 1
        sup_count = 0
        obs_count = 0
        for pid, pd in cd.get("planets", {}).items():
            if isinstance(pd, dict):
                if pd.get("house") == sup_house:
                    sup_count += 1
                if pd.get("house") == obs_house:
                    obs_count += 1
        if sup_count > 0 and obs_count < sup_count:
            support += sup_count - obs_count

    # Secondary argala: 5th house, obstructed by 9th
    h5 = ((house_num - 1 + 5) % 12) + 1
    h9 = ((house_num - 1 + 9) % 12) + 1
    s5 = sum(1 for pid, pd in cd.get("planets", {}).items() if isinstance(pd, dict) and pd.get("house") == h5)
    o9 = sum(1 for pid, pd in cd.get("planets", {}).items() if isinstance(pd, dict) and pd.get("house") == h9)
    if s5 > 0 and o9 < s5:
        support += 1

    return support


def _get_arudha_lagnas(jd):
    """Extract AL, UL, KL from jaimini_data JSONB. Tries multiple key formats."""
    jd = _sj(jd)
    result = {"AL": None, "UL": None, "KL": None}

    # Try direct keys
    for key in ["arudha_lagna", "arudha", "AL", "al"]:
        v = jd.get(key)
        if v:
            if isinstance(v, str):
                result["AL"] = _si(v)
            elif isinstance(v, int):
                result["AL"] = v % 12
            elif isinstance(v, dict):
                result["AL"] = _si(v.get("sign", v.get("sign_name", "")))
            break

    for key in ["upapada_lagna", "upapada", "UL", "ul"]:
        v = jd.get(key)
        if v:
            if isinstance(v, str):
                result["UL"] = _si(v)
            elif isinstance(v, int):
                result["UL"] = v % 12
            elif isinstance(v, dict):
                result["UL"] = _si(v.get("sign", v.get("sign_name", "")))
            break

    for key in ["karakamsa", "karakamsha", "KL", "kl"]:
        v = jd.get(key)
        if v:
            if isinstance(v, str):
                result["KL"] = _si(v)
            elif isinstance(v, int):
                result["KL"] = v % 12
            elif isinstance(v, dict):
                result["KL"] = _si(v.get("sign", v.get("sign_name", "")))
            break

    return result


def _get_chara_dasha(jd):
    """Extract current Jaimini Chara Dasha MD and AD signs from jaimini_data."""
    jd = _sj(jd)
    result = {"md_sign": None, "ad_sign": None, "md_sign_name": "", "ad_sign_name": ""}

    cd_data = jd  # current_md and current_ad are at root level of jaimini_data

    if isinstance(cd_data, dict):
        # Direct current period
        md = cd_data.get("current_md", cd_data.get("mahadasha", cd_data.get("md", {})))
        ad = cd_data.get("current_ad", cd_data.get("antardasha", cd_data.get("ad", {})))

        if isinstance(md, dict):
            ms = md.get("sign", md.get("sign_name", ""))
            if ms:
                result["md_sign"] = _si(ms)
                result["md_sign_name"] = ms if isinstance(ms, str) and ms in SIGNS else SIGNS[_si(ms)]
        elif isinstance(md, str):
            result["md_sign"] = _si(md)
            result["md_sign_name"] = md if md in SIGNS else SIGNS[_si(md)]

        if isinstance(ad, dict):
            ads = ad.get("sign", ad.get("sign_name", ""))
            if ads:
                result["ad_sign"] = _si(ads)
                result["ad_sign_name"] = ads if isinstance(ads, str) and ads in SIGNS else SIGNS[_si(ads)]
        elif isinstance(ad, str):
            result["ad_sign"] = _si(ad)
            result["ad_sign_name"] = ad if ad in SIGNS else SIGNS[_si(ad)]

    elif isinstance(cd_data, list):
        # Find active period from list
        now_str = datetime.now(timezone.utc).isoformat()
        for period in cd_data:
            if isinstance(period, dict):
                start = period.get("start", period.get("start_date", ""))
                end = period.get("end", period.get("end_date", ""))
                if start and end and start <= now_str <= end:
                    sign = period.get("sign", period.get("sign_name", ""))
                    if sign:
                        if period.get("level", 1) == 1 or not result["md_sign_name"]:
                            result["md_sign"] = _si(sign)
                            result["md_sign_name"] = sign if isinstance(sign, str) and sign in SIGNS else SIGNS[_si(sign)]
                        # Check for sub-periods
                        ads_list = period.get("ads", period.get("antardashas", []))
                        if isinstance(ads_list, list):
                            for sub in ads_list:
                                if isinstance(sub, dict):
                                    ss = sub.get("start", sub.get("start_date", ""))
                                    se = sub.get("end", sub.get("end_date", ""))
                                    if ss and se and ss <= now_str <= se:
                                        subsign = sub.get("sign", sub.get("sign_name", ""))
                                        if subsign:
                                            result["ad_sign"] = _si(subsign)
                                            result["ad_sign_name"] = subsign if isinstance(subsign, str) and subsign in SIGNS else SIGNS[_si(subsign)]

    return result


def _jaimini_house_from_sign(sign_idx, natal_lagna):
    """Convert a sign index to house number relative to natal lagna."""
    if isinstance(natal_lagna, dict):
        natal_lagna = natal_lagna.get("sign", natal_lagna.get("sign_name", 0))
    if isinstance(natal_lagna, str):
        natal_lagna = _si(natal_lagna)
    if not isinstance(natal_lagna, int):
        natal_lagna = 0
    return ((sign_idx - natal_lagna) % 12) + 1


def _score_jaimini_predictive(cd, h, jd):
    """
    Jaimini Predictive Rules — check if current Chara Dasha activates
    specific life events for this instrument.

    Rules from the Jaimini Predictive Engine spec:
    - AmK in 1st/10th/11th from dasha sign → Professional Rise
    - DK in dasha sign or aspecting it → Relationship Event
    - GK in dasha sign or aspecting it → Conflict/Health Event
    - PK in dasha sign → Children/Creative Event
    - Dasha sign = 7th from UL → Marriage Window
    - Dasha sign = 11th from AL → Wealth through networks
    - Dasha sign aspects Karakamsa → Soul purpose activation
    """
    sc = 0
    factors = []
    jd_data = _sj(jd)
    if not jd_data:
        return sc, factors

    lg = _si(cd.get("lagna_sign", cd.get("lagna", 0)))

    kr = _karakas(jd)
    chara = _get_chara_dasha(jd)
    arudhas = _get_arudha_lagnas(jd)
    md_sign = chara.get("md_sign")
    ad_sign = chara.get("ad_sign")

    if md_sign is None:
        return sc, factors

    # What house does the Chara Dasha MD sign correspond to?
    cd_house = _jaimini_house_from_sign(md_sign, lg)

    # Check if this instrument's house is the Chara Dasha house
    if cd_house == h:
        sc += 20
        factors.append("Jaimini Chara Dasha MD sign activates this instrument directly")

    # Check if AD sign activates
    if ad_sign is not None:
        ad_house = _jaimini_house_from_sign(ad_sign, lg)
        if ad_house == h:
            sc += 12
            factors.append("Jaimini Chara Dasha AD sign activates this instrument")

    # Check Rashi Drishti from MD sign to this house's sign
    house_sign = (lg + h - 1) % 12
    if house_sign in _rashi_drishti(md_sign):
        sc += 8
        factors.append("Jaimini MD sign aspects this instrument via Rashi Drishti")

    # === KARAKA-BASED PREDICTIVE RULES ===

    # H10 (Authority): AmK in 1st/10th/11th from dasha sign → Professional Rise
    if h == 10 and kr.get("AmK"):
        amk_data = _fp(cd, kr["AmK"])
        if amk_data:
            amk_sign = amk_data.get("sign", -1)
            dist_from_dasha = (amk_sign - md_sign) % 12
            if dist_from_dasha in [0, 9, 10]:  # 1st, 10th, 11th from dasha sign
                sc += 15
                factors.append("AmK in power position from Chara Dasha sign — Professional Rise indicated")

    # H7 (Alliance): DK in dasha sign or aspecting it → Relationship Event
    if h == 7 and kr.get("DK"):
        dk_data = _fp(cd, kr["DK"])
        if dk_data:
            dk_sign = dk_data.get("sign", -1)
            if dk_sign == md_sign:
                sc += 15
                factors.append("DK in Chara Dasha sign — Relationship Event activated")
            elif md_sign in _rashi_drishti(dk_sign):
                sc += 10
                factors.append("DK aspects Chara Dasha sign — Relationship activation")

    # H6 (Conflict) / H1 (Health): GK in dasha sign → Conflict/Health Event
    if h in [6, 1] and kr.get("GK"):
        gk_data = _fp(cd, kr["GK"])
        if gk_data:
            gk_sign = gk_data.get("sign", -1)
            if gk_sign == md_sign:
                sc -= 15
                factors.append("GK in Chara Dasha sign — Conflict/Health challenge activated")
            elif md_sign in _rashi_drishti(gk_sign):
                sc -= 8
                factors.append("GK aspects Chara Dasha sign — Minor conflict/health friction")

    # H5 (Creation): PK in dasha sign → Children/Creative Event
    if h == 5 and kr.get("PK"):
        pk_data = _fp(cd, kr["PK"])
        if pk_data and pk_data.get("sign", -1) == md_sign:
            sc += 12
            factors.append("PK in Chara Dasha sign — Creative/Progeny event activated")

    # === ARUDHA-BASED RULES ===

    # UL check: Dasha sign = 1st or 7th from UL → Marriage/Commitment window
    if h == 7 and arudhas.get("UL") is not None:
        ul = arudhas["UL"]
        dist_from_ul = (md_sign - ul) % 12
        if dist_from_ul in [0, 6]:  # 1st or 7th from UL
            sc += 15
            factors.append("Chara Dasha sign aligns with Upapada — Commitment window active")

    # AL check: Dasha sign = 11th from AL → Wealth through networks
    if h in [2, 11] and arudhas.get("AL") is not None:
        al = arudhas["AL"]
        dist_from_al = (md_sign - al) % 12
        if dist_from_al == 10:  # 11th from AL
            sc += 12
            factors.append("Chara Dasha sign in 11th from Arudha Lagna — Network wealth activation")
        elif dist_from_al in [1, 6]:  # 2nd or 7th from AL
            sc += 8
            factors.append("Chara Dasha favorably placed from Arudha Lagna for gains")

    # KL check: Dasha sign aspects Karakamsa → Soul purpose activation
    if arudhas.get("KL") is not None:
        kl = arudhas["KL"]
        if md_sign == kl:
            sc += 10
            factors.append("Chara Dasha sign IS the Karakamsa — Soul purpose fully activated")
        elif kl in _rashi_drishti(md_sign):
            sc += 6
            factors.append("Chara Dasha sign aspects Karakamsa — Soul purpose resonance")

    # === ARGALA CHECK ===
    argala_support = _check_argala(cd, h)
    if argala_support >= 2:
        sc += 10
        factors.append("Strong Argala support (" + str(argala_support) + " unobstructed interventions)")
    elif argala_support == 1:
        sc += 5
        factors.append("Moderate Argala support on this instrument")

    return sc, factors


# ═══════════════════════════════════════════════════════════════════
# LAYER 1: BLUEPRINT (Natal D1 + Jaimini DNA)
# Permanent potential — calculated once, pinned forever
# ═══════════════════════════════════════════════════════════════════

def _score_blueprint(cd, h, jd=None):
    """Score one instrument's permanent potential 0-100."""
    sc=50; factors=[]
    ln=_hl(cd,h); ld=_fp(cd,ln); en=ENERGY.get(ln,ln)

    if _strong(ld): sc+=20; factors.append(en+" at peak structural power")
    elif _weak(ld,cd): sc-=15; factors.append(en+" structurally weakened")

    if ld:
        lh=ld.get("house",0)
        if lh in [1,4,7,10]: sc+=10; factors.append(en+" in angular (power) position")
        elif lh in [5,9]: sc+=10; factors.append(en+" in trikona (fortune) position")
        elif lh in [6,8,12]: sc-=10; factors.append(en+" in dusthana (stress) position")

    if _bih(cd,h): sc+=8; factors.append("Benefic energy present in sector")
    if _mih(cd,h): sc-=8; factors.append("Malefic pressure in sector")

    # Jaimini karaka boost for relevant instruments
    kr=_karakas(jd)
    karaka_map={10:"AmK",7:"DK",5:"PK",1:"AK",6:"GK"}
    if h in karaka_map and kr:
        kp=kr.get(karaka_map[h],"")
        if kp:
            kd=_fp(cd,kp)
            if _strong(kd): sc+=15; factors.append(karaka_map[h]+" significator at peak")
            elif _weak(kd,cd): sc-=10; factors.append(karaka_map[h]+" significator weakened")

    # Arudha Lagna checks for blueprint
    arudhas=_get_arudha_lagnas(jd)
    lagna_raw=cd.get("lagna_sign",cd.get("lagna",0))
    lagna_idx=_si(lagna_raw)
    if arudhas.get("AL") is not None:
        al=arudhas["AL"]; al_house=((al-lagna_idx)%12)+1
        # Benefics in 11th from AL = wealth through networks (permanent trait)
        if h==11:
            h11_from_al=((al+10)%12)
            for pid,pd in cd.get("planets",{}).items():
                if isinstance(pd,dict) and pd.get("name","").lower() in {"jupiter","venus"} and pd.get("sign")==h11_from_al:
                    sc+=10; factors.append("Benefic in 11th from Arudha Lagna — structural wealth through networks")
                    break

    # Argala support check (permanent structural support)
    argala=_check_argala(cd, h)
    if argala>=2: sc+=8; factors.append("Strong Argala support ("+str(argala)+" unobstructed)")
    elif argala==1: sc+=4; factors.append("Moderate Argala support")

    return max(10,min(100,sc)), factors


# ═══════════════════════════════════════════════════════════════════
# LAYER 2: INFRASTRUCTURE (D-Charts)
# Hardware check — is the engine capable?
# ═══════════════════════════════════════════════════════════════════

def _score_infrastructure(cd, h):
    """Check D-chart support for this instrument. Reads from chart_data.divisional_charts."""
    div=cd.get("divisional_charts",{})
    sc=0; factors=[]

    # D10 for career (house 10)
    if h==10:
        d10=_sj(div.get("D10",div.get("d10",{})))
        if d10:
            d10_lagna=d10.get("lagna_sign",d10.get("lagna",""))
            if d10_lagna: sc+=15; factors.append("D10 career chart available — infrastructure verified")
            # Check if 10L in D10 is strong
            d10_planets=d10.get("planets",{})
            if d10_planets: sc+=5; factors.append("D10 planetary data loaded")
        else:
            factors.append("D10 career chart not available — infrastructure unverified")

    # D9 for alliance (house 7)
    if h==7:
        d9=_sj(div.get("D9",div.get("d9",{})))
        if d9:
            sc+=15; factors.append("D9 alliance chart available")
            d9_planets=d9.get("planets",{})
            if d9_planets: sc+=5
        else:
            factors.append("D9 alliance chart not available")

    # D2 for wealth (house 2, 8, 11)
    if h in [2,8,11]:
        d2=_sj(div.get("D2",div.get("d2",div.get("hora",{}))))
        if d2:
            sc+=15; factors.append("D2 wealth chart available")
        else:
            factors.append("D2 wealth chart not available")

    # D7 for children (house 5)
    if h==5:
        d7=_sj(div.get("D7",div.get("d7",div.get("saptamsa",{}))))
        if d7:
            sc+=10; factors.append("D7 progeny chart available")

    return sc, factors


# ═══════════════════════════════════════════════════════════════════
# LAYER 3: CLOCK (Vimsottari Dasha + LK Sleeping/Rin)
# Is the power ON or OFF for this instrument?
# ═══════════════════════════════════════════════════════════════════

def _score_clock(cd, h, current_dasha, lk=None):
    """Check if current dasha activates this instrument."""
    sc=0; factors=[]
    md,ad=_pd(current_dasha)
    hl=_hl(cd,h)
    mdd=_fp(cd,md) if md else None

    # MD lord rules this house
    if md and md.lower()==hl.lower():
        sc+=40; factors.append("Chapter lord directly governs this instrument — FULLY ACTIVE")
    # MD lord sits in this house
    elif mdd and mdd.get("house")==h:
        sc+=35; factors.append("Chapter energy occupies this instrument — HIGHLY ACTIVE")
    # AD lord activates
    elif ad:
        if ad.lower()==hl.lower():
            sc+=25; factors.append("Sub-period activates this instrument")
        add=_fp(cd,ad)
        if add and add.get("house")==h:
            sc+=20; factors.append("Sub-period energy in this instrument")
    # Trikona aspect from MD lord
    elif mdd:
        dist=abs(h-mdd.get("house",0)) if mdd.get("house") else 99
        if dist in [4,8,0]: sc+=12; factors.append("Chapter energy aspects this instrument (trikona)")
        elif dist==6: sc+=10; factors.append("Chapter energy in opposition to this instrument")

    # LK sleeping planet check
    lk=_sj(lk) if lk else {}
    sleeping=lk.get("sleeping_planets",lk.get("sleeping",lk.get("advanced",{}).get("sleeping_planets",[])))
    if isinstance(sleeping,list):
        for sp in sleeping:
            planet=""
            if isinstance(sp,dict): planet=sp.get("planet",sp.get("name",""))
            elif isinstance(sp,str): planet=sp
            if planet and planet.lower()==hl.lower():
                sc-=20; factors.append(ENERGY.get(planet,planet)+" is SLEEPING — power OFF for this instrument")

    # On-the-fly LK computation when stored data is missing
    if not sleeping and HAS_LK_ADVANCED:
        try:
            natal_p = lk.get("natal_planets", {})
            if not natal_p:
                natal_p = {}
                for _lpid, _lpd in cd.get("planets", {}).items():
                    if isinstance(_lpd, dict) and _lpd.get("name"):
                        _sn = SIGNS[_lpd.get("sign", 0)] if isinstance(_lpd.get("sign"), int) else str(_lpd.get("sign", ""))
                        natal_p[_lpd["name"]] = {"house": _lpd.get("house", 0), "sign": _sn}
            if natal_p:
                _lagna = cd.get("lagna_sign", "Aries")
                if isinstance(_lagna, (dict, int)):
                    _lagna = SIGNS[_si(_lagna)]
                _sleeping = detect_sleeping_planets(natal_p, _lagna)
                if isinstance(_sleeping, list):
                    for _sp in _sleeping:
                        _spn = _sp.get("planet", "") if isinstance(_sp, dict) else str(_sp)
                        if _spn and _spn.lower() == hl.lower():
                            sc -= 20
                            factors.append(ENERGY.get(_spn, _spn) + " is SLEEPING (computed) — power OFF")
        except Exception:
            pass


    # LK Rin (karmic debt) check
    rin=lk.get("rin_debts",lk.get("rin",lk.get("advanced",{}).get("rin",lk.get("advanced",{}).get("comprehensive_rin",[]))))
    if isinstance(rin,list):
        for debt in rin[:3]:
            if isinstance(debt,dict):
                dp=debt.get("planet","")
                if dp and dp.lower()==hl.lower():
                    sc-=15; factors.append("Karmic debt (Rin) on "+ENERGY.get(dp,dp)+" — pattern loop draining this instrument")

    # On-the-fly Rin computation when stored data is missing
    if not rin and HAS_LK_ADVANCED:
        try:
            natal_p = lk.get("natal_planets", {})
            if not natal_p:
                natal_p = {}
                for _lpid, _lpd in cd.get("planets", {}).items():
                    if isinstance(_lpd, dict) and _lpd.get("name"):
                        _sn = SIGNS[_lpd.get("sign", 0)] if isinstance(_lpd.get("sign"), int) else str(_lpd.get("sign", ""))
                        natal_p[_lpd["name"]] = {"house": _lpd.get("house", 0), "sign": _sn}
            if natal_p:
                _rin = calculate_comprehensive_rin(natal_p)
                if isinstance(_rin, list):
                    for _debt in _rin[:3]:
                        if isinstance(_debt, dict):
                            _dp = _debt.get("planet", "")
                            if _dp and _dp.lower() == hl.lower():
                                sc -= 15
                                factors.append("Rin (computed) on " + ENERGY.get(_dp, _dp) + " — karmic pattern active")
        except Exception:
            pass


    return sc, factors


# ═══════════════════════════════════════════════════════════════════
# LAYER 3B: JAIMINI CHARA DASHA (parallel clock)
# Sign-based timing that cross-validates Vimsottari
# ═══════════════════════════════════════════════════════════════════

def _score_jaimini_clock(cd, h, jd):
    """Jaimini predictive scoring for this instrument using Chara Dasha + Karakas + Arudhas."""
    return _score_jaimini_predictive(cd, h, jd)


# ═══════════════════════════════════════════════════════════════════
# LAYER 4: TRAFFIC (Live Transits)
# Real-time environmental pressure — is the road open or blocked?
# ═══════════════════════════════════════════════════════════════════

def _get_current_transits():
    """Compute current planetary positions using Swiss Ephemeris."""
    if not HAS_SWE:
        return {}
    try:
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        now=datetime.now(timezone.utc)
        jd=swe.julday(now.year,now.month,now.day,now.hour+now.minute/60.0+now.second/3600.0)
        transits={}
        for name,sid in SWE_IDS.items():
            result=swe.calc_ut(jd,sid,swe.FLG_SIDEREAL|swe.FLG_SPEED)
            lon=result[0][0]; spd=result[0][3]
            transits[name]={"longitude":round(lon,4),"sign":int(lon/30),"degree":round(lon%30,2),"speed":round(spd,4),"retrograde":spd<0,"house_from_aries":int(lon/30)+1}
        # Rahu (mean node)
        rr=swe.calc_ut(jd,swe.MEAN_NODE,swe.FLG_SIDEREAL|swe.FLG_SPEED)
        rlon=rr[0][0]
        transits["Rahu"]={"longitude":round(rlon,4),"sign":int(rlon/30),"degree":round(rlon%30,2),"speed":0,"retrograde":True,"house_from_aries":int(rlon/30)+1}
        transits["Ketu"]={"longitude":round((rlon+180)%360,4),"sign":int(((rlon+180)%360)/30),"degree":round(((rlon+180)%360)%30,2),"speed":0,"retrograde":True,"house_from_aries":int(((rlon+180)%360)/30)+1}
        return transits
    except Exception as e:
        logger.warning("Transit computation failed: %s",e)
        return {}


def _transit_house(transit_sign, natal_lagna_sign):
    """What house does this transit planet occupy relative to natal lagna?"""
    return ((transit_sign - natal_lagna_sign) % 12) + 1


def _score_traffic(cd, h, transits=None):
    """Score real-time transit pressure on this instrument."""
    if not transits:
        return 0, ["Live transit data not available"]

    sc=0; factors=[]
    lg=_si(cd.get("lagna_sign",cd.get("lagna",0)))

    for pname, tdata in transits.items():
        tsign=tdata.get("sign",0)
        thouse=_transit_house(tsign, lg)
        is_retro=tdata.get("retrograde",False)

        if thouse==h:
            if pname.lower() in {"jupiter","venus"}:
                sc+=15; factors.append(ENERGY.get(pname,pname)+" transiting through this instrument — BOOST")
            elif pname.lower() in {"saturn","rahu","ketu","mars"}:
                sc-=15; factors.append(ENERGY.get(pname,pname)+" transiting through this instrument — PRESSURE")
                if is_retro:
                    sc-=5; factors.append(ENERGY.get(pname,pname)+" is retrograde — pressure intensified")
            elif pname.lower() in {"sun","mercury","moon"}:
                sc+=5; factors.append(ENERGY.get(pname,pname)+" transiting — minor activation")

        # Check aspects (7th from transit = opposition)
        opp_house=((thouse-1+6)%12)+1
        if opp_house==h:
            if pname.lower() in {"saturn","mars","rahu"}:
                sc-=8; factors.append(ENERGY.get(pname,pname)+" opposing this instrument from H"+str(thouse))
            elif pname.lower() in {"jupiter"}:
                sc+=8; factors.append(ENERGY.get(pname,pname)+" aspecting this instrument from H"+str(thouse)+" — protective")

    return sc, factors


# ═══════════════════════════════════════════════════════════════════
# LAYER 5: ANNUAL AGENDA (Varshphal + Muntha)
# What is the 12-month mission?
# ═══════════════════════════════════════════════════════════════════

def _score_annual(cd, h, lk=None):
    """Check annual placements and Varshphal data."""
    sc=0; factors=[]
    lk=_sj(lk) if lk else {}

    # Try standard varshphal keys first
    varsh=lk.get("varshphal",lk.get("varshaphal",lk.get("annual",{})))

    # If no varshphal dict, check for "placements" (LK annual house positions)
    placements = lk.get("placements", {})
    if placements and not varsh:
        # placements = {planet: annual_house_number}
        # Check if any planet's annual house matches this instrument's house
        hl = _hl(cd, h)  # lord of this house
        for planet, annual_house in placements.items():
            if isinstance(annual_house, int) and annual_house == h:
                en = ENERGY.get(planet, planet)
                sc += 8
                factors.append(en + " placed in this instrument for the year — annual activation")
            # If the house lord is placed in a strong annual house
            if planet.lower() == hl.lower() and isinstance(annual_house, int):
                en2 = ENERGY.get(planet, planet)
                if annual_house in [1, 4, 7, 10]:
                    sc += 10
                    factors.append(en2 + " (instrument lord) in angular annual house — strong yearly position")
                elif annual_house in [6, 8, 12]:
                    sc -= 8
                    factors.append(en2 + " (instrument lord) in dusthana annual house — yearly pressure")
    if isinstance(varsh,dict):
        year_lord=varsh.get("year_lord",varsh.get("yearLord",""))
        muntha_house=varsh.get("muntha_house",varsh.get("muntha",0))
        if isinstance(muntha_house,str):
            try: muntha_house=int(muntha_house)
            except: muntha_house=0

        # Year lord governs this house
        hl=_hl(cd,h)
        if year_lord and year_lord.lower()==hl.lower():
            sc+=15; factors.append("Annual Year Lord governs this instrument — yearly focus active")

        # Muntha in this house
        if muntha_house==h:
            sc+=20; factors.append("Muntha (Yearly Focus Point) in this instrument — TOP PRIORITY this year")
        elif muntha_house in [6,8,12] and h in [6,8,12]:
            sc-=10; factors.append("Muntha in dusthana — yearly pressure on internal restructuring")

        # Annual predictions for this house
        annual_preds=varsh.get("predictions",varsh.get("house_predictions",{}))
        if isinstance(annual_preds,dict):
            house_pred=annual_preds.get(str(h),annual_preds.get(h,""))
            if house_pred:
                factors.append("Annual prediction available for this instrument")
                sc+=5

    return sc, factors


# ═══════════════════════════════════════════════════════════════════
# CONVERGENCE SCORER (weighted)
# ═══════════════════════════════════════════════════════════════════

def _converge(clock_sc, traffic_sc, infra_sc, annual_sc, jaimini_sc=0):
    """
    Weighted convergence: Vimsottari 30%, Jaimini 15%, Transit 25%, D-Chart 20%, Varshphal 10%.
    When Jaimini is present, Vimsottari drops from 40% to 30% and Jaimini gets 15%.
    Total always = 100%.
    """
    def norm(v, lo=-40, hi=50): return max(0, min(100, ((v-lo)/(hi-lo))*100))

    nc=norm(clock_sc, -40, 50)
    nj=norm(jaimini_sc, -20, 30)
    nt=norm(traffic_sc, -30, 30)
    ni=norm(infra_sc, 0, 25)
    na=norm(annual_sc, -15, 25)

    has_jaimini = abs(jaimini_sc) > 0
    if has_jaimini:
        weighted = nc*0.30 + nj*0.15 + nt*0.25 + ni*0.20 + na*0.10
    else:
        weighted = nc*WEIGHTS["dasha"] + nt*WEIGHTS["transit"] + ni*WEIGHTS["dchart"] + na*WEIGHTS["varshphal"]

    all_scores = [clock_sc, traffic_sc, infra_sc, annual_sc]
    if has_jaimini:
        all_scores.append(jaimini_sc)

    sources_active = sum(1 for s in all_scores if abs(s) > 5)

    if sources_active >= 4:
        pos = sum(1 for s in all_scores if s > 5)
        neg = sum(1 for s in all_scores if s < -5)
        if pos >= 4: lock = "QUAD LOCK POSITIVE"
        elif pos >= 3: lock = "TRIPLE LOCK POSITIVE"
        elif neg >= 3: lock = "TRIPLE LOCK NEGATIVE"
        else: lock = "MIXED SIGNALS"
    elif sources_active >= 3:
        pos = sum(1 for s in all_scores if s > 5)
        neg = sum(1 for s in all_scores if s < -5)
        if pos >= 3: lock = "TRIPLE LOCK POSITIVE"
        elif neg >= 3: lock = "TRIPLE LOCK NEGATIVE"
        else: lock = "MIXED SIGNALS"
    elif sources_active >= 2:
        lock = "DOUBLE CONFIRM"
    else:
        lock = "SINGLE SOURCE"

    return round(weighted, 1), lock


# ═══════════════════════════════════════════════════════════════════
# MASTER SCAN: 12-INSTRUMENT DIAGNOSTIC
# ═══════════════════════════════════════════════════════════════════

def scan_all_instruments(cd, jd=None, lk=None, current_dasha=None, transits=None):
    """
    Run the full 6-layer diagnostic across all 12 instruments.

    Layers: Blueprint, Infrastructure, Vimsottari Clock, Jaimini Clock,
            Transit Traffic, Annual Agenda.

    Returns dict keyed by instrument key.
    """
    cd=_sj(cd)
    if transits is None and HAS_SWE:
        transits=_get_current_transits()

    results={}
    for h, meta in INSTRUMENTS.items():
        # Layer 1: Blueprint (permanent)
        bp_sc, bp_f = _score_blueprint(cd, h, jd)

        # Layer 2: Infrastructure (D-charts)
        inf_sc, inf_f = _score_infrastructure(cd, h)

        # Layer 3A: Vimsottari Clock (Dasha + LK)
        clk_sc, clk_f = _score_clock(cd, h, current_dasha, lk)

        # Layer 3B: Jaimini Clock (Chara Dasha + Karakas + Arudhas + Argala)
        jai_sc, jai_f = _score_jaimini_clock(cd, h, jd) if jd else (0, [])

        # Layer 4: Traffic (Live Transits)
        trf_sc, trf_f = _score_traffic(cd, h, transits)

        # Layer 5: Annual Agenda (Varshphal + Muntha)
        ann_sc, ann_f = _score_annual(cd, h, lk)

        # Weighted convergence (6 layers)
        signal_score, lock = _converge(clk_sc, trf_sc, inf_sc, ann_sc, jai_sc)

        # Determine status
        if signal_score >= 70: status="PEAK"; color="teal"; verdict="EXECUTE"
        elif signal_score >= 50: status="ACTIVE"; color="teal"; verdict="ADVANCE"
        elif signal_score >= 35: status="PREPARING"; color="amber"; verdict="POSITION"
        elif signal_score >= 20: status="FRICTION"; color="amber"; verdict="COMPENSATE"
        elif signal_score >= 10: status="DORMANT"; color="muted"; verdict="MONITOR"
        else: status="BLOCKED"; color="red"; verdict="RESTRUCTURE"

        # Build symptom summary
        all_factors=clk_f+jai_f+trf_f+inf_f+ann_f
        negative=[f for f in all_factors if any(w in f.lower() for w in ["pressure","weak","sleeping","debt","rin","blocked","stress","malefic","opposition","conflict","friction","challenge"])]
        positive=[f for f in all_factors if any(w in f.lower() for w in ["peak","active","boost","benefic","governs","fortune","protective","activated","rise","wealth","convergence","argala","karakamsa"])]
        symptom=negative[0] if negative else (positive[0] if positive else "No active disruption")

        results[meta["key"]]={
            "house": h,
            "label": meta["label"],
            "name": meta["name"],
            "blueprint_score": bp_sc,
            "blueprint_factors": bp_f,
            "signal_score": signal_score,
            "signal_status": status,
            "signal_color": color,
            "verdict": verdict,
            "convergence_lock": lock,
            "symptom": symptom,
            "layers": {
                "blueprint": {"score": bp_sc, "factors": bp_f},
                "infrastructure": {"score": inf_sc, "factors": inf_f},
                "vimsottari_clock": {"score": clk_sc, "factors": clk_f},
                "jaimini_clock": {"score": jai_sc, "factors": jai_f},
                "traffic": {"score": trf_sc, "factors": trf_f},
                "annual": {"score": ann_sc, "factors": ann_f},
            },
        }

    return results


# ═══════════════════════════════════════════════════════════════════
# WEALTH BLUEPRINT (headline card)
# ═══════════════════════════════════════════════════════════════════

def calculate_wealth_blueprint(cd, jd=None):
    cd=_sj(cd); yogas=[]
    if _lc(cd,2,11): yogas.append({"name":"Wealth-Gains Axis","desc":"Earning and gains structurally linked"})
    if _lc(cd,1,2): yogas.append({"name":"Self-Made Wealth","desc":"Identity tied to wealth creation"})
    if _lc(cd,5,9): yogas.append({"name":"Fortune Convergence","desc":"Intelligence and luck aligned"})
    if _lc(cd,9,10): yogas.append({"name":"Authority-Fortune Lock","desc":"Power positions bring wealth"})
    jup=_fp(cd,"Jupiter")
    if jup and jup.get("house") in [2,5,9,11]: yogas.append({"name":"Growth Amplifier Active","desc":"Expansion in wealth house"})
    ven=_fp(cd,"Venus")
    if ven and ven.get("house") in [2,7]: yogas.append({"name":"Magnetism-Wealth Link","desc":"Attraction feeds earning"})
    l11d=_fp(cd,_hl(cd,11))
    if _strong(l11d): yogas.append({"name":"Revenue Engine Strong","desc":"Gains pipeline robust"})
    rahu=_fp(cd,"Rahu")
    if rahu and rahu.get("house") in [10,11]: yogas.append({"name":"Ambition-Wealth Axis","desc":"Drive wired to gains"})
    kr=_karakas(jd)
    amk=kr.get("AmK",""); amk_st="UNKNOWN"
    if amk:
        ad=_fp(cd,amk)
        if _strong(ad): amk_st="PEAK"; yogas.append({"name":"Career Significator Peak","desc":ENERGY.get(amk,amk)+" at maximum"})
        elif ad: amk_st="ACTIVE"
    yc=len(yogas)
    if yc>=5: tier,cap="UNICORN BLUEPRINT","$1B+"
    elif yc>=3: tier,cap="HIGH-GROWTH BLUEPRINT","$100M+"
    elif yc>=2: tier,cap="GROWTH BLUEPRINT","$10M+"
    elif yc>=1: tier,cap="STANDARD BLUEPRINT","$1M+"
    else: tier,cap="EMERGING BLUEPRINT","Developing"
    return {"tier":tier,"capacity":cap,"verified":yc>=1,"yoga_count":yc,"yogas":yogas,"amk_status":amk_st,"amk_planet":amk}


# ═══════════════════════════════════════════════════════════════════
# LIFE EVENT TRIGGERS
# ═══════════════════════════════════════════════════════════════════

def scan_life_events(cd, current_dasha=None, jd=None):
    cd=_sj(cd); md,ad=_pd(current_dasha); active=[]
    for ev in LIFE_EVENTS:
        sc=0; sigs=[]
        for h in ev["houses"]:
            hl=_hl(cd,h)
            if md and md.lower()==hl.lower(): sc+=30; sigs.append("Chapter lord governs "+INSTRUMENTS.get(h,{}).get("name","H"+str(h)))
            if ad and ad.lower()==hl.lower(): sc+=20; sigs.append("Sub-period activates "+INSTRUMENTS.get(h,{}).get("name","H"+str(h)))
        for pl in ev["planets"]:
            for h in ev["houses"]:
                pd=_fp(cd,pl)
                if pd and pd.get("house")==h: sc+=15; sigs.append(ENERGY.get(pl,pl)+" in key position")
        if len(ev["houses"])>=2 and _lc(cd,ev["houses"][0],ev["houses"][1]): sc+=20; sigs.append("Key instrument lords connected")
        if sc>=30:
            ph="ACTIVE" if sc>=60 else "WARMING" if sc>=40 else "POSSIBLE"
            active.append({"id":ev["id"],"name":ev["name"],"label":ev["label"],"score":min(100,sc),"phase":ph,"signals":sigs})
    active.sort(key=lambda e:-e["score"])
    return active


# ═══════════════════════════════════════════════════════════════════
# SYSTEM STATUS (single-line header)
# ═══════════════════════════════════════════════════════════════════

def calculate_system_status(instruments):
    if not instruments: return {"status":"INITIALIZING","color":"amber","detail":"Run first scan"}
    blocked=[k for k,v in instruments.items() if v.get("signal_status") in ("BLOCKED",)]
    friction=[k for k,v in instruments.items() if v.get("signal_status") in ("FRICTION","DORMANT")]
    peak=[k for k,v in instruments.items() if v.get("signal_status") in ("PEAK","ACTIVE")]
    if blocked: return {"status":"RESTRUCTURING PHASE","color":"red","detail":str(len(blocked))+" instrument(s) blocked: "+", ".join(v.upper() for v in blocked[:3])}
    if len(friction)>=4: return {"status":"FRICTION ELEVATED","color":"amber","detail":str(len(friction))+" instruments under friction"}
    if len(peak)>=6: return {"status":"PEAK WINDOW ACTIVE","color":"teal","detail":str(len(peak))+" instruments at peak"}
    if peak: return {"status":"PARTIAL ACTIVATION","color":"teal","detail":str(len(peak))+" instrument(s) active, "+str(len(friction))+" in friction"}
    return {"status":"ALL SYSTEMS STABLE","color":"teal","detail":"No active disruptions"}


# ═══════════════════════════════════════════════════════════════════
# THREE-POINT DIAGNOSTIC
# ═══════════════════════════════════════════════════════════════════

def build_three_point_diagnostic(wbp, instruments):
    promise=wbp.get("tier","BLUEPRINT")+": ACTIVE"
    promise_d=wbp.get("capacity","Growth")+" Blueprint (Verified)" if wbp.get("verified") else "Blueprint developing"

    best_k=None; best_sig=0
    for k,v in (instruments or {}).items():
        if v.get("signal_score",0)>best_sig: best_sig=v["signal_score"]; best_k=k
    if best_k and best_sig>=50:
        bv=instruments[best_k]
        window=bv.get("label","")+": "+bv.get("signal_status","")
        window_d=bv.get("symptom","")
    else:
        window="BUILDING FOUNDATIONS"; window_d="No instrument at peak — continue building"

    worst_k=None; worst_sig=100
    for k,v in (instruments or {}).items():
        if v.get("signal_score",0)<worst_sig: worst_sig=v["signal_score"]; worst_k=k
    if worst_k and worst_sig<35:
        wv=instruments[worst_k]
        move="STRATEGY: "+wv.get("verdict","MONITOR")
        move_d=wv.get("symptom","Continue trajectory")
    else:
        move="STRATEGY: EXECUTE"; move_d="All instruments clear — push priorities"

    return {
        "promise":{"label":"THE PROMISE","value":promise,"detail":promise_d},
        "window":{"label":"THE WINDOW","value":window,"detail":window_d},
        "move":{"label":"THE MOVE","value":move,"detail":move_d},
    }


# ═══════════════════════════════════════════════════════════════════
# DIAGNOSTIC PROMPT BLOCK (for Claude injection)
# ═══════════════════════════════════════════════════════════════════

def build_diagnostic_prompt_block(cd, question, concern=None, jd=None, lk=None, current_dasha=None):
    """Build diagnostic context block for Claude prompt injection."""
    cd=_sj(cd)
    instruments=scan_all_instruments(cd, jd, lk, current_dasha)

    domain=concern if concern and concern in DOMAIN_VOCABULARY else "general"
    vocab=DOMAIN_VOCABULARY.get(domain,DOMAIN_VOCABULARY["general"])

    # Find most relevant instrument for this domain
    domain_house_map={"career":10,"wealth":2,"finance":8,"relationship":7,"health":1,"legal":6,"property":4,"education":9,"children":5,"foreign":12,"general":10}
    primary_h=domain_house_map.get(domain,10)
    primary_key=INSTRUMENTS.get(primary_h,{}).get("key","authority")
    primary=instruments.get(primary_key,{})

    lines=["="*60, "DIAGNOSTIC PRE-SCAN — 5-LAYER BLOOD WORK", "="*60]
    lines.append("DOMAIN: "+domain.upper())
    lines.append("ACTIVE DASHA: "+str(current_dasha or "unknown"))
    lines.append("TONE: "+vocab["tone"])
    lines.append("INSTRUCTION: "+vocab["instruction"])
    lines.append("")

    if primary:
        lines.append("PRIMARY INSTRUMENT: "+primary.get("label",""))
        lines.append("BLUEPRINT SCORE: "+str(primary.get("blueprint_score",""))+" / 100")
        lines.append("LIVE SIGNAL: "+str(primary.get("signal_score",""))+" / 100")
        lines.append("STATUS: "+primary.get("signal_status",""))
        lines.append("VERDICT: "+primary.get("verdict",""))
        lines.append("CONVERGENCE: "+primary.get("convergence_lock",""))
        lines.append("SYMPTOM: "+primary.get("symptom",""))
        lines.append("")
        for layer_name, layer_data in primary.get("layers",{}).items():
            if layer_data.get("factors"):
                lines.append(layer_name.upper()+": "+"; ".join(layer_data["factors"][:2]))

    # Cross-instrument alerts
    blocked=[k for k,v in instruments.items() if v.get("signal_status") in ("BLOCKED","FRICTION")]
    if blocked:
        lines.append("")
        lines.append("CROSS-INSTRUMENT ALERTS:")
        for bk in blocked[:3]:
            bv=instruments[bk]
            lines.append("  - "+bv.get("label","")+": "+bv.get("signal_status","")+" ("+bv.get("verdict","")+")")

    lines.append("")
    lines.append("VOCABULARY: "+", ".join(vocab["nouns"][:5]))
    lines.append("="*60)
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════

def build_executive_summary(chart_data, jaimini_data=None, lal_kitab_data=None, current_dasha=None, dasha_periods=None):
    """Complete executive summary — wire to GET /api/v1/executive-summary/{chart_id}"""
    cd=_sj(chart_data)
    transits=_get_current_transits() if HAS_SWE else {}
    instruments=scan_all_instruments(cd, jaimini_data, lal_kitab_data, current_dasha, transits)
    wbp=calculate_wealth_blueprint(cd, jaimini_data)
    events=scan_life_events(cd, current_dasha, jaimini_data)
    sys_status=calculate_system_status(instruments)
    diagnostic=build_three_point_diagnostic(wbp, instruments)

    return {
        "instruments": instruments,
        "wealth_blueprint": wbp,
        "life_events": events,
        "system_status": sys_status,
        "diagnostic_card": diagnostic,
        "current_dasha": current_dasha,
        "transit_computed": bool(transits),
    }


def get_domain_vocabulary(domain):
    return DOMAIN_VOCABULARY.get(domain, DOMAIN_VOCABULARY["general"])


# Backward compatibility aliases
def scan_chart_symptoms(cd, jd=None, lk=None, current_dasha=None):
    """Legacy compatibility — returns flat symptom list from instrument scan."""
    instruments=scan_all_instruments(_sj(cd), jd, lk, current_dasha)
    symptoms=[]
    for key, inst in instruments.items():
        if inst.get("signal_status") in ("BLOCKED","FRICTION","DORMANT"):
            symptoms.append({
                "id": key.upper()+"_"+inst.get("signal_status",""),
                "domain": _instrument_to_domain(inst.get("house",0)),
                "source": "multi_layer",
                "severity": 3 if inst["signal_status"]=="BLOCKED" else 2 if inst["signal_status"]=="FRICTION" else 1,
                "symptom": inst.get("symptom",""),
                "status_label": inst.get("signal_status",""),
                "verdict": inst.get("verdict",""),
                "jargon": {"ceo": inst.get("symptom",""), "general": inst.get("symptom","")},
                "action": "Check your "+inst.get("label","")+" instrument for details.",
                "convergence": inst.get("convergence_lock",""),
                "convergence_weight": 3 if "TRIPLE" in inst.get("convergence_lock","") else 2 if "DOUBLE" in inst.get("convergence_lock","") else 1,
            })
    symptoms.sort(key=lambda s: -s.get("severity",0))
    return symptoms


def get_domain_status(cd, jd=None, lk=None, current_dasha=None):
    """Legacy compatibility — returns domain status dict."""
    instruments=scan_all_instruments(_sj(cd), jd, lk, current_dasha)
    domain_map={"career":"authority","wealth":"reserves","relationship":"alliance","health":"vitals"}
    status={}
    for domain, ikey in domain_map.items():
        inst=instruments.get(ikey,{})
        status[domain]={
            "status_label": inst.get("signal_status","STABLE"),
            "verdict": inst.get("verdict","MONITOR"),
            "symptom": inst.get("symptom","No disruption"),
            "action": "Check "+inst.get("label","")+" for details",
            "source": "5_layer_scan",
            "convergence": inst.get("convergence_lock","NONE"),
            "severity": 3 if inst.get("signal_status")=="BLOCKED" else 2 if inst.get("signal_status")=="FRICTION" else 0,
            "id": ikey,
        }
    return status


def get_primary_symptom(cd, jd=None, lk=None, current_dasha=None, domain=None):
    symptoms=scan_chart_symptoms(cd, jd, lk, current_dasha)
    if domain:
        f=[s for s in symptoms if s["domain"]==domain]
        return f[0] if f else None
    return symptoms[0] if symptoms else None


def _instrument_to_domain(house):
    m={1:"health",2:"wealth",3:"general",4:"property",5:"children",6:"legal",7:"relationship",8:"wealth",9:"general",10:"career",11:"wealth",12:"foreign"}
    return m.get(house,"general")
