-- Preferencias del tablero Núcleo IA y reglas de alerta por usuario.
-- El backend escribe con service role. Con la sesión del usuario, RLS
-- limita cada fila a profile_id = auth.uid().
-- Las suscripciones push siguen en push_subscriptions (secretos de Web Push
-- solo los lee el backend). Aquí solo se agregan plataforma e idioma.

alter table public.push_subscriptions
  add column if not exists platform text,
  add column if not exists locale text;

comment on column public.push_subscriptions.platform is
  'Plataforma detectada al suscribir: ios, android, macos, windows, linux.';
comment on column public.push_subscriptions.locale is
  'Idioma de la interfaz al suscribir (es, en, fr, it, pt).';

create table if not exists public.donexto_preferences (
  profile_id uuid primary key references public.profiles(id) on delete cascade,
  workspace_id uuid references public.workspaces(id) on delete set null,
  preferences jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now(),
  constraint chk_donexto_preferences_object
    check (jsonb_typeof(preferences) = 'object')
);

create table if not exists public.donexto_alert_rules (
  profile_id uuid not null references public.profiles(id) on delete cascade,
  rule_id text not null,
  workspace_id uuid references public.workspaces(id) on delete set null,
  kind text not null check (kind in ('sender', 'case_type', 'subject', 'concept')),
  value text not null,
  enabled boolean not null default true,
  area text,
  updated_at timestamptz not null default now(),
  primary key (profile_id, rule_id)
);

create index if not exists idx_donexto_alert_rules_profile
  on public.donexto_alert_rules (profile_id, enabled);

alter table public.donexto_preferences enable row level security;
alter table public.donexto_alert_rules enable row level security;

revoke all on table public.donexto_preferences from anon;
revoke all on table public.donexto_alert_rules from anon;
grant select, insert, update, delete on table public.donexto_preferences to authenticated;
grant select, insert, update, delete on table public.donexto_alert_rules to authenticated;
grant all on table public.donexto_preferences to service_role;
grant all on table public.donexto_alert_rules to service_role;

drop policy if exists donexto_preferences_own on public.donexto_preferences;
create policy donexto_preferences_own
  on public.donexto_preferences
  for all
  to authenticated
  using (profile_id = auth.uid())
  with check (profile_id = auth.uid());

drop policy if exists donexto_alert_rules_own on public.donexto_alert_rules;
create policy donexto_alert_rules_own
  on public.donexto_alert_rules
  for all
  to authenticated
  using (profile_id = auth.uid())
  with check (profile_id = auth.uid());

comment on table public.donexto_preferences is
  'Tema, accesibilidad, sonido y reglas del tablero Núcleo IA por usuario.';
comment on table public.donexto_alert_rules is
  'Copia consultable de las reglas de alerta (remitente, tipo, asunto, concepto).';
