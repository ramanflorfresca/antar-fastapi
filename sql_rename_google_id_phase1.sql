-- charts.google_id -> charts.auth_user_id   ·   PHASE 1 of 3 (additive)
--
-- Run in the Supabase SQL editor for project ovszdbymflpwnynmpgqk:
--   https://supabase.com/dashboard/project/ovszdbymflpwnynmpgqk/sql/new
-- Idempotent. Must run BEFORE the phase-2 backend deploys.
--
-- ── Why this is not a plain RENAME COLUMN ────────────────────────────────────
-- The column name is wrong: it holds ANY provider's Supabase auth user id, not
-- a Google id. But the FRONTEND reads this column directly through PostgREST
-- (AuthCallback.tsx, the sign-in fallback lookups), and the frontend ships only
-- on a manual Lovable Publish while Railway redeploys in ~2 minutes. They never
-- change together, so a rename would take sign-in down in between. Add first,
-- migrate the code, drop later.
--
-- ── Why there is no sync trigger any more ────────────────────────────────────
-- The first version of this file created a BEFORE INSERT/UPDATE trigger to keep
-- the two columns in step. The Supabase SQL editor runs a script as ONE
-- transaction, and CREATE TRIGGER on `charts` needs table ownership the
-- dashboard role may not have — so the trigger failed and took the ALTER down
-- with it in the rollback, leaving the column silently absent.
--
-- It was never needed. Nothing writes google_id directly to the database:
--   - the backend writes user_id + auth_user_id + google_id explicitly
--   - the frontend only READS the column; the only column it writes direct is
--     user_id
--   - an unpublished frontend still sends the legacy `google_id` KEY in the
--     link-chart request BODY, and the backend maps it to auth_user_id
-- so both columns stay correct without a trigger. Three plain statements below,
-- each of which can stand on its own.

-- 1. The new column.
ALTER TABLE public.charts
    ADD COLUMN IF NOT EXISTS auth_user_id TEXT;

-- 2. Backfill from the old column.
UPDATE public.charts
   SET auth_user_id = google_id
 WHERE google_id IS NOT NULL
   AND auth_user_id IS DISTINCT FROM google_id;

-- 3. auth/restore filters on this column on every sign-in.
CREATE INDEX IF NOT EXISTS charts_auth_user_id_idx
    ON public.charts (auth_user_id);

NOTIFY pgrst, 'reload schema';

-- ── Proof, returned by this same run ────────────────────────────────────────
-- Want: in_the_right_project = 1, column_added = 1, rows_with_google_id > 0,
-- backfill_gaps = 0.
SELECT
  (SELECT count(*) FROM pg_tables
     WHERE schemaname = 'public' AND tablename = 'charts')          AS in_the_right_project,
  (SELECT count(*) FROM information_schema.columns
     WHERE table_schema = 'public' AND table_name = 'charts'
       AND column_name = 'auth_user_id')                            AS column_added,
  (SELECT count(*) FROM public.charts WHERE google_id IS NOT NULL)  AS rows_with_google_id,
  (SELECT count(*) FROM public.charts
     WHERE google_id IS NOT NULL AND auth_user_id IS NULL)          AS backfill_gaps;
