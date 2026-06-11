-- sql_relocation_split.sql
-- Founder ruling 2026-06-11: major_relocation houses become 12,4,9 with the
-- foreign(12/9, Rahu) vs domestic(4/3, Moon) split (the split itself lives in
-- event_convergence.stage1_promise; this row keeps the config table coherent
-- and drives event_gating + non-convergence consumers).
update event_engine_config
   set houses = '12,4,9'
 where event_type = 'major_relocation';

-- verify:
-- select event_type, houses, karaka from event_engine_config
--  where event_type = 'major_relocation';
