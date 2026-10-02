-- WhatsApp conversation state per linked number (last numbered list, language,
-- once-a-day limit notice). Lives on the link row because Railway runs several
-- workers that don't share memory. Run via Lovable. Backend fails open without it.
alter table public.messaging_links
  add column if not exists context jsonb not null default '{}'::jsonb;
