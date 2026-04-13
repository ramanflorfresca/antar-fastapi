#!/usr/bin/env python3
"""
patch_exec_return.py
Targeted fix: replaces `return result` in get_executive_summary with
a version that adds plain_signal and language param.
Run from ~/antarai: python patch_exec_return.py
"""
import shutil, os, ast

TARGET = os.path.expanduser("~/antarai/main.py")
BACKUP = TARGET + ".bak_exec_return"
shutil.copy2(TARGET, BACKUP)

with open(TARGET, "r") as f:
    src = f.read()

# ── Fix 1: Add language param to function signature ──────────────────────────
OLD_SIG = 'async def get_executive_summary(chart_id: str):'
NEW_SIG = 'async def get_executive_summary(chart_id: str, language: str = "es"):'

if OLD_SIG in src:
    src = src.replace(OLD_SIG, NEW_SIG)
    print("✅ Added language param to signature")
elif NEW_SIG in src:
    print("✅ language param already present")
else:
    print("⚠️  Could not find signature — check manually")

# ── Fix 2: Replace `return result` with enriched return ──────────────────────
# The exact lines are:
#   result = build_executive_summary(cd, jd, lk, current_dasha, dasha_list)
#   return result

OLD_RETURN = '''        result = build_executive_summary(cd, jd, lk, current_dasha, dasha_list)
        return result'''

NEW_RETURN = '''        result = build_executive_summary(cd, jd, lk, current_dasha, dasha_list)
        instruments = result.get("instruments", {})
        result["plain_signal"] = _build_plain_dashboard_signal(instruments, language)
        return result'''

if OLD_RETURN in src:
    src = src.replace(OLD_RETURN, NEW_RETURN)
    print("✅ plain_signal injected into return")
else:
    print("❌ Could not find exact return block. Trying looser match...")
    # Try with different whitespace
    import re
    pattern = r'(        result = build_executive_summary\([^)]+\)\n)(        return result)'
    replacement = r'\1        instruments = result.get("instruments", {})\n        result["plain_signal"] = _build_plain_dashboard_signal(instruments, language)\n        return result'
    new_src, n = re.subn(pattern, replacement, src)
    if n:
        src = new_src
        print(f"✅ plain_signal injected via regex ({n} match)")
    else:
        print("❌ FAILED. Print context around line 7035:")
        lines = src.split('\n')
        for i in range(7030, 7042):
            print(f"  {i}: {repr(lines[i])}")
        exit(1)

