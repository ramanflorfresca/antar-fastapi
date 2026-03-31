"""
apply_sprint_w_patch.py
Run from your project root: python apply_sprint_w_patch.py
Makes three targeted changes:
  1. welcome_signal.py — add age_utils import
  2. welcome_signal.py — add age rules to system prompt
  3. main.py           — calculate age before create_task, pass birth_date
"""

import sys

# ─────────────────────────────────────────────────────────────────
# PATCH 1 + 2: antar_engine/welcome_signal.py
# ─────────────────────────────────────────────────────────────────

ws_path = "antar_engine/welcome_signal.py"
with open(ws_path) as f:
    ws = f.read()

# 1. Add import after "from typing import Optional"
OLD_IMPORT = "from typing import Optional"
NEW_IMPORT = """from typing import Optional
from antar_engine.age_utils import (
    calculate_current_age, get_floor_age,
    filter_umra_activations, filter_future_dasha_transitions,
    format_timing_pill,
)"""

if "from antar_engine.age_utils" in ws:
    print("SKIP 1: age_utils import already present")
else:
    ws = ws.replace(OLD_IMPORT, NEW_IMPORT, 1)
    print("OK   1: age_utils import added")

# 2. Add age rules block to system prompt — insert before the closing rules line
OLD_PROMPT_TAIL = """The goal: in 3 sentences, make them feel that Antar sees them specifically — 
not a sun sign, not a generic reading, but their exact life situation right now."""

NEW_PROMPT_TAIL = """AGE RULES — CRITICAL:
- The user's current age and temporal floor are in the context — read them first
- NEVER reference themes, events, or life stages from before the floor age
- All timing references must be FUTURE dates — never past
- Career signals for 55+ = authority, legacy, succession — NOT starting out
- Relationship signals for 60+ = depth, companionship — NOT first relationship
- Never reference childhood, teenage years, or early adulthood for users over 40

The goal: in 3 sentences, make them feel that Antar sees them specifically — 
not a sun sign, not a generic reading, but their exact life situation right now."""

if "AGE RULES — CRITICAL" in ws:
    print("SKIP 2: age rules already in system prompt")
else:
    ws = ws.replace(OLD_PROMPT_TAIL, NEW_PROMPT_TAIL, 1)
    print("OK   2: age rules added to system prompt")

# 3. Replace _build_welcome_context with age-aware version
OLD_CONTEXT_FN = '''def _build_welcome_context(
    chart_data:    dict,
    dashas:        dict,
    first_name:    Optional[str],
    lagna:         Optional[str],
    moon_sign:     Optional[str],
    current_dasha: Optional[str],
    age:           Optional[int],
    country_code:  Optional[str],
) -> str:
    name_line = f"User's name: {first_name}" if first_name else "User's name: not provided"
    age_line  = f"Age: {age}" if age else ""
    country_line = f"Country: {country_code}" if country_code else ""

    # Extract key chart facts
    planets = chart_data.get("planets", {})
    sun_sign  = planets.get("Sun",  {}).get("sign", "")
    mars_sign = planets.get("Mars", {}).get("sign", "")

    # Get top yoga if available
    yogas = chart_data.get("yogas", [])
    top_yoga = yogas[0].get("name", "") if yogas else ""

    # Get current dasha
    dasha_text = current_dasha or ""
    if not dasha_text and dashas:
        vim = dashas.get("vimsottari", [])
        if vim:
            first = vim[0]
            lord = first.get("lord_or_sign") or first.get("planet_or_sign", "")
            dasha_text = lord

    lines = [
        name_line,
        f"Rising sign (Lagna): {lagna or \'unknown\'}",
        f"Moon sign: {moon_sign or \'unknown\'}",
        f"Sun sign: {sun_sign}",
        f"Current planetary period: {dasha_text}",
    ]
    if age_line:    lines.append(age_line)
    if country_line: lines.append(country_line)
    if top_yoga:    lines.append(f"Strongest yoga in chart: {top_yoga}")
    if mars_sign:   lines.append(f"Mars in: {mars_sign}")

    lines.append(
        "\\nGenerate a welcome signal that makes this person feel immediately understood. "
        "Reference their rising sign and current planetary period specifically. "
        "Tell them what chapter of life they are in and what it means for right now."
    )

    return "\\n".join(lines)'''

