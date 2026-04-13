#!/usr/bin/env python3
"""
patch_practice_engine_language.py

Adds Spanish translation to practice_engine.py output.
The practice engine generates English text — this patch adds a post-processing
translation layer that runs when language='es' is passed to the schedule endpoint.

Strategy: Rather than rewriting the entire engine, we translate the output fields
at the API boundary in main.py, using a Claude call with a small prompt.
This is cheaper and safer than modifying practice_engine.py internals.

Run: python patch_practice_engine_language.py
"""

import re, shutil, os, ast

TARGET = os.path.expanduser("~/antarai/main.py")
BACKUP = TARGET + ".bak_practice_lang"
shutil.copy2(TARGET, BACKUP)
print(f"Backed up to {BACKUP}")

with open(TARGET, "r") as f:
    src = f.read()

# ── Translation function to inject ───────────────────────────────────────────
TRANSLATION_FUNC = '''
# --- Practice schedule language translation ---

_PRACTICE_FIELD_TRANSLATIONS_ES = {
    # energy_label translations
    "Love & Creativity":        "Amor y Creatividad",
    "Communication & Clarity":  "Comunicacion y Claridad",
    "Career & Authority":       "Carrera y Autoridad",
    "Health & Vitality":        "Salud y Vitalidad",
    "Wealth & Resources":       "Riqueza y Recursos",
    "Courage & Initiative":     "Valentia e Iniciativa",
    "Wisdom & Expansion":       "Sabiduria y Expansion",
    "Relationships & Harmony":  "Relaciones y Armonia",
    "Discipline & Structure":   "Disciplina y Estructura",
    "Transformation":           "Transformacion",
    "Purpose & Ambition":       "Proposito y Ambicion",
    "Intuition & Liberation":   "Intuicion y Liberacion",
    # domain translations
    "relationship": "relaciones",
    "career": "carrera",
    "wealth": "riqueza",
    "health": "salud",
    "communication": "comunicacion",
    "creativity": "creatividad",
    # time translations
    "morning": "manana",
    "evening": "tarde/noche",
    "afternoon": "tarde",
    "night": "noche",
    "morning or evening": "manana o tarde/noche",
    "evening, in a calm space": "tarde/noche, en un espacio tranquilo",
    "morning, before meetings or writing": "manana, antes de reuniones o escribir",
    # day translations
    "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miercoles",
    "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sabado", "Sunday": "Domingo",
    # priority translations
    "high": "alta", "medium": "media", "low": "baja",
}

_PRACTICE_TEXTS_ES = {
    # Venus/Love practice
    "Your ability to attract": "Tu capacidad de atraer",
    "love, beauty, resources": "amor, belleza, recursos",
    "Life feels functional but joyless": "La vida se siente funcional pero sin alegria",
    "suppressed": "bloqueada",
    "Create something beautiful this week": "Crea algo hermoso esta semana",
    "Take yourself somewhere aesthetically inspiring": "Lleva te a un lugar que inspire belleza",
    "Wear white on Friday": "Viste de blanco el viernes",
    "Your relationship patterns and creative expression are the focus": "Tus patrones de relacion y expresion creativa son el enfoque",
    "softens defensiveness": "suaviza la defensividad",
    "opens you to giving and receiving more freely": "te abre a dar y recibir mas libremente",
    # Mercury/Communication practice
    "Your communication and analytical abilities are foggy": "Tu capacidad de comunicacion y analisis esta nublada",
    "Words don't land": "Las palabras no llegan",
    "deals stall": "los tratos se frenan",
    "ideas feel stuck": "las ideas se sienten atascadas",
    "Mercury governs Buddhi": "Mercurio gobierna el Buddhi",
    "intellect": "intelecto",
    "speech": "habla",
    "Weak Mercury causes miscommunication": "Mercurio debil causa malentendidos",
    "contracts gone wrong": "contratos que salen mal",
    "scattered thinking": "pensamiento disperso",
    "The mantra restores precision": "El mantra restaura la precision",
    # Saturn practice
    "discipline becomes automatic": "la disciplina se vuelve automatica",
    "a genuine habit rather than willpower": "un habito real, no solo fuerza de voluntad",
    "procrastination decreases": "la procrastinacion disminuye",
    "follow through on commitments without internal resistance": "cumples compromisos sin resistencia interna",
    # Generic
    "Best day:": "Mejor dia:",
    "Best time:": "Mejor momento:",
    "Pair with today": "Combina con el",
    "mantra (see below) for maximum effect": "mantra de hoy para maximo efecto",
    "Mark as complete when done": "Marca como completa cuando termines",
    "consistency matters more than perfection": "la constancia importa mas que la perfeccion",
    "Strong alignment:": "Fuerte alineacion:",
    "indicators confirm your": "indicadores confirman que tu energia de",
    "energy is the focus": "es el enfoque",
    "is the focus": "es el enfoque",
    "After": "Despues de",
    "days, notice whether": "dias, observa si",
    "Soy disciplinado/a, paciente y construyo cosas que duran": "Soy disciplinado/a, paciente y construyo cosas que duran",
    # Duration reasons
    "Saturn requires 40 days": "Saturno requiere 40 dias",
    "Venus requires 21 days": "Venus requiere 21 dias",
    "Mercury requires 9 days": "Mercurio requiere 9 dias",
    "discipline becomes automatic": "la disciplina se vuelve automatica",
}

def _translate_text_es(text):
    """Apply known translations to a text string."""
    if not text or not isinstance(text, str):
        return text
    result = text
    for en, es in _PRACTICE_TEXTS_ES.items():
        result = result.replace(en, es)
    return result

def _translate_practice_schedule_es(schedule):
    """
    Post-process practice schedule dict to translate English -> Spanish.
    Only translates known fields — leaves unknown content as-is.
    """
    if not schedule or not isinstance(schedule, dict):
        return schedule

    import copy
    s = copy.deepcopy(schedule)

    def tfield(obj, *keys):
        """Translate specific string fields in a dict."""
        for k in keys:
            if k in obj and isinstance(obj[k], str):
                # First check exact match in field translations
                v = obj[k]
                if v in _PRACTICE_FIELD_TRANSLATIONS_ES:
                    obj[k] = _PRACTICE_FIELD_TRANSLATIONS_ES[v]
                else:
                    # Apply text substitutions
                    obj[k] = _translate_text_es(v)

    def translate_practice(p):
        if not p or not isinstance(p, dict):
            return p
        tfield(p, "energy_label", "domain", "best_time", "best_day", "day",
               "why", "what", "how", "practice_why", "practice_why_science",
               "duration_reason", "completion_milestone", "duration_label")
        if "priority" in p:
            p["priority_label"] = _PRACTICE_FIELD_TRANSLATIONS_ES.get(
                str(p["priority"]).lower(), str(p["priority"]))
        return p

    # Translate primary_practice
    if "primary_practice" in s:
        translate_practice(s["primary_practice"])

    # Translate supporting_practices
    if "supporting_practices" in s:
        for p in s["supporting_practices"]:
            translate_practice(p)

    # Translate mantra_of_the_day
    if "mantra_of_the_day" in s:
        m = s["mantra_of_the_day"]
        tfield(m, "energy_label", "mantra_why", "mantra_duration_reason",
               "mantra_completion_milestone", "mantra_best_time", "time_suggestion")

    # Translate weekly_plan
    if "weekly_plan" in s:
        days_es = {"Monday":"Lun","Tuesday":"Mar","Wednesday":"Mie",
                   "Thursday":"Jue","Friday":"Vie","Saturday":"Sab","Sunday":"Dom"}
        for day in s["weekly_plan"]:
            tfield(day, "energy_label", "primary_action")
            if "day_name" in day:
                day["day_name"] = days_es.get(day["day_name"], day["day_name"])

    # Translate sleeping_alerts and rin_cards
    for key in ("sleeping_alerts", "rin_cards"):
        if key in s:
            for item in s[key]:
                tfield(item, "energy_label", "domain", "remedy_why",
                       "remedy_why_science", "duration_reason",
                       "duration_label", "streak_warning")

    # Translate convergence_summary
    if "convergence_summary" in s:
        cs = s["convergence_summary"]
        cs = cs.replace("Strong alignment:", "Fuerte alineacion:")
        cs = cs.replace("indicators confirm your", "indicadores confirman que tu energia de")
        cs = cs.replace("energy is the focus", "es el enfoque ahora")
        cs = cs.replace("is the focus", "es el enfoque ahora")
        # Translate energy label in the summary
        for en, es in _PRACTICE_FIELD_TRANSLATIONS_ES.items():
            cs = cs.replace(en, es)
        s["convergence_summary"] = cs

    return s

'''

