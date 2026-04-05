"""
patch_jsonb_keys.py — Fix 3 JSONB key mismatches in symptom_library.py

Problem: The stored jaimini_data and lal_kitab_data use different keys
than what the diagnostic engine expects.

Actual stored format:
  jaimini_data.current_md = {sign: 1, sign_name: "Taurus", ...}
  jaimini_data.current_ad = {sign: 5, sign_name: "Virgo", ...}
  jaimini_data.arudha_lagna = {sign: 7, sign_name: "Scorpio"}
  jaimini_data.upapada_lagna = {sign: 0, sign_name: "Aries"}
  jaimini_data.karakamsa = {sign: 7, sign_name: "Scorpio"}
  lal_kitab_data has NO varshphal/sleeping_planets/rin keys

Run: python patch_jsonb_keys.py
"""
import re

TARGET = "antar_engine/symptom_library.py"

def patch():
    with open(TARGET, "r") as f:
        lines = f.readlines()

    content = "".join(lines)
    changes = 0

    # ═══════════════════════════════════════════════════════
    # FIX 1: _get_chara_dasha() — read current_md/current_ad
    # directly from jaimini_data root, not from chara_dasha sub-key
    # ═══════════════════════════════════════════════════════

    old_chara = 'cd_data = jd.get("chara_dasha", jd.get("charaDasha", jd.get("current_chara_dasha", {})))'
    new_chara = 'cd_data = jd  # current_md and current_ad are at root level of jaimini_data'

    if old_chara in content:
        content = content.replace(old_chara, new_chara, 1)
        changes += 1
        print("FIX 1: _get_chara_dasha — reading current_md/current_ad from root")
    else:
        print("FIX 1: Pattern not found (may already be fixed)")

    # ═══════════════════════════════════════════════════════
    # FIX 2: _get_arudha_lagnas() — the stored keys are
    # arudha_lagna, upapada_lagna, karakamsa (already tried)
    # but values are dicts like {sign: 7, sign_name: "Scorpio"}
    # The _si() function should handle this, but let's also
    # add the direct sign extraction for safety
    # ═══════════════════════════════════════════════════════

    # This should already work since _si() handles dicts now.
    # But let's verify the key order is correct by checking
    # that "arudha_lagna" is tried BEFORE "al"
    
    old_al_order = '''    for key in ["AL", "al", "arudha_lagna", "arudha"]:'''
    new_al_order = '''    for key in ["arudha_lagna", "arudha", "AL", "al"]:'''
    if old_al_order in content:
        content = content.replace(old_al_order, new_al_order, 1)
        changes += 1
        print("FIX 2a: AL key order — arudha_lagna first")

    old_ul_order = '''    for key in ["UL", "ul", "upapada_lagna", "upapada"]:'''
    new_ul_order = '''    for key in ["upapada_lagna", "upapada", "UL", "ul"]:'''
    if old_ul_order in content:
        content = content.replace(old_ul_order, new_ul_order, 1)
        changes += 1
        print("FIX 2b: UL key order — upapada_lagna first")

    old_kl_order = '''    for key in ["KL", "kl", "karakamsa", "karakamsha"]:'''
    new_kl_order = '''    for key in ["karakamsa", "karakamsha", "KL", "kl"]:'''
    if old_kl_order in content:
        content = content.replace(old_kl_order, new_kl_order, 1)
        changes += 1
        print("FIX 2c: KL key order — karakamsa first")

    # ═══════════════════════════════════════════════════════
    # FIX 3: _score_annual() — lal_kitab_data has NO varshphal
    # key. Instead it has "placements" (annual house positions).
    # We need to read placements to determine which houses
    # are activated this year.
    # ═══════════════════════════════════════════════════════

    # Find and replace the _score_annual function body
    old_annual_start = '''def _score_annual(cd, h, lk=None):
    """Check Varshphal year lord and Muntha position."""
    sc=0; factors=[]
    lk=_sj(lk) if lk else {}

    varsh=lk.get("varshphal",lk.get("varshaphal",lk.get("annual",{})))'''

    new_annual_start = '''def _score_annual(cd, h, lk=None):
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
                if annual_house in [1, 4, 7, 10]:
                    sc += 10
                    factors.append(en + " (instrument lord) in angular annual house — strong yearly position")
                elif annual_house in [6, 8, 12]:
                    sc -= 8
                    factors.append(en + " (instrument lord) in dusthana annual house — yearly pressure")'''

    if old_annual_start in content:
        content = content.replace(old_annual_start, new_annual_start, 1)
        changes += 1
        print("FIX 3: _score_annual — reads 'placements' when no varshphal key exists")
    else:
        print("FIX 3: Pattern not found (check manually)")

    # Write
    with open(TARGET, "w") as f:
        f.write(content)

    print(f"\nDone. {changes} changes applied to {TARGET}")
    if changes > 0:
        print("Deploy: git add -A && git commit -m 'fix: JSONB key alignment for jaimini + lal kitab' && git push")

if __name__ == "__main__":
    patch()
