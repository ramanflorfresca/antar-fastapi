#!/usr/bin/env python3
"""
apply_sprint_d_patch.py — Sprint D: Domain Intelligence Engine
Run from repo root: python apply_sprint_d_patch.py

Changes:
  1. Wire domain system prompt as system_override in /predict LLM call
  2. Add missing domain configs to concern_router.py
  3. Make DKP domain-aware
"""

import shutil
import sys
from pathlib import Path

MAIN   = Path("main.py")
ROUTER = Path("antar_engine/concern_router.py")

if not MAIN.exists():
    print("❌  main.py not found — run from repo root")
    sys.exit(1)

shutil.copy(MAIN,   "main.py.bak_d")
shutil.copy(ROUTER, "antar_engine/concern_router.py.bak_d")
print("✅  Backed up main.py and concern_router.py")

# ─────────────────────────────────────────────────────────────────────────────
# CHANGE 1 — Wire domain system prompt as system_override
# Find the _using_master / _master_system block and add domain system prompt
# ─────────────────────────────────────────────────────────────────────────────

src = MAIN.read_text()

OLD = """        _master_system = (
            "You are Antar — a precise Vedic astrology AI. "
            "Answer directly and specifically using the data provided. "
            "Reference specific planets, houses, yogas, and timing. "
            "Lead with the actual answer in the first sentence. "
            "Never start responses with template headers like 'YOUR SIGNAL RIGHT NOW'."
        )
        prediction_text, tokens_used = await call_llm_claude(
            prompt,
            history=request.conversation_history or [],
            system_override=_master_system,
        )"""

NEW = """        # Sprint D: Use domain-specific system prompt as system_override
        try:
            from antar_engine.concern_router import build_concern_system_prompt
            _domain_system = build_concern_system_prompt(concern)
        except Exception:
            _domain_system = ""

        _master_system = _domain_system if _domain_system else (
            "You are Antar — a precise Vedic astrology AI. "
            "Answer directly and specifically using the data provided. "
            "Reference specific planets, houses, yogas, and timing. "
            "Lead with the actual answer in the first sentence. "
            "Never start responses with template headers like 'YOUR SIGNAL RIGHT NOW'."
        )
        prediction_text, tokens_used = await call_llm_claude(
            prompt,
            history=request.conversation_history or [],
            system_override=_master_system,
        )"""

if "Sprint D: Use domain-specific system prompt" in src:
    print("⚠️   Change 1 already applied — skipping")
elif OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("✅  Change 1 applied — domain system prompt wired as system_override")
else:
    print("❌  Change 1 FAILED — _master_system block not found")
    print("    Manually add: system_override=build_concern_system_prompt(concern)")

# Also wire for the non-master path
OLD2 = """        prediction_text, tokens_used = await call_llm_claude(
            prompt,
            history=request.conversation_history or [],
        )"""

NEW2 = """        # Sprint D: domain system prompt for non-master path too
        try:
            from antar_engine.concern_router import build_concern_system_prompt
            _domain_system_fallback = build_concern_system_prompt(concern)
        except Exception:
            _domain_system_fallback = ""
        prediction_text, tokens_used = await call_llm_claude(
            prompt,
            history=request.conversation_history or [],
            system_override=_domain_system_fallback or "",
        )"""

if "domain system prompt for non-master path" in src:
    print("⚠️   Change 1b already applied — skipping")
elif OLD2 in src:
    src = src.replace(OLD2, NEW2, 1)
    print("✅  Change 1b applied — domain system prompt for fallback path")
else:
    print("⚠️   Change 1b — fallback path not found (may not be needed)")

MAIN.write_text(src)

# ─────────────────────────────────────────────────────────────────────────────
# CHANGE 2 — Add missing domain configs to concern_router.py
# ─────────────────────────────────────────────────────────────────────────────

router_src = ROUTER.read_text()

