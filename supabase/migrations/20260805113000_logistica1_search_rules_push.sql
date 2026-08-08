create extension if not exists unaccent;

create table if not exists public.message_classification_rules (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  account_id uuid not null references public.communication_accounts(id) on delete cascade,
  profile_id uuid not null references public.profiles(id) on delete cascade,
  source_message_id uuid references public.communication_messages(id) on delete set null,
  name text not null,
  match_type text not null check (
    match_type in (
      'sender',
      'sender_domain',
      'subject_contains',
      'body_contains',
      'sender_subject'
    )
  ),
  match_value text not null,
  secondary_value text,
  target_category text not null check (
    target_category in (
      'action_required',
      'review',
      'notice',
      'social',
      'promotional',
      'automated',
      'informational'
    )
  ),
  notify_push boolean not null default false,
  is_active boolean not null default true,
  priority integer not null default 100,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_message_classification_rules_account
  on public.message_classification_rules(account_id, is_active, priority, created_at);

create table if not exists public.push_subscriptions (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  profile_id uuid not null references public.profiles(id) on delete cascade,
  endpoint text not null,
  p256dh text not null,
  auth_secret text not null,
  user_agent text,
  device_label text,
  is_active boolean not null default true,
  last_seen_at timestamptz not null default now(),
  last_success_at timestamptz,
  last_error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(profile_id, endpoint)
);

create index if not exists idx_push_subscriptions_profile_active
  on public.push_subscriptions(profile_id, is_active);

create table if not exists public.hms_notifications (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  account_id uuid references public.communication_accounts(id) on delete cascade,
  profile_id uuid not null references public.profiles(id) on delete cascade,
  notification_type text not null,
  title text not null,
  body text not null,
  url text not null default '/',
  message_id uuid references public.communication_messages(id) on delete cascade,
  case_id uuid references public.intelligent_cases(id) on delete cascade,
  dedupe_key text not null,
  pushed_at timestamptz,
  read_at timestamptz,
  created_at timestamptz not null default now(),
  unique(profile_id, dedupe_key)
);

create index if not exists idx_hms_notifications_profile_unread
  on public.hms_notifications(profile_id, read_at, created_at desc);

create table if not exists public.push_delivery_log (
  id uuid primary key default gen_random_uuid(),
  notification_id uuid references public.hms_notifications(id) on delete cascade,
  subscription_id uuid references public.push_subscriptions(id) on delete set null,
  status text not null check (status in ('sent', 'failed', 'expired', 'skipped')),
  http_status integer,
  error_text text,
  created_at timestamptz not null default now()
);

alter table public.communication_messages
  add column if not exists classification_rule_id uuid
    references public.message_classification_rules(id) on delete set null,
  add column if not exists push_notified_at timestamptz;

alter table public.message_classification_rules enable row level security;
alter table public.push_subscriptions enable row level security;
alter table public.hms_notifications enable row level security;
alter table public.push_delivery_log enable row level security;

revoke all on public.message_classification_rules from anon, authenticated;
revoke all on public.push_subscriptions from anon, authenticated;
revoke all on public.hms_notifications from anon, authenticated;
revoke all on public.push_delivery_log from anon, authenticated;

create or replace function public.hms_mail_threads(
  p_account_id uuid,
  p_profile_id uuid,
  p_search text default null,
  p_triage_category text default null,
  p_direction text default null,
  p_favorites_only boolean default false,
  p_limit integer default 40,
  p_offset integer default 0
)
returns table (
  conversation_key text,
  latest_message_id uuid,
  message_count bigint,
  unread_count bigint,
  latest_received_at timestamptz,
  sender text,
  recipients jsonb,
  subject text,
  normalized_subject text,
  summary text,
  triage_category text,
  direction text,
  has_attachments boolean,
  favorite boolean,
  participants text,
  total_count bigint
)
language sql
security definer
set search_path = public, extensions
as $$
with base as (
  select
    m.*,
    coalesce(
      case
        when nullif(btrim(m.normalized_subject), '') is not null
          then 'subject:' || lower(btrim(m.normalized_subject))
      end,
      case
        when nullif(
          btrim(
            regexp_replace(
              lower(coalesce(m.subject, '')),
              '^\\s*((re|rv|fw|fwd)\\s*:\\s*)+',
              '',
              'i'
            )
          ),
          ''
        ) is not null
          then 'subject:' || btrim(
            regexp_replace(
              lower(coalesce(m.subject, '')),
              '^\\s*((re|rv|fw|fwd)\\s*:\\s*)+',
              '',
              'i'
            )
          )
      end,
      case when m.thread_id is not null then 'thread:' || m.thread_id::text end,
      'message:' || m.id::text
    ) as conv_key,
    unaccent(
      lower(
        concat_ws(
          ' ',
          m.sender,
          m.recipients::text,
          m.cc::text,
          m.bcc::text,
          m.subject,
          m.snippet,
          m.body_text,
          m.labels::text,
          m.normalized_subject
        )
      )
    ) as search_blob
  from public.communication_messages m
  where m.account_id = p_account_id
    and (p_triage_category is null or m.triage_category = p_triage_category)
    and (p_direction is null or m.direction = p_direction)
),
matching_keys as (
  select distinct b.conv_key
  from base b
  where (
    p_search is null
    or btrim(p_search) = ''
    or b.search_blob like '%' || unaccent(lower(btrim(p_search))) || '%'
  )
  and (
    not p_favorites_only
    or exists (
      select 1
      from public.message_watch_rules r
      join base source_message
        on source_message.id = r.source_message_id
      where r.profile_id = p_profile_id
        and r.account_id = p_account_id
        and r.is_active = true
        and source_message.conv_key = b.conv_key
    )
  )
),
stats as (
  select
    b.conv_key,
    count(*)::bigint as message_count,
    count(*) filter (where b.is_unread)::bigint as unread_count,
    max(b.received_at) as latest_received_at,
    bool_or(coalesce(b.has_attachments, false)) as has_attachments,
    string_agg(distinct coalesce(nullif(b.sender, ''), 'Sin remitente'), ' · ') as participants
  from base b
  join matching_keys k on k.conv_key = b.conv_key
  group by b.conv_key
),
latest as (
  select distinct on (b.conv_key)
    b.conv_key,
    b.id,
    b.received_at,
    b.sender,
    b.recipients,
    b.subject,
    b.normalized_subject,
    regexp_replace(
      coalesce(nullif(b.snippet, ''), nullif(b.body_text, ''), 'Sin contenido disponible.'),
      '\\s+',
      ' ',
      'g'
    ) as summary,
    b.triage_category,
    b.direction
  from base b
  join matching_keys k on k.conv_key = b.conv_key
  order by b.conv_key, b.received_at desc nulls last, b.created_at desc, b.id desc
),
combined as (
  select
    l.conv_key,
    l.id as latest_message_id,
    s.message_count,
    s.unread_count,
    s.latest_received_at,
    l.sender,
    l.recipients,
    l.subject,
    l.normalized_subject,
    left(l.summary, 360) as summary,
    l.triage_category,
    l.direction,
    s.has_attachments,
    exists (
      select 1
      from public.message_watch_rules r
      join base source_message
        on source_message.id = r.source_message_id
      where r.profile_id = p_profile_id
        and r.account_id = p_account_id
        and r.is_active = true
        and source_message.conv_key = l.conv_key
    ) as favorite,
    s.participants
  from latest l
  join stats s on s.conv_key = l.conv_key
)
select
  c.conv_key,
  c.latest_message_id,
  c.message_count,
  c.unread_count,
  c.latest_received_at,
  c.sender,
  c.recipients,
  c.subject,
  c.normalized_subject,
  c.summary,
  c.triage_category,
  c.direction,
  c.has_attachments,
  c.favorite,
  c.participants,
  count(*) over()::bigint as total_count
from combined c
order by c.latest_received_at desc nulls last, c.latest_message_id desc
limit greatest(1, least(coalesce(p_limit, 40), 100))
offset greatest(coalesce(p_offset, 0), 0);
$$;

revoke all on function public.hms_mail_threads(
  uuid, uuid, text, text, text, boolean, integer, integer
) from anon, authenticated;