NEW_CONTEXT_FN = '''def _build_welcome_context(
    chart_data:    dict,
    dashas:        dict,
    first_name:    Optional[str],
    lagna:         Optional[str],
    moon_sign:     Optional[str],
    current_dasha: Optional[str],
    age:           Optional[int],
    country_code:  Optional[str],
    birth_date:    Optional[str] = None,
) -> str:
    # ── Age intelligence (Sprint W) ───────────────────────────────
    if birth_date:
        current_age = calculate_current_age(birth_date[:10])
    elif age:
        current_age = age
    else:
        current_age = None

    floor_age = get_floor_age(current_age) if current_age else None

    umra_block = ""
    if current_age:
        umra_items = filter_umra_activations(current_age, max_upcoming=2)
        if umra_items:
            umra_lines = [
                f"  House {u[\'house\']} (age {u[\'activation_age\']}): {u[\'theme\']}"
                for u in umra_items
            ]
            umra_block = "Upcoming age activations:\\n" + "\\n".join(umra_lines)

    # ── Dasha — future transitions only ──────────────────────────
    dasha_text = current_dasha or ""
    future_transition = ""
    if not dasha_text and dashas:
        vim = dashas.get("vimsottari", [])
        if vim:
            first = vim[0]
            dasha_text = first.get("lord_or_sign") or first.get("planet_or_sign", "")

    raw_ts = []
    for d in dashas.get("vimsottari", []) if dashas else []:
        if d.get("end_date"):
            raw_ts.append({
                "planet": d.get("lord_or_sign") or d.get("planet_or_sign", ""),
                "end_date": d["end_date"],
            })
    future_ts = filter_future_dasha_transitions(raw_ts)
    if future_ts:
        future_transition = f"Current period ends: {format_timing_pill(future_ts[0][\'end_date\'])}"

    # ── Chart facts ───────────────────────────────────────────────
    planets   = chart_data.get("planets", {})
    sun_sign  = planets.get("Sun",  {}).get("sign", "")
    mars_sign = planets.get("Mars", {}).get("sign", "")
    yogas     = chart_data.get("yogas", [])
    top_yoga  = yogas[0].get("name", "") if yogas else ""

    # ── Assemble — temporal grounding first ───────────────────────
    lines = []
    if current_age and floor_age:
        lines.append(f"TEMPORAL GROUNDING: This user is {current_age} years old.")
        lines.append(f"Temporal floor: never reference themes or events from before age {floor_age}.")
        lines.append(f"Today: {datetime.now().strftime(\'%B %d, %Y\')}")
        lines.append("")

    if first_name:    lines.append(f"User\'s name: {first_name}")
    if country_code:  lines.append(f"Country: {country_code}")
    lines.append(f"Rising sign (Lagna): {lagna or \'unknown\'}")
    lines.append(f"Moon sign: {moon_sign or \'unknown\'}")
    lines.append(f"Sun sign: {sun_sign}")
    lines.append(f"Current planetary period: {dasha_text}")
    if future_transition: lines.append(future_transition)
    if top_yoga:    lines.append(f"Strongest yoga in chart: {top_yoga}")
    if mars_sign:   lines.append(f"Mars in: {mars_sign}")
    if umra_block:  lines.append(umra_block)

    age_note = f"someone who is currently {current_age} years old." if current_age else "an adult."
    lines.append(
        "\\nGenerate a welcome signal that makes this person feel immediately understood. "
        "Reference their rising sign and current planetary period specifically. "
        "Tell them what chapter of life they are in and what it means for right now. "
        "All content must be appropriate for " + age_note
    )

    return "\\n".join(lines)'''

if "birth_date:    Optional[str] = None" in ws:
    print("SKIP 3: _build_welcome_context already patched")
else:
    if OLD_CONTEXT_FN in ws:
        ws = ws.replace(OLD_CONTEXT_FN, NEW_CONTEXT_FN, 1)
        print("OK   3: _build_welcome_context patched with age intelligence")
    else:
        print("FAIL 3: Could not find _build_welcome_context — check manually")
        sys.exit(1)

with open(ws_path, "w") as f:
    f.write(ws)
print(f"     Saved {ws_path}\n")

