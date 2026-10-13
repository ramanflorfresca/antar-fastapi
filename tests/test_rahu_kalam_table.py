from antar_engine import daily_panchanga as DP
from antar_engine import muhurta_engine as ME


def test_rahu_kalam_tables_agree_and_follow_the_classical_order():
    classical = {0: 2, 1: 7, 2: 5, 3: 6, 4: 4, 5: 3, 6: 8}                     # Mon..Sun, 8 equal parts of daylight
    assert DP.RAHU_KALAM_PART == classical
    assert ME.RAHU_KALAM_SEGMENT == classical                                   # the two engines must never disagree again


def test_every_part_is_used_once_across_the_week_except_the_first_and_none_is_out_of_range():
    assert sorted(DP.RAHU_KALAM_PART.values()) == [2, 3, 4, 5, 6, 7, 8]          # the 1st part is never Rahu Kalam
