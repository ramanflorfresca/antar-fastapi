#!/usr/bin/env python3
"""
patch_dashboard_panchang_v2.py
Same as v1 but headline never shows "Tithi 26" or "Shatabhisha" to user.
Only shows plain meaning. Nakshatra and tithi names are internal only.
"""
import shutil, os, ast, re

TARGET = os.path.expanduser("~/antarai/main.py")
BACKUP = TARGET + ".bak_panchang_v2"
shutil.copy2(TARGET, BACKUP)
print(f"Backed up to {BACKUP}")

with open(TARGET, "r") as f:
    src = f.read()

PANCHANG_FUNC = '''
# ─── Panchang plain language (27 nakshatras, 30 tithis, 7 varas) ─────────────

_NAK = {
    "Ashwini":           {"es": "inicio rápido y curación",      "en": "fast starts and healing"},
    "Bharani":           {"es": "transformación profunda",       "en": "deep transformation"},
    "Krittika":          {"es": "claridad y determinación",      "en": "clarity and determination"},
    "Rohini":            {"es": "crecimiento y abundancia",      "en": "growth and abundance"},
    "Mrigashira":        {"es": "búsqueda y curiosidad",         "en": "searching and curiosity"},
    "Ardra":             {"es": "tormenta y renovación",         "en": "storm and renewal"},
    "Punarvasu":         {"es": "renovación y retorno",          "en": "renewal and return"},
    "Pushya":            {"es": "nutrición y crecimiento",       "en": "nourishment and growth"},
    "Ashlesha":          {"es": "percepción y estrategia",       "en": "perception and strategy"},
    "Magha":             {"es": "poder y autoridad",             "en": "power and authority"},
    "Purva Phalguni":    {"es": "placer y creatividad",          "en": "pleasure and creativity"},
    "Uttara Phalguni":   {"es": "acuerdos y compromisos",        "en": "agreements and commitments"},
    "Hasta":             {"es": "habilidad y precisión",         "en": "skill and precision"},
    "Chitra":            {"es": "diseño y brillantez",           "en": "design and brilliance"},
    "Swati":             {"es": "independencia y movimiento",    "en": "independence and movement"},
    "Vishakha":          {"es": "enfoque y propósito",           "en": "focus and purpose"},
    "Anuradha":          {"es": "devoción y cooperación",        "en": "devotion and cooperation"},
    "Jyeshtha":          {"es": "autoridad y protección",        "en": "authority and protection"},
    "Mula":              {"es": "raíces y transformación",       "en": "roots and transformation"},
    "Purva Ashadha":     {"es": "invencibilidad y pureza",       "en": "invincibility and purification"},
    "Uttara Ashadha":    {"es": "victoria definitiva",           "en": "definitive victory"},
    "Shravana":          {"es": "escucha y aprendizaje",         "en": "listening and learning"},
    "Shatabhisha":       {"es": "sanación y misterio",           "en": "healing and mystery"},
    "Purva Bhadrapada":  {"es": "intensidad y fuego interior",   "en": "intensity and inner fire"},
    "Uttara Bhadrapada": {"es": "profundidad y sabiduría",       "en": "depth and wisdom"},
    "Revati":            {"es": "viaje y compasión",             "en": "journey and compassion"},
    "Abhijit":           {"es": "momento victorioso",            "en": "victorious moment"},
}

_NAK_ACTION = {
    "Ashwini":           {"es": "Bueno para lanzar proyectos nuevos.",               "en": "Good for launching new projects."},
    "Bharani":           {"es": "Día intenso para trabajo de fondo.",                "en": "Intense day for deep work."},
    "Krittika":          {"es": "Bueno para decisiones directas.",                   "en": "Good for direct decisions."},
    "Rohini":            {"es": "Excelente para negocios y creatividad.",            "en": "Excellent for business and creativity."},
    "Mrigashira":        {"es": "Bueno para investigar y explorar.",                 "en": "Good for research and exploration."},
    "Ardra":             {"es": "Permite soltar lo viejo.",                          "en": "Good for letting go."},
    "Punarvasu":         {"es": "Los segundos intentos tienen éxito hoy.",           "en": "Second attempts succeed today."},
    "Pushya":            {"es": "Uno de los mejores días del mes para iniciar.",     "en": "One of the best days to start anything."},
    "Ashlesha":          {"es": "Bueno para negociaciones profundas.",               "en": "Good for deep negotiations."},
    "Magha":             {"es": "Día para liderar y tomar decisiones grandes.",      "en": "Day to lead and make big decisions."},
    "Purva Phalguni":    {"es": "Bueno para arte, amor y descanso.",                 "en": "Good for art, love, and rest."},
    "Uttara Phalguni":   {"es": "Excelente para firmar contratos.",                  "en": "Excellent for signing contracts."},
    "Hasta":             {"es": "Bueno para trabajo detallado y manual.",            "en": "Good for detailed and hands-on work."},
    "Chitra":            {"es": "Energía creativa alta — bueno para crear.",         "en": "High creative energy — good for making things."},
    "Swati":             {"es": "Bueno para viajes y nuevas ideas.",                 "en": "Good for travel and new ideas."},
    "Vishakha":          {"es": "Energía fuerte para lograr metas.",                 "en": "Strong energy for achieving goals."},
    "Anuradha":          {"es": "Bueno para relaciones y trabajo en equipo.",        "en": "Good for relationships and teamwork."},
    "Jyeshtha":          {"es": "Día de liderazgo — toma el control.",               "en": "Leadership day — take charge."},
    "Mula":              {"es": "Día para sanar heridas profundas.",                 "en": "Day to heal deep wounds."},
    "Purva Ashadha":     {"es": "Energía para superar obstáculos.",                  "en": "Energy to overcome obstacles."},
    "Uttara Ashadha":    {"es": "Lo que inicies hoy tiene éxito duradero.",          "en": "What you start today has lasting success."},
    "Shravana":          {"es": "Bueno para absorber conocimiento nuevo.",           "en": "Good for absorbing new knowledge."},
    "Shatabhisha":       {"es": "Energía para trabajo profundo y solitario.",        "en": "Energy for deep, solo work."},
    "Purva Bhadrapada":  {"es": "Día para compromisos profundos.",                   "en": "Day for deep commitments."},
    "Uttara Bhadrapada": {"es": "Bueno para meditación y estudio serio.",            "en": "Good for meditation and serious study."},
    "Revati":            {"es": "Energía nutritiva — bueno para ayudar a otros.",    "en": "Nurturing energy — good for helping others."},
    "Abhijit":           {"es": "Ventana especial de éxito durante el mediodía.",    "en": "Special window of success around midday."},
}

_TITHI_MEANING = {
    "1st":  {"es": "energía de inicio — momento para comenzar",      "en": "new beginning energy — time to start"},
    "2nd":  {"es": "energía suave de planificación",                  "en": "gentle planning energy"},
    "3rd":  {"es": "energía de expansión y conexión",                 "en": "expansion and connection energy"},
    "4th":  {"es": "energía de construcción y estabilidad",           "en": "building and stability energy"},
    "5th":  {"es": "energía de riqueza — uno de los mejores días",    "en": "wealth energy — one of the best days"},
    "6th":  {"es": "energía de salud y vitalidad",                    "en": "health and vitality energy"},
    "7th":  {"es": "energía de movimiento y acción",                  "en": "movement and action energy"},
    "8th":  {"es": "energía de prueba — actúa con paciencia",         "en": "challenge energy — act with patience"},
    "9th":  {"es": "energía de fortuna — día auspicioso",             "en": "fortune energy — auspicious day"},
    "10th": {"es": "energía de éxito — bueno para cerrar tratos",     "en": "success energy — good for closing deals"},
    "11th": {"es": "energía espiritual elevada",                      "en": "elevated spiritual energy"},
    "12th": {"es": "energía de logros — completa pendientes",         "en": "achievement energy — complete what's pending"},
    "13th": {"es": "energía de victoria — día favorable",             "en": "victory energy — favorable day"},
    "14th": {"es": "energía intensa — requiere enfoque",              "en": "intense energy — requires focus"},
    "15th": {"es": "luna llena — energía máxima, todo se amplifica",  "en": "full moon — maximum energy, everything amplifies"},
    "16th": {"es": "energía de soltar y sanar",                       "en": "releasing and healing energy"},
    "17th": {"es": "energía de reflexión interior",                   "en": "inner reflection energy"},
    "18th": {"es": "energía de claridad y perspectiva",               "en": "clarity and perspective energy"},
    "19th": {"es": "energía de organización y preparación",           "en": "organization and preparation energy"},
    "20th": {"es": "energía de profundidad estratégica",              "en": "strategic depth energy"},
    "21st": {"es": "energía de transición — mantén flexibilidad",     "en": "transition energy — stay flexible"},
    "22nd": {"es": "energía de consolidación",                        "en": "consolidation energy"},
    "23rd": {"es": "energía introspectiva — escucha tu intuición",    "en": "introspective energy — listen to your intuition"},
    "24th": {"es": "energía de recuperación y descanso",              "en": "recovery and rest energy"},
    "25th": {"es": "energía de revisión interior",                    "en": "inner review energy"},
    "26th": {"es": "energía de introspección profunda — suelta lo viejo", "en": "deep introspection energy — release the old"},
    "27th": {"es": "energía de preparación final",                    "en": "final preparation energy"},
    "28th": {"es": "energía de cierre — libera lo que no sirve",      "en": "closing energy — release what no longer serves"},
    "29th": {"es": "energía de fin de ciclo",                         "en": "end of cycle energy"},
    "30th": {"es": "energía de luna nueva — cierre y comienzo",       "en": "new moon energy — closing and beginning"},
}

_VARA = {
    "Sunday":    {"es_day": "Domingo",   "planet_es": "Sol",       "planet_en": "Sun",      "es": "Bueno para liderazgo, visibilidad y autoridad.",         "en": "Good for leadership, visibility, and authority."},
    "Monday":    {"es_day": "Lunes",     "planet_es": "Luna",      "planet_en": "Moon",     "es": "Bueno para trabajo creativo, intuición y relaciones.",   "en": "Good for creative work, intuition, and relationships."},
    "Tuesday":   {"es_day": "Martes",    "planet_es": "Marte",     "planet_en": "Mars",     "es": "Bueno para iniciar y confrontar obstáculos.",            "en": "Good for starting things and confronting obstacles."},
    "Wednesday": {"es_day": "Miércoles", "planet_es": "Mercurio",  "planet_en": "Mercury",  "es": "Mejor día para reuniones, comunicación y contratos.",    "en": "Best day for meetings, communication, and contracts."},
    "Thursday":  {"es_day": "Jueves",    "planet_es": "Júpiter",   "planet_en": "Jupiter",  "es": "Bueno para aprender y tomar decisiones importantes.",    "en": "Good for learning and making important decisions."},
    "Friday":    {"es_day": "Viernes",   "planet_es": "Venus",     "planet_en": "Venus",    "es": "Bueno para relaciones, amor y creatividad.",             "en": "Good for relationships, love, and creativity."},
    "Saturday":  {"es_day": "Sábado",    "planet_es": "Saturno",   "planet_en": "Saturn",   "es": "Día para trabajo serio, disciplina y responsabilidad.",  "en": "Day for serious work, discipline, and responsibility."},
}

_ACTION_TRANS = {
    "research": {"es": "investigación", "en": "research"},
    "solo work": {"es": "trabajo en solitario", "en": "solo work"},
    "unconventional approaches": {"es": "enfoques innovadores", "en": "unconventional approaches"},
    "public-facing work": {"es": "trabajo público", "en": "public-facing work"},
    "partnerships": {"es": "asociaciones", "en": "partnerships"},
    "communication": {"es": "comunicación", "en": "communication"},
    "business meetings": {"es": "reuniones de negocios", "en": "business meetings"},
    "contracts": {"es": "contratos", "en": "contracts"},
    "creative work": {"es": "trabajo creativo", "en": "creative work"},
    "leadership": {"es": "liderazgo", "en": "leadership"},
    "presentations": {"es": "presentaciones", "en": "presentations"},
    "travel": {"es": "viajes", "en": "travel"},
    "learning": {"es": "aprendizaje", "en": "learning"},
    "relationships": {"es": "relaciones", "en": "relationships"},
    "physical activity": {"es": "actividad física", "en": "physical activity"},
    "meditation": {"es": "meditación", "en": "meditation"},
    "financial decisions": {"es": "decisiones financieras", "en": "financial decisions"},
    "new beginnings": {"es": "nuevos comienzos", "en": "new beginnings"},
    "deep work": {"es": "trabajo profundo", "en": "deep work"},
    "networking": {"es": "networking", "en": "networking"},
    "writing": {"es": "escritura", "en": "writing"},
    "healing": {"es": "sanación", "en": "healing"},
    "planning": {"es": "planificación", "en": "planning"},
}

def _build_panchang_card(day_data, language="es"):
    """
    Converts raw daily-week day into plain-language panchang.
    NEVER shows nakshatra names or tithi numbers to users.
    Only shows meaning.
    """
    if not day_data or not isinstance(day_data, dict):
        return {}

    lang = language if language in ("es", "en") else "es"
    nak       = day_data.get("moon_nakshatra", "")
    tithi     = day_data.get("tithi", "")
    day_name  = day_data.get("day", "")
    aligned   = day_data.get("aligned_for") or []
    friction  = day_data.get("friction_for") or []
    signal    = day_data.get("signal", "")
    move      = day_data.get("move", "")
    event_signal = day_data.get("event_signal") or {}
    score     = day_data.get("score", 5)
    is_friction = day_data.get("is_friction_day", False)

    nak_energy  = _NAK.get(nak, {}).get(lang, "")
    nak_action  = _NAK_ACTION.get(nak, {}).get(lang, "")
    tithi_meaning = _TITHI_MEANING.get(tithi, {}).get(lang, "")
    vara        = _VARA.get(day_name, {})

    def trans(items):
        return [_ACTION_TRANS.get(a, {}).get(lang, a) for a in items]

    if lang == "es":
        day_display = vara.get("es_day", day_name)
        planet      = vara.get("planet_es", "")
        vara_action = vara.get("es", "")

        # Headline: NO tithi numbers, NO nakshatra names
        # Just: "Lunes · energía de sanación y misterio"
        headline = f"{day_display} · energía de {nak_energy}" if nak_energy else day_display

        # Sub: what does today's energy mean + what to do
        energy_desc = f"{nak_action} {tithi_meaning}".strip()

        # Day context (planet)
        day_context = f"Día de {planet} — {vara_action}" if planet else vara_action

        day_quality = "Alta fricción — actúa con cuidado" if is_friction else ("Día fuerte" if score >= 7 else "Día favorable")

        event_out = None
        if event_signal and event_signal.get("fires"):
            cat_map = {"relationship":"relaciones","career":"carrera","wealth":"riqueza","health":"salud","general":"general"}
            event_out = {
                "category": cat_map.get(event_signal.get("category",""), event_signal.get("category","")),
                "hint": event_signal.get("hint",""),
                "strength": event_signal.get("strength",""),
                "follow_up": "Si algo pasa hoy en esta área — pregúntale a Antar."
            }
    else:
        day_display = day_name
        planet      = vara.get("planet_en", "")
        vara_action = vara.get("en", "")

        headline    = f"{day_display} · {nak_energy} energy" if nak_energy else day_display
        energy_desc = f"{nak_action} {tithi_meaning}".strip()
        day_context = f"{planet}'s day — {vara_action}" if planet else vara_action
        day_quality = "High friction — act carefully" if is_friction else ("Strong day" if score >= 7 else "Favorable day")

        event_out = None
        if event_signal and event_signal.get("fires"):
            event_out = {
                "category": event_signal.get("category",""),
                "hint": event_signal.get("hint",""),
                "strength": event_signal.get("strength",""),
                "follow_up": event_signal.get("follow_up","")
            }

    return {
        "headline":          headline,
        "energy_desc":       energy_desc,
        "day_context":       day_context,
        "day_quality":       day_quality,
        "do_today":          trans(aligned),
        "dont_today":        trans(friction),
        "signal":            signal,
        "move":              move,
        "event_signal":      event_out,
        "score":             score,
        "is_friction_day":   is_friction,
        "moon_nakshatra":    nak,
        "tithi":             tithi,
        "day":               day_display,
    }

'''

