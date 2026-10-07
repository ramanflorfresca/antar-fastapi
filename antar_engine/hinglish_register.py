"""
antar_engine/hinglish_register.py — Hinglish answers always use the respectful 'aap' register.

[hinglish-aap 2026-10-06] Owner: Antar speaks like a respected astrologer — 'aap', never 'tu' / 'tum'.
Live: "Tera partnership potential strong hai … kya tum genuinely ready ho?", "Is hafte apne aap mein
invest kar". The narrator is told to use 'aap'; this is the deterministic backstop. It only rewrites the
informal pronouns, their possessives, and the common informal imperatives — never ordinary words.
"""
from __future__ import annotations

import re

# pronouns and possessives (whole words, any case; first letter case is preserved)
_PRONOUNS = (
    (r"tumhara|tera", "aapka"), (r"tumhari|teri", "aapki"), (r"tumhare|tere", "aapke"),
    (r"tumhe|tumhein|tumko|tujhe|tujhko", "aapko"), (r"tumse|tujhse", "aapse"),
    (r"tum|tu", "aap"),
)
# informal imperatives → polite ('-iye')
_IMPERATIVES = {
    "karo": "kijiye", "likho": "likhiye", "dekho": "dekhiye", "socho": "sochiye", "bolo": "boliye",
    "pucho": "poochiye", "poocho": "poochiye", "rakho": "rakhiye", "banao": "banaiye", "chuno": "chuniye",
    "milo": "miliye", "jao": "jaiye", "batao": "bataiye", "suno": "suniye", "padho": "padhiye",
    "chalo": "chaliye", "ruko": "rukiye", "bhejo": "bhejiye", "lagao": "lagaiye", "nikalo": "nikaliye",
    "bachao": "bachaiye", "sambhalo": "sambhaliye", "uthao": "uthaiye", "badhao": "badhaiye",
}
# a bare 'kar' / 'rakh' / 'dekh' at the end of a clause is an informal command ("invest kar —")
_BARE = {"kar": "kijiye", "rakh": "rakhiye", "dekh": "dekhiye", "likh": "likhiye", "soch": "sochiye",
         "bol": "boliye", "puch": "poochiye", "bhej": "bhejiye"}


def _case(src: str, rep: str) -> str:
    return rep[:1].upper() + rep[1:] if src[:1].isupper() else rep


def to_aap(text):
    if not isinstance(text, str) or not text.strip():
        return text
    out = text
    for pat, rep in _PRONOUNS:
        out = re.sub(rf"\b(?:{pat})\b", lambda m, r=rep: _case(m.group(0), r), out, flags=re.IGNORECASE)
    for w, rep in _IMPERATIVES.items():
        out = re.sub(rf"\b{w}\b", lambda m, r=rep: _case(m.group(0), r), out, flags=re.IGNORECASE)
    for w, rep in _BARE.items():
        out = re.sub(rf"\b{w}\b(?=\s*(?:[—–\-.,!?;:]|$))", lambda m, r=rep: _case(m.group(0), r), out,
                     flags=re.IGNORECASE)
    # verb agreement with 'aap': "aap … ho" → "aap … hain", "aap … hai" → "aap … hain" (same clause)
    out = re.sub(r"(?i)\b(aap\b[^.!?,;]{0,40}?\b)(ho|hai)\b(?=\s*[.!?,;]|\s*$)", lambda m: m.group(1) + "hain", out)
    return out
