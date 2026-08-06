# Logística 1 · Bloque B

## Objetivo

Este bloque convierte la descarga inicial en operación continua:

- busca cualquier cadena dentro de remitentes, destinatarios, asunto, etiquetas y cuerpo completo;
- agrupa respuestas, responder a todos y reenvíos por tema normalizado;
- ordena conversaciones por la fecha del correo más reciente;
- mantiene separados Correos y Casos;
- clasifica automáticamente el correo nuevo;
- elimina el acceso general a la reclasificación masiva;
- permite reglas dirigidas creadas por el usuario;
- habilita Web Push por dispositivo y abre directamente el correo relacionado;
- actualiza métricas desde la base cada 30 segundos;
- adapta login, descarga, bandeja y modales al alto real del dispositivo.

## Flujo operativo

1. La importación inicial descarga y clasifica una sola vez.
2. El scheduler revisa correo nuevo cada 120 segundos.
3. Las reglas del usuario se aplican primero.
4. El clasificador seguro procesa lo restante.
5. Favoritos y correos accionables generan avisos internos y push.
6. El usuario puede ejecutar una sincronización manual inmediata, pero no una reclasificación masiva.

## Seguridad

- Gmail permanece en solo lectura.
- Las suscripciones push se vinculan al perfil HMS autenticado.
- Las llaves VAPID se guardan fuera de Git en `.hms-secrets/`.
- El emisor Web Push usa las dependencias criptográficas ya incluidas en HMS; no descarga paquetes externos durante la instalación.
- El HTML de los correos se muestra en un iframe sin permisos.
- Aplicar una regla al historial solo modifica mensajes que coinciden con esa regla.
