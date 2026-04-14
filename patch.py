#!/usr/bin/env python3
"""
patch_past_predictions_accuracy.py
All 5 event types covered. Lagna-aware rules.
"""
import sys, ast
from pathlib import Path

PAST_EVENT_RULES = '''
## PAST EVENT TIMING — CLASSICAL VIMSOTTARI RULES

When a question asks about a PAST event, follow these steps exactly.

### STEP 1: Establish eligible year range using birth year + age

  Marriage (age 20-35):           birth_year+20 to birth_year+35
  First child (age 22-37):        birth_year+22 to birth_year+37 AND after marriage
  Second child:                   first_child_year+1 to first_child_year+4
  Foreign relocation (age 15-45): birth_year+15 to birth_year+45
  Divorce:                        marriage_year+5 to marriage_year+25

ELIMINATE any MD or AD window outside the eligible range.

### STEP 2: Find which MD covers the eligible year range

### STEP 3: Within that MD, apply AD priority rules

MARRIAGE:
  1. Saturn AD = formal legal union, ceremony, registration. STRONGEST.
  2. Moon AD = emotional commitment (strongest if Moon rules 7H).
  3. Jupiter AD = dharmic marriage through family/wisdom.
  4. Venus AD = romance (weaker when Venus is already the MD planet).
  5. Rahu AD = unconventional romance BEGINS but rarely formalizes immediately.
  RULE: If both Rahu AD and Saturn AD are in range, CHOOSE Saturn AD for formal marriage.

FOREIGN RELOCATION:
  1. Rahu AD = unconventional foreign move, often permanent. STRONGEST.
  2. 12H lord AD (varies by lagna) = foreign through opportunity.
  3. Jupiter AD = foreign for education/wisdom.
  RULE: Rahu AD is almost always the primary trigger for permanent foreign relocation.

FIRST CHILD:
  1. Jupiter AD = natural karaka for children. STRONGEST.
  2. 5H lord AD (varies by lagna) = house of children.
  3. Mercury AD = 9H lord for many lagnas (luck/dharma/children). Strong.
  4. Moon AD = nurturing period. Moderate.
  RULE: First child MUST come AFTER marriage. Eliminate any AD before marriage AD.
  RULE: If Venus is MD planet, look for Jupiter AD or Mercury AD (9H lord) within Venus MD.

SECOND CHILD:
  1. AD immediately following first child AD (sequential, ~2 years later).
  2. Ketu AD = completion of karma, often brings second child.
  3. Mercury AD = 9H lord (classical 2nd child house).
  RULE: Find which AD is active ~2 years after the first child year.

DIVORCE / SEPARATION:
  1. Saturn AD during 7H lord MD = TEXTBOOK divorce. Moon MD + Saturn AD
     for Capricorn lagna (Moon = 7H lord). STRONGEST.
  2. Ketu AD = spiritual detachment, separation.
  3. Rahu AD = sudden/foreign element causing separation.
  RULE: Saturn AD during the 7H lord mahadasha is the most classical divorce signature.

### STEP 4: House lords by lagna

  Lagna      | 5H (children) | 7H (marriage) | 12H (foreign)
  -----------|---------------|---------------|---------------
  Aries      | Sun           | Venus         | Jupiter
  Taurus     | Mercury       | Mars          | Mars
  Gemini     | Venus         | Jupiter       | Venus
  Cancer     | Mars          | Saturn        | Mercury
  Leo        | Jupiter       | Saturn        | Moon
  Virgo      | Saturn        | Jupiter       | Sun
  Libra      | Saturn        | Mars          | Mercury
  Scorpio    | Jupiter       | Venus         | Jupiter
  Sagittarius| Mars          | Mercury       | Mars
  Capricorn  | Venus         | Moon          | Jupiter
  Aquarius   | Mercury       | Moon          | Saturn
  Pisces     | Moon          | Mercury       | Saturn

### STEP 5: State a specific year

  Give a SINGLE most likely year within the AD window.
  Use the middle of the AD window as the starting point.
  Example: Saturn AD = Jun 1996 - Aug 1999 → state "1997 or 1998"

### CRITICAL: NEVER predict past events as future events

  If a clear past dasha window exists, state when it OCCURRED.
  Do NOT say "this hasn't happened yet" or redirect to future dashas.
  The person is asking about something that ALREADY HAPPENED.
  If uncertain between two windows, give BOTH with reasoning.
'''

