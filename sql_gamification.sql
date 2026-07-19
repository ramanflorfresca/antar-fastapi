-- [gamification] Server-authoritative streaks + earned Ask/compat credits.
-- Run in the Supabase SQL Editor BEFORE deploying.
--
-- IMPORTANT: user_streaks ALREADY EXISTS and holds live rows written by the
-- frontend hook (src/hooks/useStreak.ts). This migration EXTENDS it rather
-- than replacing it, so the existing streak widget keeps working and simply
-- becomes accurate. Nothing here drops or rewrites existing data.
--
-- Why the backend takes over ownership:
--   * The frontend hook treats localStorage as the source of truth and only
--     mirrors to the DB — so a new device resets a 30-day streak to 1.
--   * It keys days off UTC (toISOString), so an evening user in Bogota rolls
--     over early and loses days they were actually active.
--   * Its milestones [7,14,30,60,100] award nothing; they're a toast.
-- Server-side, days are the user's LOCAL day (tz_offset, same convention as
-- ask_usage.ask_count_date) and milestones pay real credits.

-- ── 1. Extend the existing streak table ──────────────────────────────────
alter table user_streaks add column if not exists total_days_active integer not null default 0;
alter table user_streaks add column if not exists freeze_available  boolean not null default true;
alter table user_streaks add column if not exists freeze_last_reset date;
alter table user_streaks add column if not exists freeze_last_used  date;

-- The frontend upserts on user_id and reads with .single(), which both assume
-- uniqueness. Enforce it so a race can't create two rows for one user.
create unique index if not exists idx_user_streaks_user on user_streaks (user_id);

-- ── 2. Earned credits ────────────────────────────────────────────────────
-- A ledger, not a counter: every award is auditable ("why do I have 7?"), and
-- a unique award_key makes grants idempotent — the same milestone cannot pay
-- twice however many times the endpoint is called.
create table if not exists reward_ledger (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null,
  chart_id     uuid,                   -- provenance only; balance is per user
  kind         text not null,          -- 'ask' | 'compat'
  delta        integer not null,       -- >0 grant, <0 spend
  reason       text not null,          -- 'streak_7', 'monthly_compat_2026_07', 'spend'
  award_key    text,                   -- stable key for idempotent grants
  expires_at   timestamptz,            -- null = never
  created_at   timestamptz not null default now()
);
create unique index if not exists idx_reward_award_key
  on reward_ledger (user_id, kind, award_key) where award_key is not null;
create index if not exists idx_reward_balance
  on reward_ledger (user_id, kind, expires_at);
