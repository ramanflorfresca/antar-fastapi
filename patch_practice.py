#!/usr/bin/env python3
"""
fix_practice_complete.py
Complete fix in one script:
1. Verifies we're on good commit (3deefe0 state)
2. Injects translation function + patches both return lines atomically
Run from ~/antarai: python fix_practice_complete.py
"""
import shutil, os, ast

TARGET = os.path.expanduser("~/antarai/main.py")
BACKUP = TARGET + ".bak_fix_complete"
shutil.copy2(TARGET, BACKUP)

with open(TARGET, "r") as f:
    src = f.read()

# ── Verify we're on clean state ───────────────────────────────────────────────
if "_translate_practice_schedule_es" in src:
    print("ERROR: Translation function already present — still on bad state")
    print("Run: git checkout 3deefe0 -- main.py && python3 -c \"import ast; ast.parse(open('main.py').read()); print('OK')\"")
    print("Then re-run this script")
    exit(1)

# Verify the two target lines exist
CACHE_RETURN = '        return {"status": "ok", "source": "cache", "schedule": _sched}'
GEN_RETURN   = '        return {"status": "ok", "source": "generated", "schedule": _sched}'

if CACHE_RETURN not in src:
    print("ERROR: cache return line not found. Check main.py")
    exit(1)
if GEN_RETURN not in src:
    print("ERROR: generated return line not found. Check main.py")
    exit(1)

print("Clean state verified. Applying patch...")