# ── Fix 3: Replace the OLD _build_plain_dashboard_signal (list-based) ────────
# with the new dict-based version if needed
if "Takes raw 12-instrument list" in src:
    print("⚠️  Old list-based _build_plain_dashboard_signal still present")
    print("   Replacing with dict-based version...")

    OLD_FUNC_START = "def _build_plain_dashboard_signal(instruments: list"
    NEW_FUNC = '''def _build_plain_dashboard_signal(instruments, language="es"):
    """Dict-based: instruments keyed by slug (vitals, reserves, action...)"""
    _NAMES_ES = {
        "vitals": "Salud y Energia", "reserves": "Ahorros y Riqueza",
        "action": "Valentia e Iniciativa", "real_estate": "Hogar y Raices",
        "creation": "Creatividad y Proyectos", "conflict": "Retos y Legal",
        "alliance": "Socios y Alianzas", "runway": "Transformacion",
        "fortune": "Oportunidad y Suerte", "authority": "Carrera y Autoridad",
        "revenue": "Ingresos y Negocios", "global_vec": "Viajes y Expansion",
        "global": "Viajes y Expansion",
    }
    if not instruments:
        return {"focus_area": "Energia general", "focus_message": "Tu senal se esta calculando.", "do_this": "Mantente en tu rutina hoy.", "caution_area": None, "caution_message": None, "avoid_this": None, "open_window": None, "open_window_message": None, "urgency": "low"}
    # Normalize: handle both dict and list
    if isinstance(instruments, dict):
        items = [(k, float(v.get("signal_score") or v.get("blueprint_score") or 0), (v.get("signal_status") or v.get("verdict") or "DORMANT").upper()) for k, v in instruments.items()]
    else:
        items = [(v.get("name","x"), float(v.get("signal_score") or v.get("blueprint_score") or 0), (v.get("signal_status") or v.get("verdict") or "DORMANT").upper()) for v in instruments]
    items.sort(key=lambda x: x[1], reverse=True)
    def nme(k): return _NAMES_ES.get(k, k.replace("_"," ").title())
    focus_key = next((k for k,s,st in items if st in ("ACTIVE","PEAK")), items[0][0] if items else None)
    caution_key = next((k for k,s,st in items if st == "FRICTION"), None)
    window_key = next((k for k,s,st in items if st == "PREPARING" and k != focus_key), None)
    top = items[0][1] if items else 0
    urgency = "high" if (caution_key and top > 65) else "medium" if caution_key else "low"
    focus_st = next((st for k,s,st in items if k == focus_key), "ACTIVE")
    st_map = {"ACTIVE":"activa","PEAK":"en su mejor momento","PREPARING":"preparandose","FRICTION":"bajo presion","DORMANT":"dormida","POSITION":"preparandose"}
    if language == "es":
        fname = nme(focus_key) if focus_key else "Energia general"
        flabel = st_map.get(focus_st, "activa")
        suffix = " Es buen momento para avanzar." if focus_st in ("ACTIVE","PEAK") else " Se esta preparando." if focus_st=="PREPARING" else ""
        return {
            "focus_area": fname, "focus_status": flabel,
            "focus_message": f"Tu energia de {fname.lower()} esta {flabel}.{suffix}",
            "do_this": f"Pon atencion activa a {fname.lower()} esta semana.",
            "caution_area": nme(caution_key) if caution_key else None,
            "caution_message": f"{nme(caution_key)} esta bajo presion ahora." if caution_key else None,
            "avoid_this": f"Evita decisiones en {nme(caution_key).lower()} esta semana." if caution_key else None,
            "open_window": nme(window_key) if window_key else None,
            "open_window_message": f"Una oportunidad en {nme(window_key).lower()} se esta preparando." if window_key else None,
            "urgency": urgency,
        }
    fname = focus_key.replace("_"," ").title() if focus_key else "General energy"
    return {
        "focus_area": fname,
        "focus_message": f"Your {fname.lower()} energy is active. Good time to move forward.",
        "do_this": f"Give active attention to {fname.lower()} this week.",
        "caution_area": caution_key if caution_key else None,
        "caution_message": f"{caution_key} is under pressure." if caution_key else None,
        "avoid_this": f"Avoid major {caution_key} decisions this week." if caution_key else None,
        "open_window": window_key if window_key else None,
        "open_window_message": f"A {window_key} opportunity is opening." if window_key else None,
        "urgency": urgency,
    }
'''
    # Find the old function and replace it entirely
    # Locate start
    func_idx = src.find(OLD_FUNC_START)
    if func_idx >= 0:
        # Find the def line start
        line_start = src.rfind('\n', 0, func_idx) + 1
        # Find end of function: next top-level def or class
        import re
        end_match = re.search(r'\ndef [a-zA-Z_]|\n@app\.', src[func_idx:])
        if end_match:
            func_end = func_idx + end_match.start()
            src = src[:line_start] + NEW_FUNC + '\n' + src[func_end:]
            print("✅ Old list-based function replaced with dict-based version")
        else:
            print("⚠️  Could not find end of old function")
    else:
        print("⚠️  Could not locate old function start")

# ── Write and verify ──────────────────────────────────────────────────────────
with open(TARGET, "w") as f:
    f.write(src)

import ast as _ast
try:
    _ast.parse(src)
    print("✅ Syntax OK")
except SyntaxError as e:
    print(f"❌ Syntax error: {e}")
    shutil.copy2(BACKUP, TARGET)
    print("Backup restored.")
    exit(1)

print("""
DONE. Now run:
  git add -A && git commit -m "feat: plain_signal in executive-summary" && git push

Verify after ~60s:
  curl -s "https://antar-fastapi-production.up.railway.app/api/v1/executive-summary/de02bb52-d43a-4b09-be25-b45a07bfbf8a?language=es" | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d.get('plain_signal'), indent=2, ensure_ascii=False))"
""")
