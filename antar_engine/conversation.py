"""
antar_engine/conversation.py — turn a message into a turn in a conversation.

[conversation-layer 2026-10-02] Two gaps seen live on WhatsApp (they apply to the
app's Ask too):

  1. A follow-up ("How about tomorrow", "and money?", "y mañana?") reached every
     engine as a fragment. Concern inheritance patched routing, but the intent
     classifier, KP, follow-up chips and the integrity gate all saw "How about
     tomorrow" and logged it 'general'. Fix: rewrite a likely follow-up into a
     standalone question ("How is speculation for me tomorrow?") with one small
     verified model call, BEFORE Ask routes it. History keeps what was typed.

  2. The narrator never saw its own previous advice, so "protect your savings"
     came back every turn. Fix: hand it the recent moves with a no-repeat rule.

Pure helpers; main.py owns the model call. Fail-open everywhere: on any doubt
the original question is used unchanged.
"""
from __future__ import annotations

import json
import re
from typing import Optional

FOLLOWUP_WINDOW_MIN = 60          # only resolve against a turn from the last hour
_MAX_WORDS = 9

_OPENERS = (
    # EN
    "how about", "what about", "and ", "also", "then ", "so ", "but ", "what if",
    "same for", "why", "how come", "really", "is that", "and if", "or ",
    # ES / PT
    "y ", "¿y ", "y si", "entonces", "pero ", "qué tal", "que tal", "¿qué tal",
    "e ", "e se", "então", "mas ", "e quanto", "e o ", "e a ",
    # Hinglish
    "aur ", "toh ", "to ", "phir ", "lekin ", "kya woh", "aur agar",
)
_REFERENTS = re.compile(
    r"(?i)\b(it|that|this|those|these|then|there|same|again|tomorrow|tonight|"
    r"next (week|month|year)|after that|eso|esto|eso|ahí|mañana|isso|isto|amanhã|"
    r"woh|ye|yeh|kal|uske|iske)\b")
_STOP = frozenset("""
how about what and also then so but if the a an is are for me my of to in on it
that this y e o que el la los las de para mi como qué cómo e o a os as de do da
para meu minha aur toh kya hai ka ki ke
""".split())


def looks_like_followup(text: str, thread: list) -> bool:
    """Cheap gate before spending a model call: a short message, right after a
    recent turn, that opens like a follow-up or leans on a referent."""
    if not thread or not isinstance(text, str):
        return False
    t = text.strip().lower()
    words = re.findall(r"[\w'¿]+", t)
    if not words or len(words) > _MAX_WORDS:
        return False
    if t.startswith(_OPENERS):
        return True
    if _REFERENTS.search(t):
        return True
    return len(words) <= 3


REWRITE_SYSTEM = (
    "You rewrite a short follow-up message into ONE standalone question, using "
    "the recent conversation for what it refers to.\n"
    "Rules:\n"
    "- Keep the person's language (English, Spanish, Portuguese or Hinglish) "
    "and their own words wherever possible.\n"
    "- Only fill in what the follow-up leaves implicit (the topic, the person, "
    "the timeframe). Never add new topics, facts, dates or advice.\n"
    "- If the message is NOT a follow-up (a new topic, or complete on its own), "
    "return it unchanged with type \"new\".\n"
    "- Write it as the person would ask it, first person (\"How is speculation "
    "for me tomorrow?\").\n"
    'Output JSON only: {"type": "follow_up" | "new", "standalone": "..."}'
)


def rewrite_request(text: str, thread: list, language: str) -> str:
    turns = [{"user_asked": t.get("q", ""), "antar_answered": (t.get("a") or "")[:240]}
             for t in (thread or [])[-2:]]
    return json.dumps({"language": language, "recent_conversation": turns,
                       "new_message": text}, ensure_ascii=False)


def _content_words(s: str) -> set:
    return {w for w in re.findall(r"[\w']+", (s or "").lower()) if w not in _STOP and len(w) > 2}


def parse_rewrite(raw: Optional[str], original: str) -> Optional[str]:
    """The standalone question, or None (keep the original). Guards: valid JSON,
    marked follow_up, a sane length, and it must keep the person's own content
    words (so a rewrite can't swap the question for a different one)."""
    if not raw or "{" not in raw:
        return None
    try:
        got = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
    except Exception:
        return None
    if not isinstance(got, dict) or got.get("type") != "follow_up":
        return None
    s = (got.get("standalone") or "").strip()
    if not s or len(s) > 220 or s.lower() == (original or "").strip().lower():
        return None
    mine = _content_words(original)
    if mine and len(mine & _content_words(s)) < max(1, (len(mine) + 1) // 2):
        return None
    return s


def moves_block(thread: list) -> str:
    """Narrator instruction listing the moves already given this conversation."""
    moves = []
    for t in (thread or [])[-3:]:
        m = (t.get("m") or "").strip()
        if m and m not in moves:
            moves.append(m)
    if not moves:
        return ""
    lines = "\n".join(f"- {m}" for m in moves)
    return ("\n\n## ALREADY ADVISED IN THIS CONVERSATION\n" + lines +
            "\nDo NOT repeat these moves or restate their wording. If the same caution "
            "still applies, say so in a few words and give a DIFFERENT, more specific "
            "next step that builds on it — or a step that fits this question's timeframe.")
