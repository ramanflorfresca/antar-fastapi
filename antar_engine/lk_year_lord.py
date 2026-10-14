"""
Lal Kitab year lord: the age-based 35-year planet cycle (owner decision 2026-10-13: the age cycle is correct,
not the weekday of the last birthday).

Provenance, stated plainly: Pt. Roop Chand's own text gives the child cycle (Saturn ages 1-6, Rahu 7-12, Ketu 13-15,
Jupiter 16-21) and the planet awakening ages (Jupiter 16, Sun 22, Moon 24, Venus 25, Mars 28, Saturn 36, Rahu 42,
Ketu 48), and says a planet's bad result in the first 35-year round is not repeated in the second. The complete
age-to-planet table below is the one printed in the Goswami and Vashisth 1952-edition commentary; it agrees with all
of those ages except Mercury (Roop Chand lists 17, the table has Mercury at 34-35). Roop Chand's annual rules do not
use the year lord, so it is context only.
Years are RUNNING years of life (age completed + 1).
"""
from datetime import date

YEAR_LORD_BY_RUNNING_YEAR = [
    (1, 6, "Saturn"), (7, 12, "Rahu"), (13, 15, "Ketu"), (16, 21, "Jupiter"), (22, 23, "Sun"), (24, 24, "Moon"),
    (25, 27, "Venus"), (28, 33, "Mars"), (34, 35, "Mercury"), (36, 41, "Saturn"), (42, 47, "Rahu"), (48, 50, "Ketu"),
    (51, 56, "Jupiter"), (57, 58, "Sun"), (59, 59, "Moon"), (60, 62, "Venus"), (63, 68, "Mars"), (69, 70, "Mercury"),
    (71, 76, "Saturn"), (77, 82, "Rahu"), (83, 85, "Ketu"), (86, 91, "Jupiter"), (92, 93, "Sun"), (94, 94, "Moon"),
    (95, 97, "Venus"), (98, 103, "Mars"), (104, 105, "Mercury"), (106, 111, "Saturn"), (112, 117, "Rahu"),
    (118, 120, "Ketu")]


def completed_age(born: date, today: date) -> int:
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def year_lord_for_running_year(ry: int) -> str:
    ry = max(1, min(120, ry))
    for a, b, p in YEAR_LORD_BY_RUNNING_YEAR:
        if a <= ry <= b:
            return p
    return YEAR_LORD_BY_RUNNING_YEAR[-1][2]


def year_lord_by_age(birth_date, today=None) -> str:
    """Planet ruling the current year of life, or '' if the birth date cannot be read."""
    try:
        born = birth_date if isinstance(birth_date, date) else date.fromisoformat(str(birth_date)[:10])
        return year_lord_for_running_year(completed_age(born, today or date.today()) + 1)
    except Exception:
        return ""
