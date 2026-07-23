"""
antar_engine/wealth_channel.py
How wealth reaches this person, where from, and when.          2026-07-22

Four references, each answering a different question, assembled into plain
sentences rather than another score. The scoring surface in this codebase is
already larger than its validation, so this layer explains and does not rank.

    WHAT   career_mode      owned or employed, and what kind of work
    HOW    D-10             the career chart's lagna lord — the instrument
    WHERE  Sri Lagna        the house it falls in, read as a place
    WHEN   dasha            when the channel lord is actually live

The WHERE and WHEN are the parts that were missing, and WHEN is the one that
stops this being a horoscope. A channel statement with no timing is a
compliment; with timing it is a claim.

A worked example from the chart this was built against. Sri Lagna in the 12th,
its lord Jupiter in the 2nd — wealth arrives from far away and settles into
savings. The Sri Lagna's own nakshatra is Purva Ashadha, lord Venus, so Venus is
the channel. But his next Venus antardasha is 2038, twelve years out, and
"wait for your channel lord" would be worthless advice to a man carrying debt
now.

What makes it live is the conjunction: Rahu, whose eighteen-year mahadasha
begins 13 August 2026, sits 1.78 degrees from Venus in the 11th. The channel
lord is activated by the incoming period lord rather than by its own period.
That distinction is the difference between a real timing statement and a
platitude, and it is why WHEN is computed here rather than assumed.
"""

from typing import Dict, List, Optional

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
NAKSHATRA_LORDS = [
    ("Ashwini", "Ketu"), ("Bharani", "Venus"), ("Krittika", "Sun"),
    ("Rohini", "Moon"), ("Mrigashira", "Mars"), ("Ardra", "Rahu"),
    ("Punarvasu", "Jupiter"), ("Pushya", "Saturn"), ("Ashlesha", "Mercury"),
    ("Magha", "Ketu"), ("P.Phalguni", "Venus"), ("U.Phalguni", "Sun"),
    ("Hasta", "Moon"), ("Chitra", "Mars"), ("Swati", "Rahu"),
    ("Vishakha", "Jupiter"), ("Anuradha", "Saturn"), ("Jyeshtha", "Mercury"),
    ("Mula", "Ketu"), ("P.Ashadha", "Venus"), ("U.Ashadha", "Sun"),
    ("Shravana", "Moon"), ("Dhanishta", "Mars"), ("Shatabhisha", "Rahu"),
    ("P.Bhadrapada", "Jupiter"), ("U.Bhadrapada", "Saturn"), ("Revati", "Mercury"),
]

# Where the Sri Lagna falls, said as a PLACE a person recognises. "From a
# distance" was the first phrasing and it was too vague to act on; a reader
# should be able to tell whether it describes their life.
SRI_HOUSE_PLACE = {
    1:  "close to home and under your own name",
    2:  "through what you have already built — savings, family, existing holdings",
    3:  "through your own hands and your own contacts, close by",
    4:  "through home, property, and the place you actually live",
    5:  "through what you create yourself, and through risk you choose",
    6:  "through service and daily work — the grind, not the windfall",
    7:  "through partners and clients, not alone",
    8:  "through other people's money — investors, inheritance, a sudden turn",
    9:  "through teachers, long journeys, and people senior to you",
    10: "through your public standing — being known for the work",
    11: "through networks and gains that come to you rather than are chased",
    12: "from a foreign country and a different culture, away from where you were born",
}

# What the channel lord actually is, in ordinary words.
CHANNEL_PLANET = {
    "Sun": "authority and being seen to lead",
    "Moon": "the public, and people's trust in you",
    "Mars": "drive, machinery, competition",
    "Mercury": "trade, logic, communication, product",
    "Jupiter": "counsel, teaching, reputation, expansion",
    "Venus": "what people find worth paying for — design, relationships, the deal",
    "Saturn": "endurance, structure, work nobody else will do",
    "Rahu": "the unconventional route, scale, technology",
    "Ketu": "specialised, solitary or technical work — and it cuts as often as it gives",
}


