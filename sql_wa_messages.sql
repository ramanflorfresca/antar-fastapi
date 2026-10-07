-- [wa-log 2026-10-06] Every WhatsApp message, both directions — the conversation record that
-- product-quality review and (only with training consent) model training are built from.
-- Run in Lovable (Build mode). Until it exists, antar_engine/wa_log.py fails open (stdout only).
create table if not exists public.wa_messages (
  id              uuid primary key default gen_random_uuid(),
  created_at      timestamptz not null default now(),
  direction       text not null check (direction in ('in', 'out')),
  wa_number       text not null,            -- the user's number (E.164); purged with the chart
  sender_number   text,                     -- which Antar business number carried it
  chart_id        uuid references public.charts(id) on delete cascade,
  message_sid     text,                     -- Twilio MessageSid (inbound) / outbound sid
  kind            text not null default 'text',   -- text | list | template | media | location | button
  template        text,                     -- antar_* template name when kind = template
  body            text,
  lang            text,
  country         text,
  consent_version text,                     -- the link's consent wording when this was written
  meta            jsonb not null default '{}'::jsonb   -- topic / subject / intent / engine / media type...
);
create index if not exists wa_messages_chart_idx  on public.wa_messages (chart_id, created_at desc);
create index if not exists wa_messages_number_idx on public.wa_messages (wa_number, created_at desc);
create index if not exists wa_messages_sid_idx    on public.wa_messages (message_sid);
alter table public.wa_messages enable row level security;
-- No policies: backend service role only.
