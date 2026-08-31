# DonexSeptember — arranque de chat (31 ago 2026)

**Nombre del chat nuevo:** DonexSeptember  
**Dueño:** Héctor M. Salcido Roacho  
**Repo:** `com22fb-bot/hms-ai-assistant` · producto **Donexto** (Do Next To…)  
**Trabajo de código:** GitHub Codespace `/workspaces/hms-ai-assistant`. Nunca la laptop `C:\Users\hsalc\hms-ai-assistant`.  
**Este archivo:** pegar el bloque de la sección “Primer mensaje” en el chat nuevo y leer este doc + `docs/ops/PLAN-ORIGINAL-PASOS.md`.

---

## Primer mensaje (copiar / pegar)

```text
Este chat se llama DonexSeptember.

Eres el agente de Donexto (com22fb-bot/hms-ai-assistant, main). Dueño: Héctor M. Salcido Roacho. Español de México.

Lee primero y no recortes:
- docs/ops/DONEX-SEPTEMBER.md
- docs/ops/PLAN-ORIGINAL-PASOS.md

Plan original completo (no usar listas cortas de infra):
P0 cuenta ≠ buzón → P1 matriz buzones → P2 verificar buzón → P3 conteos → P4 sample 20+20 → P5 top 10 atención → P6 modal 90 días → P7 add-ons 180/365 → P8 Stripe Test Normal $19.99 → P9 sync full → P10 Home N1 → P11 Free (después) → P12 admin con datos reales.
En paralelo: Logística 1 (import 6 meses), push+PWA en celular/tablet/PC/laptop, video 40 s de la landing, P00 (Banamex, catálogo, idiomas, Yahoo OAuth, cuatro frentes).

Septiembre: barato. Railway Hobby $5 es obligatorio o la API se pausa. Cloudflare Pages+Worker y Supabase Free. No migrar FastAPI a Workers. No Cloud Agents largos. Código en Codespace; Cursor Windows solo chat. Deploy Worker: CLOUDFLARE_API_TOKEN + cd frontend && npm run deploy. Landing: bash landing/donexto/deploy-production.sh --branch main. No Vercel.

Yahoo: no pedir contraseña. mail-r aún no; no pongas YAHOO_MAIL_READ_ENABLED=true. Verify-email Donexto (#31) no se salta con login Yahoo/Microsoft. iCloud: decisión abierta.

Confirma que leíste ambos docs y espera instrucción de Héctor.
```

---

## URLs

| Pieza | URL |
|-------|-----|
| App | https://app.donexto.com |
| API | https://hms-ai-assistant-production.up.railway.app |
| Landing | https://www.donexto.com |
| Admin | https://app.donexto.com/admin |
| Repo | https://github.com/com22fb-bot/hms-ai-assistant |

---

## Cuentas (no mezclar)

| Cuenta | Uso |
|--------|-----|
| `hsalcidor@yahoo.com` | Buzón de prueba personal |
| `donexto@yahoo.com` | Empresa / YDN / solicitud mail-r |
| `donexto@hotmail.com` | Entra / Hotmail |
| `hsalcidolapdell@outlook.com` | Outlook de prueba (verify a veces en basura) |
| `hmcelinfo@gmail.com` | Cloudflare + Cursor + `ADMIN_EMAILS` |

Continuar = usuario que **ya existe**. Suscribirse = alta nueva Yahoo/Outlook. Gmail/iCloud **nuevos** = `pending_review`.

---

## Septiembre — cotización y opciones

| Escenario | USD / mes | Qué |
|-----------|-----------|-----|
| **A (recomendado)** | ~25 | Railway Hobby $5 + Cursor Pro $20 (si ya está). CF y Supabase Free. Desarrollo en Codespace + chat, sin Cloud Agents. |
| **B mínimo** | ~5 | Solo Railway. Cursor Hobby / VS Code en Codespace. |
| **C como agosto** | 40–100+ | Cloud Agents. No. |

**Sí o sí esta semana:** Railway Hobby. Sin eso no hay OAuth ni import.

**No migrar “todo” a Cloudflare ahora.** Landing y app ya están. FastAPI + IMAP no caben en Workers. Containers siempre encendidos salen más caros que Hobby $5.

Barato: apagar este Cloud Agent; Codespace en el navegador (cupo se reinicia 1 sep); no abrir el clone Windows; no OpenAI en prod; no Stripe Live; no Workers Paid; no Supabase Pro.

---

## Lo que no se debe volver a recortar

1. **P12 Admin** — `/admin`, datos reales, `ADMIN_EMAILS`.
2. **Video 40 s** — landing, Do-NEX-to, no Donextu, `promo.mp4` cuando Héctor grabe.
3. **Push** — celular, tablet, PC, laptop + PWA + campana; solo N1; al tocar, el caso.

Fuentes: `docs/ops/PLAN-ORIGINAL-PASOS.md`.

---

## Estado al 31 ago 2026 (resumen)

- P0 código OK; **validación dueño en prod pendiente**.
- P1 parcial: Outlook Mail.Read sí; Yahoo identidad sí, inbox no (`mail-r`); Gmail nuevo pending; iCloud sin decidir.
- P2 en parte sustituido por verify-email Donexto (PR #31). Falta `mailbox_verified` formal.
- P3–P11 pendientes como en el plan original.
- P12 admin: UI/API base; falta allowlist en Railway + migración + datos/cobros reales.
- Push: módulo VAPID existe; no cerrado en prod en todos los dispositivos.
- Video: historia muda en la landing; falta voz + MP4 + guion actualizado (ya no es solo Gmail).
- P00: clasificador Banamex en código; validar en el buzón de Héctor.
- Yahoo YDN app `Garq7SCZ`: Email+Profile only. No Mail. No activar `YAHOO_MAIL_READ_ENABLED`.
- Google OAuth: dejar Testing. Search Console “página con redirección”: no quitar http→https / apex→www.

PRs recientes en `main` (agosto): #28 idiomas, #29 Microsoft callback, #30 login layout, #31 verify-email gate, #32 higiene git.

---

## Reglas fijas

- No password de Gmail/Yahoo/Outlook en formularios Donexto.
- Sin clic en el correo de **verificación Donexto** → no dashboard. Firmar en Yahoo/Microsoft no salta eso.
- Deploy Worker solo con `CLOUDFLARE_API_TOKEN` (no OAuth Wrangler en Codespace).
- Railway publica `main`. Ramas `cursor/<nombre>-3d73`.
- No Vercel.
- `support@yahoo.com` es inbox interno de dominios no soportados, no el mailer de verify (eso es SMTP de Supabase).
