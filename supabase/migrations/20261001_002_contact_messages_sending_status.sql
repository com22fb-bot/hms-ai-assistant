-- Estado intermedio para reservar el envío antes de llamar a Resend.
-- Así un doble clic no puede mandar el correo dos veces.
-- Corre después de 20261001_001_contact_messages.sql.

alter table public.contact_messages
  drop constraint if exists contact_messages_status_check;

alter table public.contact_messages
  add constraint contact_messages_status_check
  check (
    status in (
      'nuevo',
      'borrador listo',
      'enviando',
      'respondido',
      'archivado'
    )
  );