HIST_INJECTION = '''
                # ── PAST EVENT HISTORICAL DASHA INJECTION ─────────────────
                _past_keywords = [
                    "when did", "when was", "what year", "which year",
                    "when did i", "when were", "what happened", "how old",
                    "married", "marriage", "wedding",
                    "born", "birth", "child", "children", "son", "daughter",
                    "moved", "relocat", "immigrat", "america", "foreign",
                    "divorc", "separat", "ended", "split",
                    "cuándo", "cuando", "qué año", "que año",
                    "casé", "matrimonio", "boda", "nació", "hijo", "hija",
                    "mudé", "emigr", "divorcié", "separé", "terminó",
                ]
                _is_past_q = any(kw in request.question.lower() for kw in _past_keywords)

                if _is_past_q:
                    try:
                        _hist = supabase.table("dasha_periods") \\
                            .select("planet_or_sign,start_date,end_date,level,type,metadata,sequence") \\
                            .eq("chart_id", request.chart_id) \\
                            .eq("system", "vimsottari") \\
                            .order("sequence") \\
                            .execute()

                        _mds, _ads = [], []
                        for _row in _hist.data:
                            _lv = _row.get("level")
                            _tp = str(_row.get("type","")).lower()
                            if _lv == 1 or _tp in ("mahadasha","md","1"):
                                _mds.append(_row)
                            elif _lv == 2 or _tp in ("antardasha","ad","2"):
                                _ads.append(_row)

                        try:
                            _bd_row = supabase.table("charts") \\
                                .select("birth_date,chart_data") \\
                                .eq("id", request.chart_id) \\
                                .single().execute()
                            _birth_year = int(str(_bd_row.data.get("birth_date","1974"))[:4])
                            _lagna_sign = (_bd_row.data.get("chart_data") or {}) \\
                                .get("lagna", {}).get("sign", "unknown")
                        except Exception:
                            _birth_year = 1974
                            _lagna_sign = "unknown"

                        _tl = "\\n\\n## HISTORICAL VIMSOTTARI DASHA SEQUENCE\\n"
                        _tl += f"Birth year: {_birth_year} | Lagna: {_lagna_sign}\\n\\n"
                        _tl += "MAHADASHAS:\\n"
                        for _r in _mds:
                            _p = _r.get("planet_or_sign","")
                            _s = str(_r.get("start_date",""))[:10]
                            _e = str(_r.get("end_date",""))[:10]
                            _tl += f"  {_p} MD: {_s} to {_e}\\n"

                        _ads_by_md = {}
                        for _r in _ads:
                            _parent = (_r.get("metadata") or {}).get("parent_lord","?")
                            if _parent not in _ads_by_md:
                                _ads_by_md[_parent] = []
                            _p = _r.get("planet_or_sign","")
                            _s = str(_r.get("start_date",""))[:10]
                            _e = str(_r.get("end_date",""))[:10]
                            _ads_by_md[_parent].append(f"    {_p} AD: {_s} to {_e}")

                        _tl += "\\nANTARDASHAS BY MD:\\n"
                        for _md_p, _ad_lines in _ads_by_md.items():
                            _tl += f"  {_md_p} MD:\\n" + "\\n".join(_ad_lines) + "\\n"

                        _tl += f"""
## ELIGIBLE YEAR RANGES (birth year = {_birth_year})
  Marriage eligible:          {_birth_year+20} to {_birth_year+35}
  First child eligible:       {_birth_year+22} to {_birth_year+37} (must be after marriage)
  Second child:               first_child_year + 1 to + 4
  Foreign relocation:         {_birth_year+15} to {_birth_year+45}
  Divorce:                    marriage_year + 5 to + 25

Apply the classical AD priority rules from the system prompt.
State a specific year. Never predict past events as future windows.
"""
                        if isinstance(_json_ctx, dict):
                            _json_ctx["_historical_dasha"] = _tl
                        print(f"[json-v2] Past event: {len(_mds)} MDs, {len(_ads)} ADs, birth={_birth_year}, lagna={_lagna_sign}")

                    except Exception as _he:
                        print(f"[json-v2] Historical dasha failed (non-fatal): {_he}")
                # ── END PAST EVENT INJECTION ──────────────────────────────
'''


