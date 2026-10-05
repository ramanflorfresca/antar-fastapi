-- sql_wa_policy_acceptances.sql  (2026-10-05) — run once via Lovable (Build mode).
-- Append-only evidence of the in-WhatsApp data-policy acceptance ("Para continuar, acepta nuestra política
-- de tratamiento de datos"), required before processing under Colombia's Ley 1581 de 2012, India's DPDP and
-- Brazil's LGPD. Until this table exists the gate fails OPEN (today's behaviour) — nothing is recorded.

create table if not exists public.wa_policy_acceptances (
  id             bigserial primary key,
  number         text        not null,          -- E.164, e.g. +573001112233
  policy_version text        not null,          -- = WA_CONSENT_VERSION at the time
  decision       text        not null check (decision in ('accepted', 'declined')),
  language       text,
  policy_url     text,
  source         text        not null default 'whatsapp',
  created_at     timestamptz not null default now()
);
create index if not exists wa_policy_acceptances_number_idx
  on public.wa_policy_acceptances (number, policy_version, created_at desc);

-- service-role only (the backend); no client access
alter table public.wa_policy_acceptances enable row level security;
