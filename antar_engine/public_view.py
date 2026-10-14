"""
One voice. Antar speaks as one astrologer: no method names (KP, Jaimini, Vimshottari, Lal Kitab...), no book authors, no rule ids
and no internal line names ever reach a user surface or the public API. The engine's internal blocks keep that detail (it is
how the owner reads and edits rules); the endpoints pass them through these functions unless the request carries X-Admin-Key.
Each shown item gets an opaque `ref`, so a "Did this hold?" answer can be tied back to the rule server-side without revealing it.
Confidence is Antar's own wording: "likely" (the source states the condition outright) or "possible" (interpreted / one signal).
"""
import hashlib
import hmac
import os
from typing import Dict, List, Optional

_SECRET = (os.environ.get("REF_SECRET") or os.environ.get("ADMIN_EXPORT_KEY") or "antar-ref").encode()


def ref_for(rule_id: Optional[str]) -> Optional[str]:
    if not rule_id:
        return None
    return hmac.new(_SECRET, str(rule_id).encode(), hashlib.sha256).hexdigest()[:12]


_index: Optional[Dict[str, str]] = None


def resolve_ref(ref: str) -> Optional[str]:
    """ref -> rule id (library, Roop Chand, combinations). Used when a check-in arrives."""
    global _index
    if _index is None:
        ids = []
        try:
            from antar_engine import book_rules, rc_rules, combo_rules, kp_rules
            ids += ["BK." + r["id"] for r in book_rules.load_rules()]
            ids += [r["id"] for r in rc_rules.load_rules()]
            ids += [r["id"] for r in combo_rules.load_rules()]
            ids += ["BK." + r["id"] for r in kp_rules.load_rules()]
        except Exception:
            pass
        _index = {ref_for(i): i for i in ids}
    return _index.get(ref)


def _conf(item: dict) -> str:
    return "possible" if item.get("tendency") or item.get("clarity") == "inferred" else "likely"


def _item(i: dict, rid_key="rule_id") -> dict:
    out = {"ref": ref_for(i.get(rid_key)), "text": i.get("text"), "confidence": _conf(i)}
    for k in ("start", "end", "label", "days", "do", "timing", "remedy"):
        if i.get(k) is not None:
            out[k] = i[k]
    return out


def _dedupe(items: List[dict], cap: int) -> List[dict]:
    seen, out = set(), []
    for i in items:
        if i["text"] and i["text"] not in seen:
            seen.add(i["text"])
            out.append(i)
    return out[:cap]


def wellness(w: Optional[dict]) -> Optional[dict]:
    if not w:
        return None
    return {"themes": [{"ref": ref_for(t.get("rule_id")), "text": t["text"], "timing": t["timing"], "label": t.get("label"),
                        "remedy": t.get("remedy")} for t in w.get("themes", [])],
            "more": w.get("more", 0), "note": w.get("note")}


def when(wc: Optional[dict]) -> Optional[dict]:
    if not wc:
        return None
    return {"agree": [{"start": w["start"], "end": w["end"], "strength": w["strength"],
                       "peaks": w.get("peaks", [])} for w in wc.get("agree", [])],
            "also": [{"start": w["start"], "end": w["end"]} for w in wc.get("also", [])]}


def week(out: Optional[dict]) -> Optional[dict]:
    if not out:
        return out
    g = (out.get("vimshottari") or {}).get("gochara") or {}
    return {"start": out["start"], "days": out["days"],
            "lean_in": _dedupe([_item(i) for i in out.get("lean_in", [])], 4),
            "watch": [_item(i) for i in out.get("watch", [])],
            "watch_more": len(out.get("watch_more", [])),
            "best_days": g.get("best_days", []), "slow_days": g.get("slow_days", []),
            "wellness": wellness(out.get("wellness"))}


def library(lib: Optional[dict]) -> Optional[dict]:
    """The reading's library block: the two method lines merge into one ordered list."""
    if not lib:
        return lib
    lean = [i for ln in ("vimshottari", "jaimini") for i in lib[ln]["lean_in"]]
    watch = [i for ln in ("vimshottari", "jaimini") for i in lib[ln]["watch"]]
    key = lambda i: i.get("start") or ""
    return {"horizon": lib.get("horizon"),
            "lean_in": _dedupe([_item(i) for i in sorted(lean, key=key)], 4),
            "watch": _dedupe([_item(i) for i in sorted(watch, key=key)], 4),
            "agree": [{"subject": a["subject"], "start": a["start"], "end": a["end"]} for a in lib.get("agree", [])],
            "wellness": wellness(lib.get("wellness"))}


def answer(a: Optional[dict]) -> Optional[dict]:
    """/astrologer answer: text and structured windows only; no rule ids, no periods, no method names."""
    if not a:
        return a
    out = {k: a[k] for k in ("available", "subject", "subject_label", "qword", "language", "headline", "lines", "applicable", "text")
           if k in a}
    out["windows"] = [{k: w[k] for k in ("start", "end", "label", "strength", "strength_label", "headline", "why", "action") if k in w}
                      for w in a.get("windows", [])]
    out["remedies"] = a.get("remedies", [])
    out["when"] = when(a.get("when_combined"))
    out["refs"] = [r for r in dict.fromkeys(ref_for(i) for i in a.get("rules_used", [])) if r][:12]
    for k in ("kp_speculation",):
        if a.get(k) is not None:
            out[k] = a[k]
    return out
