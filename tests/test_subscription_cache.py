"""[entitlements-perf 2026-10-15] get_subscription reads the row once per 10 s, and every write path clears it."""
from antar_engine import subscription_engine as se
from antar_engine import entitlements as ent


class _Q:
    def __init__(self, sb): self.sb = sb
    def select(self, *_): return self
    def eq(self, *_): return self
    def execute(self):
        self.sb.reads += 1
        class R: data = [{"plan": "seeker", "status": "active", "current_period_end": None}]
        return R()


class _SB:
    reads = 0
    def table(self, _): return _Q(self)


def setup_function(_):
    se._SUB_CACHE.clear()


def test_second_read_is_cached():
    sb = _SB()
    a = se.get_subscription("c1", sb)
    b = se.get_subscription("c1", sb)
    assert sb.reads == 1 and a == b and a["plan"] == "seeker"


def test_cached_copy_is_not_shared():
    sb = _SB()
    se.get_subscription("c1", sb)["plan"] = "hacked"
    assert se.get_subscription("c1", sb)["plan"] == "seeker"


def test_bust_entitlement_cache_clears_it():
    sb = _SB()
    se.get_subscription("c1", sb)
    ent.bust_entitlement_cache("c1")
    se.get_subscription("c1", sb)
    assert sb.reads == 2
