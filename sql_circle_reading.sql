-- Circle: the joint reading ("Our reading"). One column on the existing circle_sharing table.
-- Run via Lovable / the Supabase SQL editor. Idempotent. Run AFTER sql_circle.sql.
--
-- share_reading = chart_id's own choice, for this one person, to share a joint reading of the two
-- charts. Default OFF. The reading is shown only while BOTH people have it on; either turning it
-- off hides it for both. Nothing is stored about the reading itself (it is recomputed and cached
-- in memory), so there is nothing extra to purge.
--
-- Until this runs the backend fails open: the switch reads as off and the reading is never shown;
-- turning it on answers 503 circle_unavailable. Nothing else in Circle is affected.
alter table public.circle_sharing
  add column if not exists share_reading boolean not null default false;