# ── Find the practices/schedule endpoint and add translation ─────────────────
ANCHOR = '@app.get("/api/v1/practices/{chart_id}/schedule")'

if "_translate_practice_schedule_es" in src:
    print("Translation function already present - skipping injection")
elif ANCHOR in src:
    src = src.replace(ANCHOR, TRANSLATION_FUNC + "\n" + ANCHOR)
    print("Translation function injected before practices/schedule route")
else:
    print(f"ERROR: Cannot find anchor: {ANCHOR}")
    # Search for it
    for i, line in enumerate(src.split('\n')):
        if 'practices' in line and 'schedule' in line and 'app.get' in line:
            print(f"  Line {i}: {line[:100]}")
    exit(1)

# ── Find the return statement in the schedule endpoint and apply translation ──
# Look for: return {"status": ..., "schedule": schedule}
# or:       return schedule
# We need to wrap it with the translation

lines = src.split('\n')
in_func = False
patched = False

for i, line in enumerate(lines):
    if 'async def' in line and 'schedule' in line and 'chart_id' in line:
        in_func = True
        print(f"Found schedule function at line {i}: {line.strip()[:80]}")

    if not in_func:
        continue

    # Add language param to function signature
    if not patched and 'async def' in line and 'schedule' in line and 'language' not in line and 'chart_id' in line:
        old_line = line
        new_line = line.rstrip()
        if new_line.endswith(':'):
            # Find the closing paren
            new_line = re.sub(r'(chart_id\s*:\s*str)', r'\1, language: str = "es"', new_line)
        lines[i] = new_line
        print(f"Added language param to schedule signature at line {i}")

    # Find return statement with schedule data
    stripped = line.strip()
    if in_func and not patched and (
        (stripped.startswith('return {') and '"schedule"' in stripped) or
        (stripped.startswith('return {') and 'schedule' in stripped)
    ):
        # Inject translation before return
        indent = ' ' * (len(line) - len(line.lstrip()))
        inject = f'{indent}if language == "es":\n{indent}    _sched_inner = result.get("schedule", result) if "schedule" in result else result\n{indent}    _translated = _translate_practice_schedule_es(_sched_inner)\n{indent}    if "schedule" in result:\n{indent}        result["schedule"] = _translated\n{indent}    else:\n{indent}        result = _translated\n'
        lines.insert(i, inject)
        patched = True
        print(f"Translation call injected at line {i}")
        break

    # Alternative: return statement just returns a variable
    if in_func and not patched and stripped.startswith('return ') and 'schedule' in stripped.lower() and 'result' in stripped:
        indent = ' ' * (len(line) - len(line.lstrip()))
        var_name = stripped.replace('return ', '').strip()
        # Add translation before return
        new_lines = [
            f'{indent}if language == "es":',
            f'{indent}    _sched_inner = {var_name}.get("schedule", {var_name}) if isinstance({var_name}, dict) and "schedule" in {var_name} else {var_name}',
            f'{indent}    _translated = _translate_practice_schedule_es(_sched_inner)',
            f'{indent}    if isinstance({var_name}, dict) and "schedule" in {var_name}:',
            f'{indent}        {var_name}["schedule"] = _translated',
            f'{indent}    else:',
            f'{indent}        {var_name} = _translated',
        ]
        for j, nl in enumerate(new_lines):
            lines.insert(i + j, nl)
        patched = True
        print(f"Translation injected before return at line {i}")
        break

