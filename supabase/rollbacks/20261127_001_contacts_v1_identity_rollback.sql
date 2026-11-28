-- Rollback de 20261127_001_contacts_v1_identity.sql (CONTACTS_V1 F1).
-- Solo elimina objetos NUEVOS de esa migración. Las tablas son derivadas
-- (reconstruibles) salvo own_address_aliases con status confirmed/rejected:
-- exportarlas antes si ya contienen decisiones del usuario.
drop table if exists public.own_address_aliases;
drop table if exists public.contact_addresses;
drop table if exists public.message_participants;
drop function if exists public.contacts_v1_participant_guard();
