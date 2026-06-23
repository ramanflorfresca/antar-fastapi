"""
ask_intent.py — Haiku intent classifier for /ask (shadow-first).

Replaces brittle keyword/regex intent detection with a Haiku classify step
WITHOUT putting the LLM anywhere near the verdict. Haiku picks the route
(domain + houses + is_decision); the deterministic engines still compute
verdict and timing.

Modes (env INTENT_CLASSIFIER_MODE):
    off     — keyword path only, no Haiku call, no logging
    shadow  — (default) Haiku classifies + logs in the BACKGROUND;
              the keyword result drives the live answer. Zero latency,
              zero user-facing change.
    primary — Haiku result drives (awaited inline, tight timeout);
              keyword path is the fallback on any failure.

Product constraint (founder decision 2026-06): /ask mode (yesno vs explore)
is chosen by the CLIENT TOGGLE only. Haiku's `mode` field is logged for
analysis but NEVER routes, in either classifier mode.

classify_intent() never raises into the request path.
"""
from antar_engine.constants import HAIKU_MODEL

import os
import re
import json
import asyncio
import logging
from typing import Optional

logger = logging.getLogger("antar.ask_intent")

# Canonical taxonomy — Haiku chooses from this menu, never invents values.
# Houses are ALWAYS derived from DOMAIN_HOUSE_MAP (single source of truth);
# Haiku's own house list is kept only as a log/tiebreaker field.
INTENT_DOMAINS = [
    "career", "finance", "funding", "business", "relationship", "health",
    "legal", "property", "children", "travel", "education", "purpose",
    "general",
]

# prashna-domain → detect_concern taxonomy (for the explore branch, which
# keys diagnostics/convergence off the concern classifier, not detect_domain).
DOMAIN_TO_CONCERN = {
    "career": "career", "business": "career",
    "finance": "finance", "funding": "funding",
    "relationship": "relationship", "health": "health",
    "legal": "legal", "property": "property",
    "children": "children", "travel": "foreign",
    "education": "education", "purpose": "spiritual",
    "general": "general",
}

_MODE_ENV = "INTENT_CLASSIFIER_MODE"          # off | shadow | primary
_MODEL_ENV = "INTENT_CLASSIFIER_MODEL"
_DEFAULT_MODEL = HAIKU_MODEL
_MIN_CONFIDENCE = float(os.getenv("INTENT_MIN_CONFIDENCE", "0.55"))
_TIMEOUT_S = float(os.getenv("INTENT_CLASSIFIER_TIMEOUT_S", "4.0"))
_CACHE_TABLE = "intent_classify_log"

_SYSTEM_PROMPT = (
    "You classify a user's question for a life-guidance app. Reply with STRICT "
    "JSON only — no prose, no markdown, no code fences:\n"
    '{"mode": "yesno" or "explore", "is_decision": true or false, '
    '"domain": "<one value from the menu>", "houses": [], "confidence": 0.0-1.0}\n'
    "domain menu (choose EXACTLY one, never invent a value): "
    + ", ".join(INTENT_DOMAINS) + ".\n"
    "Definitions: mode=yesno when the question expects a binary answer "
    "(will/should/can X happen). is_decision=true when the user wants a "
    "verdict, a decision, or a timing window (when will...). domain = the "
    "life area the question is REALLY about; funding = raising investment/"
    "loans/equity; business = running/starting a venture; purpose = life "
    "direction/meaning; use general ONLY when no listed domain fits.\n"
    "The question may be in English, Spanish, or Portuguese — classify the "
    "MEANING regardless of language. confidence = your certainty in the "
    "domain choice. JSON only."
)

_anthropic_client = None


def _get_client():
    global _anthropic_client
    if _anthropic_client is None:
        from anthropic import AsyncAnthropic
        _anthropic_client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _anthropic_client


def classifier_mode() -> str:
    m = (os.getenv(_MODE_ENV) or "shadow").strip().lower()
    return m if m in ("off", "shadow", "primary") else "shadow"


def intent_concern(domain: Optional[str]) -> Optional[str]:
    """Map a classified prashna domain to the detect_concern taxonomy."""
    return DOMAIN_TO_CONCERN.get(domain or "")


def normalize_question(question: str) -> str:
    q = (question or "").strip().lower()
    q = re.sub(r"[?!¿¡.]+$", "", q)
    return re.sub(r"\s+", " ", q)[:500]


# ───────────────────────── keyword baseline ─────────────────────────

