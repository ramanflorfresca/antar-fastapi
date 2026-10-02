-- WhatsApp: conversation state + recorded consent on each link row. Run via Lovable.
--
-- context: last numbered list, language, once-a-day limit notice. Lives on the row
--   because Railway runs several workers that don't share memory (fail-open without it).
-- consent_*: the user's opt-in to WhatsApp messages + Terms/Privacy acceptance,
--   recorded BEFORE a number can be linked. The backend refuses to link without it,
--   so WhatsApp linking stays off until these columns exist.
alter table public.messaging_links
  add column if not exists context         jsonb not null default '{}'::jsonb,
  add column if not exists consent_at      timestamptz,
  add column if not exists consent_version text,
  add column if not exists consent_source  text;   -- 'app' | 'wa_signin'

-- Event alerts on WhatsApp (upcoming windows, chapter changes, did-it-happen):
-- a SEPARATE opt-in from Ask, default off, never implied by linking.
alter table public.messaging_links
  add column if not exists alerts_opt_in    boolean not null default false,
  add column if not exists alerts_opt_in_at timestamptz;
