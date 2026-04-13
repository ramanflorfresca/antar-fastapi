#!/usr/bin/env python3
"""
patch_executive_summary_plain.py
Adds plain-language translation layer to /api/v1/executive-summary/{chart_id}
Translates 12-channel instrument scores into simple human dashboard signal.

Run: python patch_executive_summary_plain.py
"""

import re, shutil, os

TARGET = os.path.expanduser("~/antarai/main.py")
BACKUP = TARGET + ".bak_exec_plain"

shutil.copy2(TARGET, BACKUP)
print(f"✅ Backed up to {BACKUP}")

with open(TARGET, "r") as f:
    src = f.read()

# ── The plain-language translation function to inject ─────────────────────────
TRANSLATION_FUNC = '''
# ─── Plain language translation for executive-summary dashboard signal ───────

_INSTRUMENT_TO_DOMAIN = {
    "SYSTEM_VITALS":      "salud",
    "CAPITAL_RESERVES":   "finanzas",
    "ACTION_CAPACITY":    "accion",
    "REAL_ESTATE_RADAR":  "hogar",
    "CREATION_ENGINE":    "creatividad",
    "CONFLICT_SHIELD":    "conflictos",
    "ALLIANCE_SYNC":      "relaciones",
    "CAPITAL_RUNWAY":     "transformacion",
    "FORTUNE_VECTOR":     "oportunidad",
    "AUTHORITY_ENGINE":   "carrera",
    "REVENUE_PIPELINE":   "ingresos",
    "GLOBAL_VECTOR":      "viajes",
}

_DOMAIN_NAMES_ES = {
    "carrera":        "Carrera",
    "ingresos":       "Ingresos",
    "relaciones":     "Relaciones",
    "finanzas":       "Finanzas",
    "salud":          "Salud y energía",
    "accion":         "Iniciativa",
    "hogar":          "Hogar y raíces",
    "creatividad":    "Creatividad",
    "conflictos":     "Manejo de conflictos",
    "transformacion": "Transformación",
    "oportunidad":    "Oportunidad",
    "viajes":         "Viajes y expansión",
}

_STATUS_TO_ES = {
    "ACTIVE":    "activo",
    "PREPARING": "preparando",
    "FRICTION":  "bajo presión",
    "PEAK":      "en su mejor momento",
    "DORMANT":   "dormido",
}

def _build_plain_dashboard_signal(instruments: list, language: str = "es") -> dict:
    """
    Takes raw 12-instrument list from executive-summary.
    Returns a simple dict for the dashboard hero card.
    
    Output:
    {
      "focus_area": "Carrera",
      "focus_status": "activo",
      "focus_message": "Tu energía de carrera está activa. Es buen momento para avanzar.",
      "caution_area": "Finanzas",
      "caution_message": "Las finanzas están bajo presión esta semana. Evita decisiones grandes.",
      "open_window": "Ingresos",
      "open_window_message": "Una oportunidad de ingresos se está preparando. Mantente atento.",
      "do_this": "Avanza en el proyecto de carrera que has pospuesto.",
      "avoid_this": "Evita compromisos financieros grandes esta semana.",
      "urgency": "medium"
    }
    """
    if not instruments:
        return _default_signal(language)

    # Sort by score descending
    scored = sorted(instruments, key=lambda x: x.get("score", 0), reverse=True)
    
    # Find top ACTIVE/PEAK instrument (the focus)
    focus = None
    for inst in scored:
        status = inst.get("status", "").upper()
        if status in ("ACTIVE", "PEAK"):
            focus = inst
            break
    
    # Find top FRICTION instrument (the caution)
    caution = None
    for inst in scored:
        status = inst.get("status", "").upper()
        if status == "FRICTION":
            caution = inst
            break
    
    # Find top PREPARING instrument (the opportunity)
    window = None
    for inst in scored:
        status = inst.get("status", "").upper()
        if status == "PREPARING" and inst != focus and inst != caution:
            window = inst
            break

    def get_domain_name(inst):
        raw = inst.get("name", "").upper().replace(" ", "_")
        domain_key = _INSTRUMENT_TO_DOMAIN.get(raw, "general")
        return _DOMAIN_NAMES_ES.get(domain_key, raw.replace("_", " ").title())

    def get_status_es(inst):
        raw = inst.get("status", "").upper()
        return _STATUS_TO_ES.get(raw, raw.lower())

    if language == "es":
        result = {}
        
        if focus:
            area = get_domain_name(focus)
            status_es = get_status_es(focus)
            result["focus_area"] = area
            result["focus_status"] = status_es
            result["focus_message"] = f"Tu energía de {area.lower()} está {status_es}. Buen momento para avanzar."
            result["do_this"] = f"Pon atención activa a {area.lower()} esta semana."
        else:
            result["focus_area"] = "Energía general"
            result["focus_status"] = "preparando"
            result["focus_message"] = "Tu energía está en fase de preparación. Consolida antes de expandir."
            result["do_this"] = "Consolida lo que ya tienes. No inicies nuevos proyectos esta semana."

        if caution:
            area = get_domain_name(caution)
            result["caution_area"] = area
            result["caution_message"] = f"{area} está bajo presión. Actúa con cuidado."
            result["avoid_this"] = f"Evita decisiones grandes relacionadas con {area.lower()} esta semana."
        else:
            result["caution_area"] = None
            result["caution_message"] = None
            result["avoid_this"] = None

        if window:
            area = get_domain_name(window)
            result["open_window"] = area
            result["open_window_message"] = f"Una oportunidad de {area.lower()} se está abriendo. Mantente atento."
        else:
            result["open_window"] = None
            result["open_window_message"] = None

        # Urgency based on friction presence and top score
        top_score = scored[0].get("score", 0) if scored else 0
        if caution and top_score > 65:
            result["urgency"] = "high"
        elif caution or top_score > 55:
            result["urgency"] = "medium"
        else:
            result["urgency"] = "low"

        return result
    
    else:  # English fallback
        result = {}
        if focus:
            area = get_domain_name(focus)
            result["focus_area"] = area
            result["focus_message"] = f"Your {area.lower()} energy is active. Good time to move forward."
            result["do_this"] = f"Give active attention to {area.lower()} this week."
        else:
            result["focus_area"] = "General energy"
            result["focus_message"] = "Your energy is in a preparation phase. Consolidate before expanding."
            result["do_this"] = "Consolidate what you have. Don't start new projects this week."

        if caution:
            area = get_domain_name(caution)
            result["caution_area"] = area
            result["caution_message"] = f"{area} is under pressure. Act carefully."
            result["avoid_this"] = f"Avoid major {area.lower()} decisions this week."
        else:
            result["caution_area"] = None
            result["caution_message"] = None
            result["avoid_this"] = None

        if window:
            area = get_domain_name(window)
            result["open_window"] = area
            result["open_window_message"] = f"A {area.lower()} opportunity is opening. Stay alert."
        else:
            result["open_window"] = None
            result["open_window_message"] = None

        top_score = scored[0].get("score", 0) if scored else 0
        result["urgency"] = "high" if (caution and top_score > 65) else "medium" if caution else "low"
        return result


def _default_signal(language: str = "es") -> dict:
    if language == "es":
        return {
            "focus_area": "Energía general",
            "focus_status": "calculando",
            "focus_message": "Tu señal se está calculando. Vuelve en unos minutos.",
            "do_this": "Mantén tu rutina habitual hoy.",
            "caution_area": None,
            "caution_message": None,
            "avoid_this": None,
            "open_window": None,
            "open_window_message": None,
            "urgency": "low"
        }
    return {
        "focus_area": "General energy",
        "focus_status": "calculating",
        "focus_message": "Your signal is being calculated. Check back in a few minutes.",
        "do_this": "Maintain your usual routine today.",
        "caution_area": None,
        "caution_message": None,
        "avoid_this": None,
        "open_window": None,
        "open_window_message": None,
        "urgency": "low"
    }
'''

