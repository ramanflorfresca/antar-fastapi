-- sql_signature_ledger.sql
-- Precision ledger (founder brief 2026-06-11): every signature question
-- asked + its full lock trace + the user's Yes/Close/No. The harness reads
-- this table (--ledger) — it is the living precision measure for the
-- convergence engine, accumulating ground truth chart by chart.
-- Run in the Supabase SQL Editor. Additive only.

create table if not exists signature_question_log (
  question_id   text primary key,          -- sq_ + sha256(chart|event|ws|we)[:16]
  chart_id      uuid not null,
  event_type    text not null,
  window_start  date,
  window_end    date,
  locks         integer,                   -- convergence count 0-3 at ask time
  lock_trace    jsonb,                     -- FULL _debug_reasoning (admin-only data)
  question      text,                      -- EN question as asked
  language      text default 'en',
  engine        text default 'convergence_v1',
  asked_at      timestamptz default now(),
  response      text,                      -- confirmed | close | declined | skipped
  responded_at  timestamptz
);

create index if not exists idx_sqlog_chart on signature_question_log (chart_id);
create index if not exists idx_sqlog_response on signature_question_log (response)
  where response is not null;
create index if not exists idx_sqlog_event on signature_question_log (event_type);

comment on table signature_question_log is
  'Confirm-then-predict precision ledger: one row per question asked; the '
  'user response lands on the same row. Harness --ledger aggregates '
  'precision by locks/event_type. lock_trace is admin-only jargon.';

-- verify:
-- select event_type, locks, response, count(*) from signature_question_log
--  group by 1,2,3 order by 1,2,3;
