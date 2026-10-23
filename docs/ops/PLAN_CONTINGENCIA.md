# Plan de contingencia por servicio — Donexto

Fecha: 22 oct 2026 (hora CDMX). Documento vivo: se actualiza tras cada incidente (ver Bitácora en /admin).

**Reglas de este plan**
- Aquí solo aparecen **nombres** de claves, nunca sus valores.
- Todas las claves viven en **Doppler, proyecto `donexto`, entorno `prd`** (41 claves). Copia de emergencia de `BACKUP_PASSPHRASE` y `OAUTH_ENCRYPTION_KEY` en la memoria SD de recuperación.
- **No se crea ningún servicio de pago sin el visto bueno de Héctor.**
- Cualquier borrado en producción requiere lista y confirmación de Héctor.

## Cómo nos enteramos de una caída (para todos los servicios)
1. **Monitor cada 15 minutos** (GitHub Actions `uptime.yml`) → aviso por correo y Slack.
2. **Bitácora en /admin** → cada caída queda registrada como evento abierto/resuelto.
3. **Alertas de respaldo** → si el respaldo diario falla, aviso a Slack y por correo.
4. Páginas de estado oficiales: status.railway.com, cloudflarestatus.com, status.supabase.com, githubstatus.com, status.doppler.com, slack-status.com.

---

## 1. Railway — la API (api.donexto.com)
- **Qué se rompe para los usuarios:** la app abre, pero no carga correos, no conecta buzones ni sincroniza. El inicio de sesión puede fallar en pasos que pasan por la API.
- **Cómo lo detectamos:** el monitor de 15 min revisa la API; Bitácora; status.railway.com.
- **Pasos inmediatos:**
  1. Confirmar en status.railway.com si es caída general (como la del 21–22 oct).
  2. Si es general: no tocar nada, registrar el evento en la Bitácora y avisar a Héctor.
  3. Si es solo nuestro servicio: revisar el último despliegue y volver al anterior desde Railway.
  4. Si dura más de unas horas: activar el plan B (abajo), con OK de Héctor.
- **Claves que necesitamos:** `RAILWAY_API_TOKEN` (Doppler; regenerado el 22 oct tras el incidente de Railway).
- **Plan B:** volver a desplegar la misma API en otro proveedor con el mismo código del repositorio y las mismas variables de Doppler, y cambiar `api.donexto.com` en Cloudflare DNS hacia el nuevo servidor.
  - Gratis: Render (plan gratis, se “duerme” sin uso), Fly.io (cuota pequeña), Koyeb (plan gratis).
  - De pago: Railway Pro, Render de pago, Fly.io de pago. **Requiere OK de Héctor.**
  - Ver “Ruta de despliegue alterna” más abajo.

## 2. Cloudflare — app, landing, DNS y respaldos
- **Qué se rompe:**
  - **Workers (`donexto-app`, app.donexto.com y /admin):** la app no abre.
  - **Pages (www.donexto.com):** la página principal no abre.
  - **DNS:** nada de Donexto abre (ni la API, aunque Railway funcione).
  - **R2:** los usuarios no notan nada; solo fallan los respaldos nuevos.
- **Cómo lo detectamos:** monitor de 15 min; cloudflarestatus.com; falla del paso “deploy” en GitHub Actions.
- **Pasos inmediatos:** confirmar si es caída general; si es un despliegue nuestro, volver a la versión anterior del Worker desde el panel de Cloudflare; si es R2, guardar el respaldo del día también en Drive (Donexto/Backups, cifrado).
- **Claves:** `CLOUDFLARE_API_TOKEN` (vence 10 oct 2027), `CLOUDFLARE_ANALYTICS_TOKEN` (vence 10 oct 2027), `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_ZONE_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY` (Doppler y secretos de GitHub).
- **Plan B:**
  - App y landing: se pueden publicar en Netlify o Vercel (planes gratis) y apuntar el dominio allí.
  - DNS: el dominio puede moverse a otro DNS (gratis en muchos registradores), pero tarda horas; solo en caída larga.
  - Respaldos: copia adicional cifrada en Google Drive (gratis, ya existe la carpeta). Alternativa: Backblaze B2 (10 GB gratis).

