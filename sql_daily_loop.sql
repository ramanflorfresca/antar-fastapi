-- [daily-loop 2026-10-12] One row per chart per LOCAL day: the 3-step loop (read today's call,
-- do the practice, ask today's question). A streak day is counted when all three are done.
-- Run in the Supabase SQL Editor BEFORE turning the `loop_streak` app_config flag on.
-- The backend fails open when this table is missing (the loop reads as empty, nothing breaks).
create table if not exists daily_loop_log (
  id             uuid primary key default gen_random_uuid(),
  chart_id       uuid not null,
  local_date     date not null,
  read_at        timestamptz,
  practice_at    timestamptz,
  ask_at         timestamptz,
  mantra_count   integer not null default 0,
  completed_at   timestamptz,
  question_id    text,
  question_text  text,
  question_theme text,
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now()
);
create unique index if not exists idx_daily_loop_chart_day on daily_loop_log (chart_id, local_date);
create index if not exists idx_daily_loop_chart_recent on daily_loop_log (chart_id, local_date desc);
