"""
patch_lk_onthefly.py — Compute LK sleeping planets + enemy houses on-the-fly

Problem: lal_kitab_data JSONB has NO sleeping_planets, rin_debts, or enemy_houses.
But lal_kitab_advanced.py computes these on-the-fly in /predict.
Fix: Import and call those functions in the diagnostic engine's _score_clock().

Run: python patch_lk_onthefly.py
"""

TARGET = "antar_engine/symptom_library.py"

def patch():
    with open(TARGET, "r") as f:
        content = f.read()

    changes = 0

    # ═══════════════════════════════════════════════════════
    # PATCH 1: Add LK advanced import at top
    # ═══════════════════════════════════════════════════════

    if "lal_kitab_advanced" not in content:
        # Find the logger line and add import after it
        marker = "logger = logging.getLogger(__name__)"
        if marker in content:
            new_import = marker + """

# Import LK advanced functions for on-the-fly computation
try:
    from antar_engine.lal_kitab_advanced import detect_sleeping_planets, detect_enemy_houses, calculate_comprehensive_rin
    HAS_LK_ADVANCED = True
except ImportError:
    HAS_LK_ADVANCED = False
"""
            content = content.replace(marker, new_import, 1)
            changes += 1
            print("PATCH 1: Added lal_kitab_advanced import")
    else:
        print("PATCH 1: Already imported")

    # ═══════════════════════════════════════════════════════
    # PATCH 2: In _score_clock, if no sleeping/rin in stored LK,
    # compute on-the-fly from chart_data
    # ═══════════════════════════════════════════════════════

    old_sleeping = '''    # LK sleeping planet check
    lk=_sj(lk) if lk else {}
    sleeping=lk.get("sleeping_planets",lk.get("sleeping",lk.get("advanced",{}).get("sleeping_planets",[])))'''

    new_sleeping = '''    # LK sleeping planet check — try stored first, compute on-the-fly if missing
    lk=_sj(lk) if lk else {}
    sleeping=lk.get("sleeping_planets",lk.get("sleeping",lk.get("advanced",{}).get("sleeping_planets",[]))))
    # If no stored sleeping planets, compute on-the-fly
    if not sleeping and HAS_LK_ADVANCED:
        try:
            natal_planets = lk.get("natal_planets", {})
            if not natal_planets:
                natal_planets = {}
                for pid, pd in cd.get("planets", {}).items():
                    if isinstance(pd, dict) and pd.get("name"):
                        natal_planets[pd["name"]] = {"house": pd.get("house", 0), "sign": SIGNS[pd.get("sign", 0)] if isinstance(pd.get("sign"), int) else pd.get("sign", "")}
            if natal_planets:
                lagna = cd.get("lagna_sign", "Aries")
                if isinstance(lagna, (dict, int)): lagna = SIGNS[_si(lagna)]
                sleeping_result = detect_sleeping_planets(natal_planets, lagna)
                if isinstance(sleeping_result, list):
                    sleeping = sleeping_result
        except Exception as e:
            logger.debug("LK sleeping on-the-fly failed: %s", e)'''

    # Actually, the extra parenthesis will cause a syntax error. Let me use a simpler approach.
    # Instead of replacing the complex block, just add the on-the-fly computation AFTER the existing check.

    # Find the end of the sleeping planet check loop
    after_sleeping_marker = '''                sc-=20; factors.append(ENERGY.get(planet,planet)+" is SLEEPING — power OFF for this instrument")'''

    if after_sleeping_marker in content and "compute on-the-fly" not in content:
        # Find the full sleeping section and add on-the-fly after it
        idx = content.find(after_sleeping_marker)
        # Find the end of the if block (next blank line or next section)
        end_idx = content.find("\n\n    # LK Rin", idx)
        if end_idx == -1:
            end_idx = content.find("\n\n    return sc, factors", idx)

        if end_idx > 0:
            inject = '''

    # On-the-fly LK computation when stored data is missing
    if not sleeping and HAS_LK_ADVANCED:
        try:
            natal_p = lk.get("natal_planets", {})
            if not natal_p:
                natal_p = {}
                for _pid, _pd in cd.get("planets", {}).items():
                    if isinstance(_pd, dict) and _pd.get("name"):
                        _sn = SIGNS[_pd.get("sign", 0)] if isinstance(_pd.get("sign"), int) else str(_pd.get("sign", ""))
                        natal_p[_pd["name"]] = {"house": _pd.get("house", 0), "sign": _sn}
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
'''
            content = content[:end_idx] + inject + content[end_idx:]
            changes += 1
            print("PATCH 2: Added on-the-fly sleeping planet computation")
    else:
        print("PATCH 2: Already patched or marker not found")

    # ═══════════════════════════════════════════════════════
    # PATCH 3: Same for Rin — compute on-the-fly if missing
    # ═══════════════════════════════════════════════════════

    after_rin_marker = '''                    sc-=15; factors.append("Karmic debt (Rin) on "+ENERGY.get(dp,dp)+" — pattern loop draining this instrument")'''

    if after_rin_marker in content and "Rin computed" not in content:
        idx = content.find(after_rin_marker)
        end_idx = content.find("\n\n    return sc, factors", idx)

        if end_idx > 0:
            inject_rin = '''

    # On-the-fly Rin computation when stored data is missing
    if not rin and HAS_LK_ADVANCED:
        try:
            natal_p = lk.get("natal_planets", {})
            if not natal_p:
                natal_p = {}
                for _pid, _pd in cd.get("planets", {}).items():
                    if isinstance(_pd, dict) and _pd.get("name"):
                        _sn = SIGNS[_pd.get("sign", 0)] if isinstance(_pd.get("sign"), int) else str(_pd.get("sign", ""))
                        natal_p[_pd["name"]] = {"house": _pd.get("house", 0), "sign": _sn}
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
'''
            content = content[:end_idx] + inject_rin + content[end_idx:]
            changes += 1
            print("PATCH 3: Added on-the-fly Rin computation")
    else:
        print("PATCH 3: Already patched or marker not found")

    with open(TARGET, "w") as f:
        f.write(content)

    print(f"\nDone. {changes} changes applied.")
    if changes > 0:
        print("Deploy: git add -A && git commit -m 'feat: on-the-fly LK sleeping + rin computation' && git push")

if __name__ == "__main__":
    patch()