# ── Translation dict (minimal — only what's needed) ──────────────────────────
TRANSLATION_FUNC = '''
def _translate_practice_schedule_es(sched):
    """Translate practice schedule fields English->Spanish."""
    if not sched or not isinstance(sched, dict):
        return sched
    import copy
    s = copy.deepcopy(sched)

    LABELS = {
        "Love & Creativity": "Amor y Creatividad",
        "Communication & Clarity": "Comunicacion y Claridad",
        "Career & Authority": "Carrera y Autoridad",
        "Health & Vitality": "Salud y Vitalidad",
        "Wealth & Resources": "Riqueza y Recursos",
        "Courage & Initiative": "Valentia e Iniciativa",
        "Wisdom & Expansion": "Sabiduria y Expansion",
        "Relationships & Harmony": "Relaciones y Armonia",
        "Discipline & Structure": "Disciplina y Estructura",
        "Transformation": "Transformacion",
        "Purpose & Ambition": "Proposito y Ambicion",
        "Intuition & Liberation": "Intuicion y Liberacion",
    }
    TIMES = {
        "morning": "manana",
        "evening": "tarde/noche",
        "afternoon": "tarde",
        "morning or evening": "manana o tarde/noche",
        "evening, in a calm space": "tarde/noche, en un espacio tranquilo",
        "morning, before meetings or writing": "manana, antes de reuniones o escribir",
        "morning, before important conversations": "manana, antes de conversaciones importantes",
    }
    DAYS = {
        "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miercoles",
        "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sabado", "Sunday": "Domingo",
    }
    TEXTS = {
        "Your ability to attract": "Tu capacidad de atraer",
        "love, beauty, resources": "amor, belleza, recursos",
        "suppressed. Life feels functional but joyless": "bloqueada. La vida se siente funcional pero sin alegria",
        "Create something beautiful this week": "Crea algo hermoso esta semana",
        "Take yourself somewhere aesthetically inspiring": "Ve a un lugar que inspire belleza",
        "Wear white on Friday": "Viste de blanco el viernes",
        "Your relationship patterns and creative expression are the focus": "Tus patrones de relacion y expresion creativa son el enfoque",
        "softens defensiveness and opens you to giving and receiving more freely": "suaviza la defensividad y te abre a dar y recibir con mas libertad",
        "Your communication and analytical abilities are foggy": "Tu capacidad de comunicacion y analisis esta nublada",
        "Words don't land, deals stall, ideas feel stuck": "Las palabras no llegan, los tratos se frenan, las ideas se atascan",
        "discipline becomes automatic": "la disciplina se vuelve automatica",
        "a genuine habit rather than willpower": "un habito real, no solo fuerza de voluntad",
        "Best day:": "Mejor dia:",
        "Best time:": "Mejor momento:",
        "Mark as complete when done": "Marca como completa cuando termines",
        "consistency matters more than perfection": "la constancia importa mas que la perfeccion",
        "Strong alignment:": "Fuerte alineacion:",
        "indicators confirm your": "indicadores confirman que tu energia de",
        "energy is the focus right now": "es el enfoque ahora",
        "is the focus": "es el enfoque",
        "I attract love, beauty, and creative abundance": "Atraigo amor, belleza y abundancia creativa",
        "I am disciplined, patient, and build things that last": "Soy disciplinado/a, paciente y construyo cosas que duran",
    }

    def t(text):
        if not text or not isinstance(text, str): return text
        result = text
        for en, es in LABELS.items(): result = result.replace(en, es)
        for en, es in TEXTS.items(): result = result.replace(en, es)
        return result

    def translate_practice(p):
        if not p or not isinstance(p, dict): return p
        if "energy_label" in p: p["energy_label"] = LABELS.get(p["energy_label"], p["energy_label"])
        if "best_time" in p: p["best_time"] = TIMES.get(p["best_time"], p["best_time"])
        if "best_day" in p: p["best_day"] = DAYS.get(p["best_day"], p["best_day"])
        if "day" in p: p["day"] = DAYS.get(p["day"], p["day"])
        for f in ("why","what","how","practice_why","practice_why_science","duration_reason","completion_milestone"):
            if f in p: p[f] = t(p[f])
        return p

    if "primary_practice" in s: translate_practice(s["primary_practice"])
    if "supporting_practices" in s:
        for p in s["supporting_practices"]: translate_practice(p)
    if "mantra_of_the_day" in s:
        m = s["mantra_of_the_day"]
        if "energy_label" in m: m["energy_label"] = LABELS.get(m["energy_label"], m["energy_label"])
        if "affirmation" in m: m["affirmation"] = TEXTS.get(m["affirmation"], m["affirmation"])
        if "mantra_best_time" in m: m["mantra_best_time"] = TIMES.get(m["mantra_best_time"], m["mantra_best_time"])
        for f in ("mantra_why","mantra_duration_reason","mantra_completion_milestone"):
            if f in m: m[f] = t(m[f])
    if "sleeping_alerts" in s:
        for a in s["sleeping_alerts"]:
            if "energy_label" in a: a["energy_label"] = LABELS.get(a["energy_label"], a["energy_label"])
            for f in ("remedy_why","duration_reason"): 
                if f in a: a[f] = t(a[f])
    if "convergence_summary" in s:
        cs = s["convergence_summary"]
        for en, es in {**LABELS, **TEXTS}.items(): cs = cs.replace(en, es)
        s["convergence_summary"] = cs
    if "weekly_plan" in s:
        for d in s["weekly_plan"]:
            if "energy_label" in d: d["energy_label"] = LABELS.get(d["energy_label"], d["energy_label"])
            if "day_name" in d: d["day_name"] = DAYS.get(d["day_name"], d["day_name"])
            if "primary_action" in d: d["primary_action"] = t(d["primary_action"])
    return s

'''

# ── Inject function just before the route ────────────────────────────────────
ROUTE_ANCHOR = '@app.get("/api/v1/practices/{chart_id}/schedule")'
src = src.replace(ROUTE_ANCHOR, TRANSLATION_FUNC + "\n" + ROUTE_ANCHOR)
print("Translation function injected")

# ── Patch both return lines ───────────────────────────────────────────────────
src = src.replace(
    CACHE_RETURN,
    '        if language == "es": _sched = _translate_practice_schedule_es(_sched)\n' + CACHE_RETURN
)
src = src.replace(
    GEN_RETURN,
    '        if language == "es": _sched = _translate_practice_schedule_es(_sched)\n' + GEN_RETURN
)
print("Both return lines patched")

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
DONE. Run:
  git add -A && git commit -m "feat: Spanish practice schedule translation" && git push

Verify after 60s:
  curl -s "https://antar-fastapi-production.up.railway.app/api/v1/practices/de02bb52-d43a-4b09-be25-b45a07bfbf8a/schedule?language=es" | python3 -c "
import sys,json; d=json.load(sys.stdin); s=d.get('schedule',{}); pp=s.get('primary_practice',{})
print('STATUS:', d.get('status'))
print('energy_label:', pp.get('energy_label'))
print('why:', pp.get('why','')[:60])
"
""")
