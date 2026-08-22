create table if not exists public.domain_integration_requests (
  id uuid primary key default gen_random_uuid(),
  email text not null,
  domain text not null,
  notified_to text,
  created_at timestamptz not null default now()
);

create index if not exists idx_domain_integration_requests_domain
  on public.domain_integration_requests (domain, created_at desc);

alter table public.domain_integration_requests enable row level security;