# ── Inject the translation function before the executive-summary route ────────
ANCHOR = '@app.get("/api/v1/executive-summary/{chart_id}")'
ALT_ANCHOR = "async def executive_summary"

if ANCHOR in src:
    insert_before = ANCHOR
elif ALT_ANCHOR in src:
    insert_before = ALT_ANCHOR
else:
    print("❌ Could not find executive-summary route anchor. Searching...")
    # Try to find any reference
    matches = [line for line in src.split('\n') if 'executive' in line.lower()]
    print("Found lines with 'executive':")
    for m in matches[:10]:
        print(f"  {m}")
    print("Manual insertion required.")
    exit(1)

if "_build_plain_dashboard_signal" in src:
    print("⚠️  Translation function already exists — skipping injection")
else:
    src = src.replace(insert_before, TRANSLATION_FUNC + "\n" + insert_before)
    print("✅ Translation function injected")

# ── Patch the executive-summary return to include plain_signal ────────────────
# Find the return statement in executive-summary and add plain_signal to it

# Pattern: look for the return dict in executive-summary
RETURN_PATTERN = r'(return\s*\{[^}]*"instruments"\s*:\s*instruments[^}]*\})'

def add_plain_signal_to_return(match):
    old_return = match.group(0)
    if "plain_signal" in old_return:
        return old_return  # already patched
    # Add plain_signal before the closing brace
    new_return = old_return.rstrip("}")
    new_return += ',\n        "plain_signal": _build_plain_dashboard_signal(instruments, language)\n    }'
    return new_return

