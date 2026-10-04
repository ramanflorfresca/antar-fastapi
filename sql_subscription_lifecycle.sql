-- sql_subscription_lifecycle.sql  (2026-10-04)  — run once via Lovable (Build mode), like the other sql_*.sql files.
-- OPTIONAL columns for the billing lifecycle. The backend works WITHOUT them (it retries the write without
-- these columns if they are missing), but the app can only show "cancels on …" / "payment failed" once they exist.

alter table public.subscriptions add column if not exists cancel_at_period_end boolean not null default false;
alter table public.subscriptions add column if not exists canceled_at timestamptz;
alter table public.subscriptions add column if not exists provider_customer_id text;     -- Stripe cus_… / Razorpay customer
alter table public.subscriptions add column if not exists last_payment_status text;      -- paid | failed | refunded | disputed | stripe_unpaid …
alter table public.subscriptions add column if not exists last_event_at timestamptz;

create index if not exists subscriptions_provider_sub_id_idx on public.subscriptions (provider_sub_id);
create index if not exists subscriptions_provider_customer_id_idx on public.subscriptions (provider_customer_id);
