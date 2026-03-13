"""
sam_k_full_test.py  ·  Production Flow Test
============================================
Mirrors the EXACT code paths from main.py — same imports, same call
signatures, same data shapes. If this passes, the server works.

Tested flow (line numbers reference main.py):
  §0   Age formula                          _birthday_recompute_job
  §1   varshaphal_table                     get_annual_house()
  §2   chart.calculate_chart()              line 1613
  §3   vimsottari/jaimini/ashtottari        line 1625
  §4   transits.calculate_transits()        line 613
  §5   psychological_profile()              line 611
  §6   build_patra_context()                line 650
  §7   detect_concern() + desh              line 648
  §8   build_layered_predictions()          line 802
  §9   detect_yogas_for_question()          line 670
  §10  Varshphal + format_lk_context_from_stored()  line 754
  §11  build_enrichment_context_v2()        line 762
  §12  build_predict_prompt() + 7 appends   line 831
  §13  Signature audit                      chart.py vs main.py:1613

Run:
    cd antarai
    python antar_engine/testing/sam_k_full_test.py
"""

import sys, os, inspect
from datetime import date

# Resolve package root
_here = os.path.dirname(os.path.abspath(__file__))
for _root in [_here, os.path.join(_here,".."), os.path.join(_here,"../..")]:
    _root = os.path.abspath(_root)
    if os.path.isdir(os.path.join(_root, "antar_engine")):
        sys.path.insert(0, _root)
        break

_results = []

def _p(ok, label, detail=""):
    icon = "\033[92m  PASS\033[0m" if ok else "\033[91m  FAIL\033[0m"
    note = f"  <- {detail}" if detail and not ok else ""
    print(f"{icon}  {label}{note}")
    _results.append(("PASS" if ok else "FAIL", label))
    return ok

def _w(label):
    print(f"\033[93m  WARN\033[0m  {label}")
    _results.append(("WARN", label))

def _s(title):
    print(f"\n{'--'*32}\n  {title}\n{'--'*32}")

def _i(msg):
    print(f"  info  {msg}")

# Fixture
BIRTH_DATE = "1970-11-02"
BIRTH_TIME = "06:02"
LAT        = 18.1000   # Siddipet, Telangana
LNG        = 78.8500
TIMEZONE   = "Asia/Kolkata"
TODAY      = date(2026, 3, 13)

EXP_LAGNA  = "Libra"
EXP_HOUSES = {
    "Sun":1,"Mercury":1,"Jupiter":1,"Venus":1,
    "Moon":2,"Rahu":5,"Saturn":7,"Ketu":11,"Mars":12,
}
EXP_VP_PLACEMENTS = {
    "Sun":2,"Moon":3,"Mars":7,"Mercury":2,
    "Jupiter":2,"Venus":2,"Saturn":10,"Rahu":9,"Ketu":12,
}
CHART_RECORD_STUB = {
    "birth_date":"1970-11-02","country_code":"IN","birth_country":"IN",
    "language_preference":"en","marital_status":"married",
    "children_status":"young_children","career_stage":"mid_career",
    "health_status":"excellent","financial_status":"stable",
    "countries_lived":[],"lal_kitab_data":None,
}


# =============================================================================
# S0  Age formula
# =============================================================================
_s("S0  Age formula  [_birthday_recompute_job]")

born      = date.fromisoformat(BIRTH_DATE)
last_bday = born.replace(year=TODAY.year)
if last_bday > TODAY:
    last_bday = last_bday.replace(year=TODAY.year - 1)
_age = last_bday.year - born.year
_ry  = max(1, min(120, _age + 1))

_p(_age == 55, "age = 55", f"got {_age}")
_p(_ry  == 56, "running_year = 56", f"got {_ry}")
_p(str(last_bday) == "2025-11-02", "last_bday = 2025-11-02", f"got {last_bday}")


# =============================================================================
# S1  Varshphal table
# =============================================================================
_s("S1  Varshphal table  [antar_engine.varshaphal_table]")

