-- [desh-kaal-patra P0 2026-07-12] Persist the user's geocoded CURRENT location
-- so sunrise-anchored daily timing isn't geocoded per request.
--
-- Additive + nullable + idempotent (IF NOT EXISTS). Safe to run on production;
-- the backend already reads/writes these best-effort (works before AND after).
-- Run in Supabase SQL editor.

ALTER TABLE charts ADD COLUMN IF NOT EXISTS current_latitude   double precision;
ALTER TABLE charts ADD COLUMN IF NOT EXISTS current_longitude  double precision;
ALTER TABLE charts ADD COLUMN IF NOT EXISTS current_timezone   text;  -- IANA id, e.g. America/Denver
ALTER TABLE charts ADD COLUMN IF NOT EXISTS current_geocode_city text; -- the city these coords were resolved from

-- Optional: index for the backfill's "needs geocoding" scan.
CREATE INDEX IF NOT EXISTS idx_charts_current_geocode_pending
    ON charts (id) WHERE current_city IS NOT NULL AND current_latitude IS NULL;

-- Rollback (if ever needed):
--   ALTER TABLE charts DROP COLUMN IF EXISTS current_latitude, DROP COLUMN IF EXISTS current_longitude,
--     DROP COLUMN IF EXISTS current_timezone, DROP COLUMN IF EXISTS current_geocode_city;
