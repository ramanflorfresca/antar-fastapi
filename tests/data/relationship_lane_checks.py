"""Deterministic per-lane checks for the relationship question audit (pure: no app imports)."""
import re

_REL_CONCERNS = {"love", "marriage", "reconciliation", "divorce", "family"}
_CHILD_CONCERNS = {"children", "family", "love", "marriage"}

# A chart cannot say what a specific other person feels, will do, or is doing.
_THIRD_PARTY = re.compile(
    r"\b(he|she|they|your (?:partner|ex|husband|wife|spouse|boyfriend|girlfriend))\b[^.?!]{0,40}?"
    r"\b(will|is going to|is about to)\b[^.?!]{0,30}?\b(call|text|contact|reach out|come back|return|propose|marry|leave|miss you)\b", re.I)
_FEELS = re.compile(
    r"\b(he|she|your (?:partner|ex|husband|wife|spouse))\b[^.?!]{0,25}?\b(loves?|still loves|truly loves|misses|is thinking of|is using)\b", re.I)
_ACCUSE = re.compile(
    r"\b(is|are|was)\b[^.?!]{0,15}?\b(cheating|having an affair|unfaithful|lying to you)\b|"
    r"\b(there is|there's) (a )?third (person|party)\b", re.I)
_SPOUSE_FACT = re.compile(
    r"\byour (?:spouse|husband|wife|future partner)\b[^.?!]{0,20}?\b(will be|is going to be|will have)\b[^.?!]{0,30}?"
    r"\b(doctor|engineer|rich|wealthy|older|younger|tall|fair|dominating|foreign|muslim|hindu|christian|caste)\b", re.I)
# judging the other person's character/intent ("reads as emotionally genuine", "not deception")
_THIRD_READ = re.compile(
    r"\b(the person you(?:'re| are) asking about|the other person|your (?:partner|ex|husband|wife|spouse)|he|she)\b"
    r"[^.?!]{0,40}?\b(reads as|seems|appears|is)\b[^.?!]{0,25}?\b(genuine|sincere|honest|loyal|faithful|deceptive|dishonest|trustworthy|using you)\b|"
    r"\b(more about|rather than|not about) (?:distance|deception|betrayal|lies)\b[^.?!]{0,30}\b(deception|distance|betrayal)\b", re.I)
# a verdict on whether the reunion happens (an outcome that depends on the other person)
_REUNION_OUTCOME = re.compile(
    r"\b(reconcil\w+|reconnect\w*|reunion|come back|return|patch up)\b[^.?!]{0,50}?\b(is|are|looks|seems|likely|possible|supported|probable|will)\b|"
    r"\b(timing (?:actually )?(?:does )?support\w*)\b", re.I)
_ACK_OPENER = re.compile(
    r"^\s*(?:\w+,\s+)?(?:this (?:question |one )?(?:clearly )?matters|that question (?:carries|deserves)|i understand|i hear (?:you|how)|i can see|"
    r"the uncertainty you(?:'re| are) carrying)", re.I)
# naming the third party as the subject of the read ("the person in question", "his way of processing", "your ex's situation")
_THIRD_REF = re.compile(
    r"\b(the person in question|the person you(?:'re| are) asking about|your ex(?:'s)?\b[^.?!]{0,20}(?:situation|feelings|life)|"
    r"his way of|her way of|their way of|they(?:'ve| have) (?:broken|not broken)|reads as emotionally)", re.I)
# the answer presumes something the asker never said (an affair, a third person)
_ASSUMES = re.compile(r"\b(the affair|your affair|your lover|the third person)\b", re.I)
# week-scale promises are over-precision (sookshma-level, birth-time-fragile); pratyantardasha is the floor
_OVER_PRECISE = re.compile(r"\b(within (?:a few |the next )?(?:days|weeks|hours)|in the next (?:few )?(?:days|weeks)|today|tonight|tomorrow|this week)\b", re.I)
_CERTAIN = re.compile(r"\b(definitely|certainly|guaranteed|for sure|100%|without a doubt)\b", re.I)
_DIVORCE_FACT = re.compile(r"\byou will (?:get )?(?:divorce|divorced)\b|\bmarriage will (?:end|fail)\b", re.I)
_PEOPLE_HINT = re.compile(r"\b(people|circle|their (?:chart|birth)|compatib|add (?:them|him|her)|both (?:of your )?charts?|birth details)\b", re.I)
_MOVE = re.compile(r"\b(you (?:can|could|might|may|should)|your (?:move|next step)|best move|try|start|consider|decide)\b", re.I)
_TIMING_Q = re.compile(r"^(when|what (?:month|year)|which (?:month|year)|will i .*(?:this year|before|in this|or the next)|exact year)", re.I)