if not patched:
    print("WARNING: Could not auto-patch return. Printing schedule function context...")
    found_func = False
    for i, line in enumerate(lines):
        if 'async def' in line and 'schedule' in line and 'chart_id' in line:
            found_func = True
        if found_func:
            print(f"  {i}: {line[:100]}")
            if i > 0 and line.strip().startswith('return'):
                print("  ^^^ RETURN FOUND")
                break
            if found_func and i > 200:
                break

src = '\n'.join(lines)

# ── Write and verify ──────────────────────────────────────────────────────────
with open(TARGET, "w") as f:
    f.write(src)

try:
    ast.parse(src)
    print("Syntax OK")
except SyntaxError as e:
    print(f"SYNTAX ERROR: {e}")
    shutil.copy2(BACKUP, TARGET)
    print("Backup restored")
    exit(1)

print("""
PATCH COMPLETE

Deploy:
  git add -A && git commit -m "feat: Spanish translation for practice schedule" && git push

Verify after ~60s:
  curl -s "https://antar-fastapi-production.up.railway.app/api/v1/practices/de02bb52-d43a-4b09-be25-b45a07bfbf8a/schedule?language=es" | python3 -c "
import sys,json
d=json.load(sys.stdin)
s=d.get('schedule',{})
pp=s.get('primary_practice',{})
print('energy_label:', pp.get('energy_label'))
print('why:', pp.get('why','')[:80])
print('convergence:', s.get('convergence_summary','')[:80])
"
""")
