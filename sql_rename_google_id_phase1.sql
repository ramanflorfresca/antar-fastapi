-- charts.google_id -> charts.auth_user_id   ·   PHASE 1 of 3 (additive, safe)
--
-- Run in the Supabase SQL editor for project ovszdbymflpwnynmpgqk:
--   https://supabase.com/dashboard/project/ovszdbymflpwnynmpgqk/sql/new
-- Idempotent. Run this BEFORE deploying the phase-2 code.
--
-- ── Why this is not a plain RENAME COLUMN ────────────────────────────────────
-- The column name is wrong: it holds ANY provider's Supabase auth user id, not
-- a Google id. auth/link-chart writes the same value to user_id and google_id,
-- and auth/restore matches `user_id.eq.{id},google_id.eq.{id}`. The name is the
-- single biggest reason the email sign-in path read as unbuilt.
--
-- But a straight rename breaks live users. The FRONTEND queries this column
-- directly through PostgREST, not only through the API:
--   src/pages/AuthCallback.tsx:170  .from("charts").eq("google_id", ...)
--   src/pages/AuthCallback.tsx:565  .from("charts").eq("google_id", ...)
-- Those are the sign-in fallback lookups. The backend redeploys on Railway in
-- ~2 minutes, but the frontend ships only when someone clicks Publish in
-- Lovable — so a rename opens a window where the published app queries a column
-- that no longer exists, and sign-in fails for real people.
--
-- So: add the new column, keep both in sync with a trigger, migrate the code,
-- then drop the old one in phase 3. At no point does either name stop working.

-- 1. The new column.
ALTER TABLE public.charts
    ADD COLUMN IF NOT EXISTS auth_user_id TEXT;

-- 2. Backfill from the old column.
UPDATE public.charts
   SET auth_user_id = google_id
 WHERE auth_user_id IS DISTINCT FROM google_id
   AND google_id IS NOT NULL;

-- 3. Keep the two in lockstep, in BOTH directions, for as long as both exist.
--    Old code writes google_id; new code writes auth_user_id; either way both
--    columns end up correct, so a row written by one is readable by the other.
CREATE OR REPLACE FUNCTION public.charts_sync_auth_user_id()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF NEW.auth_user_id IS NULL AND NEW.google_id IS NOT NULL THEN
            NEW.auth_user_id := NEW.google_id;
        ELSIF NEW.google_id IS NULL AND NEW.auth_user_id IS NOT NULL THEN
            NEW.google_id := NEW.auth_user_id;
        END IF;
        RETURN NEW;
    END IF;

    -- UPDATE: whichever column actually changed wins.
    IF NEW.auth_user_id IS DISTINCT FROM OLD.auth_user_id THEN
        NEW.google_id := NEW.auth_user_id;
    ELSIF NEW.google_id IS DISTINCT FROM OLD.google_id THEN
        NEW.auth_user_id := NEW.google_id;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS charts_sync_auth_user_id_trg ON public.charts;
CREATE TRIGGER charts_sync_auth_user_id_trg
    BEFORE INSERT OR UPDATE ON public.charts
    FOR EACH ROW EXECUTE FUNCTION public.charts_sync_auth_user_id();

-- 4. auth/restore filters on this column on every sign-in.
CREATE INDEX IF NOT EXISTS charts_auth_user_id_idx
    ON public.charts (auth_user_id);

NOTIFY pgrst, 'reload schema';

-- ── Proof, returned by this same run ────────────────────────────────────────
-- in_the_right_project must be 1: `charts` exists only in the backend's
-- project, so 0 means the SQL editor is pointed somewhere else.
-- mismatched must be 0: every row with a google_id now has a matching
-- auth_user_id.
SELECT
  (SELECT count(*) FROM pg_tables
     WHERE schemaname = 'public' AND tablename = 'charts')              AS in_the_right_project,
  (SELECT count(*) FROM information_schema.columns
     WHERE table_schema = 'public' AND table_name = 'charts'
       AND column_name = 'auth_user_id')                                AS column_added,
  (SELECT count(*) FROM public.charts WHERE google_id IS NOT NULL)      AS rows_with_google_id,
  (SELECT count(*) FROM public.charts
     WHERE google_id IS NOT NULL
       AND auth_user_id IS DISTINCT FROM google_id)                     AS mismatched;