MISSING_CONFIGS = '''
    "children": {
        "display_name": "Children & Fertility",
        "priority_data": [
            "5th house condition and lord (children house)",
            "D7 Saptamsa — children chart",
            "Jupiter position (children karaka for both genders)",
            "Moon condition (motherhood karaka)",
            "Putrakaraka planet and position",
            "Current dasha lord's children signification",
            "D60 karma for children (past life pattern)",
            "Age window feasibility",
        ],
        "system_instruction": """CHILDREN FOCUS MODE — prioritize fertility and children data.
1. D7 Saptamsa — the children chart. What does it show?
2. 5th house condition — how strong is the children house?
3. Jupiter — the primary children karaka. Where is it and what does it promise?
4. Putrakaraka — which planet holds the children karma for this person?
5. Current dasha — is this a children-activation period?
6. D60 karma — any past-life patterns around children?
7. Timing — when is the strongest window for children?
8. ONE remedy for 5th house and Jupiter activation

Be sensitive. Frame biological age realities gently but honestly.
If window is limited: reframe as legacy, adoption, mentoring, creativity.
MUST mention: D7 reading, timing window, Jupiter strength""",
        "required_elements": [
            "D7 reading",
            "5th house strength",
            "timing window",
            "Jupiter karma",
        ],
        "answer_format": """
**Your Children Blueprint**
[5th house + D7 reading]

**Timing Window**
[When the chart supports children most strongly]

**What Jupiter Says**
[Jupiter as children karaka — strength and promise]

**What Helps**
[One remedy + one practice for children activation]""",
    },

    "property": {
        "display_name": "Property & Real Estate",
        "priority_data": [
            "4th house (home and property)",
            "4th lord position and strength",
            "Mars position (property karaka)",
            "Saturn position (land and permanent assets)",
            "Moon sign (movable vs fixed — affects property timing)",
            "D4 Chaturthamsa — property and fixed assets chart",
            "Current dasha lord's property signification",
            "Lal Kitab annual chart for property this year",
        ],
        "system_instruction": """PROPERTY FOCUS MODE — prioritize real estate and property data.
1. 4th house — the house of home and property. What is its condition?
2. Mars as property karaka — where is Mars and what does it promise?
3. D4 Chaturthamsa — the property chart. What does it show?
4. 4th lord position — where is property energy going?
5. Current dasha lord's relationship to 4th house
6. Is this a buying, selling, or holding period?
7. Timing — when is the strongest window for property transactions?
8. ONE Lal Kitab remedy for property matters

Be specific about timing and transaction type.
Ground in DKP real estate market conditions.
MUST mention: D4 reading, Mars position, timing, buy/sell/hold verdict""",
        "required_elements": [
            "D4 reading",
            "Mars karaka strength",
            "buy/sell/hold verdict",
            "timing window",
        ],
        "answer_format": """
**Your Property Blueprint**
[4th house + D4 reading]

**Buy, Sell, or Hold?**
[Direct verdict from chart + market conditions]

**Best Timing**
[When property transactions are most favored]

**What to Do**
[One specific action + Lal Kitab remedy]""",
    },

    "funding": {
        "display_name": "Funding & Investment",
        "priority_data": [
            "11th house (gains and group money)",
            "11th lord position and strength",
            "Jupiter position (expansion and investors)",
            "Rahu in wealth houses (unconventional funding)",
            "12th house (foreign investment)",
            "D2 Hora chart for wealth type",
            "Current dasha lord's gains signification",
            "DKP venture capital and funding climate",
        ],
        "system_instruction": """FUNDING FOCUS MODE — prioritize investment and fundraising data.
1. 11th house — the house of gains and group money. What is its condition?
2. Jupiter — the primary investor karaka. Is it supporting gains now?
3. Rahu in wealth houses — any unconventional funding channels?
4. 12th house — foreign investor signals?
5. Current dasha lord's relationship to 11th house
6. DKP funding climate — is the market environment supporting raises?
7. Funding type verdict — VC / angel / grants / loans / bootstrapping?
8. Timing — when is the strongest fundraising window?
9. ONE specific action and remedy

If previous funding attempts failed: diagnose the blockage specifically.
Name the planet causing delay and when it clears.
MUST mention: 11th house strength, funding type, timing window, blockage if any""",
        "required_elements": [
            "11th house reading",
            "funding type recommendation",
            "timing window",
            "blockage diagnosis if relevant",
        ],
        "answer_format": """
**Your Funding Blueprint**
[11th house + Jupiter reading]

**Best Funding Type**
[VC / Angel / Grants / Bootstrap — direct recommendation]

**What's Blocking It** (if relevant)
[Specific planet causing delay + when it clears]

**Your Window**
[Timing for strongest fundraising period]

**Do This Now**
[One specific action + remedy]""",
    },

    "education": {
        "display_name": "Education & Exams",
        "priority_data": [
            "4th house (formal education)",
            "9th house (higher education and wisdom)",
            "D24 Chaturvimshamsa — education and learning chart",
            "Mercury position (intellect and communication)",
            "Jupiter position (wisdom and higher learning)",
            "5th house (intelligence and creativity)",
            "Current dasha lord's education signification",
            "Exam timing from Mercury transits",
        ],
        "system_instruction": """EDUCATION FOCUS MODE — prioritize learning and academic data.
1. D24 Chaturvimshamsa — the education chart. What field is supported?
2. Mercury — intelligence karaka. What is its strength?
3. 4th and 9th houses — what level of education is supported?
4. Jupiter — wisdom and higher learning. What does it promise?
5. Current dasha lord's relationship to education houses
6. Field of study verdict — what subjects does this chart naturally support?
7. Exam timing — when is Mercury strongest for competitive exams?
8. ONE remedy for Mercury and Jupiter activation

Be specific about field of study and exam timing.
MUST mention: D24 reading, Mercury strength, field verdict, exam timing""",
        "required_elements": [
            "D24 reading",
            "Mercury strength",
            "field of study indication",
            "exam timing",
        ],
        "answer_format": """
**Your Learning Blueprint**
[D24 + Mercury reading]

**Your Natural Field**
[What subjects and careers the chart supports]

**Exam Timing**
[When Mercury is strongest for competitive exams]

**What Helps**
[One study practice + Mercury remedy]""",
    },

    "travel": {
        "display_name": "Travel",
        "priority_data": [
            "3rd house (short travel)",
            "9th house (long travel and fortune abroad)",
            "12th house (foreign lands)",
            "Moon sign (movable signs support travel)",
            "Rahu position (foreign connections)",
            "Current dasha lord's travel signification",
            "DKP travel advisories and visa conditions",
        ],
        "system_instruction": """TRAVEL FOCUS MODE — prioritize travel and movement data.
1. 3rd vs 9th vs 12th house — short trip, long journey, or foreign stay?
2. Moon sign — movable sign Moon supports frequent travel
3. Rahu — foreign and unconventional travel connections
4. Current dasha — is this a travel-activation period?
5. Direction of travel (based on planet and sign combinations)
6. DKP — current travel conditions for their country
7. Timing — best period for travel in next 6 months
8. ONE travel remedy or precaution

Distinguish between short trips, long journeys, and foreign stays.
Be specific about direction and timing.
MUST mention: travel type, direction, timing, DKP travel conditions""",
        "required_elements": [
            "travel type (short/long/foreign)",
            "direction indicator",
            "timing window",
            "DKP travel conditions",
        ],
        "answer_format": """
**Travel Type**
[Short trip / long journey / foreign stay — what the chart shows]

**Direction**
[Which direction is favored based on planets]

**Best Timing**
[When to travel in next 6 months]

**What to Know**
[One precaution or remedy for safe travel]""",
    },

    "mental_health": {
        "display_name": "Mental Health & Wellbeing",
        "priority_data": [
            "Moon condition and sign (emotional foundation)",
            "Mercury position (mental clarity and anxiety)",
            "4th house (peace of mind and home environment)",
            "12th house (isolation and mental retreat)",
            "Saturn afflictions to Moon (depression patterns)",
            "Rahu afflictions to Moon (anxiety patterns)",
            "Current dasha lord's mental health theme",
            "D30 active mental stress indicators",
        ],
        "system_instruction": """MENTAL HEALTH FOCUS MODE — prioritize emotional and mental wellbeing data.
1. Moon condition — the primary mental health indicator. What is its strength?
2. Mercury — anxiety, mental chatter, clarity. What does it show?
3. Saturn-Moon relationship — chronic emotional patterns
4. Rahu-Moon relationship — anxiety and restlessness patterns
5. 4th house — home and inner peace. Is it supported?
6. Current dasha mental health theme — what emotional patterns are active now?
7. D30 — any active mental stress indicators?
8. TWO specific practices — one for Moon, one for the challenging planet

Be deeply empathetic. Frame everything as patterns, not defects.
Never diagnose. Always recommend professional support alongside cosmic remedies.
Frame challenges as "the soul working through X pattern."
Connect cosmic timing to real emotional experience.
MUST mention: Moon strength, current emotional theme, two practices, professional support note""",
        "required_elements": [
            "Moon condition",
            "current emotional theme",
            "two specific practices",
            "professional support note",
        ],
        "answer_format": """
**Your Emotional Blueprint**
[Moon condition + 4th house reading]

**What You're Moving Through Now**
[Current dasha mental health theme — normalise the experience]

**The Pattern**
[Saturn or Rahu Moon relationship — frame as growth pattern]

**What Helps**
[Two practices — one physical, one spiritual]

**Important Note**
[Encourage professional support — cosmic wisdom + human support work together]""",
    },

    "luck": {
        "display_name": "Luck & Speculation",
        "priority_data": [
            "5th house (speculation and luck)",
            "9th house (fortune and dharmic luck)",
            "Jupiter position (natural luck amplifier)",
            "Rahu in luck houses (unconventional gains)",
            "D10 for timing of fortunate events",
            "Current dasha lord's luck signification",
            "WOW effects for luck amplification",
        ],
        "system_instruction": """LUCK FOCUS MODE — prioritize fortune and speculation data.
1. 5th house — speculation, gambling, investments, creative luck
2. 9th house — dharmic fortune. Is luck earned or gifted?
3. Jupiter — the primary luck amplifier. Where is it pointing?
4. Rahu in luck houses — unconventional windfalls
5. WOW effects — any extraordinary fortune combinations?
6. Current dasha — is this a lucky period or a consolidation period?
7. Timing — when is luck maximally active?
8. What TYPE of luck — career luck, financial luck, relationship luck?

Be honest about speculation risk. Chart luck ≠ investment advice.
MUST mention: luck type, timing window, WOW effects if present""",
        "required_elements": [
            "luck type",
            "Jupiter reading",
            "timing window",
            "speculation caution if relevant",
        ],
        "answer_format": """
**Your Luck Blueprint**
[5th + 9th house reading]

**Type of Luck**
[What area luck flows most naturally]

**Right Now**
[Current dasha luck theme]

**Peak Window**
[When luck is maximally active]

**One Action**
[How to align with the lucky energy + one remedy]""",
    },
}
'''