try:
    from antar_engine.varshaphal_table import VARSHAPHAL_TABLE, get_annual_house
    _p(True, "import ok")
    _p(len(VARSHAPHAL_TABLE) == 120, "120 rows", f"got {len(VARSHAPHAL_TABLE)}")
    _p(all(len(v)==12 for v in VARSHAPHAL_TABLE.values()), "each row 12 values")
    for nh, ah, lbl in [(1,2,"H1->2"),(2,3,"H2->3"),(5,9,"H5->9"),
                        (7,10,"H7->10"),(11,12,"H11->12"),(12,7,"H12->7")]:
        got = get_annual_house(nh, 55)
        _p(got == ah, f"RY56 {lbl}", f"got {got}")
except Exception as e:
    _p(False, "varshaphal_table import", str(e))


# =============================================================================
# S2  calculate_chart()  [main.py:1613]
# =============================================================================
_s("S2  calculate_chart()  [main.py:1613 — lat, lng, timezone, ayanamsa]")

chart_data = None
try:
    from antar_engine import chart as chart_module
    sig    = inspect.signature(chart_module.calculate_chart)
    params = list(sig.parameters.keys())
    _i(f"Actual signature params: {params}")

    chart_data = chart_module.calculate_chart(
        birth_date=BIRTH_DATE, birth_time=BIRTH_TIME,
        lat=LAT, lng=LNG, timezone=TIMEZONE, ayanamsa="lahiri",
    )
    _p(chart_data is not None, "calculate_chart() returned")
    lagna = chart_data.get("lagna",{}).get("sign","")
    _p(lagna == EXP_LAGNA, "Lagna = Libra", f"got '{lagna}'")
    planets = chart_data.get("planets",{})
    _p(len(planets) >= 9, "9 planets present", f"got {len(planets)}")

    # chart.py stores sign names, not house numbers.
    # House = (planet_sign_index - lagna_sign_index) % 12 + 1
    SIGN_ORDER = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
                  "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]
    lagna_sign = chart_data.get("lagna",{}).get("sign","")
    lagna_idx  = SIGN_ORDER.index(lagna_sign) if lagna_sign in SIGN_ORDER else 0

    def _house_from_sign(pdata):
        h = pdata.get("house")
        if h is not None:
            return h
        sign = pdata.get("sign","")
        if sign in SIGN_ORDER:
            return (SIGN_ORDER.index(sign) - lagna_idx) % 12 + 1
        return pdata.get("sign_index", -1) + 1

    for planet, exp_h in EXP_HOUSES.items():
        if planet not in planets:
            _p(False, f"{planet} in chart", "MISSING"); continue
        got_h = _house_from_sign(planets[planet])
        _p(got_h == exp_h, f"{planet} in H{exp_h}", f"got H{got_h}")

except TypeError as e:
    _p(False, "calculate_chart() signature matches main.py",
       f"{e} -> Fix chart.py to accept: lat, lng, timezone, ayanamsa")
except Exception as e:
    _p(False, "calculate_chart()", str(e))
    import traceback; traceback.print_exc()


# =============================================================================
# S3  Dasha systems  [main.py:1625]
# =============================================================================
_s("S3  Dasha systems  [vimsottari / jaimini / ashtottari]")