new_src, count = re.subn(RETURN_PATTERN, add_plain_signal_to_return, src, flags=re.DOTALL)

if count == 0:
    print("⚠️  Could not auto-patch return statement — adding manual hook")
    # Simpler approach: find the executive-summary function and patch its return
    # Look for return {...} near the executive-summary route
    SIMPLE_ANCHOR = '"blueprint_score"'
    if SIMPLE_ANCHOR in src:
        # Find the return containing blueprint_score and add plain_signal
        src_lines = src.split('\n')
        patched_lines = []
        i = 0
        patched = False
        while i < len(src_lines):
            line = src_lines[i]
            if '"blueprint_score"' in line and not patched:
                # Look for the closing of this return dict
                patched_lines.append(line)
                # Scan forward to find closing brace of this return
                depth = 0
                j = i + 1
                inserted = False
                while j < len(src_lines):
                    l = src_lines[j]
                    depth += l.count('{') - l.count('}')
                    if not inserted and '"instruments"' in l:
                        patched_lines.append(l)
                        # Insert after instruments line
                        indent = len(l) - len(l.lstrip())
                        patched_lines.append(' ' * indent + '"plain_signal": _build_plain_dashboard_signal(instruments, language),')
                        inserted = True
                        j += 1
                        continue
                    patched_lines.append(l)
                    if depth < 0:
                        break
                    j += 1
                i = j + 1
                patched = True
                continue
            patched_lines.append(line)
            i += 1
        
        if patched:
            new_src = '\n'.join(patched_lines)
            print("✅ plain_signal added via line-scan method")
        else:
            new_src = src
            print("❌ Could not patch return — manual edit needed (see instructions below)")
    else:
        new_src = src
        print("❌ Could not find 'blueprint_score' anchor — manual edit needed")
else:
    print(f"✅ Return statement patched ({count} location(s))")

# ── Also add `language` param to executive-summary if not present ─────────────
if 'language: str = "es"' not in new_src and "executive-summary" in new_src:
    new_src = re.sub(
        r'(async def executive_summary\([^)]*chart_id[^)]*)\)',
        r'\1, language: str = "es")',
        new_src
    )
    print("✅ Added language param to executive-summary")

# ── Write and verify ──────────────────────────────────────────────────────────
with open(TARGET, "w") as f:
    f.write(new_src)

import ast
try:
    ast.parse(new_src)
    print("✅ Syntax OK")
except SyntaxError as e:
    print(f"❌ Syntax error: {e}")
    print("Restoring backup...")
    shutil.copy2(BACKUP, TARGET)
    print("Backup restored. Manual edit required.")
    exit(1)

print("""
✅ PATCH COMPLETE

What was added:
- _build_plain_dashboard_signal() function
- plain_signal field in executive-summary response

New response shape:
{
  ...existing fields...,
  "plain_signal": {
    "focus_area": "Carrera",
    "focus_message": "Tu energía de carrera está activa. Buen momento para avanzar.",
    "do_this": "Pon atención activa a carrera esta semana.",
    "caution_area": "Finanzas",
    "caution_message": "Finanzas está bajo presión. Actúa con cuidado.",
    "avoid_this": "Evita decisiones grandes relacionadas con finanzas esta semana.",
    "open_window": "Ingresos",
    "open_window_message": "Una oportunidad de ingresos se está abriendo.",
    "urgency": "medium"
  }
}

NEXT STEPS:
1. git add -A && git commit -m "feat: plain_signal in executive-summary" && git push
2. Test: curl https://antar-fastapi-production.up.railway.app/api/v1/executive-summary/de02bb52-d43a-4b09-be25-b45a07bfbf8a?language=es | python3 -m json.tool | grep -A 20 plain_signal
3. Send LOVABLE_Dashboard_PlainSignal.md to Lovable
""")
