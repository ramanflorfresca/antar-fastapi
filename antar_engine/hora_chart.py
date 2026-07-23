"""
antar_engine/hora_chart.py
D-2, the Hora chart — read the way the tradition actually reads it.  2026-07-23

WHY THIS FILE EXISTS. The previous D-2 logic scored "the Sri Lagna lord is in
its own sign". In a chart with two signs that is not a dignity, it is an
accident: only the Sun can be in Leo's hora and only the Moon in Cancer's, so
five of the seven grahas were disqualified before wealth was considered.
Measured on 93 live charts the rule was POSSIBLE for 33% and FIRED for 18%.
It was measuring which sign the Sri Lagna fell in. Removed in f94764d.

WHAT THE TEXTS ACTUALLY SUPPORT, and this is a short list on purpose. BPHS
gives the division (Ch. 6 — odd sign: first half the Sun's hora, second half
the Moon's; even sign reversed) and assigns D-2 the subject of dhana. It gives
almost no predictive technique. The elaborate hora methods in circulation are
later parampara, not Parashara, and this module says so rather than dressing
them up. Three layers, in descending order of how well attested they are:

    1. THE SPLIT      how many grahas fall in each hora. Oldest and strongest.
                      The Sun's hora is wealth that must be generated; the
                      Moon's is wealth that arrives. This is the chart's
                      headline and everything else qualifies it.

    2. THE HOUSE LORD IN ITS VARGA    the 2nd lord of the rasi, located in D-2,
                      and the 11th lord likewise. This is the mainstream
                      technique — K.N. Rao's school teaches the D-1 house lord
                      read in the corresponding varga — and it was entirely
                      missing from this engine until now.

    3. NATURE MATCH   a malefic prospers in the Sun's active hora, a benefic in
                      the Moon's receptive one. Real, and the weakest of the
                      three: it fires for 56% of charts, near a coin flip, so
                      it qualifies a reading and can never carry one.

TWO TRAPS THIS CHART SETS, both of which have already caught me once.

  DO NOT read conjunction in D-2. Every graha lands in Cancer or Leo, so four
  or five of them share a sign in every chart alive. "Jupiter conjunct Venus in
  the Hora chart" is a statement about arithmetic, not about a person.

  DO NOT read dignity by sign here — exaltation, own sign, moolatrikona. Same
  reason. The only dignity D-2 supports is nature-matching, layer 3.

WHAT THIS MODULE WILL NOT DO. It will not time wealth and it will not size it.
Both were tested against Gates, Ambani and Musk over 11 dated wealth events and
both died — see tests/negative_result_d2_wealth_chain.md. The Sri Lagna
nakshatra-lord chain scored 1/11 against 2.8 expected (p=0.962), WORSE than
chance. The classical 2nd/11th-lord dasha rule scored 6/11 against 5.2 expected
(p=0.425) — which reads like a success and is exactly noise, because that rule
is true for roughly half of any adult life.

So D-2 gives the SHAPE of a wealth channel and nothing else. Timing has to come
from the dasha layer, where it has actually been measured.
"""

from typing import Dict, List, Optional

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
SIGN_LORD = ["Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
             "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"]

SUN_HORA, MOON_HORA = "Leo", "Cancer"
BENEFIC = {"Jupiter", "Venus", "Mercury", "Moon"}
MALEFIC = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}

# Measured on the 93 live charts in this base, 2026-07-23. Used to say where a
# given chart sits relative to real people rather than against a round number
# somebody picked. Recompute if the base grows materially.
COHORT_MEAN_SUN_HORA = 4.27
COHORT_SD_SUN_HORA = 1.47
COHORT_N = 93

HORA_NAME = {SUN_HORA: "the Sun's hora", MOON_HORA: "the Moon's hora"}

# What each graha's placement says about the money it governs. Kept to one
# clause each — this chart has two signs and cannot support more resolution
# than that without inventing it.
IN_SUN_HORA = {
    "Sun": "it is yours to make, and it will carry your name",
    "Moon": "even what should arrive easily has to be worked for",
    "Mars": "it comes through direct effort and through competition won",
    "Mercury": "it comes from what you build and sell, not from what you hold",
    "Jupiter": "advice and reputation pay, but only when you go and get it",
    "Venus": "what you make beautiful or agreeable has to be sold, not offered",
    "Saturn": "it comes late and by endurance, and nothing arrives unearned",
    "Rahu": "scale is available, and it will demand the unconventional route",
    "Ketu": "specialised work pays, but it will not compound quietly",
}
IN_MOON_HORA = {
    "Sun": "position brings money without you having to press for it",
    "Moon": "it flows — through the public, through family, and it moves",
    "Mars": "effort is rewarded through others rather than by force",
    "Mercury": "trade and word of mouth carry it more than product does",
    "Jupiter": "counsel, teaching and goodwill bring it, and it settles",
    "Venus": "relationships and taste bring it, and people offer before asked",
    "Saturn": "slow accumulation that holds — it does not leave once it arrives",
    "Rahu": "it arrives through networks and other people's momentum",
    "Ketu": "it comes and goes without much attachment on your side",
}