def patch_system_prompt():
    path = Path("antar_engine/predict_system_prompt_v2.py")
    if not path.exists():
        print("❌ predict_system_prompt_v2.py not found"); return False

    content = path.read_text(encoding="utf-8")

    # Remove old version if exists
    if "PAST EVENT TIMING" in content:
        start = content.find("## PAST EVENT TIMING")
        markers = ["## OUTPUT FORMAT", "## RESPONSE FORMAT", "YOUR MOVE", "ANTAR voice"]
        end = len(content)
        for m in markers:
            idx = content.find(m, start + 100)
            if 0 < idx < end:
                end = idx
                break
        content = content[:start] + content[end:]
        print("ℹ️  Removed old past event rules")

    landmarks = ["## OUTPUT FORMAT", "## RESPONSE FORMAT", "YOUR MOVE", 'ANTAR voice', '"""']
    inserted = False
    for lm in landmarks:
        if lm in content:
            content = content.replace(lm, PAST_EVENT_RULES + "\n" + lm, 1)
            inserted = True
            print(f"✅ Past event rules injected before: {lm[:40]}")
            break

    if not inserted:
        idx = content.rfind('"""')
        content = content[:idx] + PAST_EVENT_RULES + '\n"""'
        print("✅ Past event rules appended")

    try:
        ast.parse(content)
    except SyntaxError as e:
        print(f"❌ Syntax error: {e}"); return False

    path.write_text(content, encoding="utf-8")
    return True


def patch_main():
    path = Path("main.py")
    if not path.exists():
        print("❌ Run from ~/antarai/"); return False

    content = path.read_text(encoding="utf-8")

    # Remove all old injection blocks
    for start_m, end_m in [
        ("                # ── PAST EVENT HISTORICAL DASHA INJECTION", "                # ── END PAST EVENT INJECTION"),
        ("                # ── IMPROVED HISTORICAL DASHA INJECTION", "                # ── END HISTORICAL DASHA INJECTION"),
        ("                # Detect past-tense questions", "                print(f\"[json-v2] JSON path activated"),
    ]:
        if start_m in content and end_m in content:
            si = content.find(start_m)
            ei = content.find(end_m, si) + len(end_m) + 1
            content = content[:si] + content[ei:]
            print(f"ℹ️  Removed: {start_m[:50]}")

    landmark = "                _static_json = chart_static_to_json(_json_ctx)"
    if landmark not in content:
        print("❌ Landmark not found"); return False

    content = content.replace(landmark, HIST_INJECTION + "\n" + landmark, 1)
    print("✅ Historical dasha injection added")

    # Fix _json_system
    new_sys = '''                _hist_suffix = _json_ctx.get("_historical_dasha", "") if isinstance(_json_ctx, dict) else ""
                _json_system = (
                    PREDICT_SYSTEM_PROMPT_V2
                    + "\\n\\n## CHART DATA (JSON)\\n"
                    + _static_json
                    + "\\n\\n## LIVE DATA\\n"
                    + _live_json
                    + (_hist_suffix if _hist_suffix else "")
                )'''

    for old in [
        '''                _hist_suffix = ""
                if isinstance(_json_ctx, dict) and _json_ctx.get("_historical_dasha"):
                    _hist_suffix = _json_ctx["_historical_dasha"]
                _json_system = (
                    PREDICT_SYSTEM_PROMPT_V2
                    + "\\n\\n## CHART DATA (JSON)\\n"
                    + _static_json
                    + "\\n\\n## LIVE DATA\\n"
                    + _live_json
                    + (_hist_suffix if _hist_suffix else "")
                )''',
        '''                _json_system = (
                    PREDICT_SYSTEM_PROMPT_V2
                    + "\\n\\n## CHART DATA (JSON)\\n"
                    + _static_json
                    + "\\n\\n## LIVE DATA\\n"
                    + _live_json
                    + (_hist_suffix if _hist_suffix else "")
                )''',
        '''                _json_system = (
                    PREDICT_SYSTEM_PROMPT_V2
                    + "\\n\\n## CHART DATA (JSON)\\n"
                    + _static_json
                    + "\\n\\n## LIVE DATA\\n"
                    + _live_json
                )''',
    ]:
        if old in content:
            content = content.replace(old, new_sys, 1)
            print("✅ _json_system updated with hist_suffix")
            break

    try:
        ast.parse(content)
        print("✅ main.py syntax OK")
    except SyntaxError as e:
        print(f"❌ {e}"); return False

    path.write_text(content, encoding="utf-8")
    return True


def main():
    print("=" * 60)
    print("PAST PREDICTIONS PATCH — ALL 5 EVENT TYPES")
    print("=" * 60)
    ok1 = patch_system_prompt()
    print()
    ok2 = patch_main()
    print()
    if ok1 and ok2:
        print("✅ Done. Deploy:")
        print("  git add -A && git commit -m 'fix: past predictions all 5 event types' && git push")
        print()
        print("Then test:")
        print("  python3 /tmp/test_blind_claude.py")
        print()
        print("Expected: 60%+ (3-4 of 6 correct)")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
