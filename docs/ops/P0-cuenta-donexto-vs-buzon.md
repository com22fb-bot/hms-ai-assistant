# P0 — Cuenta Donexto ≠ buzón

**Estado:** Cerrado en código (2026-08-12) · **validación dueño en prod pendiente**  
**Respaldo:** `docs/recovery/CONTINUIDAD_DONEXTO_2026-08-11.md`  
**Siguiente tras validar P0 en app.donexto.com:** **P2** (verificar buzón + conteo + sample).

**Ámbito:** Solo identidad Donexto vs conexión de buzón. Sin billing, Free plan, sample 20, ni sync 90d.

## Principio de producto

| Concepto | Qué es | Credenciales |
|----------|--------|--------------|
| **Cuenta Donexto** | Acceso a la app (Supabase Auth) | Nombre completo + email Donexto + contraseña Donexto |
| **Buzón** | Fuente de correo a vigilar | Gmail OAuth, Yahoo correo+clave IMAP, (futuro Outlook/Apple/IMAP) |

El correo de login **puede ser distinto** del buzón. La contraseña Donexto **nunca** es la de Gmail/Yahoo.

## Flujo

```text
[Landing / gate]
       │
       ▼
┌──────────────────────────┐
│ Paso 1 — Cuenta Donexto  │
│ · Nombre completo (alta) │
│ · Email cuenta           │
│ · Contraseña Donexto     │
└────────────┬─────────────┘
             │ sesión OK
             ▼
┌──────────────────────────┐
│ Paso 2 — Buzón a vigilar │
│ · Gmail (OAuth) o Yahoo  │
│ · Banner: no es login    │
│   Donexto                │
│ · Opción: ver app y      │
│   conectar después       │
└────────────┬─────────────┘
             │ communication_account activa
             ▼
      [Home / AttentionHome]
```

Copy compartido: `frontend/lib/accountVsMailbox.ts`  
Hint UI: `frontend/components/auth/AccountVsMailboxHint.tsx`  
Misión/calidad acceso: `frontend/lib/donextoQuality.ts`

## Criterios de aceptación

- [x] Copy canónico explica por qué el email de login puede diferir del buzón (`oneLiner` / hints)
- [x] El alta pide **nombre completo** (`full_name` en `user_metadata`)
- [x] Backend sincroniza `profiles.full_name` si nació vacío y Auth ya trae el nombre
- [x] Login Donexto no pide “contraseña de Gmail”
- [x] Tras login sin buzón: modal **Paso 2** + empty state AttentionHome con CTA
- [x] UI Gmail/Yahoo: banner *cuenta ≠ buzón*
- [x] “Cambiar buzón” / “Conectar buzón” reabre el picker
- [x] Mensajes de API de identidad en español hablan de **Donexto**, no HMS
- [ ] **Validación dueño en https://app.donexto.com** (tras deploy con token)

## Cómo probar (prod o local)

1. Deploy frontend con `CLOUDFLARE_API_TOKEN` + `npm run deploy` (no OAuth Wrangler).
2. Sin sesión → login Donexto (misión/calidad + labels cuenta Donexto).
3. **Crear cuenta** con nombre, email y contraseña Donexto.
4. Sin buzón → modal Paso 2 (Gmail/Yahoo) + hint; o “ver app y conectar después” → home vacío con CTA Paso 2.
5. Conectar Gmail o Yahoo; banner de conexión deja claro que no es login Donexto.
6. Con buzón: **Cambiar buzón** disponible.

## Residual (P1+)

- Onboarding multipaso con progreso visual persistente
- Outlook / Apple / IMAP genérico
- i18n EN complete
- Confirmación de email Supabase (ops)