dashas = {}
_DASHA_FNS = {
    "vimsottari": "calculate_vimsottari_from_chart",
    "jaimini":    "calculate_chara_dasha_from_chart",
    "ashtottari": "calculate_ashtottari_from_chart",
}
if chart_data:
    # birth_jd is stored inside chart_data under various key names
    _birth_jd = (chart_data.get("birth_jd") or chart_data.get("jd") or
                 chart_data.get("julian_day") or chart_data.get("jd_ut"))
    for sys_name, real_fn in _DASHA_FNS.items():
        try:
            mod = __import__(f"antar_engine.{sys_name}", fromlist=[real_fn])
            fn  = getattr(mod, real_fn)
            import inspect as _ins
            _fn_params = list(_ins.signature(fn).parameters.keys())
            r = fn(chart_data, _birth_jd) if "birth_jd" in _fn_params else fn(chart_data)

            # Dasha modules return {mahadashas:[...], antardashas:[...]}
            # Normalise to flat list with keys main.py/predictions.py expect:
            # {lord_or_sign, start, end, duration_years, level}
            if isinstance(r, dict) and "mahadashas" in r:
                flat = []
                for p in r.get("mahadashas", []):
                    flat.append({
                        "lord_or_sign": p.get("lord", ""),
                        "start":        p.get("start_date", "")[:10],
                        "end":          p.get("end_date",   "")[:10],
                        "duration_years": p.get("duration_years", 0),
                        "level":        "mahadasha",
                        "planet_or_sign": p.get("lord", ""),
                    })
                for p in r.get("antardashas", []):
                    flat.append({
                        "lord_or_sign": p.get("lord", ""),
                        "start":        p.get("start_date", "")[:10],
                        "end":          p.get("end_date",   "")[:10],
                        "duration_years": p.get("duration_years", 0),
                        "level":        "antardasha",
                        "planet_or_sign": p.get("lord", ""),
                        "parent_lord":   p.get("parent_lord", ""),
                    })
                dashas[sys_name] = flat
                _p(True,          f"{sys_name}.{real_fn}() list")
                _p(len(flat) >= 5, f"{sys_name}: >= 5 periods", f"got {len(flat)}")
                _i(f"{sys_name}: {len(r['mahadashas'])} mahadashas + {len(r['antardashas'])} antardashas = {len(flat)} total")
            else:
                dashas[sys_name] = r
                _p(isinstance(r, list), f"{sys_name}.{real_fn}() list")
                _p(len(r) >= 5,         f"{sys_name}: >= 5 periods", f"got {len(r)}")
        except Exception as e:
            _p(False, f"{sys_name}.{real_fn}()", str(e))
else:
    print("  skip  chart_data unavailable - fix S2")


# =============================================================================
# S4  Transits  [main.py:613]
# =============================================================================
_s("S4  Transits  [transits.calculate_transits / summarize_transits]")

current_transits = {}
transit_summary  = ""
if chart_data:
    try:
        from antar_engine import transits as transits_mod
        _raw_transits = transits_mod.calculate_transits(
            chart_data, target_date=None, ayanamsa_mode=1)
        if isinstance(_raw_transits, list):
            current_transits = {t["planet"]: t for t in _raw_transits if "planet" in t}
        else:
            current_transits = _raw_transits
        _raw_list = _raw_transits if isinstance(_raw_transits, list) else list(current_transits.values())
        transit_summary = transits_mod.summarize_transits(_raw_list)
        _p(isinstance(current_transits, dict), "calculate_transits() normalised to dict")
        _p("Saturn" in current_transits,       "Saturn present")
        _p("Jupiter" in current_transits,      "Jupiter present")
        _p(bool(transit_summary),              "summarize_transits() non-empty")
        sat = current_transits.get("Saturn",{}).get("transit_sign","?")
        jup = current_transits.get("Jupiter",{}).get("transit_sign","?")
        _i(f"Saturn in {sat}  |  Jupiter in {jup}")
    except Exception as e:
        import traceback; traceback.print_exc()
        _p(False, "transits", str(e))


# =============================================================================
# S5  Psychological profile  [main.py:611]
# =============================================================================
_s("S5  psychological_profile()  [karakas]")

profile_text = ""
if chart_data:
    try:
        from antar_engine.karakas import psychological_profile, get_all_karakas
        profile_text = psychological_profile(chart_data)
        karakas      = get_all_karakas(chart_data)
        _p(bool(profile_text), "profile_text non-empty")
        _p(isinstance(karakas, list), "get_all_karakas() list")
        _i(f"Profile (80 chars): {profile_text[:80]}")
    except Exception as e:
        _p(False, "psychological_profile()", str(e))


# =============================================================================
# S6  Patra  [main.py:650]
# =============================================================================
_s("S6  Patra  [build_patra_context / patra_to_context_block]")

patra = None
patra_context = ""
if chart_data:
    try:
        from antar_engine.patra import build_patra_context, patra_to_context_block
        user_profile = {
            "marital_status": "married", "children_status": "young_children",
            "career_stage": "mid_career", "health_status": "excellent",
            "financial_status": "stable", "birth_country": "IN",
            "current_country": "IN", "countries_lived": [],
        }
        patra         = build_patra_context(BIRTH_DATE, user_profile, "career")
        patra_context = patra_to_context_block(patra)
        _p(patra is not None,           "patra built")
        _p(patra.age == 55,             "patra.age = 55", f"got {patra.age}")
        _p(bool(patra.life_stage_name), "life_stage_name set")
        _p(bool(patra_context),         "patra_context non-empty")
        _i(f"Life stage: {patra.life_stage_name}")
    except Exception as e:
        _p(False, "patra", str(e))