# Inject before dashboard route
ANCHOR = '@app.get("/api/v1/dashboard/{chart_id}")'

if "_build_panchang_card" in src:
    print("Panchang function already present — replacing...")
    # Replace old version
    start = src.find("# ─── Panchang plain language")
    end = src.find("\n@app.get", start)
    if start > 0 and end > 0:
        src = src[:start] + PANCHANG_FUNC.strip() + "\n\n" + src[end:]
        print("Replaced existing panchang function")
    else:
        print("Could not find bounds to replace — skipping")
elif ANCHOR in src:
    src = src.replace(ANCHOR, PANCHANG_FUNC + "\n" + ANCHOR)
    print("Panchang function injected")
else:
    print(f"ERROR: Cannot find anchor")
    exit(1)

# Find dashboard function and inject panchang call before return
lines = src.split("\n")
dashboard_func_line = None
for i, line in enumerate(lines):
    if "async def" in line and "dashboard" in line and "chart_id" in line:
        dashboard_func_line = i
        print(f"Dashboard function at line {i+1}")
        break

if dashboard_func_line is None:
    print("ERROR: Dashboard function not found"); exit(1)

# Find return statement
in_return = False
return_line = None
return_end = None
brace_depth = 0

for i in range(dashboard_func_line, min(dashboard_func_line+300, len(lines))):
    line = lines[i]
    stripped = line.strip()
    if not in_return and stripped.startswith("return {"):
        in_return = True; return_line = i
        brace_depth = line.count("{") - line.count("}")
        if brace_depth <= 0: return_end = i; break
    elif in_return:
        brace_depth += line.count("{") - line.count("}")
        if brace_depth <= 0: return_end = i; break

