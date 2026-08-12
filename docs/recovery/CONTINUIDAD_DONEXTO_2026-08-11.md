# Respaldo de continuidad — Donexto
**Fecha:** 2026-08-11  
**Incluye:** decisiones de producto, brand, cobros, admin, roadmap P0–P12  
**Descartar como “ruta principal”:** trabajo de landing/video del domingo (quedó como infra secundaria).

---

## 1. Principio de producto

**Donexto = capa de atención sobre el correo** (hogar/personal). No es otro Gmail ni dashboard de fábricas.

| Identidad | Qué es |
|-----------|--------|
| **Cuenta Donexto** | Nombre completo + email + contraseña (o flujo verify→pago futuro) |
| **Buzón** | Gmail / Yahoo / Outlook / Apple / dominio privado (IMAP) — **paso aparte** |

**Cuenta ≠ buzón** (P0 implementado). Login Donexto nunca = contraseña Gmail.

---

## 2. Flujo de alta acordado (orden)

```text
1) Alta Donexto (nombre + email)
2) Verificar email de cuenta (inbox real; incluye dominio privado)
3) Password / sesión Donexto
4) Conectar buzón + validación lectura
5) Conteo INBOX/Sent → sample (~20) → hasta 10 “requieren atención”
6) Aviso sync ~90 días
7) Plan Normal $19.99/mes (90 días incluidos)
   · Extra 180 d: +$9.99 one-time
   · Extra 365 d: +$16.99 one-time
8) Sync full del plan + Home N1
9) Free con restricciones DESPUÉS del plan Normal (recortar el mismo motor)
```

**Preferencia dueño:** primero Normal de pago; Free restringido después.  
**Cobro:** tras buzón verificado (o trial 24 h sobre Normal). Stripe principal, PayPal secundario. Tests en **Stripe Test Mode** (no hace falta 1¢ real).

Trial 24 h: “quien no lo pruebe en 1 día no lo va a hacer.”

---

## 3. Roadmap checklist (uno por uno)

| ID | Tema | Estado |
|----|------|--------|
| **P0** | Cuenta ≠ buzón (copy, signup nombre, gate Paso 2, banners) | **Cerrado en código 2026-08-12** — validar en prod |
| **P1** | Matriz buzones (Gmail, Yahoo, Outlook, Apple, dominio privado) | Pendiente |
| **P2** | Conectar + **verificar** buzón (`mailbox_verified`) | Siguiente |
| **P3** | Conteos INBOX / Sent | Pendiente |
| **P4** | Sample 20 INBOX + 20 Sent | Pendiente |
| **P5** | Motor: hasta 10 “requieren atención” | Pendiente |
| **P6** | Modal aviso 90 días | Pendiente |
| **P7** | Add-ons historial 180/365 | Pendiente |
| **P8** | Stripe Normal $19.99 (Test Mode) | Pendiente |
| **P9** | Sync full del plan | Pendiente |
| **P10** | Home N1 post-sync | AttentionHome base existe |
| **P11** | Free restringido | Después de Normal |
| **P12** | Admin conectado a datos reales | Base stub existe |

---

## 4. Marca y logo (oficial 2026-08-11)

### Concepto monograma
- **@ de teclado** pero la **a** se sustituye por **D** mayúscula  
- El anillo sale de la misma D (glifo @ real)  
- Colores: **teal `#0c8a80` / `#5ecfc4`** + **magenta `#ff2d6a`** + slate `#0a1620`  
- Ambiente: metal 3D + **glow** (brillar), sobres de colores (sin texto de categorías legible en tamaño logo)  
- Slogan: **Do Next To…**

### Assets oficiales
| Uso | Archivo |
|-----|---------|
| **Logo / icono (preferido)** | `frontend/public/brand/donexto-envelopes-glow-icon.png` |
| Hero horizontal | `frontend/public/brand/donexto-envelopes-glow-3d.png` (+ v2) |
| Copy legal micro | `© HMSR · MR` + `Héctor M. Salcido Roacho` (2 líneas) — **MR** = Marca registrada |

Kit: `frontend/public/brand/` y `landing/donexto/brand/`  
Doc legal: `frontend/public/brand/COPYRIGHT-HMSR.md`

### No usar como marca principal
- Versiones con paneles de texto de categorías legibles  
- Reflejos espejo grandes del wordmark  
- Logos genéricos “D” mayúscula simple sin concepto @  

---

## 5. Cobros (resumen)

| | |
|--|--|
| Principal | **Stripe** (Test Mode para aprender) |
| Secundario | PayPal |
| Stripe US (orden) | ~2.9% + $0.30 + Billing ~0.7% |
| Stripe MX (orden) | ~3.6% + MXN $3 (+ IVA si aplica) |
| Trial | 24 h con tarjeta / webhook |
| Activación | `mailbox_ok` ∧ (`trialing` \| `active`) |

---

## 6. Admin

Base en código: `/admin`, API `/admin/*`, allowlist `ADMIN_EMAILS`.  
Migración: `supabase/migrations/20260811120000_admin_ops_foundation.sql`  
Doc: `docs/ops/ADMIN_MODULE.md`  
Billing/metrics host: stubs hasta Stripe + Railway.

---

## 7. Infra (snapshot)

| Pieza | URL / nota |
|-------|------------|
| App | https://app.donexto.com (`donexto-app`) |
| Landing | https://donexto.pages.dev / donexto.com |
| API | https://hms-ai-assistant-production.up.railway.app |
| Repo | `com22fb-bot/hms-ai-assistant` |
| Rama habitual | `main` |

Deploy frontend Codespace: `CLOUDFLARE_API_TOKEN` (no OAuth browser).

---

## 8. P0 — cómo validar hoy

Ver `docs/ops/P0-cuenta-donexto-vs-buzon.md`.

Siguiente tras P0 OK en prod/local: **P2** (verify buzón).

---

## 9. En qué te ayuda el dueño (checklist)

- [ ] Probar P0 en app (signup + gate buzón)  
- [ ] Aplicar migración admin en Supabase si no está  
- [ ] `ADMIN_EMAILS=hmcelinfo@gmail.com` en Railway  
- [ ] Cuenta Stripe Test + (luego) llaves  
- [ ] Confirmar logo oficial en app tras deploy  
- [ ] No compartir secretos en el chat  

---

## 10. Frase de continuidad para el próximo agente

> Retomar **P0 validado por Héctor** y continuar **P2 mailbox verify + sample + top 10**. Brand: `donexto-envelopes-glow-icon.png`, cuenta ≠ buzón, Normal $19.99 y 90 días **después** de conexión ok. Respaldo: este archivo.