## 3. Supabase — base de datos e inicio de sesión (proyecto hms-ai-assistant)
- **Qué se rompe:** nadie puede iniciar sesión ni ver sus datos. Es el servicio más crítico.
- **Cómo lo detectamos:** monitor de 15 min (la API falla al consultar la base); status.supabase.com; errores en /admin.
- **Pasos inmediatos:** confirmar caída general; si es nuestro proyecto, revisar si está pausado o al límite del plan; nunca restaurar sobre la base viva sin confirmación de Héctor.
- **Claves:** `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `SUPABASE_DB_URL` (Doppler y GitHub). Para descifrar respaldos: `BACKUP_PASSPHRASE` (Doppler y memoria SD).
- **Plan B:** restaurar el último respaldo (diario o semanal, en R2) en un proyecto Supabase nuevo (plan gratis permite 2 proyectos) o en otro Postgres (Neon, gratis). Luego cambiar `SUPABASE_URL`/`SUPABASE_SECRET_KEY`/`SUPABASE_DB_URL` en Doppler. Ojo: los usuarios tendrían que volver a iniciar sesión.

## 4. GitHub — código y tareas automáticas (com22fb-bot/hms-ai-assistant)
- **Qué se rompe:** los usuarios no notan nada de inmediato. Se detienen: publicaciones automáticas, monitor de 15 min, respaldos diario/semanal.
- **Cómo lo detectamos:** githubstatus.com; tareas que no corren (como el respaldo de las 3 am del 22 oct, que GitHub se saltó).
- **Pasos inmediatos:** correr a mano el respaldo si se saltó; publicar a mano con Wrangler si urge.
- **Claves:** `GH_BOT_TOKEN` (Doppler; vence 21 oct 2027). Secretos del repositorio: los mismos nombres de Doppler que usan los flujos (`SUPABASE_*`, `BACKUP_PASSPHRASE`, `R2_*`, `CLOUDFLARE_*`, `SLACK_BOT_TOKEN`, `RESEND_API_KEY`).
- **Plan B:** copia del código en la laptop de Héctor y en Drive. Mover las tareas programadas críticas (respaldo y monitor) al cron del Worker de Cloudflare (gratis), ver recomendaciones.

## 5. Doppler — caja fuerte de claves (donexto/prd)
- **Qué se rompe:** nada de inmediato (los servicios ya tienen sus claves cargadas). Sin Doppler no podemos cambiar ni consultar claves.
- **Cómo lo detectamos:** status.doppler.com; error al consultar claves.
- **Pasos inmediatos:** no cambiar claves mientras dure; usar las ya cargadas en Railway, Cloudflare y GitHub.
- **Claves:** acceso a la cuenta de Doppler (sesión del bot en la caja). Claves de recuperación en la memoria SD.
- **Plan B:** exportación periódica cifrada de los **nombres y valores** a un lugar fuera de Drive (las claves nunca se suben a Drive). Alternativa gratis: Infisical o los secretos de GitHub/Cloudflare.

## 6. Slack — alertas (#alertas, #usuarios, #admin)
- **Qué se rompe:** solo los avisos internos. Los usuarios no notan nada.
- **Cómo lo detectamos:** slack-status.com; los avisos dejan de llegar.
- **Pasos inmediatos:** los avisos siguen llegando por correo (Resend) y quedan en la Bitácora.
- **Claves:** `SLACK_BOT_TOKEN`.
- **Plan B:** correo (ya activo). Gratis: Telegram o Discord como segundo canal.

## 7. Inicio de sesión con Google, Microsoft y Yahoo (OAuth)
- **Qué se rompe:** no se pueden conectar buzones nuevos ni renovar el acceso a los conectados de ese proveedor.
- **Cómo lo detectamos:** errores al conectar buzón; avisos del proveedor; status de Google Workspace / Microsoft 365.
- **Pasos inmediatos:** avisar a los usuarios afectados; **no** cambiar permisos (scopes) ni direcciones de retorno (redirect URIs) sin decisión de Héctor.
- **Claves:** `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_REDIRECT_URI`, `YAHOO_CLIENT_ID`, `YAHOO_CLIENT_SECRET`, `YAHOO_REDIRECT_URI`, y `OAUTH_ENCRYPTION_KEY` (cifra los accesos guardados; copia en memoria SD — si se pierde, todos los usuarios reconectan).
- **Plan B:** conexión por IMAP con contraseña de aplicación (Gmail, Yahoo, iCloud), sin costo.

## 8. Proveedores de correo (envío de avisos y soporte)
- **Qué se rompe:** no llegan correos de confirmación, avisos ni respuestas de soporte.
- **Cómo lo detectamos:** errores de envío en la Bitácora; panel de Resend.
- **Pasos inmediatos:** cambiar temporalmente al otro canal (Resend ↔ SMTP de soporte).
- **Claves:** `RESEND_API_KEY`, `SUPPORT_SMTP_HOST`, `SUPPORT_SMTP_PORT`, `SUPPORT_SMTP_USER`, `SUPPORT_SMTP_PASSWORD`, `SUPPORT_SMTP_FROM`.
- **Plan B:** ya hay dos vías (Resend y SMTP). Gratis adicional: Brevo (300 correos/día).

## 9. IA (OpenAI)
- **Qué se rompe:** resúmenes y clasificación inteligente; el correo sigue funcionando.
- **Claves:** `OPENAI_API_KEY`, `AI_PROVIDER`.
- **Plan B:** cambiar `AI_PROVIDER` a otro proveedor (requiere clave nueva; de pago, con OK de Héctor).

---

## Recomendaciones concretas

### A. Mover el disparador del respaldo diario al cron del Worker de Cloudflare
GitHub se saltó el respaldo de las 3 am del 22 oct (sus tareas programadas pueden retrasarse o saltarse). Propuesta: que el cron del Worker de Cloudflare (código de respaldo de PR #167) dispare el respaldo diario a las 3:00 am CDMX y que GitHub quede solo como respaldo manual (`workflow_dispatch`). Gratis en el plan de Workers. Mantener la cobertura semanal actual. *Pendiente de aprobar; no se cambió ningún flujo en este documento.*

### B. API en espera (plan B documentado)
**Ruta de despliegue alterna** (sin crear nada hasta que Héctor apruebe):
1. Tener elegido el proveedor gratis (sugerido: Render o Koyeb) y probado una vez con una copia de prueba.
2. Mismo código (`com22fb-bot/hms-ai-assistant`, rama `main`) y mismo comando de arranque que Railway.
3. Cargar las variables desde Doppler (lista de nombres abajo, sin las `RAILWAY_*` propias de Railway).
4. Comprobar `/health` en la URL nueva.
5. En Cloudflare DNS, apuntar `api.donexto.com` a la URL nueva. Registrar en la Bitácora.
6. Al volver Railway, regresar el DNS y apagar el plan B.

### C. Inventario de claves (solo nombres y vencimientos)
| Clave | Dónde vive | Vence |
|---|---|---|
| `CLOUDFLARE_API_TOKEN` | Doppler, GitHub | 10 oct 2027 |
| `CLOUDFLARE_ANALYTICS_TOKEN` | Doppler, Railway | 10 oct 2027 |
| `GH_BOT_TOKEN` | Doppler | 21 oct 2027 |
| `RAILWAY_API_TOKEN` | Doppler, Railway | Sin vencimiento visible (nuevo, 22 oct 2026) |
| `SUPABASE_SECRET_KEY`, `SUPABASE_DB_URL`, `SUPABASE_URL` | Doppler, Railway, GitHub | Sin vencimiento |
| `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY` | Doppler, GitHub | No leído |
| `BACKUP_PASSPHRASE`, `OAUTH_ENCRYPTION_KEY` | Doppler, Railway, memoria SD | No vence |
| `SLACK_BOT_TOKEN`, `RESEND_API_KEY`, `OPENAI_API_KEY` | Doppler, Railway, GitHub | No leído |
| `GOOGLE_*`, `AZURE_*`, `YAHOO_*` | Doppler, Railway | El secreto de Azure vence según su consola (revisar) |
| `SUPPORT_SMTP_*`, `HMS_PROXY_SECRET`, `HMS_VAPID_*` | Doppler, Railway | No vence |

Recordatorio: revisar vencimientos en septiembre 2027 (Cloudflare y GitHub vencen en octubre 2027).

### D. Lista de rotación recomendada por Railway tras su incidente de seguridad
Railway recomendó cambiar las claves guardadas en sus variables. **No se ha cambiado ninguna.** Variables del servicio `hms-ai-assistant` (entorno production), solo nombres:

Claves secretas (candidatas a cambiar, en este orden sugerido):
1. `SUPABASE_SECRET_KEY`
2. `OPENAI_API_KEY`
3. `RESEND_API_KEY`
4. `SLACK_BOT_TOKEN`
5. `SUPPORT_SMTP_PASSWORD`
6. `GOOGLE_CLIENT_SECRET`, `AZURE_CLIENT_SECRET`, `YAHOO_CLIENT_SECRET`
7. `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ANALYTICS_TOKEN`
8. `HMS_PROXY_SECRET`, `HMS_VAPID_PRIVATE_KEY` (cambiar VAPID obliga a reactivar notificaciones)
9. `RAILWAY_API_TOKEN` (ya es nuevo)
10. `OAUTH_ENCRYPTION_KEY` — **no cambiar sin plan**: obligaría a todos a reconectar buzones.

No secretas (no requieren cambio): `ADMIN_EMAILS`, `AI_PROVIDER`, `AZURE_CLIENT_ID`, `AZURE_REDIRECT_URI`, `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_ZONE_ID`, `FRONTEND_ORIGINS`, `GOOGLE_CLIENT_ID`, `GOOGLE_REDIRECT_URI`, `HMS_AUTO_SYNC_ENABLED`, `HMS_VAPID_PUBLIC_KEY`, `HMS_VAPID_SUBJECT`, `SUPABASE_URL`, `SUPPORT_SMTP_FROM`, `SUPPORT_SMTP_HOST`, `SUPPORT_SMTP_PORT`, `SUPPORT_SMTP_USER`, `YAHOO_CLIENT_ID`, `YAHOO_REDIRECT_URI` y las propias de Railway (`RAILWAY_ENVIRONMENT`, `RAILWAY_ENVIRONMENT_ID`, `RAILWAY_ENVIRONMENT_NAME`, `RAILWAY_PRIVATE_DOMAIN`, `RAILWAY_PROJECT_ID`, `RAILWAY_PROJECT_NAME`, `RAILWAY_PUBLIC_DOMAIN`, `RAILWAY_SERVICE_HMS_AI_ASSISTANT_URL`, `RAILWAY_SERVICE_ID`, `RAILWAY_SERVICE_NAME`, `RAILWAY_STATIC_URL`).

Pasos por cada clave (cuando Héctor lo apruebe): crear la nueva en el proveedor → guardarla en Doppler → actualizar Railway/GitHub/Cloudflare → volver a desplegar → probar → borrar la vieja → registrar en la Bitácora.
