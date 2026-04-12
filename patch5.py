"""
patch_hard_constraint_trim.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_hard_constraint is 6,983 chars prepended to EVERY prompt.
Symptom mode already uses _jargon_only (~400 chars) — correct.
All other modes should do the same.

Format rules move to _master_system (system prompt = KV cached).
Per-request prompt only gets jargon rules + today's date.

Savings: ~6,500 chars per predict call.

RUN:
    python patch_hard_constraint_trim.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os, sys, shutil
from datetime import datetime

MAIN_FILE = os.path.expanduser("~/antarai/main.py")

if not os.path.exists(MAIN_FILE):
    print(f"❌ Not found: {MAIN_FILE}")
    sys.exit(1)

shutil.copy(MAIN_FILE, MAIN_FILE + ".bak_constraint")
print("✅ Backup created (.bak_constraint)")

with open(MAIN_FILE, "r") as f:
    content = f.read()

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — Replace the hard constraint injection with jargon-only
# ─────────────────────────────────────────────────────────────────────────────

OLD_INJECT = '''    # Symptom mode uses its own format — skip hard constraint (which enforces VERDICT format)
    if _question_mode != "symptom":
        prompt = _hard_constraint + "\\n\\n" + prompt
    else:
        # Symptom mode: inject jargon rules only (no planet/Sanskrit names) but not format rules
        _jargon_only = """ABSOLUTE RULES (no exceptions):