ANCHOR = '    "general": {'

if "children" in router_src and '"display_name": "Children' in router_src:
    print("⚠️   Change 2 already applied — missing domains already added")
elif ANCHOR not in router_src:
    print("❌  Change 2 FAILED — general config anchor not found")
else:
    router_src = router_src.replace(ANCHOR, MISSING_CONFIGS + "\n    " + '"general": {', 1)
    print("✅  Change 2 applied — 7 missing domain configs added")

# ─────────────────────────────────────────────────────────────────────────────
# CHANGE 3 — Domain-aware DKP in desh_kal_patra.py
# ─────────────────────────────────────────────────────────────────────────────

DKP = Path("antar_engine/desh_kal_patra.py")
dkp_src = DKP.read_text()

DOMAIN_DKP_FUNCTION = '''

# ── Domain-aware DKP summary ──────────────────────────────────────────────────

def get_domain_dkp_note(
    concern: str,
    context_block: str,
    country_code: str,
) -> str:
    """
    Extract the most relevant part of the DKP context block for the given domain.
    Returns a focused one-paragraph note instead of the full block.
    """
    if not context_block:
        return ""

    lines      = context_block.split("\\n")
    lower_block = context_block.lower()

    if concern in ("career", "business", "funding"):
        relevant = [l for l in lines if any(
            w in l.lower() for w in [
                "growing", "contracting", "sector", "employment",
                "expansion", "contraction", "gdp", "job"
            ]
        )]
        if relevant:
            return f"MARKET CONTEXT ({country_code}): " + " ".join(relevant[:3])

    if concern == "wealth":
        relevant = [l for l in lines if any(
            w in l.lower() for w in [
                "inflation", "gdp", "economic climate", "expansion",
                "contraction", "currency", "stable"
            ]
        )]
        if relevant:
            return f"ECONOMIC CONTEXT ({country_code}): " + " ".join(relevant[:3])

    if concern in ("foreign", "travel"):
        relevant = [l for l in lines if any(
            w in l.lower() for w in ["emigration", "immigration", "visa", "currency"]
        )]
        if relevant:
            return f"MIGRATION CONTEXT ({country_code}): " + " ".join(relevant[:3])

    if concern == "legal":
        relevant = [l for l in lines if any(
            w in l.lower() for w in ["legal", "stability", "geopolitical", "currency"]
        )]
        if relevant:
            return f"LEGAL ENVIRONMENT ({country_code}): " + " ".join(relevant[:2])

    if concern == "property":
        relevant = [l for l in lines if any(
            w in l.lower() for w in [
                "property", "real estate", "expansion", "contraction",
                "inflation", "gdp"
            ]
        )]
        if relevant:
            return f"PROPERTY MARKET ({country_code}): " + " ".join(relevant[:2])

    # Default — return the economic climate line only
    for line in lines:
        if "economic climate" in line.lower():
            return f"ECONOMIC CONTEXT ({country_code}): {line.strip()}"

    return ""
'''