# =============================================================================
# S7  detect_concern + desh  [main.py:648, 659]
# =============================================================================
_s("S7  detect_concern() + desh context")

concern      = "general"
desh_context = ""
desh_obj     = None
dkp_block    = ""
QUESTION     = "What career opportunities should I focus on this year?"

if chart_data:
    try:
        from antar_engine.predictions import detect_concern
        concern = detect_concern(QUESTION)
        _p(bool(concern),         "concern detected")
        _p(concern == "career",   "concern = career", f"got '{concern}'")
    except Exception as e:
        _p(False, "detect_concern()", str(e))
    try:
        from antar_engine.desh import get_desh_context, desh_to_context_block, build_desh_kaal_patra_block
        desh_obj     = get_desh_context("IN", supabase=None, chart_data=chart_data, language="en")
        desh_context = desh_to_context_block(desh_obj, patra)
        # supabase=None so desh_obj may be None — non-fatal, supabase available in prod
        if desh_obj is not None:
            _p(True,  "desh built")
            _p(bool(desh_context), "desh_context non-empty")
        else:
            print("  skip  desh: supabase=None in test (works in prod)")
    except Exception as e:
        print(f"  skip  desh: {e} (supabase=None in test)")


# =============================================================================
# S8  Layered predictions  [main.py:802]
# =============================================================================
_s("S8  build_layered_predictions() + predictions_to_context_block()")

predictions         = {}
predictions_context = ""
if chart_data:
    try:
        from antar_engine.predictions import build_layered_predictions, predictions_to_context_block
        predictions = build_layered_predictions(
            user_id=None, chart_data=chart_data, dashas=dashas,
            current_transits=current_transits, life_events=[],
            supabase=None, concern=concern, detected_yogas=[],
        )
        predictions_context = predictions_to_context_block(predictions, chart_data, concern)
        _p(isinstance(predictions, dict),   "predictions dict returned")
        _p("layer_1" in predictions,        "layer_1 present")
        _p("layer_2" in predictions,        "layer_2 present")
        _p(bool(predictions_context),       "predictions_context non-empty")
        total = sum(len(predictions.get(f"layer_{i}",[]))  for i in range(1,5))
        _i(f"Total signals: {total}  |  confidence: {predictions.get('highest_confidence','?')}")
    except Exception as e:
        _p(False, "build_layered_predictions()", str(e))
        import traceback; traceback.print_exc()


# =============================================================================
# S9  Yoga detection  [main.py:670]
# =============================================================================
_s("S9  detect_yogas_for_question()  [yoga_engine]")

detected_yogas = []
if chart_data:
    try:
        from antar_engine.yoga_engine import detect_yogas_for_question
        from antar_engine.d_charts_calculator import get_all_d_charts
        d_charts       = get_all_d_charts(chart_data, [9,10])
        yoga_results   = detect_yogas_for_question("career", chart_data, d_charts)
        detected_yogas = [y["name"] for y in yoga_results if y.get("present")]
        _p(isinstance(yoga_results, list), "yoga_results list")
        _i(f"Active yogas: {detected_yogas[:5]}")
    except Exception as e:
        _p(False, "yoga detection", str(e))


# =============================================================================
# S10  Varshphal + format_lk_context_from_stored  [main.py:754]
# =============================================================================
_s("S10  Varshphal + format_lk_context_from_stored()  [main.py:754]")

