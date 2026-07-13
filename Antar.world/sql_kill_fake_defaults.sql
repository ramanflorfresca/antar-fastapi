-- [kill-fake-defaults 2026-07-13] Make unanswered profile fields honest.
--
-- Today ~all charts store a blanket default that LOOKS like a real answer:
--   career_stage='mid_career' (213/214), children_status='no_children_unsure'
--   (212/214), marital_status='unknown' (211/214). The engine then personalizes
--   on facts it never had. The backend now normalizes these to "unknown" at
--   read-time, but this cleans the stored data + stops future column defaults.
--
-- Run in the Supabase SQL editor. Safe: only touches the blanket defaults.

-- 1) Stop the column from silently filling a default on new inserts.
ALTER TABLE charts ALTER COLUMN career_stage      DROP DEFAULT;
ALTER TABLE charts ALTER COLUMN children_status   DROP DEFAULT;
ALTER TABLE charts ALTER COLUMN marital_status    DROP DEFAULT;

-- 2) Reset the blanket-default values to NULL (= honestly unanswered).
--    Real answers (entrepreneur, has_children, married, single, no_children...)
--    are NOT touched — only the exact default sentinels.
UPDATE charts SET career_stage    = NULL WHERE career_stage    = 'mid_career';
UPDATE charts SET children_status = NULL WHERE children_status = 'no_children_unsure';
UPDATE charts SET marital_status  = NULL WHERE marital_status  = 'unknown';

-- After onboarding is updated to actually ASK (see LOVABLE_BRIEF_profile_onboarding.md),
-- these fields fill with real values and personalization can be *positively*
-- specific instead of guessing.
