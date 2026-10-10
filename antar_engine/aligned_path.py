"""
antar_engine/aligned_path.py — "Your Aligned Path" (the operating manual).

[aligned-path 2026-09-30] Productizes the deep whole-chart read into ONE card
with four jargon-free blocks the user can act on:

  EDGE   — what you're built for (the domain(s) whose SHAPE fits this chart)
  TRAP   — the approach / lane to avoid (misaligned approach + standing leak)
  SEASON — your timing right now (expand vs consolidate-protect posture)
  MOVE   — the single aligned action to take next

It reuses the Domain-Fit engine (ranks every venture domain by pure shape-fit)
and the chart-level strategic stance. HARD BOUNDARY inherited from domain_fit:
this reasons about SHAPE / APPROACH / TIMING, NEVER vertical-success. Edge =
"this is the shape you're built to run", never "this will succeed". Output is
deterministic + jargon-free (no planets/houses/Sanskrit) — safe to ship without
the LLM, same contract as the Today vote engine. Fail-open: a thin chart still
returns a usable, honest card.
"""
from __future__ import annotations

from antar_engine.domain_fit import fit_all_domains

# Jargon-free noun phrase per domain (user-facing).
_DOMAIN_PHRASE = {
    "tech": "building things in tech",
    "property": "owning and holding property",
    "hospitality": "a public-facing, people-first business",
    "partnership": "building alongside the right partner",
    "career": "a role with real authority",
}
# The short "how it works for you" clause, from the domain's natural shape.
_DOMAIN_HOW = {
    "tech": "fast, connected, built on your own insight — lead it, don't just execute",
    "property": "slowly and owned — built or bought and held, never flipped or rushed",
    "hospitality": "out front and presence-driven, where people deal with you directly",
    "partnership": "shared — it rises and falls on who you build it with, so choose well",
    "career": "inside a structure where you're the visible authority, not hidden in the ranks",
}
# The misaligned approach each slow/owned domain quietly invites (the trap).
_DOMAIN_APPROACH_TRAP = {
    "property": "trying to flip it fast or raise money against it",
    "hospitality": "scaling it before the ground under it is solid",
    "career": "staying heads-down and waiting to be noticed instead of claiming the lead",
}
_SLOW_DOMAINS = {"property"}  # shape is intrinsically slow/owned


def _edge_and_trap(fits):
    """Rank domains by pure shape-fit. Returns (edge_domains, weak_domains)."""
    ranked = sorted(fits.items(), key=lambda kv: kv[1].get("net", 0), reverse=True)
    edge = [d for d, r in ranked if r.get("net", 0) >= 2]
    if not edge and ranked:
        # nobody clears the "supported" bar — name the single best-fit softly
        top_d, top_r = ranked[0]
        if top_r.get("net", 0) >= 1:
            edge = [top_d]
    weak = [d for d, r in ranked if r.get("net", 0) < 0]
    return edge[:2], weak[:1]


def build_aligned_path(chart_data, dashas, stance="", running_lords=None,
                       first_name="", concern="business"):
    """Return {edge, trap, season, move, _facts}. Each block is
    {title, text} with plain, jargon-free text. `stance` is the label from
    _ask_strategic_stance ('expand' | 'consolidate/protect' | '')."""
    name = (first_name or "").strip()
    lead = (name + ", ") if name else ""
    out = {
        "edge":   {"title": "Your edge", "text": ""},
        "trap":   {"title": "Your trap", "text": ""},
        "season": {"title": "Right now", "text": ""},
        "move":   {"title": "Your move", "text": ""},
        "_facts": {},
    }
    try:
        fits = fit_all_domains(chart_data, dashas, running_lords=running_lords) or {}
        edge_domains, weak_domains = _edge_and_trap(fits)
        out["_facts"] = {
            "stance": stance,
            "net_by_domain": {d: r.get("net", 0) for d, r in fits.items()},
            "edge_domains": edge_domains,
            "weak_domains": weak_domains,
        }

        # ---- EDGE ----
        if edge_domains:
            parts = []
            for d in edge_domains:
                parts.append(f"{_DOMAIN_PHRASE.get(d, d)} — {_DOMAIN_HOW.get(d, '')}")
            if len(parts) == 1:
                out["edge"]["text"] = (
                    f"{lead}you're built for {parts[0]}.")
            else:
                out["edge"]["text"] = (
                    f"{lead}you're built for {parts[0]}. Close behind: "
                    f"{parts[1]}.")
        else:
            out["edge"]["text"] = (
                f"{lead}your edge isn't one single field — it's how you work: "
                f"steady, on your own terms, where you own the outcome rather than "
                f"chase it.")

        # ---- TRAP ----
        trap_bits = []
        # 1) the approach trap tied to the person's own edge (highest signal)
        for d in edge_domains:
            if d in _DOMAIN_APPROACH_TRAP:
                trap_bits.append(_DOMAIN_APPROACH_TRAP[d])
        # 2) speculation is a standing trap for everyone (the gate stays closed)
        trap_bits.append("leaning on quick bets, speculation or fast money")
        # 3) a genuinely weak lane, if any
        if weak_domains:
            wd = weak_domains[0]
            trap_bits.append(f"forcing {_DOMAIN_PHRASE.get(wd, wd)}, which isn't your lane")
        # de-dupe, keep order, cap at 2 for a tight card
        seen, clean = set(), []
        for b in trap_bits:
            if b not in seen:
                seen.add(b); clean.append(b)
        clean = clean[:2]
        if len(clean) == 1:
            out["trap"]["text"] = f"Where it goes wrong for you: {clean[0]}."
        else:
            out["trap"]["text"] = (
                f"Where it goes wrong for you: {clean[0]}, and {clean[1]}.")

        # ---- SEASON ----
        st = (stance or "").lower()
        if "consolidate" in st or "protect" in st:
            out["season"]["text"] = (
                "Right now is a consolidate-and-protect phase — guard what you've "
                "built, collect what you're owed, and tighten before you widen. Not "
                "the window to raise, over-extend, or make a big new bet.")
            out["_facts"]["season"] = "consolidate"
        elif "expand" in st:
            out["season"]["text"] = (
                "Right now is a build-and-expand phase — the momentum is with you, "
                "so this is the time to push on the thing you're built for, with "
                "discipline, not to sit still.")
            out["_facts"]["season"] = "expand"
        else:
            out["season"]["text"] = (
                "Right now is a steady phase — no need to force a big move; keep "
                "compounding the work that's already yours.")
            out["_facts"]["season"] = "steady"

        # ---- MOVE ----
        primary = edge_domains[0] if edge_domains else None
        if out["_facts"].get("season") == "consolidate":
            out["move"]["text"] = (
                "This quarter: protect and collect first — shore up your cash and "
                "close out what's owed before you build anything new or bring in "
                "outside money.")
        elif primary:
            out["move"]["text"] = (
                f"This quarter: put your next real push into {_DOMAIN_PHRASE.get(primary, primary)} "
                f"— {_DOMAIN_HOW.get(primary, '')}. That's where your effort "
                f"compounds instead of leaking.")
        else:
            out["move"]["text"] = (
                "This quarter: pick the one effort you fully own and go deep on it "
                "rather than spreading thin across new bets.")
        return out
    except Exception:
        # fail-open: return whatever we have (titles always present)
        return out