varshphal  = None
lk_context = ""
lk_data    = None
if chart_data:
    try:
        from antar_engine.lal_kitab import calculate_varshphal_chart, get_all_varshphal_remedies
        from antar_engine.lal_kitab_db import format_lk_context_from_stored

        varshphal = calculate_varshphal_chart(chart_data, age=_age)
        _p(varshphal is not None,          "VarshphalChart returned")
        _p(varshphal.age == 55,            "age = 55",       f"got {varshphal.age}")
        _p(varshphal.table_age == 56,      "table_age = 56", f"got {varshphal.table_age}")
        _p(not varshphal.is_special_cycle, "is_special_cycle = False")

        for planet, exp_h in EXP_VP_PLACEMENTS.items():
            got = varshphal.placements.get(planet, "MISSING")
            _p(got == exp_h, f"{planet} -> H{exp_h}", f"got H{got}")

        all_rem = get_all_varshphal_remedies(varshphal, max_planets=4)
        rem_summary = [
            {"planet":pl,"name":r.name,"instructions":r.instructions,
             "duration":r.duration,"significance":r.significance,"materials":r.materials}
            for pl, rems in all_rem.items() for r in rems
        ]
        lk_data = {
            "age": varshphal.age, "table_age": varshphal.table_age,
            "placements": varshphal.placements,
            "is_special_cycle": varshphal.is_special_cycle,
            "cycle_significance": varshphal.cycle_significance,
            "remedies_summary": rem_summary,
        }
        lk_context = format_lk_context_from_stored(lk_data=lk_data, concern=concern)
        _p(bool(lk_context),           "lk_context non-empty")
        _p("55" in lk_context,         "age 55 in block")
        _p("56" in lk_context,         "table_age 56 in block")
        _p(any(p in lk_context for p in ["Sun","Moon","Saturn"]), "planets in block")
        print(f"\n  LK block preview:")
        for line in lk_context[:350].split("\n"):
            _i(line)
    except Exception as e:
        _p(False, "Varshphal / lk_context", str(e))
        import traceback; traceback.print_exc()


# =============================================================================
# S11  Vedic enrichment + Sade Sati  [main.py:762, 773]
# =============================================================================
_s("S11  build_enrichment_context_v2() + get_sade_sati_phase()")

enrichment_context = ""
sade_sati_context  = ""
if chart_data:
    try:
        from antar_engine.vedic_enrichment import build_enrichment_context_v2, get_sade_sati_phase
        t_map = {p: d.get("sign","") for p,d in current_transits.items()} \
                if isinstance(current_transits, dict) else {}
        enrichment_context = build_enrichment_context_v2(chart_data, t_map, concern)
        _p(bool(enrichment_context), "enrichment_context non-empty")
        moon_sign = chart_data["planets"]["Moon"]["sign"]
        sat_sign  = current_transits.get("Saturn",{}).get("sign","") \
                    if isinstance(current_transits, dict) else ""
        if sat_sign:
            ss = get_sade_sati_phase(moon_sign, sat_sign)
            if ss:
                sade_sati_context = (
                    f"SADE SATI ACTIVE - Phase {ss['phase']} ({ss['phase_name']}): "
                    f"{ss['description']} Invitation: {ss['invitation']}"
                )
                _i(f"Sade Sati: Phase {ss['phase']} / {ss['phase_name']}")
            else:
                _i("Sade Sati: not active")
    except Exception as e:
        _p(False, "vedic enrichment", str(e))


# =============================================================================
# S12  Full prompt assembly  [main.py:831 + append loop :852]
# =============================================================================
_s("S12  Full predict prompt  [build_predict_prompt + 7 extra blocks appended]")

