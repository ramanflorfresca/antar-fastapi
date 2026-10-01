"""
antar_engine/your_pattern.py — "Your Pattern".

[your-pattern 2026-09-30] Takes the user's OWN venture history (what they tried,
when, how it turned out) and holds it up against their chart's SHAPE + the SEASON
each bet launched in — so they can see the repeating pattern in their own choices.

HARD BOUNDARY (same as domain_fit, do NOT cross): this is a DESCRIPTIVE MIRROR,
never a predictor. It must NEVER say the chart "knew" a venture would fail/succeed,
and must NEVER rank which vertical wins — that was falsified
(business-vertical-timing-study). What it CAN honestly say: these bets shared a
shape / an approach / a season, and that shape/approach sits this way against the
chart's aligned shape. The insight is in the REPETITION the user can now see, not
in a claim the chart forecasts outcomes.

Output is jargon-free + deterministic. Fail-open.
"""
from __future__ import annotations

from datetime import date

from antar_engine.domain_fit import assess_domain_fit, _resolve_domain, DOMAIN_SPEC

# plain phrasing per domain (shared spirit with aligned_path, kept local)
_DOMAIN_PHRASE = {
    "tech": "a tech platform", "property": "property", "hospitality": "a public-facing business",
    "partnership": "a partnership venture", "speculation": "a speculative bet",
    "career": "a role/position", "funding": "a capital raise",
}
_FAST_WORDS = ("flip", "quick", "raise", "investor", "capital", "fund", "scale",
               "fast", "launch", "platform", "app", "startup", "leverage", "loan")


def _parse_when(s):
    """Accept 'YYYY', 'YYYY-MM', 'YYYY-MM-DD', or an ISO datetime
    ('2015-06-01T00:00:00') → a date (mid-year/mid-month fill)."""
    try:
        s = str(s or "").strip()
        s = s.split("T")[0].split(" ")[0]   # drop any time suffix
        parts = s.split("-")
        y = int(parts[0]); m = int(parts[1]) if len(parts) > 1 else 7
        d = int(parts[2]) if len(parts) > 2 else 15
        return date(y, max(1, min(12, m)), max(1, min(28, d)))
    except Exception:
        return None


def active_lords_at(dashas, when):
    """Running Vimśottarī lords (any level) covering date `when`. Reads the same
    dasha_periods rows the rest of the app uses. Returns a set of planet names."""
    out = set()
    try:
        rows = (dashas or {}).get("vimsottari") or []
        for r in rows:
            s = _parse_when(r.get("start_date") or r.get("start"))
            e = _parse_when(r.get("end_date") or r.get("end"))
            lord = (r.get("planet_or_sign") or r.get("lord_or_sign") or "").title()
            if s and e and lord and s <= when <= e:
                out.add(lord)
    except Exception:
        pass
    return out


def _season_at(chart_data, dashas, when):
    """Was `when` a hazy / non-closure season? Mirrors domain_fit's Guru-Chāṇḍāla
    haze test, but DATE-REAL: the natal haze only COUNTS as a season when its
    lord (Rahu) was actually running at `when`. A static natal flag must not read
    as 'you launched in a foggy stretch' on every date. Returns 'haze' |
    'ordinary' (never a success/fail claim)."""
    try:
        if not when:
            return "ordinary"
        planets = (chart_data or {}).get("planets") or {}
        rahu_sign = (planets.get("Rahu") or {}).get("sign")
        rahu_h = (planets.get("Rahu") or {}).get("house")
        jup_h = (planets.get("Jupiter") or {}).get("house")
        guru_chandala = (rahu_sign in ("Sagittarius", "Pisces")
                         or (rahu_h is not None and rahu_h == jup_h))
        if not guru_chandala:
            return "ordinary"
        # date-real gate: was Rahu actually one of the running lords then?
        return "haze" if "Rahu" in active_lords_at(dashas, when) else "ordinary"
    except Exception:
        return "ordinary"


