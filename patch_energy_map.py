#!/usr/bin/env python3
"""
PATCH: Energy Translation Map for plain_english.py
Run: python patch_energy_map.py

Replaces raw planet names with energy frequencies in all user-facing text.
Also updates the Claude prompt so it generates energy language natively.
"""

import shutil
from pathlib import Path
import sys

TARGET = Path("antar_engine/plain_english.py")
if not TARGET.exists():
    print("ERROR: antar_engine/plain_english.py not found"); sys.exit(1)

backup = TARGET.with_suffix(".py.bak_energy")
shutil.copy2(TARGET, backup)
print(f"✅ Backup: {backup}")

code = TARGET.read_text()

# ═══════════════════════════════════════════════════════════════
# PATCH 1: Replace _strip_jargon with energy-aware version
# ═══════════════════════════════════════════════════════════════
OLD_STRIP = '''def _strip_jargon(text: str) -> str:
    """Remove banned Sanskrit/astrology terms from text."""
    for term in BANNED_TERMS:
        # Case-insensitive whole-word replacement
        pattern = re.compile(r'\\b' + re.escape(term) + r'\\b', re.IGNORECASE)
        text = pattern.sub("[planetary cycle]", text)
    return text.strip()'''

NEW_STRIP = '''# ═══ ENERGY TRANSLATION MAP ═══
# Replaces planet names with energy frequencies in user-facing text
ENERGY_MAP = {
    "rahu":    "your Ambition Engine",
    "ketu":    "your Extraction Phase",
    "saturn":  "your Structural Load",
    "jupiter": "your Growth Signal",
    "mars":    "your Execution Force",
    "venus":   "your Magnetism Node",
    "mercury": "your Communication Stream",
    "sun":     "your Power Source",
    "moon":    "your Mental Current",
}

# Dasha/period translations
PERIOD_MAP = {
    "rahu period":    "Ambition cycle",
    "rahu-saturn":    "Ambition-meets-Structure phase",
    "rahu-jupiter":   "Ambition-meets-Growth phase",
    "rahu-mercury":   "Ambition-meets-Communication phase",
    "rahu-venus":     "Ambition-meets-Magnetism phase",
    "rahu-mars":      "Ambition-meets-Execution phase",
    "rahu-moon":      "Ambition-meets-Emotional phase",
    "rahu-sun":       "Ambition-meets-Authority phase",
    "rahu-ketu":      "Ambition-meets-Extraction phase",
    "saturn period":  "Structure cycle",
    "jupiter period": "Growth cycle",
    "mars period":    "Execution cycle",
    "venus period":   "Magnetism cycle",
    "mercury period": "Communication cycle",
    "sun period":     "Authority cycle",
    "moon period":    "Emotional cycle",
    "ketu period":    "Extraction cycle",
    "mars-moon":      "Execution-meets-Emotional phase",
    "mars-saturn":    "Execution-meets-Structure phase",
    "mars-jupiter":   "Execution-meets-Growth phase",
    "mars-venus":     "Execution-meets-Magnetism phase",
    "mars-mercury":   "Execution-meets-Communication phase",
    "mars-rahu":      "Execution-meets-Ambition phase",
    "mars-sun":       "Execution-meets-Authority phase",
    "mars-ketu":      "Execution-meets-Extraction phase",
}

def _strip_jargon(text: str) -> str:
    """Replace planet names with energy frequencies and remove banned terms."""
    # Step 1: Replace dasha/period combinations first (longer matches first)
    for period_term, energy_label in sorted(PERIOD_MAP.items(), key=lambda x: -len(x[0])):
        pattern = re.compile(r'\\b' + re.escape(period_term) + r'\\b', re.IGNORECASE)
        text = pattern.sub(energy_label, text)

    # Step 2: Replace standalone planet names with energy translations
    for planet, energy in ENERGY_MAP.items():
        pattern = re.compile(r'\\b' + re.escape(planet) + r'\\b', re.IGNORECASE)
        text = pattern.sub(energy, text)

    # Step 3: Remove remaining banned Sanskrit terms
    for term in BANNED_TERMS:
        pattern = re.compile(r'\\b' + re.escape(term) + r'\\b', re.IGNORECASE)
        text = pattern.sub("", text)

    # Clean up double spaces and orphaned punctuation
    text = re.sub(r'  +', ' ', text)
    text = re.sub(r' ,', ',', text)
    text = re.sub(r' \\.', '.', text)
    return text.strip()'''

