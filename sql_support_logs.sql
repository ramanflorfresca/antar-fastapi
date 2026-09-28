-- support_logs — conversation log behind POST /api/v1/support
--
-- Run in the Supabase SQL Editor (project rule: schema changes never from
-- Python). Idempotent. The endpoint FAILS OPEN on a missing table: until this
-- runs, support still answers, it just logs nothing.
--
-- What this is for: tuning. The support agent's whole quality lever is the
-- knowledge base in antar_engine/support_agent.py, and the only way to know
-- what is missing from it is to read the questions that came back
-- `route = 'unknown'`.
--
-- What is deliberately NOT stored: no email, no chart_id, no user id, no
-- account identifier. The endpoint is public and unauthenticated, so the
-- question text is the only user-supplied content, and the IP is stored as a
-- salted hash purely so abuse can be counted without holding an address.

CREATE TABLE IF NOT EXISTS support_logs (
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
    -- 'fallback' when the model was unreachable and canned copy was served
    source        TEXT,
    ip_hash       TEXT
);

-- The tuning query: "what did we fail to answer, most recent first".
CREATE INDEX IF NOT EXISTS support_logs_route_created_idx
    ON support_logs (route, created_at DESC);

CREATE INDEX IF NOT EXISTS support_logs_created_idx
    ON support_logs (created_at DESC);

-- Service-role writes only. No anon/authenticated policy is created, so RLS
-- denies every client read and write; the backend uses the service key and
-- bypasses RLS.
ALTER TABLE support_logs ENABLE ROW LEVEL SECURITY;
