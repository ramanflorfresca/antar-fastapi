"""
antar_engine/circle_reading.py - "Our reading": a joint compatibility reading of a Circle pair.

The scoring is the EXISTING compatibility engine (Compatibility.calculate_compatibility +
compatibility_layers.compose_compat_v2, deterministic, no LLM) run on the two REAL charts. This module
holds only the pure parts: the consent state machine and the shaping of the engine output into the
pair-level payload. The consent rule is a SECOND opt-in on top of "Between us" (which promised only
dates and first names): the reading is shown only while BOTH people have it switched on.

State, from one person's side (mine / theirs = has that person switched it on):
  off      neither            -> explainer + my switch
  waiting  only me            -> "Waiting for {name}" (I am never told whether they have looked)
  they_on  only them          -> "{name} turned on the joint reading" + my switch
  on       both               -> the reading
Only a "yes" is ever visible to the other side; nobody can tell a "no" from "has not looked".

The payload carries first names, scores and plain sentences only: no birth details, no planets,
no houses, no chart ids.
"""
from __future__ import annotations

from typing import Optional

from antar_engine import circle_copy as CC

STATES = ("off", "waiting", "they_on", "on")


def state_of(mine: bool, theirs: bool) -> str:
    if mine and theirs:
        return "on"
    if mine:
        return "waiting"
    if theirs:
        return "they_on"
    return "off"


def layer_status(layer: dict) -> str:
    """flows | needs_care | friction - the same three words People uses."""
    if layer.get("passed"):
        return "flows"
    try:
        return "friction" if float(layer.get("score")) < 40 else "needs_care"
    except (TypeError, ValueError):
        return "needs_care"


STATUS_LABEL = {
    "en": {"flows": "Flows", "needs_care": "Needs care", "friction": "Friction"},
    "es": {"flows": "Fluye", "needs_care": "Necesita cuidado", "friction": "Fricción"},
    "pt": {"flows": "Flui", "needs_care": "Precisa de cuidado", "friction": "Atrito"},
    "hinglish": {"flows": "Flows", "needs_care": "Dhyaan chahiye", "friction": "Friction"},
}


def _as_list(v) -> list:
    return [str(x) for x in v] if isinstance(v, (list, tuple)) else ([str(v)] if v else [])


def shape(v2: dict, lang: str = "en") -> dict:
    """The engine's composed result -> the pair-level payload (English text; the route translates)."""
    lang = CC.lang_of(lang)
    labels = CC.pick(STATUS_LABEL, lang)
    layers = []
    for l in v2.get("layers") or []:
        if l.get("applicable") is False:
            continue
        st = layer_status(l)
        layers.append({"key": l.get("layer_key"), "label": l.get("layer_label"), "score": l.get("score"),
                       "status": st, "status_label": labels[st],
                       "headline": l.get("headline"), "detail": l.get("detail")})
    conf = v2.get("confidence") or {}
    tm = v2.get("timing") or {}
    return {
        "score": v2.get("score"), "badge": v2.get("badge"),
        "headline": v2.get("headline"), "summary": v2.get("summary"),
        "layers": layers,
        "watch_points": _as_list(v2.get("watch_points")),
        "catalysts": _as_list(v2.get("catalysts")),
        "confidence": {"level": conf.get("level"), "line": conf.get("line")} if conf else None,
        "timing": {"best_window": tm.get("best_window"), "line": tm.get("line")} if tm else None,
    }


def reason_for(relation: str, people_links) -> str:
    """What the OTHER person is to the viewer -> the compatibility reason key (employee/boss-or-manager keep
    their direction from the viewer's side)."""
    return people_links.relation_to_compat_type(relation)


def symmetrize(v: dict, w: dict, pass_threshold: float, badge_fn) -> dict:
    """The engine reads A->B and B->A slightly differently (63 vs 66 for the same two people), but a
    pair should see ONE set of numbers. `v` is the viewer's own order (its text is kept), `w` the
    swapped order; score and every area's score become the mean of the two (mean is symmetric, so both
    people get identical numbers), and the badge and each area's status are re-derived from those
    means with the engine's own pass threshold. Pure; returns a new dict. Not used for directional
    relations (manager / team member), which are read from each side on purpose."""
    out = dict(v)
    try:
        sc = round((float(v["score"]) + float(w["score"])) / 2)
    except (KeyError, TypeError, ValueError):
        return out
    out["score"] = sc
    try:
        out["badge"] = badge_fn(int(sc))
    except Exception:
        pass
    wl = {l.get("key"): l for l in (w.get("layers") or [])}
    layers = []
    for l in v.get("layers") or []:
        l = dict(l)
        o = wl.get(l.get("key"))
        try:
            if o is not None:
                l["score"] = round((float(l["score"]) + float(o["score"])) / 2)
                l["status"] = layer_status({"passed": l["score"] >= pass_threshold, "score": l["score"]})
                lang_labels = {x: STATUS_LABEL[x] for x in STATUS_LABEL}
                for lang_tbl in lang_labels.values():
                    if l.get("status_label") in lang_tbl.values():
                        l["status_label"] = lang_tbl[l["status"]]
                        break
        except (KeyError, TypeError, ValueError):
            pass
        layers.append(l)
    out["layers"] = layers
    return out
