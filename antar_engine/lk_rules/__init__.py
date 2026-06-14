"""
antar_engine/lk_rules — Phase 2 Lal Kitab rule engine.

Each rule is a small, pure, independently-testable function over the Phase 1
Varshphal chart object (antar_engine.varshphal_chart) plus the natal chart.
No rule ships without a `source` citation.

Rule 1: sleeping-planet engine (dual sleep + maturity gate). See sleeping.py.
"""

from antar_engine.lk_rules.maturity import (
    LK_MATURITY_AGE,
    is_mature,
)
from antar_engine.lk_rules.sleeping import (
    evaluate_sleeping_planets,
    reweight_year_events,
    SLEEP_OUTCOME_RANK,
    SLEEP_REWEIGHT_FACTOR,
)

__all__ = [
    "LK_MATURITY_AGE",
    "is_mature",
    "evaluate_sleeping_planets",
    "reweight_year_events",
    "SLEEP_OUTCOME_RANK",
    "SLEEP_REWEIGHT_FACTOR",
]
