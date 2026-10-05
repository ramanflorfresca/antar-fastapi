-- saved_decisions — the user's own list of decisions they are waiting on.
-- [saved-decisions 2026-10-05]
--
-- WHY THIS IS NOT prediction_claims: a claim is something ANTAR said, recorded
-- silently so the engine can be scored. A saved decision is something the USER
-- chose to keep. That difference is the whole point — it changes what the app
-- takes in, not just what it puts out. Keeping them in one table would collapse
-- the distinction the moment someone wrote a query.
--
-- Run this in the Supabase SQL editor before deploying the backend.

create extension if not exists "pgcrypto";

create table if not exists public.saved_decisions (
  id                     uuid primary key default gen_random_uuid(),
  chart_id               uuid not null references public.charts(id) on delete cascade,
  claim_id               uuid references public.prediction_claims(id) on delete set null,

  question               text not null,
  verdict                text,
  timing_label           text,
  window_start           date,
  window_end             date,
  note                   text,
  language               text not null default 'en',

  -- window-OPEN reminder (the check-in in prediction_claims fires at window END)
  open_reminder_due_at   timestamptz,
  open_reminder_sent_at  timestamptz,
  open_reminder_channel  text,

  archived_at            timestamptz,
  created_at             timestamptz not null default now(),
  updated_at             timestamptz not null default now()
);

-- one live save per question per chart; re-saving updates instead of duplicating
create unique index if not exists saved_decisions_chart_question_uniq
  on public.saved_decisions (chart_id, md5(lower(question)))
  where archived_at is null;

create index if not exists saved_decisions_chart_idx
  on public.saved_decisions (chart_id, created_at desc);

-- the hourly job's only query: due, not yet sent
create index if not exists saved_decisions_open_due_idx
  on public.saved_decisions (open_reminder_due_at)
  where open_reminder_sent_at is null and archived_at is null;

alter table public.saved_decisions enable row level security;

-- owner-only, mirroring the existing chart-scoped policies
drop policy if exists saved_decisions_owner_rw on public.saved_decisions;
create policy saved_decisions_owner_rw on public.saved_decisions
  for all
  using (public.is_chart_owner(chart_id))
  with check (public.is_chart_owner(chart_id));

comment on table public.saved_decisions is
  'Decisions the USER chose to keep and be reminded about. Distinct from prediction_claims, which is what Antar said.';
