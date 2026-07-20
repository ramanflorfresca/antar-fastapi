-- [birth-time-confidence 2026-07-20] Capture how accurate the user's birth time is.
--
-- Every house-based claim rests on the ascendant, which moves a sign roughly
-- every two hours. Until now a time typed as "around noon" was stored exactly
-- like a birth-certificate time, so the engine could not tell a chart it should
-- trust from one it should hedge.
--
-- Values (validated app-side in antar_engine/birth_time_confidence.py):
--   'exact'       - from a birth certificate or hospital record
--   'approximate' - family memory, "around noon"
--   'unknown'     - genuinely no idea
--   NULL          - not yet asked. NULL is NOT "exact": the engine treats an
--                   unanswered question as its own risk state, so a knife-edge
--                   chart still gets flagged rather than silently trusted.
--
-- Nothing breaks before this lands. The cusp margin is a property of the chart
-- alone, so the engine already works; this column only sharpens it.

alter table charts
  add column if not exists birth_time_accuracy text;

alter table charts
  drop constraint if exists charts_birth_time_accuracy_chk;

alter table charts
  add constraint charts_birth_time_accuracy_chk
  check (birth_time_accuracy is null
         or birth_time_accuracy in ('exact', 'approximate', 'unknown'));

comment on column charts.birth_time_accuracy is
  'How accurate the birth time is: exact | approximate | unknown. NULL = not asked. Drives house-claim confidence; see antar_engine/birth_time_confidence.py.';

-- Partial index: the engine only ever filters for rows that need rectification
-- prompting, which is the NULL / non-exact set.
create index if not exists idx_charts_birth_time_accuracy
  on charts (birth_time_accuracy)
  where birth_time_accuracy is distinct from 'exact';