if "get_domain_dkp_note" in dkp_src:
    print("⚠️   Change 3 already applied — domain DKP function exists")
else:
    dkp_src += DOMAIN_DKP_FUNCTION
    DKP.write_text(dkp_src)
    print("✅  Change 3 applied — domain-aware DKP function added")

# Wire domain DKP into main.py — replace full dkp_context with domain-focused note
src = MAIN.read_text()
OLD3 = '        if _cs_block:\n            print(f"[predict] C4 common sense — {len(_cs_block)} chars")'
NEW3 = '''        if _cs_block:
            print(f"[predict] C4 common sense — {len(_cs_block)} chars")

    # Sprint D: Replace full DKP block with domain-focused note in prompt
    try:
        from antar_engine.desh_kal_patra import get_domain_dkp_note
        _domain_dkp = get_domain_dkp_note(concern, dkp_context, country_code or "")
        if _domain_dkp:
            dkp_block = (dkp_block or "") + f"\\n\\n{_domain_dkp}"
    except Exception as _ddkp_err:
        print(f"[predict] domain DKP note failed (non-fatal): {_ddkp_err}")'''

if "domain-focused note in prompt" in src:
    print("⚠️   Change 3b already applied — skipping")
elif OLD3 in src:
    src = src.replace(OLD3, NEW3, 1)
    print("✅  Change 3b applied — domain DKP note wired into predict")
else:
    print("⚠️   Change 3b anchor not found — domain DKP note not wired")

MAIN.write_text(src)
ROUTER.write_text(router_src)

print(f"\n✅  All changes applied")
print("    Next:")
print("    1. git add main.py antar_engine/concern_router.py antar_engine/desh_kal_patra.py")
print("    2. git commit -m 'feat(D): domain intelligence engine — system prompts + missing domains + domain DKP'")
print("    3. git push")
print("    4. python test_sprint_d.py")
