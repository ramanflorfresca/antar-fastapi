"""
upaay_narration.py — serve-time LLM modernization of curated Lal Kitab
upaay (remedy) strings.

Contract (founder decision, 2026-06-04):
  * The curated UPAAY_LIBRARY string is the SOURCE; the LLM only re-voices it
    as a modern action — it never invents a different remedy.
  * Keep the weekday anchor + cadence; replace folk-ritual specifics with
    modern everyday equivalents. Zero astrology vocabulary.
  * Permanent content-keyed cache (upaay_narration_cache): each curated
    string is narrated once per PROMPT_VERSION, ever. Table-missing or any
    LLM/validation failure -> curated original is served unchanged.
  * EN-source only; es/pt ride the existing translation pipelines.
"""
from __future__ import annotations
import hashlib
import json
import re
from typing import Optional

PROMPT_VERSION = "v1"

# ── Static instruction block (byte-stable for KV caching) ────────────────────
MODERNIZE_STATIC = """You modernize one traditional remedial instruction for a global wellness app.

The instruction in the live data is a classical giving/offering practice.
Rewrite it as a MODERN ACTION the reader can do in any country, any culture,
this week. You are re-voicing the SAME practice — never invent a different one.

HARD RULES:
1. Keep: the weekday anchor if present ("On Friday...", "each Saturday"), any
   cadence ("for 7 weeks", "6 Fridays"), and the SPIRIT of the act — giving,
   offering, honoring, repairing, releasing, tangible care.
2. Replace folk-ritual specifics (offerings to animals or insects, burying or
   floating objects, scattering food on earth, temple- or shrine-specific
   acts, ritual substances and pigments) with modern everyday equivalents:
   donating, gifting, feeding a person, acts of service, decluttering,
   anonymous generosity, written amends.
3. ZERO astrology: no planet names, no Sanskrit, no karma/debt mechanics, no
   "the energy of X", no chakras. Describe the action and its human effect.
4. 1-3 sentences, second person, imperative, warm and concrete. Max 65 words.
5. English only. Output STRICT JSON and nothing else: {"action": "..."}

## LIVE DATA
"""

_JARGON_RX = re.compile(
    r"(?i)\b(sun|moon|mars|mercury|jupiter|venus|saturn|rahu|ketu|"
    r"karma|karmic|planet\w*|astrolog\w*|lal\s*kitab|upaay|mantra|yantra|"
    r"chakra\w*|dosha|sanskrit)\b"
)
_DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday",
         "saturday", "sunday")


def build_modernize_system(curated: str) -> str:
    """Static block + the one live string (below the KV split)."""
    return MODERNIZE_STATIC + json.dumps(
        {"instruction": curated}, ensure_ascii=False)


def _extract_json(raw: str) -> Optional[dict]:
    if not isinstance(raw, str):
        return None
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(),
                 flags=re.IGNORECASE)
    s, e = raw.find("{"), raw.rfind("}")
    if s < 0 or e <= s:
        return None
    try:
        return json.loads(raw[s:e + 1])
    except Exception:
        return None


def parse_and_validate_upaay(raw: str, source: str) -> Optional[str]:
    """Strict gate. None -> caller serves the curated original."""
    obj = _extract_json(raw)
    if not isinstance(obj, dict):
        return None
    action = obj.get("action")
    if not isinstance(action, str):
        return None
    action = action.strip()
    if not (30 <= len(action) <= 480):
        return None
    if _JARGON_RX.search(action):
        return None
    # Weekday fidelity: every weekday named in the source must survive.
    src_l, act_l = source.lower(), action.lower()
    for d in _DAYS:
        if d in src_l and d not in act_l:
            return None
    return action


def upaay_fingerprint(planet: str, variant: str, curated: str) -> str:
    sig = f"{PROMPT_VERSION}|{planet}|{variant}|{curated}"
    return hashlib.md5(sig.encode("utf-8")).hexdigest()[:32]


def upaay_cache_read(supabase, key: str) -> Optional[str]:
    try:
        res = supabase.table("upaay_narration_cache").select("action") \
            .eq("cache_key", key).limit(1).execute()
        if res.data and isinstance(res.data[0].get("action"), str):
            return res.data[0]["action"]
    except Exception as e:
        print(f"[upaay-modern] cache read skipped: {e}")
    return None


def upaay_cache_write(supabase, key: str, action: str,
                      planet: str = "", variant: str = "") -> None:
    try:
        supabase.table("upaay_narration_cache").upsert({
            "cache_key": key, "action": action,
            "planet": planet, "variant": variant,
        }, on_conflict="cache_key").execute()
    except Exception as e:
        print(f"[upaay-modern] cache write skipped (table missing?): {e}")
