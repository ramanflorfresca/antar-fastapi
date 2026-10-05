-- sql_wa_marketing_consent.sql  (2026-10-05) — run once via Lovable (Build mode), like the other sql_*.sql files.
-- Separate, optional, default-OFF opt-in for offers / news on WhatsApp (Meta WhatsApp Business policy,
-- TCPA, India DPDP, Brazil LGPD). The backend links numbers WITHOUT these columns (it retries without
-- them), but nothing marketing can be sent, or recorded, until they exist.

alter table public.messaging_links add column if not exists marketing_opt_in boolean not null default false;
alter table public.messaging_links add column if not exists marketing_opt_in_at timestamptz;
alter table public.messaging_links add column if not exists marketing_consent_version text;
-- alerts already exists; the timestamp may not:
alter table public.messaging_links add column if not exists alerts_opt_in boolean not null default false;
alter table public.messaging_links add column if not exists alerts_opt_in_at timestamptz;
