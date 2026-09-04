# Plan original de Donexto — todos los pasos

**Chat de continuación:** DonexSeptember — arranque en `docs/ops/DONEX-SEPTEMBER.md`.  
**Fuentes (no recortar):** continuidad 11 ago 2026, prompt maestro 12 ago, Logística 1, Bloque B, landing 40 s, P00 18 ago.  
**Dueño:** Héctor M. Salcido Roacho · marca HMSR · MR · producto **Donexto** (Do Next To…).

Este documento restaura el plan **completo**. No sustituye a P0–P12: los junta con admin, video, push y Logística 1, que en listas cortas se habían perdido.

---

## 0. Qué es el producto (no negociable)

Donexto es la **capa de atención** sobre el correo personal/hogar. No es otro Gmail. No es dashboard de fábricas.

Cuatro frentes al **mismo peso:** Dinero · Seguridad · Pedidos · Familia.  
Hogar es el mercado, no el titular. Pedidos no es “envíos”.

| | Cuenta Donexto | Buzón |
|--|----------------|-------|
| Qué | Acceso a la app | Correo vigilado |
| Credenciales | Nombre + email + contraseña Donexto | OAuth en el sitio del proveedor (Gmail, Yahoo, Outlook…) |
| Cuándo | Paso 1 | Paso 2 |

Login Donexto **nunca** pide la contraseña de Gmail/Yahoo/Outlook.

Niveles: **N1** push cuando importa · **N2** digest · **N3** silencio (promo).

---

## A. Experiencia del usuario final (producto terminado)

Orden acordado 11–12 ago 2026:

1. Crear **cuenta Donexto** (nombre completo + email + contraseña).
2. **Verificar** el email de la cuenta (inbox real; incluye dominio privado).
3. Sesión Donexto.
4. **Conectar buzón** (Gmail / Yahoo / Outlook / Apple / dominio privado) y **verificar lectura**.
5. Ver **conteos** INBOX / Sent → **sample** (~20 INBOX + ~20 Sent) → hasta **10 “requieren atención”**.
6. Aviso de sync de **~90 días**.
7. Plan **Normal $19.99/mes** (90 días incluidos) o trial **24 h**; extra historial 180 d +$9.99 y 365 d +$16.99 (one-time).
8. **Sync completo** del plan + **Home N1** + push selectivo.
9. Plan **Free restringido** *después* de Normal (mismo motor, caps duros).
10. El dueño opera **`/admin`**.

Cobro: tras buzón verificado **o** trial 24 h. Stripe Test Mode primero. PayPal secundario.  
Activación: `mailbox_ok` ∧ (`trialing` ∨ `active`).

---

## B. Roadmap P0–P12 (uno por uno)

| ID | Entrega |
|----|---------|
| **P0** | Cuenta ≠ buzón: copy, alta con nombre, gate Paso 2, banners. Validar en https://app.donexto.com |
| **P1** | Matriz de buzones: Gmail, Yahoo, Outlook, Apple, dominio privado (IMAP). **Actualizado 2 sep 2026:** personal + empresa + gobierno MX — ver abajo. |
| **P2** | Conectar + **verificar** buzón (`mailbox_verified` / `mailbox_ok`) |
| **P3** | Conteos exactos INBOX / Sent |
| **P4** | Sample ~20 INBOX + ~20 Sent |
| **P5** | Motor: hasta **10** ítems “requieren atención” |
| **P6** | Modal aviso sync **90 días** |
| **P7** | Add-ons historial **180 / 365** días |
| **P8** | Stripe **Normal $19.99** (Test Mode; luego Live) |
| **P9** | Sync **full** del plan contratado |
| **P10** | Home N1 post-sync (AttentionHome; no conteo de correos) |
| **P11** | Free restringido (después de Normal) |
| **P12** | **Admin con datos reales** (usuarios, cobros, feedback, promociones, sistema) |

### P1 — puntero 2 sep 2026 (no reescribe el plan)

La fila de arriba sigue siendo el P1 original. El detalle que no se debe perder:

- `.mx` / `.gob.mx` / `.com.mx` **no** son el proveedor: Continuar + MX.
- Microsoft (Hotmail/Outlook/Live/MSN, `@televisa.com.mx`, `@cfe.mx`) **ya**.
- Google (Gmail, `@liverpool.com.mx`, `@televisa.com`, `@cdmx.gob.mx`) **pronto**.
- Proofpoint / Trend Micro / servidores propios (TV Azteca, Telcel, SAT, IMSS, Hacienda, Función Pública, ISSSTE, SEGOB, Banxico) = waitlist. Sin password de buzón. Sin `YAHOO_MAIL_READ_ENABLED`.
- P1 **no** es “nunca empresa ni gobierno”.

