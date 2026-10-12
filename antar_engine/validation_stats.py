"""
antar_engine/validation_stats.py

The few statistics the rule-validation studies need, with no scipy dependency: exact tests on a 2x2 table, an odds ratio with a
confidence interval, AUC with a permutation null, and a power / required-n simulation. Pure; deterministic given a seed.

Used by antar_research/validate_relationship_bands.py (and written so the next rule study can reuse it). The discipline is the one the
earlier studies (business timing, D-2 wealth, Hora) established: pre-register the hypothesis and the pass bar, run a label-swap null and a
placebo, report n and power, and remove a rule that does not beat chance.
"""
from __future__ import annotations

import math
import random
from typing import Sequence

# ── exact test on a 2x2 table [[a, b], [c, d]] ──────────────────────────────────
#                outcome=1  outcome=0
#   exposed          a          b
#   unexposed        c          d


def _log_choose(n: int, k: int) -> float:
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def _hyper_pmf(x: int, row1: int, col1: int, n: int) -> float:
    """P(a = x) under independence, margins fixed: hypergeometric."""
    return math.exp(_log_choose(col1, x) + _log_choose(n - col1, row1 - x) - _log_choose(n, row1))


def fisher_exact(a: int, b: int, c: int, d: int) -> dict:
    """One-sided (exposed has MORE outcomes) and two-sided exact p, plus the sample odds ratio (Haldane-corrected when a cell is 0)."""
    n = a + b + c + d
    row1, col1 = a + b, a + c
    lo, hi = max(0, row1 + col1 - n), min(row1, col1)
    pmf = {x: _hyper_pmf(x, row1, col1, n) for x in range(lo, hi + 1)}
    p_obs = pmf.get(a, 0.0)
    greater = sum(p for x, p in pmf.items() if x >= a)
    two = sum(p for p in pmf.values() if p <= p_obs * (1 + 1e-9))
    aa, bb, cc, dd = (a, b, c, d) if min(a, b, c, d) > 0 else (a + .5, b + .5, c + .5, d + .5)
    return {"p_greater": min(1.0, greater), "p_two_sided": min(1.0, two), "odds_ratio": (aa * dd) / (bb * cc), "n": n}


def odds_ratio_ci(a: int, b: int, c: int, d: int, z: float = 1.96) -> tuple:
    """Woolf interval with the Haldane correction (0.5 in every cell) - honest about being wide on small tables."""
    aa, bb, cc, dd = a + .5, b + .5, c + .5, d + .5
    lor = math.log((aa * dd) / (bb * cc))
    se = math.sqrt(1 / aa + 1 / bb + 1 / cc + 1 / dd)
    return math.exp(lor - z * se), math.exp(lor), math.exp(lor + z * se)