if not (return_line and return_end):
    print("ERROR: Dashboard return not found"); exit(1)

print(f"Dashboard return: lines {return_line+1}–{return_end+1}")

# Check if already patched
if "_build_panchang_card" in "\n".join(lines[return_line-20:return_line]):
    print("Panchang call already injected — skipping")
else:
    indent = " " * (len(lines[return_line]) - len(lines[return_line].lstrip()))
    inject = [
        f"{indent}# Panchang from daily-week",
        f"{indent}_pc = {{}}",
        f"{indent}try:",
        f"{indent}    from antar_engine.daily_prediction_engine import build_daily_week",
        f"{indent}    _dw = build_daily_week(chart_id=chart_id, tz_offset=-5, language=language)",
        f"{indent}    _days = _dw.get('days', [])",
        f"{indent}    if _days: _pc = _build_panchang_card(_days[0], language)",
        f"{indent}except Exception as _pe:",
        f"{indent}    print(f'[dashboard] panchang: {{_pe}}')",
        "",
    ]
    for j, l in enumerate(inject):
        lines.insert(return_line + j, l)

    new_end = return_end + len(inject)
    ci = " " * (len(lines[new_end]) - len(lines[new_end].lstrip()))
    prev = lines[new_end-1].rstrip()
    if prev and not prev.endswith(","):
        lines[new_end-1] = prev + ","

    fields = [
        f'{ci}    "panchanga_headline":   _pc.get("headline", ""),',
        f'{ci}    "energy_desc_today":    _pc.get("energy_desc", ""),',
        f'{ci}    "day_context_today":    _pc.get("day_context", ""),',
        f'{ci}    "day_quality":          _pc.get("day_quality", ""),',
        f'{ci}    "do_today":             _pc.get("do_today", []),',
        f'{ci}    "dont_today":           _pc.get("dont_today", []),',
        f'{ci}    "signal_today":         _pc.get("signal", ""),',
        f'{ci}    "move_today":           _pc.get("move", ""),',
        f'{ci}    "event_signal_today":   _pc.get("event_signal"),',
        f'{ci}    "moon_nak_today":       _pc.get("moon_nakshatra", ""),',
        f'{ci}    "is_friction_day":      _pc.get("is_friction_day", False),',
    ]
    for j, fl in enumerate(fields):
        lines.insert(new_end + j, fl)
    print(f"Fields injected. Total lines added: {len(inject)+len(fields)}")

