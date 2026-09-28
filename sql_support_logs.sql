-- support_logs — conversation log behind POST /api/v1/support
--
-- APPLIED 2026-09-28 to Supabase project ovszdbymflpwnynmpgqk. Kept in the repo
-- as the record of what was run. Idempotent: safe to re-run.
--
-- ── Run it in the right place ────────────────────────────────────────────────
-- There is NO Railway Postgres. Railway runs only the web process (Procfile is
-- a single uvicorn line); the app constructs exactly one database client,
-- create_client(SUPABASE_URL, ...) at main.py:583, and every table including
-- this one goes through it. Two attempts at this migration failed by looking
-- elsewhere: once in the separate Supabase project Lovable Cloud provisions for
-- itself, once against a presumed Railway database that does not exist.
--
-- The backend's project is ovszdbymflpwnynmpgqk — confirm with GET /debug/env
-- on production. The verification select at the bottom of this file checks you
-- are in the right project before you trust the result.
--
-- Note the local .env DATABASE_URL has a stale password (psql fails auth), and
-- no exec_sql RPC exists, so this genuinely has to run from the SQL editor:
--   https://supabase.com/dashboard/project/ovszdbymflpwnynmpgqk/sql/new
--
-- ── What it is for ──────────────────────────────────────────────────────────
-- Tuning. The support agent's whole quality lever is the knowledge base in
-- antar_engine/support_agent.py, and the only way to know what is missing from
-- it is to read the questions that came back route = 'unknown'.
--
-- The endpoint FAILS OPEN on a missing table: before this ran, support answered
-- normally and logged nothing.
--
-- What is deliberately NOT stored: no email, no chart_id, no user id, no
-- account identifier. The endpoint is public and unauthenticated, so the
-- question text is the only user-supplied content, and the IP is stored as a
-- salted hash purely so abuse can be counted without holding an address.

CREATE TABLE IF NOT EXISTS public.support_logs (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    question      TEXT        NOT NULL,
    answer        TEXT,
    language      TEXT        NOT NULL DEFAULT 'en',
    -- answer | unknown | billing | offtopic  (see support_agent._VALID_ROUTES)
    route         TEXT,
    -- high | low | n/a | unavailable
    confidence    TEXT,
    latency_ms    INTEGER,
    -- 'llm', or 'fallback' when the model was unreachable and canned copy served
    source        TEXT,
    ip_hash       TEXT
);

-- The tuning query: "what did we fail to answer, most recent first".
CREATE INDEX IF NOT EXISTS support_logs_route_created_idx
    ON public.support_logs (route, created_at DESC);

CREATE INDEX IF NOT EXISTS support_logs_created_idx
    ON public.support_logs (created_at DESC);

-- RLS on with NO policy: every client is denied, the backend's service key
-- bypasses it. Verified after applying — with the anon key, SELECT returns an
-- empty set despite rows existing, and INSERT fails with 42501. The grant is
-- explicit so this does not depend on default privileges.
ALTER TABLE public.support_logs ENABLE ROW LEVEL SECURITY;
GRANT ALL ON public.support_logs TO service_role;

-- Force PostgREST to pick up the new table immediately. Without this the first
-- writes fail with PGRST205 until its schema cache happens to refresh.
NOTIFY pgrst, 'reload schema';

-- Proof, returned by this same run. in_the_right_project must be 1: `charts`
-- exists only in the backend's project, so a 0 there means the SQL editor is
-- pointed at a different Supabase project and nothing above took effect where
-- it matters.
SELECT
  (SELECT count(*) FROM pg_tables
     WHERE schemaname = 'public' AND tablename = 'charts')       AS in_the_right_project,
  (SELECT count(*) FROM pg_tables
     WHERE schemaname = 'public' AND tablename = 'support_logs') AS table_created;