def keyword_classify(question: str) -> dict:
    """The existing deterministic classifiers — fallback AND shadow baseline."""
    domain, houses = "general", [10]
    is_decision = False
    kw_mode = "explore"
    try:
        from antar_engine.prashna_engine import detect_domain, detect_prashna_intent
        domain, houses = detect_domain(question)
        kw_mode = "yesno" if detect_prashna_intent(question) else "explore"
    except Exception as e:
        logger.warning(f"[intent] keyword detect_domain failed: {e}")
    try:
        from antar_engine.ask_consultation import is_decision_question
        is_decision = bool(is_decision_question(question))
    except Exception as e:
        logger.warning(f"[intent] keyword is_decision failed: {e}")
    if isinstance(houses, int):                      # legacy int-valued maps
        houses = [houses]
    return {"mode": kw_mode, "domain": domain, "houses": list(houses or [10]),
            "is_decision": is_decision}


# ───────────────────────── haiku call ─────────────────────────

def _parse_haiku(raw: str) -> Optional[dict]:
    """Strict-parse + taxonomy-validate. Any deviation → None (fall back)."""
    try:
        raw = (raw or "").strip()
        obj = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
        domain = str(obj.get("domain") or "").strip().lower()
        if domain not in INTENT_DOMAINS:
            return None
        mode = str(obj.get("mode") or "").strip().lower()
        if mode not in ("yesno", "explore"):
            return None
        conf = float(obj.get("confidence") or 0.0)
        houses_raw = obj.get("houses")
        houses = ([int(h) for h in houses_raw if isinstance(h, (int, float))]
                  if isinstance(houses_raw, list) else [])
        return {"mode": mode, "domain": domain,
                "is_decision": bool(obj.get("is_decision")),
                "confidence": max(0.0, min(1.0, conf)),
                "houses": houses}
    except Exception:
        return None


async def _haiku_classify(question: str, language: str) -> dict:
    """Returns {'result': dict|None, 'fallback_reason': str|None}."""
    try:
        client = _get_client()
        resp = await asyncio.wait_for(
            client.messages.create(
                model=os.getenv(_MODEL_ENV, _DEFAULT_MODEL),
                max_tokens=150,
                temperature=0,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content":
                           f"[lang={language or 'en'}] {question}"}],
            ),
            timeout=_TIMEOUT_S,
        )
        raw = "".join(b.text for b in resp.content if getattr(b, "text", None))
        parsed = _parse_haiku(raw)
        if parsed is None:
            return {"result": None, "fallback_reason": "parse_or_taxonomy"}
        if parsed["confidence"] < _MIN_CONFIDENCE:
            return {"result": parsed, "fallback_reason": "low_confidence"}
        return {"result": parsed, "fallback_reason": None}
    except asyncio.TimeoutError:
        return {"result": None, "fallback_reason": "timeout"}
    except Exception as e:
        return {"result": None, "fallback_reason": f"api_error:{type(e).__name__}"}


# ───────────────────────── cache + log ─────────────────────────

def _cache_lookup(supabase, chart_id: str, q_norm: str) -> Optional[dict]:
    """Reuse a prior Haiku classification for the same (chart, question)."""
    try:
        r = supabase.table(_CACHE_TABLE) \
            .select("haiku_mode, haiku_domain, haiku_is_decision, haiku_confidence, haiku_houses") \
            .eq("chart_id", chart_id).eq("question_norm", q_norm) \
            .not_.is_("haiku_domain", "null") \
            .order("created_at", desc=True).limit(1).execute()
        if r.data:
            row = r.data[0]
            return {"mode": row.get("haiku_mode"),
                    "domain": row.get("haiku_domain"),
                    "is_decision": bool(row.get("haiku_is_decision")),
                    "confidence": float(row.get("haiku_confidence") or 0.0),
                    "houses": row.get("haiku_houses") or []}
    except Exception as e:
        logger.warning(f"[intent] cache lookup failed (non-fatal): {e}")
    return None


def _log_row(supabase, row: dict) -> None:
    try:
        supabase.table(_CACHE_TABLE).insert(row).execute()
    except Exception as e:
        # Table may not exist yet — structured log is the fallback record.
        logger.warning(f"[intent] log insert failed (non-fatal): {e}")
    print(f"[intent] surface={row.get('surface')} src={row.get('active_source')} "
          f"kw={row.get('keyword_domain')}/{row.get('keyword_is_decision')} "
          f"haiku={row.get('haiku_domain')}/{row.get('haiku_is_decision')}"
          f"@{row.get('haiku_confidence')} agree={row.get('agree')} "
          f"fallback={row.get('fallback_reason')} cached={row.get('cached')}")


