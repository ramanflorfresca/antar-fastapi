-- charts.google_id -> charts.auth_user_id   ·   PHASE 3 of 3 (teardown)
--
-- DO NOT RUN THIS UNTIL BOTH ARE TRUE:
--   1. The backend deploy containing the phase-2 code is live on Railway
--      (check: GET /api/v1/auth/profile/{id} responds, and a sign-in works).
--   2. The frontend has been PUBLISHED from Lovable — not merely merged.
--      Verify at the bundle level, not in preview:
--        curl -s https://antar.world/ | grep -oE '/assets/index-[A-Za-z0-9_-]+\.js'
--      then confirm that file contains "auth_user_id" and that the hash has
--      changed from the build that preceded it.
--
-- Until both have shipped, an older client still queries google_id directly
-- through PostgREST. Dropping the column early breaks sign-in for anyone still
-- on a cached bundle.
--
-- Once this has run, delete the legacy fallbacks left in the code:
--   main.py            request.get("google_id") in link-chart
--                      google_id.eq.{...} in the auth/restore and profile or_()
--   AuthCallback.tsx   google_id.eq.${...} in the two .or() lookups
--   types.ts           the google_id field

-- Safety check: refuse to proceed if any row would lose its identifier.
DO $$
DECLARE orphaned INT;
BEGIN
    SELECT count(*) INTO orphaned
      FROM public.charts
     WHERE google_id IS NOT NULL AND auth_user_id IS NULL;
    IF orphaned > 0 THEN
        RAISE EXCEPTION
          'Refusing to drop google_id: % row(s) have google_id but no auth_user_id. Re-run phase 1.',
          orphaned;
    END IF;
END $$;

-- No-ops unless an early version of phase 1 managed to create these.
DROP TRIGGER IF EXISTS charts_sync_auth_user_id_trg ON public.charts;
DROP FUNCTION IF EXISTS public.charts_sync_auth_user_id();

ALTER TABLE public.charts DROP COLUMN IF EXISTS google_id;

NOTIFY pgrst, 'reload schema';

SELECT
  (SELECT count(*) FROM information_schema.columns
     WHERE table_schema='public' AND table_name='charts'
       AND column_name='google_id')                              AS google_id_remaining,
  (SELECT count(*) FROM public.charts WHERE auth_user_id IS NOT NULL) AS rows_with_auth_user_id;
