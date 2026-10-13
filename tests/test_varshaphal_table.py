"""Lal Kitab annual table: structure and the checks that justify it (see header of varshaphal_table.py)."""
import pytest

from antar_engine.varshaphal_table import VARSHAPHAL_TABLE, get_annual_house


@pytest.mark.parametrize("row", range(1, 121))
def test_every_row_is_a_permutation_of_1_to_12(row):
    assert sorted(VARSHAPHAL_TABLE[row]) == list(range(1, 13))


def test_jhora_verified_rows_56_and_57():
    # Sam K (Libra lagna, DOB 02 Nov 1970), verified against Jagannatha Hora
    r56, r57 = VARSHAPHAL_TABLE[56], VARSHAPHAL_TABLE[57]
    assert [r56[h - 1] for h in (1, 2, 5, 7, 11, 12)] == [2, 3, 9, 10, 12, 7]
    assert [r57[h - 1] for h in (1, 2, 5, 7, 11, 12)] == [12, 2, 10, 9, 1, 3]


def test_running_year_offset():
    # age completed 55 -> running year 56 -> row 56
    for natal in range(1, 13):
        assert get_annual_house(natal, 55) == VARSHAPHAL_TABLE[56][natal - 1]
    assert get_annual_house(1, 0) == VARSHAPHAL_TABLE[1][0]
    assert get_annual_house(1, 200) == VARSHAPHAL_TABLE[120][0]
