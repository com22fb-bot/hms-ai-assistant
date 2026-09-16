# Verificación explícita del buzón — pendiente #64

Estado: implementación para revisión; no desplegar hasta probar el remitente.

## Comportamiento

Microsoft/OAuth autentica la cuenta, pero no habilita el dashboard. Se envía un enlace al correo de la sesión, que debe coincidir con el buzón conectado. La API también bloquea la consulta de mensajes, importación, casos y dashboard mientras falte esta prueba.

El enlace incluye un secreto aleatorio de 256 bits en el fragmento de la URL (no en la ruta enviada al proxy). Se conserva únicamente su hash en app_metadata de Supabase Auth, junto al correo y la caducidad de 30 minutos. El servidor valida la sesión y el enlace antes de escribir la confirmación. El enlace usado se invalida; un reenvío reemplaza el anterior. El reenvío tiene una espera de 60 segundos por cuenta. No se confía en user_metadata, en el indicador histórico donexto_verified ni en un parámetro donexto_verify=1.

La prueba es por buzón, no por cada login. Las cuentas existentes, incluso con OAuth, deberán verificar una vez. Cambiar el correo invalida la coincidencia de la prueba. No hay migraciones ni actualización masiva de usuarios. El envío y la confirmación sí escriben metadatos de autenticación cuando se usan en producción.

## Configuración requerida antes de activar

En Railway, configurar un remitente transaccional autorizado:

- DONEXTO_SMTP_HOST
- DONEXTO_SMTP_PORT: 587 (STARTTLS obligatorio) o 465 (TLS)
- DONEXTO_SMTP_FROM: dirección remitente autorizada
- DONEXTO_SMTP_USER y DONEXTO_SMTP_PASSWORD si el proveedor exige autenticación

No guardar contraseñas en GitHub. No se usa el fallback público de FormSubmit ni se envían los enlaces a servicios de formularios. Las variables conocidas del entorno no incluyen este SMTP; su configuración y la entrega real siguen pendientes. Esta implementación requiere un proveedor SMTP transaccional que permita el envío; no presume acceso SMTP a Hotmail por contraseña.

## Puerta de despliegue

1. Conservar la configuración actual y confirmar acceso de recuperación. Respaldo de código: backup/pre-fase-0-2026-09-15, commit b61edeca58afa9de150aface21f31e624f30b517. Worker actual identificado por el usuario: e018192a-2b71-438c-80bc-b6578f61f822. Los valores secretos y los datos no tienen una copia integral verificada.
2. Probar envío desde el remitente autorizado y la recepción del enlace en un buzón de prueba autorizado. No activar el bloqueo antes de confirmar entrega.
3. Validar en un entorno de prueba el login Microsoft, la pantalla pendiente, enlace expirado, enlace de otra cuenta, reenvío y desbloqueo. Probar también el enlace en otro navegador: debe solicitar iniciar sesión con el mismo correo.
4. Coordinar despliegue de frontend y backend. El frontend previo no entiende la nueva prueba; no dejar versiones mezcladas. No fusionar este PR hasta que ambos despliegues estén preparados y la entrega haya sido validada.
5. Confirmar que no se consulta /messages antes de verificar y que después de confirmar el dashboard funciona. No habilitar mutaciones generales ni cambiar los permisos OAuth como parte de este cambio.

## Pruebas automatizadas

- Backend: PYTHONPATH=backend pytest -q backend/tests/test_mailbox_verification.py
- Frontend: desde frontend, node --experimental-strip-types --test lib/mailboxVerification.test.ts
- Tipos: desde frontend, ./node_modules/.bin/tsc --noEmit

Las pruebas del backend usan un administrador Auth y un remitente simulados. No acreditan entrega real ni modifican producción. Concurrencia: reenvíos simultáneos pueden producir un enlace reemplazado; el servidor solo acepta el hash que permanezca guardado. La comprobación y escritura de metadatos no es una transacción CAS, por lo que confirmaciones simultáneas del mismo enlace pueden ser idempotentes; no otorgan acceso a otra cuenta. Para límites estrictos distribuidos, usar almacenamiento transaccional en una ampliación posterior.