def _build_log(chart_id, surface, question, q_norm, language,
               kw, hk, agree, active_source, fallback_reason, cached) -> dict:
    return {
        "chart_id": chart_id, "surface": surface,
        "question": (question or "")[:1000], "question_norm": q_norm,
        "language": language or "en",
        "haiku_mode": (hk or {}).get("mode"),
        "haiku_domain": (hk or {}).get("domain"),
        "haiku_houses": (hk or {}).get("houses"),
        "haiku_is_decision": (hk or {}).get("is_decision"),
        "haiku_confidence": (hk or {}).get("confidence"),
        "keyword_mode": kw.get("mode"),
        "keyword_domain": kw.get("domain"),
        "keyword_is_decision": kw.get("is_decision"),
        "agree": agree, "active_source": active_source,
        "fallback_reason": fallback_reason, "cached": cached,
    }


def _domains_agree(hk: Optional[dict], kw: dict) -> Optional[bool]:
    """Keyword domains are raw map keys (fund, promotion, surgery...) while
    Haiku speaks the canonical taxonomy (funding, career, health...) — so
    agreement is judged on the routed HOUSE SET, not the label, plus
    is_decision. Same houses = same route = agree."""
    if hk is None:
        return None
    try:
        from antar_engine.prashna_engine import DOMAIN_HOUSE_MAP
        _hh = DOMAIN_HOUSE_MAP.get(hk["domain"], [10])
        hk_houses = set(_hh) if isinstance(_hh, list) else {_hh}
        kw_houses = set(kw.get("houses") or [10])
        return (hk_houses == kw_houses
                and bool(hk["is_decision"]) == bool(kw["is_decision"]))
    except Exception:
        return hk["domain"] == kw.get("domain")


# ───────────────────────── public entry point ─────────────────────────

async def classify_intent(question: str, language: str = "en",
                          chart_id: Optional[str] = None,
                          supabase=None, surface: str = "ask") -> dict:
    """
    Single owner of the route decision. NEVER raises into the request.

    Returns the ACTIVE route:
      {domain, houses, is_decision, active_source: "keyword"|"haiku",
       agree, fallback_reason, haiku, keyword}
    shadow mode → keyword drives, Haiku runs+logs in the background.
    primary mode → Haiku drives (awaited), keyword is the fallback.
    """
    kw = keyword_classify(question)
    base = {"domain": kw["domain"], "houses": kw["houses"],
            "is_decision": kw["is_decision"], "active_source": "keyword",
            "agree": None, "fallback_reason": None, "haiku": None, "keyword": kw}

    mode = classifier_mode()
    if mode == "off":
        return base

    q_norm = normalize_question(question)

    async def _run_haiku():
        cached = False
        hk, reason = None, None
        if supabase is not None and chart_id:
            hk = _cache_lookup(supabase, chart_id, q_norm)
            cached = hk is not None
        if hk is None:
            out = await _haiku_classify(question, language)
            hk, reason = out["result"], out["fallback_reason"]
        elif hk.get("confidence", 0.0) < _MIN_CONFIDENCE:
            reason = "low_confidence"
        agree = _domains_agree(hk, kw)
        return hk, reason, agree, cached

    if mode == "shadow":
        # Fire-and-forget: zero latency added, keyword drives the answer.
        async def _shadow_task():
            try:
                hk, reason, agree, cached = await _run_haiku()
                if supabase is not None:
                    _log_row(supabase, _build_log(
                        chart_id, surface, question, q_norm, language,
                        kw, hk, agree, "keyword", reason, cached))
            except Exception as e:
                logger.warning(f"[intent] shadow task failed (non-fatal): {e}")
        try:
            asyncio.get_running_loop().create_task(_shadow_task())
        except RuntimeError:
            pass  # no loop (sync test context) — skip shadow logging
        return base

    # ── primary ──
    try:
        hk, reason, agree, cached = await _run_haiku()
        usable = hk is not None and reason is None
        result = dict(base)
        if usable:
            from antar_engine.prashna_engine import DOMAIN_HOUSE_MAP
            houses = DOMAIN_HOUSE_MAP.get(hk["domain"], [10])
            result.update({
                "domain": hk["domain"],
                "houses": list(houses) if isinstance(houses, list) else [houses],
                "is_decision": hk["is_decision"],
                "active_source": "haiku",
            })
        result.update({"agree": agree, "fallback_reason": reason, "haiku": hk})
        if supabase is not None:
            _log_row(supabase, _build_log(
                chart_id, surface, question, q_norm, language, kw, hk, agree,
                result["active_source"], reason, cached))
        return result
    except Exception as e:
        logger.warning(f"[intent] primary path failed, keyword fallback: {e}")
        base["fallback_reason"] = f"internal:{type(e).__name__}"
        return base
