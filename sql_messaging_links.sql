-- messaging_links: chat-channel identity for /ask over Telegram and WhatsApp.
-- One row per link attempt. channel_user_id = Telegram user id, or the WhatsApp
-- number in E.164 (+919812345678). status: pending → linked | expired | revoked.
-- Run via Lovable (Lovable Cloud owns Supabase DDL). Backend uses the service role.
create table if not exists public.messaging_links (
  id              uuid primary key default gen_random_uuid(),
  chart_id        uuid not null references public.charts(id) on delete cascade,
  user_id         uuid,
  channel         text not null check (channel in ('telegram', 'whatsapp')),
  channel_user_id text,
  link_code       text,
  status          text not null default 'pending'
                  check (status in ('pending', 'linked', 'expired', 'revoked')),
  created_at      timestamptz not null default now(),
  linked_at       timestamptz
);

create unique index if not exists messaging_links_code_uq
  on public.messaging_links (link_code) where link_code is not null;

-- One active link per number, and per account, per channel.
create unique index if not exists messaging_links_active_number_uq
  on public.messaging_links (channel, channel_user_id) where status = 'linked';
create unique index if not exists messaging_links_active_user_uq
  on public.messaging_links (channel, user_id) where status = 'linked' and user_id is not null;

alter table public.messaging_links enable row level security;
-- No policies: clients get no access; only the backend's service role reads/writes.