# ─────────────────────────────────────────────────────────────────
# PATCH 4: main.py — calculate age + pass birth_date in create_task
# ─────────────────────────────────────────────────────────────────

main_path = "main.py"
with open(main_path) as f:
    main = f.read()

OLD_TASK = """        # Fire and forget — don't block chart creation response
        _asyncio.create_task(generate_welcome_signal(
            chart_id=chart_id,
            chart_data=chart_data,
            dashas={"vimsottari": vim_dashas or []},
            first_name=_first_name,
            lagna=_lagna_sign,
            moon_sign=_moon_sign,
            current_dasha=_current_dasha,
            age=None,
            country_code=getattr(request, "birth_country", "") or "",
            supabase=supabase,
            claude_client=claude_client,
        ))"""

NEW_TASK = """        # Fire and forget — don't block chart creation response
        # Sprint W: calculate age from birth_date so welcome signal is age-aware
        _birth_date_str = getattr(request, "birth_date", "") or ""
        try:
            from antar_engine.age_utils import calculate_current_age as _calc_age
            _welcome_age = _calc_age(str(_birth_date_str)[:10]) if _birth_date_str else None
        except Exception:
            _welcome_age = None

        _asyncio.create_task(generate_welcome_signal(
            chart_id=chart_id,
            chart_data=chart_data,
            dashas={"vimsottari": vim_dashas or []},
            first_name=_first_name,
            lagna=_lagna_sign,
            moon_sign=_moon_sign,
            current_dasha=_current_dasha,
            age=_welcome_age,
            birth_date=_birth_date_str,
            country_code=getattr(request, "birth_country", "") or "",
            supabase=supabase,
            claude_client=claude_client,
        ))"""

if "_welcome_age" in main:
    print("SKIP 4: main.py create_task already patched")
else:
    if OLD_TASK in main:
        main = main.replace(OLD_TASK, NEW_TASK, 1)
        print("OK   4: main.py create_task patched — age now calculated from birth_date")
    else:
        print("FAIL 4: Could not find create_task block — check manually")
        sys.exit(1)

# Also patch the synchronous fallback call in get_welcome() — age=None there too
OLD_SYNC = """        result = await generate_welcome_signal(
            chart_id=chart_id,
            chart_data=chart_data,
            dashas={},
            first_name=chart_record.get("first_name", ""),
            lagna=chart_record.get("lagna_sign", "") or chart_data.get("lagna", {}).get("sign", ""),
            moon_sign=chart_record.get("moon_sign", "") or planets.get("Moon", {}).get("sign", ""),
            current_dasha=_current_dasha,
            age=None,
            country_code=chart_record.get("current_country") or chart_record.get("country_code", ""),
            supabase=supabase,
            claude_client=claude_client,
        )"""

NEW_SYNC = """        _bd = str(chart_record.get("birth_date", "") or "")[:10]
        try:
            from antar_engine.age_utils import calculate_current_age as _ca
            _sync_age = _ca(_bd) if _bd else None
        except Exception:
            _sync_age = None

        result = await generate_welcome_signal(
            chart_id=chart_id,
            chart_data=chart_data,
            dashas={},
            first_name=chart_record.get("first_name", ""),
            lagna=chart_record.get("lagna_sign", "") or chart_data.get("lagna", {}).get("sign", ""),
            moon_sign=chart_record.get("moon_sign", "") or planets.get("Moon", {}).get("sign", ""),
            current_dasha=_current_dasha,
            age=_sync_age,
            birth_date=_bd,
            country_code=chart_record.get("current_country") or chart_record.get("country_code", ""),
            supabase=supabase,
            claude_client=claude_client,
        )"""

if "_sync_age" in main:
    print("SKIP 5: main.py get_welcome sync call already patched")
else:
    if OLD_SYNC in main:
        main = main.replace(OLD_SYNC, NEW_SYNC, 1)
        print("OK   5: main.py get_welcome sync call patched")
    else:
        print("FAIL 5: Could not find get_welcome sync call — check manually")
        sys.exit(1)

with open(main_path, "w") as f:
    f.write(main)
print(f"     Saved {main_path}\n")

print("=== All patches applied. Run: python -c \"from antar_engine.welcome_signal import _build_welcome_context; print('import OK')\" ===")
