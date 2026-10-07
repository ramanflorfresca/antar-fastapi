-- sql_wa_training_consent.sql (2026-10-06) — run once via Lovable (Build mode).
-- Separate, optional, default-OFF opt-in: may Antar learn from this person's DE-IDENTIFIED WhatsApp
-- conversations to improve its own model. Linking works without these columns; nothing is ever
-- exported for training until they exist AND the person said yes (messaging.can_train).
alter table public.messaging_links add column if not exists training_opt_in boolean not null default false;
alter table public.messaging_links add column if not exists training_opt_in_at timestamptz;
alter table public.messaging_links add column if not exists training_consent_version text;
