#!/usr/bin/env python3
"""
patch_hora_spanish.py

Adds Spanish translation to /api/v1/hora/{chart_id} endpoint.

Changes:
1. Adds language parameter to the FIRST get_hora handler (line ~10685)
2. Adds _translate_hora_es() helper function
3. Applies translation to result before returning

Targets ONLY the first handler (the one FastAPI actually uses).
The three duplicate dead handlers at 10744/10804/10864 are left untouched
(separate cleanup task).

Backs up main.py, patches, ast.parses, prints verify curl.
"""

import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

MAIN = Path("main.py")
BACKUP = Path(f"main.py.bak_hora_es_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

# ---- landmarks ----

LANDMARK_SIGNATURE = (
    '@app.get("/api/v1/hora/{chart_id}")\n'
    'async def get_hora(chart_id: str, tz_offset: Optional[int] = None, n: int = 8):'
)

NEW_SIGNATURE = (
    '@app.get("/api/v1/hora/{chart_id}")\n'
    'async def get_hora(chart_id: str, tz_offset: Optional[int] = None, n: int = 8, language: Optional[str] = "en"):'
)

LANDMARK_RETURN = '''    # Add next power hora for friction days
    if is_friction_day and daily_field and result.get("upcoming_horas"):
        result["next_power_hora"] = get_next_power_hora(
            result["upcoming_horas"], daily_field
        )

    return result'''

NEW_RETURN = '''    # Add next power hora for friction days
    if is_friction_day and daily_field and result.get("upcoming_horas"):
        result["next_power_hora"] = get_next_power_hora(
            result["upcoming_horas"], daily_field
        )

    # Spanish translation layer
    if (language or "en").lower() == "es":
        result = _translate_hora_es(result)

    return result'''

# ---- helper function to inject ----

HELPER_FUNCTION = '''
# ============================================================
# HORA SPANISH TRANSLATION
# ============================================================

_HORA_WINDOW_ES = {
    "EXPANSION WINDOW": "VENTANA DE EXPANSIÓN",
    "DRIVE WINDOW": "VENTANA DE IMPULSO",
    "AUTHORITY WINDOW": "VENTANA DE AUTORIDAD",
    "LOVE WINDOW": "VENTANA DE AMOR",
    "ATTRACTION WINDOW": "VENTANA DE ATRACCIÓN",
    "REFLECTION WINDOW": "VENTANA DE REFLEXIÓN",
    "DISCIPLINE WINDOW": "VENTANA DE DISCIPLINA",
    "STRUCTURE WINDOW": "VENTANA DE ESTRUCTURA",
    "COMMUNICATION WINDOW": "VENTANA DE COMUNICACIÓN",
    "SHADOW WINDOW": "VENTANA DE SOMBRA",
    "DISSOLUTION WINDOW": "VENTANA DE DISOLUCIÓN",
}

_HORA_FIELD_ES = {
    "EXPANSION": "EXPANSIÓN",
    "COMMAND": "MANDO",
    "CONNECTION": "CONEXIÓN",
    "ATTRACTION": "ATRACCIÓN",
    "REFLECTION": "REFLEXIÓN",
    "DISCIPLINE": "DISCIPLINA",
    "STRUCTURE": "ESTRUCTURA",
    "COMMUNICATION": "COMUNICACIÓN",
    "SHADOW": "SOMBRA",
}

_HORA_MODE_ES = {
    "EXPAND": "EXPANDIR",
    "DRIVE": "IMPULSAR",
    "ATTRACT": "ATRAER",
    "REFLECT": "REFLEJAR",
    "STRUCTURE": "ESTRUCTURAR",
    "CONNECT": "CONECTAR",
    "DISSOLVE": "DISOLVER",
}

_HORA_BY_RULER_ES = {
    "Jupiter": {
        "action": "Estrategia, planificación a largo plazo, mentoría, aprendizaje",
        "plain_message": "Piensa en grande. Sesiones de estrategia, planificación a largo plazo, conversaciones de mentoría. Esta es tu ventana de pensamiento más claro.",
    },
    "Mars": {
        "action": "Ejecución de alta intensidad, gimnasio, confrontaciones, llamadas en frío",
        "plain_message": "Alta energía, alta intensidad. Buena para el gimnasio, llamadas en frío, o empujar una tarea difícil. Canalízala o te canaliza a ti.",
    },
    "Sun": {
        "action": "Reuniones de alto nivel, decisiones de liderazgo, movimientos de visibilidad",
        "plain_message": "Tu ventana de mando está abierta. Envía esa propuesta. Toma la decisión. Ten la conversación de alto riesgo.",
    },
    "Venus": {
        "action": "Relaciones, negociación, acuerdos, trabajo creativo, cerrar con calidez",
        "plain_message": "Ventana de atracción. Buena para relaciones, negociación con calidez, trabajo creativo, cerrar con encanto en vez de presión.",
    },
    "Saturn": {
        "action": "Trabajo profundo, disciplina, documentación, auditoría, compromisos a largo plazo",
        "plain_message": "Ventana de estructura. Trabajo profundo, documentación, decisiones serias. Lento pero sólido — lo que construyas aquí dura.",
    },
    "Mercury": {
        "action": "Escritura, análisis, correos, llamadas, negociación, aprendizaje rápido",
        "plain_message": "Ventana de comunicación. Escribe el correo, haz la llamada, analiza los datos. Tu mente está ágil — úsala.",
    },
    "Moon": {
        "action": "Reflexión, descanso, planificar mañana, trabajo emocional, familia",
        "plain_message": "Baja la intensidad. Reflexiona, planea mañana, conversa con la familia. Ventana suave — no fuerces decisiones grandes.",
    },
    "Rahu": {
        "action": "Movimientos no convencionales, tecnología, apuestas calculadas",
        "plain_message": "Ventana de ruptura. Buena para movimientos no convencionales y tecnología — pero verifica dos veces antes de firmar.",
    },
    "Ketu": {
        "action": "Soltar, meditar, revisión, cierre de ciclos — NO inicies nada nuevo",
        "plain_message": "Ventana de disolución. No inicies nada nuevo. Buena para soltar, meditar, cerrar ciclos pendientes.",
    },
}


def _translate_hora_entry_es(h: dict) -> dict:
    """Translate a single hora dict in-place (returns same dict)."""
    if not isinstance(h, dict):
        return h

    # Window label
    if h.get("window") in _HORA_WINDOW_ES:
        h["window"] = _HORA_WINDOW_ES[h["window"]]

    # Field / mode
    if h.get("field") in _HORA_FIELD_ES:
        h["field"] = _HORA_FIELD_ES[h["field"]]
    if h.get("mode") in _HORA_MODE_ES:
        h["mode"] = _HORA_MODE_ES[h["mode"]]

    # Action + plain_message — key off ruler (always English from engine)
    ruler = h.get("ruler")
    if ruler and ruler in _HORA_BY_RULER_ES:
        tr = _HORA_BY_RULER_ES[ruler]
        h["action"] = tr["action"]
        h["plain_message"] = tr["plain_message"]

    return h


def _translate_hora_es(result: dict) -> dict:
    """Apply Spanish translation to full hora response dict."""
    if not isinstance(result, dict):
        return result

    if result.get("current_hora"):
        result["current_hora"] = _translate_hora_entry_es(result["current_hora"])

    if isinstance(result.get("upcoming_horas"), list):
        result["upcoming_horas"] = [
            _translate_hora_entry_es(h) for h in result["upcoming_horas"]
        ]

    if result.get("next_power_hora"):
        result["next_power_hora"] = _translate_hora_entry_es(result["next_power_hora"])

    return result

# ============================================================
# END HORA SPANISH TRANSLATION
# ============================================================

'''

# ---- injection point for helper: just before the first hora handler ----

HELPER_INJECT_LANDMARK = '@app.get("/api/v1/hora/{chart_id}")\nasync def get_hora(chart_id: str, tz_offset: Optional[int] = None, n: int = 8):'


def main():
    if not MAIN.exists():
        print(f"❌ {MAIN} not found. Run from project root.")
        sys.exit(1)

    print(f"📦 Backing up to {BACKUP}")
    shutil.copy(MAIN, BACKUP)

    src = MAIN.read_text()

    # --- Safety check: helper must not already exist ---
    if "_translate_hora_es" in src:
        print("⚠️  _translate_hora_es already present in main.py — aborting to avoid double-patch.")
        print("    If you need to re-apply, restore from backup and try again.")
        sys.exit(1)

    # --- Step 1: inject helper function BEFORE the first hora handler ---
    if HELPER_INJECT_LANDMARK not in src:
        print("❌ Could not find hora handler landmark for helper injection.")
        sys.exit(1)

    src_new = src.replace(
        HELPER_INJECT_LANDMARK,
        HELPER_FUNCTION + HELPER_INJECT_LANDMARK,
        1,  # only first occurrence
    )
    print("✅ Step 1: helper function injected")

    # --- Step 2: update signature of FIRST handler to accept language ---
    # We replace ALL four duplicate signatures? No — only the first.
    # Since all four signatures are identical, .replace(old, new, 1) handles it.
    if LANDMARK_SIGNATURE not in src_new:
        print("❌ Could not find handler signature landmark.")
        shutil.copy(BACKUP, MAIN)
        sys.exit(1)

    src_new = src_new.replace(LANDMARK_SIGNATURE, NEW_SIGNATURE, 1)
    print("✅ Step 2: first handler signature updated with language param")

    # --- Step 3: wrap the return with translation call ---
    # The return block is IDENTICAL in all four handlers. We only want the first.
    # .replace(old, new, 1) gives us first occurrence.
    if LANDMARK_RETURN not in src_new:
        print("❌ Could not find return block landmark.")
        shutil.copy(BACKUP, MAIN)
        sys.exit(1)

    occurrences = src_new.count(LANDMARK_RETURN)
    print(f"   Found {occurrences} occurrences of return block (expected 4 — will patch only first)")

    src_new = src_new.replace(LANDMARK_RETURN, NEW_RETURN, 1)
    print("✅ Step 3: first handler return wrapped with translation")

    # --- Step 4: ast.parse verify ---
    try:
        ast.parse(src_new)
        print("✅ Step 4: ast.parse OK")
    except SyntaxError as e:
        print(f"❌ Syntax error after patch: {e}")
        shutil.copy(BACKUP, MAIN)
        print(f"    Restored from {BACKUP}")
        sys.exit(1)

    MAIN.write_text(src_new)
    print(f"✅ Patched {MAIN}")

    print()
    print("=" * 60)
    print("NEXT STEPS:")
    print("=" * 60)
    print("1. git diff main.py  # review")
    print("2. git add main.py && git commit -m 'feat: Spanish translation for hora endpoint'")
    print("3. git push  # Railway auto-deploy")
    print("4. Wait ~60s for deploy, then verify:")
    print()
    print("   curl -s 'https://antar-fastapi-production.up.railway.app/api/v1/hora/de02bb52-d43a-4b09-be25-b45a07bfbf8a?tz_offset=-5&language=es&n=6' \\")
    print("     | python3 -m json.tool | head -40")
    print()
    print("   Expect: window='VENTANA DE EXPANSIÓN', plain_message starts with 'Piensa en grande...'")
    print()
    print(f"   If anything breaks:  cp {BACKUP} main.py && git checkout main.py")


if __name__ == "__main__":
    main()
