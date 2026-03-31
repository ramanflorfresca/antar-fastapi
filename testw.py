import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'antar_engine'))

from datetime import date
from age_utils import (
    calculate_current_age,
    get_floor_age,
    filter_umra_activations,
    filter_future_dasha_transitions,
)
from signal_age_guard import build_age_guard_block, apply_age_guard_to_daily

print("\n=== SPRINT W — AGE UTILS ===\n")

age = calculate_current_age("1974-11-26")
print(f"Age (1974-11-26):         {age}   {'✅' if age == 51 else '❌ expected 51'}")

floor = get_floor_age(51)
print(f"Floor age (51):           {floor}   {'✅' if floor == 46 else '❌ expected 46'}")

umra = filter_umra_activations(51, max_upcoming=2)
bad = [u for u in umra if u["activation_age"] < 49]
print(f"Umra activations (51yo):  {[u['activation_age'] for u in umra]}   {'✅' if not bad else '❌ should be >= 49'}")

transitions = [
    {"planet": "Moon", "end_date": "2020-01-01"},
    {"planet": "Mars", "end_date": "2027-06-15"},
]
filtered = filter_future_dasha_transitions(transitions)
print(f"Future dasha guard:       {[t['planet'] for t in filtered]}   {'✅' if len(filtered) == 1 and filtered[0]['planet'] == 'Mars' else '❌ expected [Mars]'}")

print("\n=== SPRINT W — AGE GUARD ===\n")

block = build_age_guard_block("1974-11-26")
print(f"Age guard age:            {block['current_age']}   {'✅' if block['current_age'] == 51 else '❌'}")
print(f"Age guard floor:          {block['floor_age']}   {'✅' if block['floor_age'] == 46 else '❌'}")

ctx, prompt = apply_age_guard_to_daily("EXISTING CONTEXT", "EXISTING PROMPT", "1974-11-26")
print(f"Age injected in context:  {'✅' if '51 years old' in ctx else '❌'}")
print(f"Floor in system prompt:   {'✅' if 'age 46' in prompt else '❌'}")

print("\n=== SPRINT W — AGE BRACKETS ===\n")

for birth, label, expected_age in [
    ("1998-01-15", "Person A (28)", 28),
    ("1983-07-22", "Person B (42)", 42),
    ("1968-03-10", "Person C (58)", 58),
    ("2003-05-01", "Edge case (23)", 23),
]:
    a = calculate_current_age(birth)
    f = get_floor_age(a)
    u = filter_umra_activations(a, max_upcoming=2)
    bad_u = [x for x in u if x["activation_age"] < a - 2]
    status = "✅" if not bad_u else f"❌ bad umra ages: {[x['activation_age'] for x in bad_u]}"
    print(f"{label:22} age={a}  floor={f}  umra={[x['activation_age'] for x in u]}  {status}")

print("\nDone.\n")