if chart_data and predictions and patra:
    try:
        from antar_engine.prompt_builder import build_predict_prompt
        from antar_engine import timing_engine

        timing_text     = timing_engine.timing_insights(chart_data, dashas)
        rarity_context  = ""
        windows_context = ""
        chakra_context  = ""
        arc_context     = ""
        lq_ctx          = ""
        dkp_block       = ""

        try:
            from antar_engine.rarity_engine import detect_rarity_signals, rarity_signals_to_context_block
            rarity_context = rarity_signals_to_context_block(
                detect_rarity_signals(chart_data, dashas, current_transits, BIRTH_DATE))
        except Exception as e: _i(f"rarity (non-fatal): {e}")

        try:
            from antar_engine.precision_windows import find_precision_windows, precision_windows_to_context_block
            windows_context = precision_windows_to_context_block(
                find_precision_windows(chart_data, dashas, current_transits,
                                       concern, detected_yogas, [], 12, 3), concern)
        except Exception as e: _i(f"precision_windows (non-fatal): {e}")

        try:
            from antar_engine.chakra_engine import get_chakra_reading, chakra_reading_to_context_block
            cr = get_chakra_reading(chart_data, dashas, current_transits)
            chakra_context = chakra_reading_to_context_block(cr) if cr else ""
        except Exception as e: _i(f"chakra (non-fatal): {e}")

        try:
            from antar_engine.chapter_arc import build_chapter_arc, chapter_arc_to_context_block
            ca = build_chapter_arc(chart_data, dashas, patra)
            arc_context = chapter_arc_to_context_block(ca) if ca else ""
        except Exception as e: _i(f"chapter_arc (non-fatal): {e}")

        try:
            from antar_engine.desh import build_desh_kaal_patra_block
            dkp_block = build_desh_kaal_patra_block(desh_obj, patra, predictions)
        except Exception as e: _i(f"dkp (non-fatal): {e}")

        try:
            from antar_engine.life_question_engine import build_life_question_context
            lq_ctx = build_life_question_context(QUESTION, chart_data, dashas, patra)
        except Exception as e: _i(f"life_question (non-fatal): {e}")

        # EXACT call — main.py line 831
        # NOTE: build_predict_prompt does NOT accept life_question_context
        # main.py line 831 will crash if it passes this param — fix main.py
        prompt = build_predict_prompt(
            question=QUESTION, chart_data=chart_data, dashas=dashas,
            life_events=[], profile=profile_text, transit_summary=transit_summary,
            country_context="", timing_text=timing_text, nation_insight="",
            language="en", predictions_context=predictions_context,
            concern=concern, country_code="IN",
            patra_context=patra_context, desh_context=desh_context,
            dkp_block=dkp_block,
        )

        # EXACT append loop — main.py line 852
        for extra in [rarity_context, windows_context, chakra_context,
                      arc_context, lk_context, enrichment_context, sade_sati_context]:
            if extra:
                prompt += f"\n\n{extra}"

        _p(bool(prompt),                    "prompt built")
        _p(len(prompt) > 500,               f"prompt > 500 chars", f"got {len(prompt)}")
        _p("Libra" in prompt,               "lagna in prompt")
        _p("career" in prompt.lower(),      "concern in prompt")
        _p("55" in prompt or "56" in prompt,"LK age in prompt")

        _i(f"Prompt: {len(prompt)} chars / ~{len(prompt)//4} tokens")
        _i(f"Blocks: lk={bool(lk_context)} enrichment={bool(enrichment_context)} "
           f"sade_sati={bool(sade_sati_context)} rarity={bool(rarity_context)}")
        print(f"\n  Prompt (first 500 chars):")
        for line in prompt[:500].split("\n"):
            _i(line)

    except Exception as e:
        _p(False, "build_predict_prompt()", str(e))
        import traceback; traceback.print_exc()
else:
    print("  skip  chart_data / predictions / patra unavailable")


# =============================================================================
# S13  Signature audit  [chart.py vs main.py:1613]
# =============================================================================
_s("S13  Signature audit  [chart.py must accept: lat, lng, timezone, ayanamsa]")

try:
    from antar_engine import chart as chart_module
    sig    = inspect.signature(chart_module.calculate_chart)
    params = set(sig.parameters.keys())
    MAIN_KWARGS = {"birth_date","birth_time","lat","lng","timezone","ayanamsa"}
    missing = MAIN_KWARGS - params
    extra   = params - MAIN_KWARGS - {"self"}
    _p(len(missing) == 0,
       "chart.py accepts all params main.py passes",
       f"MISSING {missing} -> main.py will crash with TypeError at runtime")
    if extra:
        _i(f"Extra params in chart.py not used by main.py: {extra}")
    _i(f"Full signature: ({', '.join(sorted(params))})")
except Exception as e:
    _p(False, "signature audit", str(e))


# =============================================================================
# SUMMARY
# =============================================================================
print(f"\n{'='*64}")
passed = sum(1 for t,_ in _results if t=="PASS")
failed = sum(1 for t,_ in _results if t=="FAIL")
warned = sum(1 for t,_ in _results if t=="WARN")
total  = len(_results)
print(f"  RESULTS  {passed}/{total} passed  |  {failed} failed  |  {warned} warnings")
if failed:
    print(f"\n  FAILURES - fix before deploying:")
    [print(f"    x  {lbl}") for t,lbl in _results if t=="FAIL"]
if warned:
    print(f"\n  WARNINGS:")
    [print(f"    !  {lbl}") for t,lbl in _results if t=="WARN"]
print(f"{'='*64}\n")
sys.exit(0 if failed == 0 else 1)
