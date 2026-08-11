# P0 — Cuenta Donexto ≠ buzón

**Estado:** Implementado en código · **validación dueño en curso (2026-08-11)**  
**Respaldo de sesión:** `docs/recovery/CONTINUIDAD_DONEXTO_2026-08-11.md`  
**Siguiente tras validar P0:** P2 (verificar buzón + conteo + sample).

**Fecha:** 2026-08-11  
**Ámbito:** Solo identidad Donexto vs conexión de buzón. Sin billing, Free plan, sample 20, ni sync 90d.

## Principio de producto

| Concepto | Qué es | Credenciales |
|----------|--------|--------------|
| **Cuenta Donexto** | Acceso a la app (Supabase Auth) | Nombre completo + email Donexto + contraseña Donexto |
| **Buzón** | Fuente de correo a vigilar | Gmail OAuth, Yahoo app password, (futuro Outlook/Apple/IMAP) |

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
└────────────┬─────────────┘
             │ communication_account activa
             ▼
      [Home / clasificación]
```

Copy compartido: `frontend/lib/accountVsMailbox.ts`  
Hint UI: `frontend/components/auth/AccountVsMailboxHint.tsx`

## Criterios de aceptación

- [ ] El usuario puede explicar en una frase por qué el email de login puede diferir del buzón  
  → *La cuenta Donexto es el acceso a la app; el buzón es el correo que vigilamos y puede ser otro.*
- [ ] El alta pide **nombre completo** (`full_name` en `user_metadata` / perfil)
- [ ] En ningún lugar del formulario de login Donexto se pide “contraseña de Gmail”
- [ ] Tras login sin `communication_account` activa, el CTA primario es **Paso 2: Conecta el buzón** (no un dashboard roto)
- [ ] La UI de conectar Gmail/Yahoo deja claro: login Donexto ≠ credenciales del buzón
- [ ] “Cambiar buzón” sigue disponible cuando hay buzón conectado

## Cómo probar en localhost

1. `frontend`: `npm run dev` (y backend si aplica para OAuth/Yahoo).
2. Abrir la app sin sesión → pantalla **Cuenta Donexto** (no menciona contraseña Gmail).
3. **Crear cuenta** con nombre, email y contraseña Donexto.
4. Tras entrar sin buzón: modal/gate **Paso 2** + empty state en home; no métricas vacías como acción principal.
5. Conectar Gmail o Yahoo y verificar banner *“Esto no es tu login de Donexto · solo lee el buzón”*.
6. Con buzón activo: **Cambiar buzón** en sidebar/home.

## Residual (P1+)

- Onboarding multipaso con progreso visual persistente
- Outlook / Apple / IMAP genérico
- Forzar dismiss bloqueado en todos los surfaces (solo modal forzado hoy)
- Sincronizar `profiles.full_name` al actualizar metadata post-registro
- i18n EN complete
