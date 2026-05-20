"""
antar_engine/translation_cache.py

Loc-4 — per-(endpoint, chart, language, content_hash) translation cache.
Backed by the Supabase `translation_cache` table (see loc4_translation_cache.sql).

The Supabase client is created lazily so importing this module can never fail
at startup (a missing env var would only surface on first cache use, where it
is caught and treated as a cache miss).
"""

import logging
import os

logger = logging.getLogger(__name__)

_supabase = None


def _get_supabase():
    """Lazily create a Supabase client. Reused across calls."""
    global _supabase
    if _supabase is None:
        from supabase import create_client
        _supabase = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            or os.getenv("SUPABASE_KEY")
            or os.getenv("SUPABASE_ANON_KEY"),
        )
    return _supabase


async def get_cached_translation(endpoint_name, chart_id, language, content_hash):
    """
    Return the cached translated-strings dict for this key, or None on miss.
    Any error is swallowed and treated as a miss — translation still works,
    it just doesn't get served from cache.
    """
    try:
        sb = _get_supabase()
        q = (
            sb.table("translation_cache")
            .select("id, translated_data")
            .eq("endpoint_name", endpoint_name)
            .eq("language", language)
            .eq("content_hash", content_hash)
        )
        if chart_id:
            q = q.eq("chart_id", chart_id)
        else:
            q = q.is_("chart_id", "null")
        resp = q.execute()
        if resp.data:
            row = resp.data[0]
            # Touch last_accessed_at for later LRU cleanup — non-fatal.
            try:
                sb.table("translation_cache").update(
                    {"last_accessed_at": "now()"}
                ).eq("id", row["id"]).execute()
            except Exception:
                pass
            return row["translated_data"]
    except Exception as e:
        logger.warning(f"[translation-cache] read failed (treating as miss): {e}")
    return None


async def save_translation(endpoint_name, chart_id, language, content_hash, translated_data):
    """
    Upsert a translated-strings dict into the cache. Non-fatal on failure —
    the translation already succeeded, it just didn't get cached.
    """
    try:
        sb = _get_supabase()
        sb.table("translation_cache").upsert(
            {
                "endpoint_name": endpoint_name,
                "chart_id": chart_id,
                "language": language,
                "content_hash": content_hash,
                "translated_data": translated_data,
            },
            on_conflict="endpoint_name,chart_id,language,content_hash",
        ).execute()
    except Exception as e:
        logger.warning(f"[translation-cache] save failed (non-fatal): {e}")