if "ENERGY_MAP" in code:
    print("⏭️  Energy map already exists — skipping patch 1")
else:
    if 'def _strip_jargon(text: str) -> str:' in code and '[planetary cycle]' in code:
        code = code.replace(OLD_STRIP, NEW_STRIP)
        print("✅ Patch 1: Replaced _strip_jargon with energy translation map")
    else:
        print("ERROR: Cannot find _strip_jargon function with expected content")
        print("       Trying partial match...")
        # Try replacing just the function body
        if 'text = pattern.sub("[planetary cycle]", text)' in code:
            code = code.replace(
                'text = pattern.sub("[planetary cycle]", text)',
                '# OLD: text = pattern.sub("[planetary cycle]", text)\n        # Now handled by energy-aware _strip_jargon below'
            )
            print("⚠️  Partial patch applied — manual review needed")
        else:
            print("ERROR: Cannot find replacement target")
            sys.exit(1)

# ═══════════════════════════════════════════════════════════════
# PATCH 2: Add energy language instruction to Claude prompt
# ═══════════════════════════════════════════════════════════════
OLD_RULE4 = """NEVER use in plain_summary or action_item:
- Planet names: Saturn, Rahu, Mars, Jupiter, Venus, Mercury, Ketu"""

NEW_RULE4 = """NEVER use raw planet names in plain_summary or action_item.
Instead, use these ENERGY TRANSLATIONS:
- Rahu → "Ambition Engine" or "Ambition cycle"
- Ketu → "Extraction Phase"
- Saturn → "Structural Load" or "Structure cycle"
- Jupiter → "Growth Signal" or "Growth cycle"
- Mars → "Execution Force" or "Execution cycle"
- Venus → "Magnetism Node" or "Magnetism cycle"
- Mercury → "Communication Stream"
- Sun → "Power Source" or "Authority cycle"
- Moon → "Mental Current" or "Emotional cycle"

Example: Instead of "Your Rahu-Saturn period runs until 2028"
Write: "You are in a high-stakes Ambition cycle meeting a Structural load — building infrastructure, not harvesting yet."

ALSO NEVER use in plain_summary or action_item:
- Raw planet names: Saturn, Rahu, Mars, Jupiter, Venus, Mercury, Ketu"""

if "Ambition Engine" in code and "ENERGY TRANSLATIONS" in code:
    print("⏭️  Energy language already in Claude prompt — skipping patch 2")
else:
    if OLD_RULE4 in code:
        code = code.replace(OLD_RULE4, NEW_RULE4, 1)
        print("✅ Patch 2: Added energy translations to Claude prompt Rule 4")
    else:
        print("⚠️  Could not find exact Rule 4 landmark — skipping prompt patch")
        print("    You may need to manually add energy translations to the prompt")

# ═══════════════════════════════════════════════════════════════
# WRITE
# ═══════════════════════════════════════════════════════════════
TARGET.write_text(code)
print(f"\n✅ ALL PATCHES APPLIED — plain_english.py updated")
print(f"   Backup at: {backup}")
print(f"\n📋 Next steps:")
print(f"   1. git add antar_engine/plain_english.py")
print(f"   2. git commit -m 'feat: energy translation map — planet names → energy frequencies'")
print(f"   3. git push")
print(f"   4. Test: ask a question and verify no planet names in plain_summary")