Canónico: `docs/ops/MATRIZ-BUZONES.md`. Pendientes: `docs/ops/DONEX-SEPTEMBER.md` (2 sep).

### P0 — criterios originales

- Copy: el email de login puede diferir del buzón.
- Alta pide **nombre completo**.
- Login Donexto no pide “contraseña de Gmail”.
- Sin buzón: modal Paso 2 + CTA, o “ver app y conectar después”.
- Banner cuenta ≠ buzón al conectar Gmail/Yahoo.
- “Cambiar buzón” / “Conectar buzón”.
- Validación del dueño en prod (móvil y escritorio).

### P12 — app administrativa (original)

Ruta: `https://app.donexto.com/admin`  
Allowlist: `ADMIN_EMAILS` (p. ej. `hmcelinfo@gmail.com`) en Railway.  
Migración: `supabase/migrations/20260811120000_admin_ops_foundation.sql`

Secciones:

1. Resumen
2. Usuarios
3. Cobros (Stripe/PayPal; stub hasta cobros reales)
4. Quejas y ideas
5. Promociones
6. Sistema (salud API / Railway)

El dueño ve altas, buzones conectados, trials, pagos y fallos. No es un extra: es **P12**.

---

## C. Logística 1 — primera importación (pasos originales)

1. El usuario crea su cuenta.
2. La pantalla de acceso muestra el robot HMS a la izquierda *(login actual: una columna Donexto; el robot no es héroe del gate)*.
3. El método de pago se ve preparado, **sin cobrar** hasta que el programa funcione.
4. Conecta el correo con el proveedor disponible.
5. Al volver de OAuth **no** hay dashboard vacío ni “Sincronizar Gmail” obligatorio.
6. Inventario automático de los **últimos seis meses**.
7. Incluye recibidos, enviados y archivados. Excluye Spam, Papelera y Borradores.
8. Muestra el **total exacto** a descargar.
9. El usuario **confirma** la importación.
10. Se congelan los IDs de esa selección.
11. Descarga en lotes internos de hasta **100**.
12. Progreso real (robot, laptop, maletero / papeles que bajan).
13. Descarga y clasificación son **etapas aparte**.
14. Cada mensaje se guarda **una sola vez**.
15. Todos se clasifican; **no** todos se vuelven caso.
16. Relacionados pueden agruparse en un mismo caso.
17. Al terminar, abre el dashboard.
18. El dashboard separa mensajes, casos, tareas y no accionables.
19. Durante la primera carga, el botón de actualizar está deshabilitado.
20. Después se llama **“Descargar correos nuevos”** (texto **sin** nombre de Gmail/Yahoo).
21. Sincronizaciones siguientes: **solo mensajes nuevos**.
22. No se borra, archiva, etiqueta ni marca el correo original sin permiso.

---

## D. Notificaciones (original — celular, tablet, PC, laptop)

HMS/Donexto debe incorporar:

1. **Push** en celular, tablet, laptop y PC.
2. Avisos **internos** si la app está abierta.
3. Centro con **campana y contador**.
4. Solo pendientes, riesgos, fechas límite o seguimiento.
5. **Ningún** push de promociones, sociales o no accionables.
6. Al tocar: **abrir el caso** (no un “nuevo correo”).
7. Instalación **PWA** (añadir a pantalla de inicio; iPhone incluido).
8. Un dispositivo = una suscripción, ligada al perfil autenticado.
9. Llaves **VAPID** fuera de Git; prueba de envío en ese aparato.
10. Deduplicación, quiet hours, feedback y auditoría.

**No notificar cada correo. Notificar el evento de negocio** (caso nuevo, factura atrasada, vence mañana, seguridad, etc.).

| Nivel producto | Comportamiento |
|----------------|----------------|
| N1 | Atención inmediata / push |
| N2 | Resumen / digest |
| N3 | Silencio |

Categorías críticas: seguridad, 2FA, cargos, pagos, facturas, servicios, entregas, escuela, salud, viajes, VIP/favoritos.

Bloque B (operación continua, original):

- Búsqueda en remitentes, destinatarios, asunto, etiquetas y cuerpo.
- Agrupar respuestas / reenvíos.
- Scheduler de correo nuevo (~120 s).
- Reglas del usuario primero; clasificador después.
- Favoritos y accionables → aviso interno + push.
- Métricas cada 30 s.
- Login, descarga, bandeja y modales al **alto real** del dispositivo (móvil/tablet/PC).

---

## E. Landing y video de 40 segundos (original)

Sitio: `https://www.donexto.com` / `https://donexto.com` (Cloudflare Pages, **Production / `main`**).

