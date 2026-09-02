create table if not exists public.mailbox_waitlist (
  id uuid primary key default gen_random_uuid(),
  email text not null,
  provider text not null,
  created_at timestamptz not null default now(),
  unique (email, provider)
);

create index if not exists idx_mailbox_waitlist_provider
  on public.mailbox_waitlist (provider, created_at desc);

alter table public.mailbox_waitlist enable row level security;

comment on table public.mailbox_waitlist is
  'Avisos cuando el buzón aún no se puede leer (Gmail, Yahoo, iCloud, IMAP empresa).';
