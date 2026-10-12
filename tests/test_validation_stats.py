import random

from antar_engine import validation_stats as vs


def test_fisher_matches_the_textbook_tea_tasting_table():
    r = vs.fisher_exact(3, 1, 1, 3)
    assert abs(r["p_greater"] - 0.2429) < 1e-3 and abs(r["p_two_sided"] - 0.4857) < 1e-3
    assert abs(r["odds_ratio"] - 9.0) < 1e-9


def test_fisher_extremes_and_symmetry():
    assert vs.fisher_exact(10, 0, 0, 10)["p_greater"] < 1e-4
    r = vs.fisher_exact(5, 5, 5, 5)
    assert 0.5 < r["p_greater"] < 0.75 and abs(r["p_two_sided"] - 1.0) < 1e-9
    assert vs.fisher_exact(0, 5, 5, 0)["p_greater"] > 0.99                      # exposed has FEWER outcomes: one-sided greater is ~1


def test_odds_ratio_interval_is_wide_on_a_small_table_and_brackets_the_estimate():
    lo, mid, hi = vs.odds_ratio_ci(3, 1, 1, 3)
    assert lo < 1 < hi and lo < mid < hi and hi / lo > 20


def test_auc():
    assert vs.auc([1, 2, 3, 4], [0, 0, 1, 1]) == 1.0
    assert vs.auc([4, 3, 2, 1], [0, 0, 1, 1]) == 0.0
    assert vs.auc([1, 1, 1, 1], [0, 1, 0, 1]) == 0.5
    assert vs.auc([1, 2], [1, 1]) != vs.auc([1, 2], [1, 1])                    # NaN when one group is empty


def test_permutation_null_is_uniform_and_a_real_effect_is_caught():
    rng = random.Random(3)
    hits = 0
    for i in range(60):                                                         # pure noise: p<0.05 should be rare
        sc = [rng.random() for _ in range(40)]
        lab = [1 if rng.random() < 0.4 else 0 for _ in range(40)]
        hits += vs.permutation_p(sc, lab, n_perm=300, seed=i)["p"] < 0.05
    assert hits <= 8
    sc = [rng.random() + (0.8 if i % 2 else 0) for i in range(80)]
    lab = [i % 2 for i in range(80)]
    assert vs.permutation_p(sc, lab, n_perm=500)["p"] < 0.01


def test_harness_can_detect_a_planted_effect_and_does_not_invent_one():
    """The point of a validation harness: a real odds ratio of 3 is found at n=300, and a null is not."""
    assert vs.power(300, 0.3, 0.30, 3.0, sims=300) >= 0.8
    null_rate = vs.power(300, 0.3, 0.30, 1.0, sims=400)
    assert null_rate <= 0.09                                                     # false-positive rate stays near alpha


def test_small_cohorts_are_underpowered_and_the_helpers_say_so():
    assert vs.power(14, 0.3, 0.30, 2.0, sims=300) < 0.25
    assert vs.power_approx(14, 0.3, 0.30, 2.0) < 0.25
    assert vs.min_detectable_or(14, 0.3, 0.30) >= 25
    assert vs.required_n(0.3, 0.30, 2.0) >= 150
    assert vs.required_n(0.3, 0.30, 3.0) < vs.required_n(0.3, 0.30, 2.0)
    assert vs.required_n(0.3, 0.30, 1.0001, cap=500) == -1                      # no effect: never enough people


def test_the_fast_approximation_agrees_with_the_exact_test_simulation():
    for n, orr in ((300, 3.0), (300, 2.0), (150, 3.0), (80, 3.0)):
        sim, approx = vs.power(n, 0.3, 0.30, orr, sims=400, seed=21), vs.power_approx(n, 0.3, 0.30, orr)
        assert abs(sim - approx) < 0.15, (n, orr, sim, approx)                  # the exact test is a little more conservative
    assert abs(vs.power_approx(500, 0.3, 0.30, 1.0) - 0.05) < 0.02             # no effect: power is just alpha