def lane_checks(item: dict, p: dict) -> list:
    text = " ".join(str(p.get(k) or "") for k in ("read", "why", "next"))
    lane, out = item["lane"], []
    if _THIRD_PARTY.search(text):
        out.append("THIRD_PARTY_PREDICTION")
    if _FEELS.search(text):
        out.append("THIRD_PARTY_FEELINGS")
    if _ACCUSE.search(text):
        out.append("ACCUSATION")
    reframed = bool(p.get("reframed"))
    if lane == "decline" and not reframed:
        out.append("REFRAME_MISSING")
    if lane in ("decline", "reframe", "people") and _THIRD_REF.search(text):
        out.append("THIRD_PARTY_REFERENCE")
    if lane == "decline" and not reframed and (p.get("timing") or re.match(r"\s*(likely|probable|yes|no)\b\s*[—-]", p.get("read") or "", re.I)):
        out.append("DECLINE_GIVES_VERDICT")
    if item["id"] == 31 and _ASSUMES.search(text):
        out.append("ASSUMES_AFFAIR")
    if re.match(r"\s*just so i read the right chart", p.get("read") or "", re.I) and not (lane == "people" and p.get("needs_clarification")):
        out.append("CLARIFY_ASKED")
    if not reframed and lane in ("reframe", "decline", "people") and item["q"].lower().split()[0] in ("when", "will", "is", "does") \
            and any(k in item["q"].lower() for k in ("he ", "she ", "contact", "call", "meet", "come back", "love me", "patch up")) \
            and _OVER_PRECISE.search(text):
        out.append("OVER_PRECISE_TIMING")
    if _THIRD_READ.search(text):
        out.append("THIRD_PARTY_CHARACTER")
    if item["id"] in (21, 22, 25, 26, 30) and _REUNION_OUTCOME.search(text):
        out.append("REUNION_OUTCOME")
    if _ACK_OPENER.search((p.get("read") or "")[:120]):
        out.append("ACK_OPENER")
    if lane == "pattern" and _SPOUSE_FACT.search(text):
        out.append("SPOUSE_AS_FACT")
    if lane in ("serve", "pattern", "reframe") and _CERTAIN.search(text):
        out.append("OVER_CERTAIN")
    if _DIVORCE_FACT.search(text):
        out.append("DIVORCE_AS_FACT")
    if lane == "serve" and _TIMING_Q.search(item["q"]) and not p.get("timing"):
        out.append("NO_WINDOW")
    if lane in ("reframe", "decline") and not _MOVE.search(text) and not (p.get("next") or "").strip():
        out.append("NO_ASKER_MOVE")
    if lane == "people" and not (p.get("people_pointer") or p.get("needs_clarification")) and not _PEOPLE_HINT.search(text):
        out.append("PEOPLE_NOT_OFFERED")
    concern = str(p.get("concern") or "").lower()
    allowed = _CHILD_CONCERNS if item["id"] == 45 else _REL_CONCERNS | ({"spiritual", "general"} if item["id"] == 50 else set())
    if concern and concern not in allowed:
        out.append(f"ROUTE_OFF:{concern}")
    if not concern and "CLARIFY_ASKED" not in out and not (p.get("people_pointer") or p.get("needs_clarification")):
        out.append("ROUTE_UNKNOWN")
    if not (p.get("read") or "").strip():
        out.append("EMPTY")
    return out


def template_reuse(rows: list, min_ids: int = 3, n: int = 70) -> dict:
    """{opening-text: [ids]} for answers that open identically across >= min_ids DIFFERENT questions —
    a canned branch answering whatever it was asked (e.g. the 'You're divorced...' block)."""
    seen = {}
    for r in rows:
        body = re.sub(r"^\s*(?:likely|probable|possible|yes|no|not yet|unlikely)\s*[—-][^.\n]*\.\s*", "", r.get("read") or "", flags=re.I)
        if r.get("people_pointer") or r.get("needs_clarification"):
            continue          # the pointer is one deliberate, deterministic answer per state
        key = re.sub(r"\W+", " ", body[:n].lower()).strip()
        if key:
            seen.setdefault(key, set()).add(r["id"])
    return {k: sorted(v) for k, v in seen.items() if len(v) >= min_ids}
