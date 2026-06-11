-- sql_event_promise_floor.sql
-- Founder ruling 2026-06-11: parent-loss events are promise-exempt.
-- PURELY ADDITIVE. Run in the Supabase SQL Editor.
-- promise_floor semantics: NULL = engine default (2.0); 0 = promise-exempt
-- (Stage-1 never skips); any other value = per-event floor.

ALTER TABLE event_engine_config
  ADD COLUMN IF NOT EXISTS promise_floor NUMERIC DEFAULT NULL;

UPDATE event_engine_config
   SET promise_floor = 0
 WHERE event_type IN ('loss_of_father', 'loss_of_mother');
