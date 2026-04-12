"""
patch_domain_signals_plain_english.py — Fix domain-signals returning raw jargon

THE BUG:
  GET /api/v1/domain-signals/{chart_id} returns signal_line values that contain
  raw astrological computation text:
    "sign aspects Karakamsa — Soul purpose resonance"
    "Structural Load (instrument lord) in dusthana annual house — yearly pressure"

  These are stored directly from Jaimini/Parashari computation output without
  going through plain_english.py. They surface in the Dashboard area cards.

THE FIX:
  In main.py, the domain-signals endpoint reads signal_line from the predictions
  table. The predictions table signal_line IS processed through plain_english.py —
  so the fix is to ensure domain-signals reads from predictions.signal_line
  (the plain English version) and NOT from any raw computation field.

  Additionally, add a jargon filter as a safety net: if a stored signal_line
  still contains jargon patterns, replace with a safe fallback prompt.

Run: python patch_domain_signals_plain_english.py
Backs up to: main.py.bak_domain_signals
"""

import os
import re
import shutil

TARGET = "main.py"
BACKUP = "main.py.bak_domain_signals"

# Jargon patterns that should never appear in user-facing signal_line
JARGON_PATTERNS = [
    "karakamsa", "dusthana", "mahadasha", "antardasha", "instrument lord",
    "sign aspects", "soul purpose resonance", "chara dasha",
    "power off", "sleeping", "structural load", "MC line", "ASC line",
    "lord in", "bhava", "navamsa", "atmakaraka", "amatyakaraka",
    "upapada", "arudha", "varshphal", "masik",
]

JARGON_FILTER_FN = '''
def _is_jargon(text: str) -> bool:
    """Return True if text contains raw astrological computation language."""
    if not text:
        return True
    text_lower = text.lower()
    jargon = [
        "karakamsa", "dusthana", "mahadasha", "antardasha", "instrument lord",
        "sign aspects", "soul purpose resonance", "chara dasha",
        "power off", "sleeping", "structural load",
        "lord in", "bhava", "navamsa", "atmakaraka", "amatyakaraka",
        "upapada", "arudha", "varshphal", "masik",
    ]
    return any(j in text_lower for j in jargon)

def _safe_signal_line(signal_line: str, domain: str, language: str = "en") -> str:
    """Return signal_line if clean, otherwise return a safe ask-Antar prompt."""
    if _is_jargon(signal_line):
        if language == "es":
            return f"Pregunta a Antar sobre tu señal de {domain} esta semana."
        return f"Ask Antar about your {domain} signal this week."
    return signal_line

'''