src = "\n".join(lines)

# Add language param if missing
m = re.search(r'(async def \w*dashboard\w*\s*\(chart_id\s*:\s*str\s*)', src)
if m and "language" not in src[m.start():m.start()+200]:
    src = src.replace(m.group(1), m.group(1).rstrip()+", language: str = 'es', ")
    print("Added language param")

with open(TARGET, "w") as f:
    f.write(src)

try:
    ast.parse(src)
    print("Syntax OK")
except SyntaxError as e:
    print(f"SYNTAX ERROR: {e}")
    shutil.copy2(BACKUP, TARGET)
    print("Backup restored"); exit(1)

print("""
DONE. Deploy:
  git add -A && git commit -m "feat: panchang plain language in dashboard" && git push

Verify after 60s:
  curl -s "https://antar-fastapi-production.up.railway.app/api/v1/dashboard/de02bb52-d43a-4b09-be25-b45a07bfbf8a?language=es" | python3 -c "
import sys,json; d=json.load(sys.stdin)
print('headline:', d.get('panchanga_headline'))
print('energy_desc:', d.get('energy_desc_today'))
print('day_context:', d.get('day_context_today'))
print('do_today:', d.get('do_today'))
print('dont_today:', d.get('dont_today'))
"

Expected ES output:
  headline: Lunes · energía de sanación y misterio
  energy_desc: Energía para trabajo profundo y solitario. Energía de introspección profunda — suelta lo viejo.
  day_context: Día de Luna — Bueno para trabajo creativo, intuición y relaciones.
  do_today: ['investigación', 'trabajo en solitario', 'enfoques innovadores']
  dont_today: ['trabajo público', 'asociaciones']
""")
