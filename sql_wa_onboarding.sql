-- sql_wa_onboarding.sql (2026-10-06) — run once via Lovable (Build mode).
-- Conversation state for chat-first onboarding: an unknown WhatsApp number is walked through
-- name → birth date → birth time → birthplace → (optional) current city → confirm, then a phone-only
-- account + chart are created. Until this table exists the feature stays OFF (the unlinked number gets
-- today's "connect in the app" message) — nothing breaks.

create table if not exists public.wa_onboarding (
  number     text primary key,                 -- E.164, e.g. +14155550123
  state      jsonb       not null default '{}'::jsonb,
  status     text        not null default 'open' check (status in ('open', 'done', 'abandoned')),
  user_id    uuid,                             -- phone-only auth user, set once created (retries reuse it)
  chart_id   uuid,
  updated_at timestamptz not null default now()
);
create index if not exists wa_onboarding_status_idx on public.wa_onboarding (status, updated_at desc);

-- service-role only (the backend); no client access
alter table public.wa_onboarding enable row level security;