def _hora_of(longitude: float) -> Optional[str]:
    """Parashari D-2. Odd sign: first half the Sun's, second half the Moon's.
    Even sign: reversed. Verified against this engine's stored D-2 on 837
    planet-placements across 93 charts — 100% agreement.
    """
    if not isinstance(longitude, (int, float)):
        return None
    sign_idx = int(longitude // 30) % 12
    odd_sign = (sign_idx % 2 == 0)          # index 0 = Aries = the 1st sign
    first_half = (longitude % 30) < 15.0
    return SUN_HORA if (odd_sign == first_half) else MOON_HORA


def _lagna_longitude(chart: dict) -> Optional[float]:
    lg = (chart or {}).get("lagna") or {}
    si, deg = lg.get("sign_index"), lg.get("degree")
    if isinstance(si, int) and isinstance(deg, (int, float)):
        return si * 30.0 + float(deg)
    return None


def _lord_of_house(chart: dict, house: int) -> Optional[str]:
    lg = (chart or {}).get("lagna") or {}
    si = lg.get("sign_index")
    if not isinstance(si, int):
        return None
    return SIGN_LORD[(si + house - 1) % 12]


def hora_positions(chart: dict) -> Dict[str, str]:
    """Every graha's hora, plus the ascendant's under the key 'Lagna'."""
    out = {}
    for p, d in ((chart or {}).get("planets") or {}).items():
        h = _hora_of((d or {}).get("longitude"))
        if h:
            out[p] = h
    lag = _lagna_longitude(chart)
    if lag is not None:
        out["Lagna"] = _hora_of(lag)
    return out


def hora_split(chart: dict) -> Dict:
    """Layer 1 — how the chart divides between forged and received wealth.

    The oldest rule in the hora literature. It describes the CHARACTER of a
    wealth channel — generated versus received — and NOTHING about amount.

    A pilot of three billionaires (Gates 7, Musk 6, Ambani 5, mean 6.00 vs
    cohort 4.27, p=0.038) suggested the wealthy sit high in the Sun's hora.
    That was tested on eight further wealthy charts and REFUTED: they averaged
    3.88, below the cohort, opposite to the pilot. See
    tests/negative_result_sun_hora_wealth.md. So the split must NOT be read as
    a wealth-amount signal in either direction. The band language below is about
    channel character only, and is deliberately written so no sentence in it
    means "you will be rich" or "you will not".
    """
    pos = {p: h for p, h in hora_positions(chart).items() if p != "Lagna"}
    if len(pos) < 7:
        return {"available": False}
    sun_n = sum(1 for h in pos.values() if h == SUN_HORA)
    moon_n = len(pos) - sun_n
    z = (sun_n - COHORT_MEAN_SUN_HORA) / COHORT_SD_SUN_HORA

    if z >= 1.0:
        band, line = "forged", (
            "Your wealth chart sits heavily in the Sun's hora. Money in your "
            "life is generated rather than received — it does not arrive on its "
            "own, and it carries your name when it comes.")
    elif z >= 0.35:
        band, line = "leans forged", (
            "Your wealth chart leans to the Sun's hora. More of your money has "
            "to be made than comes to you, though not all of it.")
    elif z <= -1.0:
        band, line = "received", (
            "Your wealth chart sits heavily in the Moon's hora. Money reaches "
            "you through other people — partners, clients, family, backers — "
            "and it moves rather than settles.")
    elif z <= -0.35:
        band, line = "leans received", (
            "Your wealth chart leans to the Moon's hora. More of your money "
            "arrives through others than you generate alone.")
    else:
        band, line = "balanced", (
            "Your wealth chart divides evenly between the two horas. You both "
            "generate money and receive it, and neither route dominates.")

    return {"available": True, "sun_hora": sun_n, "moon_hora": moon_n,
            "z": round(z, 2), "band": band, "line": line,
            "cohort": {"mean": COHORT_MEAN_SUN_HORA, "sd": COHORT_SD_SUN_HORA,
                       "n": COHORT_N}}


def house_lord_in_hora(chart: dict, house: int) -> Dict:
    """Layer 2 — the rasi's house lord located in D-2. Rao's school's method.

    The 2nd lord is the money you hold; the 11th is the money that comes in.
    Reading each in the Hora chart says how that particular stream behaves,
    which is a different question from the whole-chart split above.
    """
    lord = _lord_of_house(chart, house)
    if not lord:
        return {"available": False}
    lon = (((chart or {}).get("planets") or {}).get(lord) or {}).get("longitude")
    seat = _hora_of(lon)
    if not seat:
        return {"available": False}
    clause = (IN_SUN_HORA if seat == SUN_HORA else IN_MOON_HORA).get(lord, "")
    label = {2: "the money you hold", 11: "the money that comes in"}.get(
        house, f"your {house}th-house matters")
    return {"available": True, "house": house, "lord": lord, "hora": seat,
            "hora_name": HORA_NAME[seat], "clause": clause,
            "line": f"{lord} rules {label}, and in the wealth chart it sits in "
                    f"{HORA_NAME[seat]} — {clause}."}


def nature_match(chart: dict, planet: str) -> Optional[bool]:
    """Layer 3 — the only dignity D-2 supports.

    A malefic is at home in the Sun's active hora, a benefic in the Moon's
    receptive one. NOT own-sign, NOT exaltation: with two signs those are
    arithmetic. Fires for 56% of charts, so it qualifies and never carries.
    """
    lon = (((chart or {}).get("planets") or {}).get(planet) or {}).get("longitude")
    seat = _hora_of(lon)
    if not seat:
        return None
    return ((planet in BENEFIC and seat == MOON_HORA)
            or (planet in MALEFIC and seat == SUN_HORA))


def read_hora_chart(chart: dict) -> Dict:
    """The full D-2 reading — shape of the wealth channel, and nothing more.

    Deliberately returns no date and no amount. Both were tested and both
    failed; see the module docstring and the negative-result file.
    """
    split = hora_split(chart)
    if not split.get("available"):
        return {"available": False}

    lines: List[str] = [split["line"]]
    second = house_lord_in_hora(chart, 2)
    eleventh = house_lord_in_hora(chart, 11)

    # One graha routinely rules both the 2nd and the 11th — it happens for four
    # of the twelve ascendants, and printing its sentence twice reads like a
    # bug to the person holding the chart. Merged, it is also a stronger
    # statement than either half: the money coming in and the money staying
    # put run through a single planet.
    if (second.get("available") and eleventh.get("available")
            and second["lord"] == eleventh["lord"]):
        lord, seat = second["lord"], second["hora"]
        lines.append(
            f"{lord} rules both the money you hold and the money that comes in, "
            f"and in the wealth chart it sits in {HORA_NAME[seat]} — "
            f"{second['clause']}. One planet carries both sides of your money, "
            f"so they rise and fall together.")
    else:
        for part in (second, eleventh):
            if part.get("available"):
                lines.append(part["line"])

    # The ascendant's own hora — how the person is oriented, as distinct from
    # how their money behaves.
    lag_hora = hora_positions(chart).get("Lagna")
    if lag_hora == SUN_HORA:
        lines.append("You yourself fall in the Sun's hora: you are built to "
                     "generate, and idle money will not sit well with you.")
    elif lag_hora == MOON_HORA:
        lines.append("You yourself fall in the Moon's hora: you are built to "
                     "gather and hold rather than to chase.")

    # Layer 3, and only as a qualifier — it fires for 56% of charts, so it can
    # never be the point of a reading. De-duplicated by graha for the same
    # reason as above.
    unsuited = []
    for part in (second, eleventh):
        if (part.get("available") and part["lord"] not in unsuited
                and nature_match(chart, part["lord"]) is False):
            unsuited.append(part["lord"])
    if len(unsuited) == 1:
        lines.append(f"{unsuited[0]} is not naturally at home in that hora, so "
                     f"that stream takes more managing than it should.")
    elif len(unsuited) == 2:
        lines.append(f"Neither {unsuited[0]} nor {unsuited[1]} is naturally at "
                     f"home in its hora, so both sides of your money take more "
                     f"managing than they should.")

    return {
        "available": True,
        "split": split,
        "second_lord": second if second.get("available") else None,
        "eleventh_lord": eleventh if eleventh.get("available") else None,
        "lagna_hora": lag_hora,
        "positions": hora_positions(chart),
        "lines": lines,
        # Stated on the object so no caller can mistake this for a forecast.
        "gives": "the shape of the wealth channel",
        "does_not_give": "timing or amount — both tested against Gates, Ambani "
                         "and Musk over 11 dated events, both failed",
    }


def hora_context(chart: dict) -> str:
    """Prompt block for the reading engines."""
    r = read_hora_chart(chart)
    if not r.get("available"):
        return ""
    s = r["split"]
    out = ["═══ D-2 HORA — THE WEALTH CHANNEL (shape only, never timing) ═══",
           f"split: {s['sun_hora']} in the Sun's hora / {s['moon_hora']} in the "
           f"Moon's — {s['band']} (cohort mean {s['cohort']['mean']}, "
           f"n={s['cohort']['n']})"]
    out += [f"  - {ln}" for ln in r["lines"]]
    out.append("  RULE: D-2 says what KIND of wealth channel this is. It does not "
               "say how much or when. Do not read conjunction or sign-dignity in "
               "this chart — it has two signs, so both are arithmetic.")
    return "\n".join(out)
