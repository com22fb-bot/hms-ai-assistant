-- Email-first: Continuar consulta si ya hay cuenta Donexto.
-- Solo devuelve boolean; no expone uid ni metadatos.
-- SECURITY DEFINER lee auth.users; anon no puede SELECT directo ahí.

create or replace function public.donexto_account_exists(lookup_email text)
returns boolean
language sql
stable
security definer
set search_path = auth, public
as $$
  select exists (
    select 1
    from auth.users u
    where u.email is not null
      and lower(u.email) = lower(trim(lookup_email))
  );
$$;

comment on function public.donexto_account_exists(text) is
  'True si ya existe una cuenta Donexto con ese correo. Usado en el login email-first.';

revoke all on function public.donexto_account_exists(text) from public;
grant execute on function public.donexto_account_exists(text) to anon, authenticated;
