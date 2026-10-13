"""
Mandook (frog) dasha per K.N. Rao, "Predicting through Karakamsha and Jaimini's Mandook Dasha"
(Jaimini Sutra 2.4.15; arithmetic is Rao's own research, validated on his printed Table I and
about 40 dated sub-periods; see RULES_LEDGER_kn_rao_karakamsha_mandook_2026-10-13.md).

Deliberately independent of the Chara dasha constants: Mandook has its own odd/even rules.
  - Applies only if >= 4 of Sun..Saturn are in kendra signs (1/4/7/10) from the lagna sign.
  - Odd lagna: first period = lagna sign, direct. Even lagna: first period = 7th sign, indirect.
  - Sequence: 3 groups of 4 signs, each leap is 3 signs: (s0 + d*g + d*3*k) % 12.
  - Duration: count from the sign to its lord's sign (starting sign = 1), forward for odd signs,
    backward for even signs; count 1 -> 12, count 7 -> 10. Scorpio uses Mars only, Aquarius Saturn only.
  - Starts at birth (no balance); cycles repeat. Each period of N years has 12 sub-periods of N months,
    in the same frog-jump order started from the major sign, in the CHART's direction.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from dateutil.relativedelta import relativedelta

ODD_SIGNS = {0, 2, 4, 6, 8, 10}                       # Ar Ge Le Li Sg Aq
_SIGN_LORD = {0: "Mars", 1: "Venus", 2: "Mercury", 3: "Moon", 4: "Sun", 5: "Mercury",
              6: "Venus", 7: "Mars", 8: "Jupiter", 9: "Saturn", 10: "Saturn", 11: "Jupiter"}
_SEVEN = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")
_KENDRA_OFFSETS = (0, 3, 6, 9)


@dataclass
class MandookSub:
    sign: int
    start: datetime
    end: datetime


@dataclass
class MandookPeriod:
    sign: int
    years: int
    start: datetime
    end: datetime
    cycle: int
    subs: List[MandookSub] = field(default_factory=list)


def mandook_applicable(lagna_sign: int, planet_signs: Dict[str, int], include_nodes: bool = False) -> bool:
    """At least four of Sun..Saturn (plus nodes only if asked) in kendra signs from the lagna sign."""
    kendras = {(lagna_sign + o) % 12 for o in _KENDRA_OFFSETS}
    names = list(_SEVEN) + (["Rahu", "Ketu"] if include_nodes else [])
    return sum(1 for n in names if planet_signs.get(n) in kendras) >= 4


def _direction(lagna_sign: int) -> int:
    return 1 if lagna_sign in ODD_SIGNS else -1


def _frog_order(start: int, d: int) -> List[int]:
    return [(start + d * g + d * 3 * k) % 12 for g in range(3) for k in range(4)]


def mandook_sign_order(lagna_sign: int) -> List[int]:
    start = lagna_sign if lagna_sign in ODD_SIGNS else (lagna_sign + 6) % 12
    return _frog_order(start, _direction(lagna_sign))


def mandook_duration(sign: int, planet_signs: Dict[str, int]) -> int:
    lord = _SIGN_LORD[sign]                              # Scorpio -> Mars, Aquarius -> Saturn (nodes ignored)
    lord_sign = planet_signs[lord]
    if sign in ODD_SIGNS:
        count = (lord_sign - sign) % 12 + 1
    else:
        count = (sign - lord_sign) % 12 + 1
    if count == 1:
        return 12
    if count == 7:
        return 10
    return count


def compute_mandook_dasha(lagna_sign: int, planet_signs: Dict[str, int], birth: datetime,
                          num_cycles: int = 3, require_gate: bool = True) -> Optional[List[MandookPeriod]]:
    """None if the chart is not a Mandook chart (and the gate is required)."""
    if require_gate and not mandook_applicable(lagna_sign, planet_signs):
        return None
    d = _direction(lagna_sign)
    order = mandook_sign_order(lagna_sign)
    periods: List[MandookPeriod] = []
    cur = birth
    for cycle in range(1, num_cycles + 1):
        for sign in order:
            n = mandook_duration(sign, planet_signs)
            end = cur + relativedelta(years=n)
            subs = []
            for k, ssign in enumerate(_frog_order(sign, d)):
                subs.append(MandookSub(ssign, cur + relativedelta(months=k * n),
                                       cur + relativedelta(months=(k + 1) * n)))
            periods.append(MandookPeriod(sign, n, cur, end, cycle, subs))
            cur = end
    return periods


def mandook_current(periods: List[MandookPeriod], when: datetime):
    for p in periods:
        if p.start <= when < p.end:
            for s in p.subs:
                if s.start <= when < s.end:
                    return p, s
            return p, None
    return None, None