def _nakshatra_of(longitude: float) -> tuple:
    idx = int((longitude % 360) // (360.0 / 27)) % 27
    return NAKSHATRA_LORDS[idx]


def wealth_channel(chart: dict, dashas: Optional[dict] = None) -> Dict:
    """Where wealth comes from, through what, and when that becomes live."""
    try:
        from antar_engine.sri_lagna import sri_lagna
        sl = sri_lagna(chart)
    except Exception:
        return {"available": False}
    if not sl.get("available"):
        return {"available": False}

    nak_name, channel = _nakshatra_of(sl["longitude"])
    house = sl["house_from_lagna"]
    sl_lord = sl["lord"]
    lord_house = ((chart.get("planets") or {}).get(sl_lord) or {}).get("house")

    lines: List[str] = []
    lines.append(f"Wealth reaches you {SRI_HOUSE_PLACE.get(house, 'through this area of life')}.")
    if lord_house:
        lines.append(f"Its lord {sl_lord} sits in your {_ord(lord_house)} house, "
                     f"which is where it ends up once it arrives.")
    lines.append(f"The channel is {channel} — {CHANNEL_PLANET.get(channel, '')}.")

    # WHEN. Two ways the channel goes live: its own period, or a period lord
    # sitting on it. The second is the one people miss, and on the chart this
    # was built against it is the only one that happens this decade.
    timing = _channel_timing(chart, channel, dashas)
    lines.extend(timing["lines"])

    return {
        "available": True,
        "sri_lagna_sign": sl["sign"],
        "sri_lagna_house": house,
        "sri_lagna_lord": sl_lord,
        "sri_lagna_lord_house": lord_house,
        "channel_nakshatra": nak_name,
        "channel_planet": channel,
        "timing": timing,
        "lines": lines,
    }


def _ord(n: int) -> str:
    return {1: "1st", 2: "2nd", 3: "3rd"}.get(n, f"{n}th")


def _channel_timing(chart: dict, channel: str, dashas: Optional[dict]) -> Dict:
    """When the channel lord is actually active — by its own period, or by contact."""
    from datetime import date
    out = {"lines": [], "own_period": None, "activated_by": None}
    today = date.today().isoformat()

    # 1. A conjunction with an incoming or running period lord activates the
    #    channel without waiting for the channel's own dasha. Same house, close
    #    degrees — this is what makes a distant period lord relevant now.
    planets = (chart or {}).get("planets") or {}
    ch = planets.get(channel) or {}
    ch_lon, ch_house = ch.get("longitude"), ch.get("house")
    conjuncts = []
    if isinstance(ch_lon, (int, float)):
        for p, d in planets.items():
            if p == channel or not isinstance(d, dict):
                continue
            lon = d.get("longitude")
            if isinstance(lon, (int, float)) and d.get("house") == ch_house:
                sep = abs(((lon - ch_lon + 180) % 360) - 180)
                if sep <= 8.0:
                    conjuncts.append((p, round(sep, 2)))

    # 2. The channel lord's own upcoming periods.
    nxt = None
    if dashas:
        for r in (dashas.get("vimsottari") or []):
            if not isinstance(r, dict):
                continue
            lord = r.get("lord_or_sign") or r.get("planet_or_sign")
            lvl = str(r.get("level") or "").lower()
            end = str(r.get("end_date") or "")[:10]
            start = str(r.get("start_date") or "")[:10]
            if lord == channel and lvl in ("mahadasha", "antardasha") and end >= today:
                if nxt is None or start < nxt[0]:
                    nxt = (start, end, lvl)
    out["own_period"] = nxt

    if conjuncts:
        ordered = [p for p, _ in sorted(conjuncts, key=lambda x: x[1])]
        names = ordered[0] if len(ordered) == 1 else (
            " and ".join([", ".join(ordered[:-1]), ordered[-1]]))
        verb = "sits" if len(ordered) == 1 else "sit"
        out["activated_by"] = ordered
        out["lines"].append(
            f"{names} {verb} with {channel} in the same house, within a few degrees. "
            f"So any period belonging to {names} switches the channel on — it does "
            f"not have to wait for {channel}'s own period.")

    if nxt:
        far = nxt[0][:4]
        if conjuncts and int(far) - int(today[:4]) > 5:
            out["lines"].append(
                f"{channel}'s own period is not until {far}, which is why the "
                f"conjunction above matters more than waiting for it.")
        else:
            out["lines"].append(
                f"{channel}'s own {nxt[2]} runs {nxt[0]} to {nxt[1]} — the stretch "
                f"where this channel carries the most weight on its own.")
    elif not conjuncts:
        out["lines"].append(
            f"No {channel} period is on record ahead, and nothing sits with it — "
            f"this channel works quietly rather than in bursts.")

    return out