1. H1 **Donexto**. Slogan Do Next To… Pronunciación **Do-NEX-to**. Nunca “Donextu”.
2. Historia de **40,0 s** en la sección “El criterio, en 40 segundos”.
3. El MP4 viejo (~10 s, “Donextu”) **no se sube**.
4. Guion de voz: `landing/donexto/GUION-40S-ES-MX.txt` *(actualizar: ya no es solo Gmail; Yahoo/Outlook y verificación Donexto)*.
5. Grabar voz en off → exportar `landing/donexto/promo.mp4` 1080p, 40,0 s.
6. Volver a poner el `<video>` en `index.html` **solo** con audio correcto.
7. Fotos de marca: escritorio, youtube, placa 3D.
8. Deploy: `cd landing/donexto && bash deploy-production.sh` (`--branch main`). Preview de rama **no** cambia www.
9. Legal: términos, privacidad, cookies. Contacto `support@donexto.com`.
10. Copyright: © HMSR · MR / Héctor M. Salcido Roacho.

El 11 ago el video se bajó a “infra secundaria”. **Sigue siendo entrega original de la web**; no está en P0–P12 porque es marketing, no el motor de la app.

---

## F. P00 — encima de P0–P12 (18 ago 2026)

1. Banamex/Citibanamex **no** va a redes sociales (match por sufijo de dominio).
2. Catálogo: banco / pedido / reserva / social / publicidad.
3. Bases de bancos MX, US, CA, UE, LATAM.
4. Idioma en ajustes y login: **ES, EN, FR, IT, PT**.
5. Yahoo: firmar **en el sitio de Yahoo** (OAuth). Donexto no pide clave de buzón.
6. Landing y app: criterio (qué sí requiere acción); cuatro frentes al mismo peso; publicar landing siempre a Production.

Validación dueño: reclasificar el buzón de Héctor; Banamex en **Avisos (N1)**; LinkedIn/X digest en Social; `offers@` de banco en Publicidad.

---

## G. Definition of Done del producto final (12 ago)

Un usuario nuevo en México/EE. UU. puede:

1. Crear cuenta Donexto y entender que **no** es Gmail.
2. Conectar Gmail o Yahoo (luego Outlook/Apple) y ver confirmación de lectura.
3. Ver en minutos una lista **corta** de lo que requiere atención (no 5 000 mails).
4. Recibir **push solo en N1**, en el teléfono, la tablet y la computadora.
5. Pagar Normal en test/live y ampliar historial si quiere.
6. Abrir el mensaje/caso original.
7. El dueño opera `/admin` con usuarios, feedback y cobros básicos.
8. La landing cuenta Donexto en 40 s, con el nombre bien pronunciado.

---

## H. Anti-patrones (originales)

- Pedir password del buzón en el login Donexto.
- Home = inbox completo.
- Notificar cada correo.
- Mezclar UI Profesional/fábricas con Family.
- Inventar logos no aprobados en el login.
- Split-screen vacío de adorno.
- Deploy Wrangler OAuth en Codespace.
- Deploy sin el commit de `main`.
- Commitear `.env`.
- Subir el MP4 “Donextu”.
- Titularizar “hogar” o reducir el producto a “envíos”.

---

## I. Otra versión anterior (HMS V2 sprints — no es la ruta UI actual)

Plan 6 ago 2026, 14 días, enfoque **Profesional** primero. La UI pública acordada el 11–12 ago es **Family/Donexto**. Se lista para no perderlo:

| Sprint | Objetivo |
|--------|----------|
| 1 | Estabilizar + Logística 1 + Push/VAPID |
| 2 | Clasificación y alertas (dedupe, explicación, feedback) |
| 3 | Multicuenta Gmail |
| 4 | Seguridad SaaS (RLS, auditoría) |
| 5 | Microsoft 365 |
| 6 | Preparar piloto empresarial |
| 7 | Piloto 3–5 empresas |
| 8 | Modelo común Profesional/Family |
| 9 | Fundación Family (hogares, shell móvil) |
| 10 | Alertas familiares (categorías, push, digest) |
| 11 | Piloto 5–10 hogares |
| 12 | Marca y comercialización |

Motor futuro B2B: no mezclar esa UI ahora.

---

## J. Orden de trabajo (cómo se leía originalmente)

```text
P0 validado en prod
 → P1 matriz buzones
 → P2 verificar buzón
 → P3 conteos
 → P4 sample 20+20
 → P5 top 10 atención
 → P6 modal 90 días
 → P7 add-ons 180/365
 → P8 Stripe Test Normal $19.99
 → P9 sync full
 → P10 Home N1
 → P11 Free (después)
 → P12 Admin datos reales
en paralelo (no estaban en la numeración P pero sí en el producto):
 → Logística 1 importación 6 meses
 → Push + PWA en móvil / tablet / PC / laptop
 → Video 40 s + landing Production
 → P00 clasificador / idiomas / Yahoo OAuth / cuatro frentes
```
