-- Outcome loop (spec: "Outcome Loop & Accuracy Board — Spec", 2026-10-02).
-- prediction_claims: one row per checkable prediction a person saw.
-- prediction_outcomes: the person's answer. NO default outcome — an absent row
-- means "unanswered", never "didn't happen" (the flaw in user_predictions.fulfilled).
-- Run via Lovable (Lovable Cloud owns Supabase DDL). Backend uses the service role.

create table if not exists public.prediction_claims (
  id               uuid primary key default gen_random_uuid(),
  chart_id         uuid not null references public.charts(id) on delete cascade,
  created_at       timestamptz not null default now(),
  source           text not null,            -- ask_explore | ask_yesno | life_arc | year | decoy
  topic            text not null,
  claim_type       text not null,            -- window | event | yesno
  window_start     date,
  window_end       date not null,
  text_shown       text,
  question         text,
  language         text,
  channel          text,                     -- app | whatsapp
  verdict          text,
  confidence_word  text,
  engines          jsonb not null default '{}'::jsonb,   -- each engine's own verdict/window
  dedupe_key       text not null unique,     -- chart|topic|type|start|end
  checkin_due_at   timestamptz not null,
  checkin_sent_at  timestamptz,
  checkin_channel  text
);
create index if not exists prediction_claims_chart_idx on public.prediction_claims (chart_id);
create index if not exists prediction_claims_due_idx on public.prediction_claims (checkin_due_at)
  where checkin_sent_at is null;

create table if not exists public.prediction_outcomes (
  claim_id      uuid primary key references public.prediction_claims(id) on delete cascade,
  outcome       text not null check (outcome in ('yes', 'partly', 'no', 'not_sure')),
  note          text,
  answered_at   timestamptz not null default now(),
  answered_via  text                          -- app | whatsapp | push
);

alter table public.prediction_claims enable row level security;
alter table public.prediction_outcomes enable row level security;
-- No policies: clients get no direct access; only the backend's service role.