def build_pattern(chart_data, dashas, ventures, first_name=""):
    """ventures = [{label, started_on, outcome}] (outcome in
    failed|succeeded|ongoing|''). Returns {summary, items[], _facts}. Descriptive
    only — never predicts or ranks verticals."""
    name = (first_name or "").strip()
    lead = (name + ", ") if name else ""
    out = {"summary": "", "items": [], "_facts": {}}
    try:
        items = []
        for v in (ventures or []):
            label = (v.get("label") or "").strip()
            if not label:
                continue
            when = _parse_when(v.get("started_on"))
            outcome = (v.get("outcome") or "").strip().lower()
            domain, raising = _resolve_domain(label, "")
            fit = assess_domain_fit(chart_data, dashas, label, "", running_lords=None) \
                if domain else {}
            shape = fit.get("shape", "")
            alignment = fit.get("alignment", "neutral")
            ql = label.lower()
            asked_fast = raising or any(w in ql for w in _FAST_WORDS)
            season = _season_at(chart_data, dashas, when) if when else "ordinary"
            items.append({
                "label": label,
                "when": when.isoformat() if when else "",
                "year": when.year if when else None,
                "outcome": outcome,
                "domain": domain,
                "shape": shape,
                # did the APPROACH fight the chart's shape for this domain?
                "alignment": alignment,
                "misaligned": alignment == "misaligned_approach",
                "approach_fast": bool(asked_fast),
                "season": season,
            })
        out["items"] = items
        if not items:
            out["summary"] = (lead + "add a few things you've tried — what it was, "
                              "roughly when, and how it went — and I'll show you the "
                              "pattern across them.").strip()
            return out
        # A pattern needs at least two points — one entry can't have a thread yet.
        # Acknowledge the one they added and invite more (never a bare name).
        if len(items) < 2:
            out["summary"] = (lead + "that's one down. Add a couple more — even "
                              "roughly — and I'll show you the thread that runs "
                              "across them.").strip()
            return out

        # ---- aggregate the DESCRIPTIVE pattern ----
        n = len(items)
        fails = [i for i in items if i["outcome"] in ("failed", "fail", "closed", "died")]
        doms = [i["domain"] for i in items if i["domain"]]
        same_domain = len(set(doms)) == 1 and len(doms) == n and n >= 2
        fast_share = sum(1 for i in items if i["approach_fast"])
        haze_fails = sum(1 for i in fails if i["season"] == "haze")
        # did the APPROACH fight the chart's shape? (Andres-flip = yes; Raman-tech = no)
        misaligned = [i for i in items if i["misaligned"]]
        approach_fought = len(misaligned) >= 2 or (fails and len(misaligned) >= len(fails))
        out["_facts"] = {
            "n": n, "fails": len(fails), "same_domain": doms[0] if same_domain else None,
            "fast_share": fast_share, "haze_fails": haze_fails,
            "misaligned": len(misaligned), "approach_fought": approach_fought,
        }

        bits = []
        if same_domain:
            bits.append(f"every one of these was {_DOMAIN_PHRASE.get(doms[0], doms[0])}")
        if fast_share == n and n >= 2:
            bits.append("each one was the same move — fast, launch-and-scale, built to "
                        "take off quickly")
        elif fast_share >= 2:
            bits.append("most leaned on the same fast, scale-quickly approach")
        # season clause only when it genuinely clusters AND is date-real
        if fails and haze_fails == len(fails) and len(fails) >= 2:
            bits.append("each was launched in one of your foggier, non-closure "
                        "stretches — when things rarely land the way they're pitched")
        elif haze_fails >= 2:
            bits.append("several were launched in your foggier, non-closure stretches")

        head = ""
        if bits:
            head = ("Looking across these: " + bits[0] + "."
                    if len(bits) == 1 else
                    "Looking across these: " + "; and ".join([", ".join(bits[:-1]), bits[-1]]) + "."
                    if len(bits) > 2 else
                    "Looking across these: " + " — and ".join(bits) + ".")

        # The honest contrast — branch on whether the approach FOUGHT the shape:
        tail = ""
        dp = _DOMAIN_PHRASE.get(doms[0], doms[0]) if same_domain else "this"
        if approach_fought and same_domain and items[0].get("shape"):
            # Andres case: the asked approach genuinely fights the chart's shape.
            tail = (f" Your chart's shape for {dp} is different — {items[0]['shape']}. "
                    f"The thread isn't the field; it's the approach fighting that shape. "
                    f"Worked the way your chart is built for, and in a clearer season, "
                    f"the same field reads very differently.")
        elif same_domain:
            # Raman case: the field + approach actually FIT the chart. Be honest —
            # the chart does NOT explain the outcomes; the variable is elsewhere.
            tail = (f" Here's the honest part: {dp} genuinely fits you, and so does that "
                    f"fast-building approach — the chart doesn't say the field was wrong. "
                    f"So the thing that varied wasn't your fit; it was the parts a chart "
                    f"doesn't decide — timing, the team, the capital, the execution. The "
                    f"pattern says keep the field; change the variables around it, and "
                    f"pick your season.")
        elif approach_fought:
            tail = (" The common thread is the approach fighting your natural shape, not "
                    "the field itself — the fast launch-and-scale move, repeated. Done "
                    "slower, more owned, and in a clearer season, the same drive sits "
                    "very differently.")
        elif len(misaligned) >= 1 or haze_fails >= 2:
            # Mixed fields, no single-field story — but there IS a thread in HOW/WHEN.
            where = []
            if len(misaligned) >= 1:
                where.append("the times you pushed fast or leveraged against something "
                             "that wanted to be owned slowly")
            if haze_fails >= 2:
                where.append("the ones you started in a foggy, non-closure season")
            thread = " and ".join(where) if where else "the approach and the timing"
            tail = (f" These span different fields, so the thread isn't the field — it's "
                    f"{thread}. That's the repeat to watch, and it's about how and when "
                    f"you move, not what you're capable of.")

        out["summary"] = (lead + (head + tail).strip()).strip() or (
            lead + "here's your track record — tell me how each went and I'll mirror "
            "the pattern back.").strip()
        return out
    except Exception:
        return out
