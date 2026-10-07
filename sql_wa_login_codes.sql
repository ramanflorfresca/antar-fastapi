-- sql_wa_login_codes.sql (2026-10-06) — run once via Lovable (Build mode).
-- "Continue with WhatsApp" sign-in: the web/app asks for a short-lived code, shows it as a QR / button that opens
-- WhatsApp with a pre-typed message, and the browser is signed in once the person taps Send. Codes live 2 minutes,
-- are one-use, and are only redeemable by the browser that holds the secret (stored here as a hash).
-- Until this table exists the endpoint reports unavailable — nothing else is affected.

create table if not exists public.wa_login_codes (
  code         text primary key,                       -- 6 chars, e.g. K7Q2MX
  browser_hash text        not null,                   -- sha256 of the secret only the asking browser holds
  status       text        not null default 'pending' check (status in ('pending', 'approved', 'consumed')),
  number       text,                                   -- E.164 that sent the code
  user_id      uuid,                                   -- the account that number belongs to
  created_at   timestamptz not null default now(),
  approved_at  timestamptz
);
create index if not exists wa_login_codes_created_idx on public.wa_login_codes (created_at);

-- service-role only (the backend); no client access
alter table public.wa_login_codes enable row level security;