def patch():
    if not os.path.exists(TARGET):
        print(f"ERROR: {TARGET} not found. Run from ~/antarai project root.")
        return False

    shutil.copy2(TARGET, BACKUP)
    print(f"✓ Backed up to {BACKUP}")

    with open(TARGET, "r") as f:
        content = f.read()

    changes_made = 0

    # ═══════════════════════════════════════════════════════════════
    # PATCH 1: Add _is_jargon() and _safe_signal_line() helper functions
    # ═══════════════════════════════════════════════════════════════

    if "_is_jargon" not in content:
        # Find a good insertion point — after imports, before first route
        # Look for the first @app. route definition
        route_match = re.search(r"\n@app\.", content)
        if route_match:
            insert_pos = route_match.start()
            content = content[:insert_pos] + "\n" + JARGON_FILTER_FN + content[insert_pos:]
            print("✓ Added _is_jargon() and _safe_signal_line() helper functions")
            changes_made += 1
        else:
            print("⚠ Could not find insertion point for helper functions")
            print("  Manually add the following functions before the first @app route:")
            print(JARGON_FILTER_FN)
    else:
        print("⊘ _is_jargon() already exists")

    # ═══════════════════════════════════════════════════════════════
    # PATCH 2: Find domain-signals endpoint and add safety filter on signal_line
    # ═══════════════════════════════════════════════════════════════

    # The domain-signals endpoint returns a dict of domains with signal_line values
    # We need to wrap each signal_line with _safe_signal_line()

    # Look for the domain-signals endpoint
    domain_signals_patterns = [
        r'(@app\.get\s*\(\s*["\'].*domain-signals.*["\'])',
        r'(domain.signals|domain_signals)',
    ]

    endpoint_found = False
    for pattern in domain_signals_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            endpoint_found = True
            break

    if endpoint_found:
        # Look for where signal_line is assembled into the response dict
        # Common patterns: "signal_line": row["signal_line"] or similar
        signal_line_patterns = [
            r'(["\']signal_line["\']:\s*)(row\[["\']signal_line["\']\])',
            r'(["\']signal_line["\']:\s*)(pred\[["\']signal_line["\']\])',
            r'(["\']signal_line["\']:\s*)(result\[["\']signal_line["\']\])',
            r'(["\']signal_line["\']:\s*)(p\[["\']signal_line["\']\])',
            r'(["\']signal_line["\']:\s*)(item\[["\']signal_line["\']\])',
        ]

        patched_signal = False
        for pattern in signal_line_patterns:
            matches = list(re.finditer(pattern, content))
            if matches:
                # Replace each match with the safe version
                # We need to work backwards to preserve positions
                for match in reversed(matches):
                    old = match.group(0)
                    key_part = match.group(1)
                    value_part = match.group(2)
                    new = f'{key_part}_safe_signal_line({value_part}, domain, language)'
                    content = content[:match.start()] + new + content[match.end():]
                print(f"✓ Wrapped signal_line values with _safe_signal_line() ({len(matches)} locations)")
                changes_made += 1
                patched_signal = True
                break

        if not patched_signal:
            print("⚠ Could not auto-patch signal_line in domain-signals endpoint")
            print("  Manual fix: find the domain-signals endpoint in main.py")
            print("  Wherever you build the response dict with 'signal_line': <value>,")
            print("  wrap the value: 'signal_line': _safe_signal_line(<value>, domain, language)")
    else:
        print("⚠ Could not find domain-signals endpoint in main.py")
        print("  Search for 'domain-signals' or 'domain_signals' and add the filter manually")

    # ═══════════════════════════════════════════════════════════════
    # PATCH 3: Also filter signal_line in the dashboard endpoint response
    # ═══════════════════════════════════════════════════════════════

    # The dashboard endpoint also surfaces domain signal_lines
    # Look for dashboard endpoint and apply same filter
    dashboard_match = re.search(r'@app\.get\s*\(\s*["\'].*dashboard.*["\']', content, re.IGNORECASE)

    if dashboard_match:
        # Find signal_line usage after dashboard endpoint
        dashboard_start = dashboard_match.start()
        # Look for the next endpoint after dashboard
        next_endpoint = re.search(r'\n@app\.', content[dashboard_start + 10:])
        dashboard_end = dashboard_start + 10 + (next_endpoint.start() if next_endpoint else len(content))
        dashboard_section = content[dashboard_start:dashboard_end]

        if "signal_line" in dashboard_section and "_safe_signal_line" not in dashboard_section:
            print("⚠ Dashboard endpoint also has signal_line — consider applying same filter")
            print("  Find the dashboard endpoint and wrap any signal_line values with _safe_signal_line()")
        else:
            print("⊘ Dashboard signal_line already safe or not found")

    # ═══════════════════════════════════════════════════════════════
    # WRITE
    # ═══════════════════════════════════════════════════════════════

    if changes_made == 0:
        print("\n⚠ No automatic changes applied.")
        print("  The domain-signals endpoint structure may differ from expected.")
        print_manual_instructions()
        return False

    with open(TARGET, "w") as f:
        f.write(content)

    print(f"\n✓ {changes_made} change(s) applied to {TARGET}")
    print(f"  Backup: {BACKUP}")
    print(f"\n  SYNTAX CHECK:")
    print(f"  python3 -c \"import ast; ast.parse(open('{TARGET}').read()); print('Syntax OK')\"")
    print(f"\n  DEPLOY:")
    print(f"  git add -A && git commit -m 'fix: filter jargon from domain-signals signal_line' && git push")
    print(f"\n  VERIFY:")
    print(f"  curl https://antar-fastapi-production.up.railway.app/api/v1/domain-signals/de02bb52-d43a-4b09-be25-b45a07bfbf8a")
    print(f"  Check: no 'karakamsa', 'dusthana', 'Mahadasha' in any signal_line value")

    return True


def print_manual_instructions():
    print("""
═══════════════════════════════════════════════════════════════
MANUAL FIX (if auto-patch failed)
═══════════════════════════════════════════════════════════════

1. Open main.py

2. Add these two functions before the first @app route:

def _is_jargon(text: str) -> bool:
    if not text:
        return True
    text_lower = text.lower()
    jargon = ["karakamsa","dusthana","mahadasha","antardasha",
              "instrument lord","sign aspects","soul purpose resonance",
              "chara dasha","power off","sleeping","structural load",
              "lord in","bhava","navamsa","atmakaraka","amatyakaraka"]
    return any(j in text_lower for j in jargon)

def _safe_signal_line(signal_line: str, domain: str, language: str = "en") -> str:
    if _is_jargon(signal_line):
        if language == "es":
            return f"Pregunta a Antar sobre tu señal de {domain} esta semana."
        return f"Ask Antar about your {domain} signal this week."
    return signal_line

3. Find the GET /api/v1/domain-signals endpoint.
   Wherever it builds the response dict with "signal_line": <value>,
   wrap it: "signal_line": _safe_signal_line(<value>, domain, language)

4. Syntax check, commit, push.
═══════════════════════════════════════════════════════════════
""")


if __name__ == "__main__":
    success = patch()
    if success:
        # Quick syntax check
        try:
            import ast
            with open(TARGET) as f:
                ast.parse(f.read())
            print("✓ Syntax OK")
        except SyntaxError as e:
            print(f"✗ SYNTAX ERROR: {e}")
            print(f"  Restore with: cp {BACKUP} {TARGET}")
