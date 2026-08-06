alter table public.communication_messages
  drop constraint if exists communication_messages_triage_category_check;

alter table public.communication_messages
  add constraint communication_messages_triage_category_check
  check (
    triage_category = any (
      array[
        'unreviewed'::text,
        'action_required'::text,
        'waiting_external'::text,
        'review'::text,
        'notice'::text,
        'informational'::text,
        'automated'::text,
        'promotional'::text,
        'social'::text
      ]
    )
  );

create index if not exists communication_messages_account_triage_received_idx
  on public.communication_messages (account_id, triage_category, received_at desc);