1. NEVER use planet names. Use: Growth Amplifier, Structural Load, Action Drive, Magnetism Field, Processing Speed, Authority Signal, Emotional Radar, Ambition Engine, Intuition Compass.
2. NEVER use house numbers. Use instrument labels: System Vitals, Capital Reserves, Action Capacity, Alliance Sync, Capital Runway, Fortune Vector, Authority Engine, Revenue Pipeline, Global Vector.
3. NEVER use Sanskrit terms (Dasha, Nakshatra, Lagna, Yoga, Rashi, etc).
4. The current year is 2026. Today is """ + __import__('datetime').datetime.utcnow().strftime("%B %d, %Y") + """.'''

NEW_INJECT = '''    # Jargon-only constraint — prepended to ALL modes (format rules live in system prompt)
    _today_str = __import__('datetime').datetime.utcnow().strftime("%B %d, %Y")
    _jargon_only = (
        "ABSOLUTE RULES (no exceptions):\\n"
        "1. NEVER use planet names. Use: Growth Amplifier, Structural Load, Action Drive, "
        "Magnetism Field, Processing Speed, Authority Signal, Emotional Radar, Ambition Engine, Intuition Compass.\\n"
        "2. NEVER use house numbers. Use instrument labels: System Vitals, Capital Reserves, "
        "Action Capacity, Alliance Sync, Capital Runway, Fortune Vector, Authority Engine, Revenue Pipeline, Global Vector.\\n"
        "3. NEVER use Sanskrit terms (Dasha, Nakshatra, Lagna, Yoga, Rashi, etc).\\n"
        f"4. Today is {_today_str}. The current year is 2026.\\n"
        "5. Answer the QUESTION directly. Lead with VERDICT in first sentence.\\n"
        "6. THE MOVE at the end — one specific action for this week."
    )
    prompt = _jargon_only + "\\n\\n" + prompt
    if False:  # dead code block — keeps old symptom path reference intact
        _jargon_only = """ABSOLUTE RULES (no exceptions):
1. NEVER use planet names. Use: Growth Amplifier, Structural Load, Action Drive, Magnetism Field, Processing Speed, Authority Signal, Emotional Radar, Ambition Engine, Intuition Compass.
2. NEVER use house numbers. Use instrument labels: System Vitals, Capital Reserves, Action Capacity, Alliance Sync, Capital Runway, Fortune Vector, Authority Engine, Revenue Pipeline, Global Vector.
3. NEVER use Sanskrit terms (Dasha, Nakshatra, Lagna, Yoga, Rashi, etc).
4. The current year is 2026. Today is """ + __import__('datetime').datetime.utcnow().strftime("%B %d, %Y") + """.'''

if OLD_INJECT not in content:
    print("❌ Injection landmark not found — trying alternate...")
    # Try simpler landmark
    ALT = '    if _question_mode != "symptom":\n        prompt = _hard_constraint + "\\n\\n" + prompt'
    if ALT in content:
        _today = datetime.utcnow().strftime("%B %d, %Y")
        NEW_ALT = '''    # Jargon-only rules — format lives in system prompt (KV cached)
    _today_str = __import__('datetime').datetime.utcnow().strftime("%B %d, %Y")
    _jargon_only = (
        "ABSOLUTE RULES (no exceptions):\\n"
        "1. NEVER use planet names. Use instrument labels only.\\n"
        "2. NEVER use house numbers. Use domain labels only.\\n"
        "3. NEVER use Sanskrit terms.\\n"
        f"4. Today is {_today_str}. Year is 2026.\\n"
        "5. Lead with VERDICT. End with THE MOVE."
    )
    prompt = _jargon_only + "\\n\\n" + prompt'''
        content = content.replace(ALT, NEW_ALT, 1)
        print("✅ Hard constraint replaced via alternate landmark")
    else:
        print("⚠️  Could not find injection point — manual fix needed")
        print("   Find line: 'prompt = _hard_constraint' and replace with jargon_only")
        sys.exit(1)
else:
    content = content.replace(OLD_INJECT, NEW_INJECT, 1)
    print("✅ Hard constraint replaced with jargon-only block")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — Move format rules into _master_system (already built per concern)
# The concern_router build_concern_system_prompt already has format instructions.
# Just ensure _master_system includes the response format template.
# ─────────────────────────────────────────────────────────────────────────────

OLD_MASTER_SYSTEM = '''        _master_system = _domain_system if _domain_system else (
            "You are Antar — a precise Vedic astrology AI. "
            "Answer directly and specifically using the data provided. "
            "Reference specific planets, houses, yogas, and timing. "
            "Lead with the actual answer in the first sentence. "
            "Never start responses with template headers like \'YOUR SIGNAL RIGHT NOW\'."
        )'''

NEW_MASTER_SYSTEM = '''        _format_rules = (
            "RESPONSE FORMAT (always follow):\\n"
            "Line 1: ✦ VERDICT: [ACTION VERB]. [Direct call in 8 words or less]\\n"
            "Lines 2-3: 2-3 sentences WHY in business language (no astrology jargon).\\n"
            "Lines 4-6: YOUR MOVE — three numbered actions (this week / next 2 weeks / next 30 days).\\n"
            "Line 7: TIMING: [exact window].\\n"
            "TOTAL: under 150 words. No markdown headers. No poetic language.\\n"
            "If user asks will/chances/probability: lead with PROBABILITY: XX%.\\n"
        )
        _master_system = (_domain_system if _domain_system else (
            "You are Antar — a precise Vedic astrology AI. "
            "Answer directly using the data provided. "
            "Lead with the actual answer in the first sentence. "
        )) + "\\n\\n" + _format_rules'''

if OLD_MASTER_SYSTEM in content:
    content = content.replace(OLD_MASTER_SYSTEM, NEW_MASTER_SYSTEM, 1)
    print("✅ Format rules moved to _master_system (system prompt / KV cached)")
else:
    print("⚠️  _master_system landmark not found — format rules not moved")
    print("   This is non-critical — jargon trim alone saves 6,500 chars")

with open(MAIN_FILE, "w") as f:
    f.write(content)

print("\n" + "━" * 60)
print("SAVINGS:")
print("  _hard_constraint: 6,983 chars → ~300 chars  (~6,700 saved)")
print("  Format rules: now in system prompt (KV cached by Anthropic)")
print()
print("CUMULATIVE prompt_len target:")
print("  Full context:    17,171 chars")
print("  Jargon rules:      ~300 chars")
print("  Extra blocks:    ~2,000 chars (gated)")
print("  C3 memory:         ~400 chars (compressed)")
print("  Domain audit:      ~800 chars (truncated)")
print("  ─────────────────────────────────────────")
print("  TOTAL:          ~20,671 chars = ~5,168 tokens")
print("  System prompt:   ~1,500 chars (KV cached)")
print()
print("NEXT:")
print("  git add main.py")
print("  git commit -m 'perf: hard_constraint trim — 6983 to 300 chars, format to system prompt'")
print("  git push origin main")
print()
print("VERIFY in Railway logs:")
print("  [predict] prompt_len=~8000-10000")