# ── AUC (does the score rank the outcome group above the rest?) + permutation null ──────
def _avg_ranks(values: Sequence[float]) -> list:
    """1-based ranks, ties share the average rank."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    k = 0
    while k < len(order):
        m = k
        while m + 1 < len(order) and values[order[m + 1]] == values[order[k]]:
            m += 1
        avg = (k + m) / 2 + 1
        for t in range(k, m + 1):
            ranks[order[t]] = avg
        k = m + 1
    return ranks


def auc(scores: Sequence[float], labels: Sequence[int]) -> float:
    """P(score of a random outcome=1 case > score of a random outcome=0 case); ties count half. 0.5 = no signal. Rank-sum, O(n log n)."""
    n_pos = sum(1 for y in labels if y)
    n_neg = len(labels) - n_pos
    if not n_pos or not n_neg:
        return float("nan")
    ranks = _avg_ranks(scores)
    rs = sum(r for r, y in zip(ranks, labels) if y)
    return (rs - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)


def permutation_p(scores: Sequence[float], labels: Sequence[int], n_perm: int = 5000, seed: int = 7) -> dict:
    """One-sided: how often does a random relabelling give an AUC at least this high. The label-swap null. Ranks are computed once."""
    n_pos = sum(1 for y in labels if y)
    n_neg = len(labels) - n_pos
    if not n_pos or not n_neg:
        return {"auc": float("nan"), "p": float("nan"), "n_perm": 0}
    ranks = _avg_ranks(scores)
    base = n_pos * (n_pos + 1) / 2
    obs_rs = sum(r for r, y in zip(ranks, labels) if y)
    obs = (obs_rs - base) / (n_pos * n_neg)
    rng = random.Random(seed)
    idx = list(range(len(ranks)))
    hits = 0
    for _ in range(n_perm):
        rs = sum(ranks[i] for i in rng.sample(idx, n_pos))
        if rs >= obs_rs - 1e-9:
            hits += 1
    return {"auc": obs, "p": (hits + 1) / (n_perm + 1), "n_perm": n_perm}


# ── power ───────────────────────────────────────────────────────────────────────
def _simulate_p(n: int, share_exposed: float, base_rate: float, odds_ratio: float, rng: random.Random) -> float:
    odds = base_rate / (1 - base_rate) * odds_ratio
    p_exposed = odds / (1 + odds)
    a = b = c = d = 0
    for _ in range(n):
        exp = rng.random() < share_exposed
        y = rng.random() < (p_exposed if exp else base_rate)
        if exp and y: a += 1
        elif exp: b += 1
        elif y: c += 1
        else: d += 1
    if a + b == 0 or c + d == 0:
        return 1.0
    return fisher_exact(a, b, c, d)["p_greater"]


def power(n: int, share_exposed: float, base_rate: float, odds_ratio: float, alpha: float = 0.05, sims: int = 400, seed: int = 11) -> float:
    """Chance a one-sided Fisher test at `alpha` detects a true `odds_ratio`, with n people, `share_exposed` of them exposed, outcome rate
    `base_rate` among the unexposed."""
    rng = random.Random(seed)
    return sum(_simulate_p(n, share_exposed, base_rate, odds_ratio, rng) < alpha for _ in range(sims)) / sims


def _phi(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _z(p: float) -> float:
    """Inverse normal CDF (Acklam-style refinement by bisection; plenty for alpha / power)."""
    lo, hi = -8.0, 8.0
    for _ in range(80):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if _phi(mid) < p else (lo, mid)
    return (lo + hi) / 2


def power_approx(n: int, share_exposed: float, base_rate: float, odds_ratio: float, alpha: float = 0.05) -> float:
    """Normal approximation of the one-sided two-proportion test (a little optimistic next to the exact test on small tables; it is used to
    size studies, and cross-checked against the simulation in tests). Instant."""
    n1, n2 = n * share_exposed, n * (1 - share_exposed)
    if n1 < 1 or n2 < 1:
        return 0.0
    odds = base_rate / (1 - base_rate) * odds_ratio
    p1, p2 = odds / (1 + odds), base_rate
    pbar = (n1 * p1 + n2 * p2) / n
    se0 = math.sqrt(pbar * (1 - pbar) * (1 / n1 + 1 / n2))
    se1 = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    return _phi(((p1 - p2) - _z(1 - alpha) * se0) / se1)


def min_detectable_or(n: int, share_exposed: float, base_rate: float, target_power: float = 0.8, alpha: float = 0.05,
                      grid: Sequence[float] = (1.25, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10, 15, 25, 50)) -> float:
    """Smallest odds ratio in the grid that the study would detect with `target_power` (inf = none up to 50)."""
    for orr in grid:
        if power_approx(n, share_exposed, base_rate, orr, alpha) >= target_power:
            return float(orr)
    return float("inf")


def required_n(share_exposed: float, base_rate: float, odds_ratio: float, target_power: float = 0.8, alpha: float = 0.05,
               cap: int = 20000) -> int:
    """People needed for `target_power` at that odds ratio (-1 if it would take more than `cap`)."""
    n = 10
    while n <= cap:
        if power_approx(n, share_exposed, base_rate, odds_ratio, alpha) >= target_power:
            return n
        n += 10 if n < 200 else 25 if n < 1000 else 100
    return -1
