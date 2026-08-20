# Restore Point — HMS-CP-20260818-210235

## Identificación

- **Checkpoint ID:** HMS-CP-20260818-210235
- **Proyecto:** Donexto / HMS AI Assistant
- **Fecha:** 2026-08-18
- **Hora:** 21:02:35 UTC
- **Sprint / lote:** P00
- **Rama de origen:** `cursor/landing-hogar-ia-3d73`
- **PR de trabajo:** https://github.com/com22fb-bot/hms-ai-assistant/pull/10
- **Estado:** REGISTRADO

## Trazabilidad Git

- **Commit de snapshot:** 2246969a1edd776846e92aaa17d6c11651bf0523
- **Commit de registro:** es el commit apuntado por el tag `restorepoint-HMS-CP-20260818-210235`
- **Tag:** `restorepoint-HMS-CP-20260818-210235`
- **Rama de respaldo (política Cursor):** `cursor/backup-p00-20260818-3d73`
- **Rama de respaldo (convención del repo):** `backup/hms-cp-20260818-210235`
- **Bundle local:** `/workspace/.hms-backups/hms-ai-assistant-HMS-CP-20260818-210235.bundle`
- **Remoto:** `https://github.com/com22fb-bot/hms-ai-assistant`
- **HEAD de trabajo al cerrar:** `cba2f2a7596a8c19ba17bd5f1b3d7117e6bd0d34` (antes del commit de registro)

## Cómo restaurar

```bash
git fetch origin
git checkout restorepoint-HMS-CP-20260818-210235
# o
git checkout cursor/backup-p00-20260818-3d73
```

Desde bundle local:

```bash
git clone --mirror /workspace/.hms-backups/hms-ai-assistant-HMS-CP-20260818-210235.bundle donexto-restore.git
```

## Decisiones de producto (no revertir)

1. **H1 siempre Donexto.** El slogan no es el título grande (Google OAuth Branding).
2. **Hogar = mercado** (correo personal, no corporativo). No titularizar “hogar” ni “correo del hogar”.
3. **Pedidos no gana a hogar.** Pedidos es uno de cuatro frentes iguales: Dinero · Seguridad · Pedidos · Familia.
4. Los cuatro frentes viven **solo en “Qué mira”**. No repetir la lista en hero, trust, video, login, topbar ni Inicio.
5. Login / topbar: “Lo siguiente que sí importa. El resto espera.”
6. Inicio: “Lo que pide acción, ahora. Lo demás, después o en silencio.”
7. Yahoo: correo + la misma clave. Sin guía de 16 dígitos, sin 2FA en Donexto.
8. Clasificador: match de dominio por **sufijo**, no substring. Versión `logistica1-triage-v4`.
9. Landing pública = Cloudflare Pages **Production / `main`**. Feature branch = Preview.
10. Código, git y deploy solo en remoto (`com22fb-bot/hms-ai-assistant`), nunca en la laptop Windows.

## Qué ya está en producción (18 ago 2026)

| Pieza | Dónde |
| --- | --- |
| Landing copy de peso igual | Pages `donexto` Production (`deploy-production.sh --branch main`) |
| App copy de peso igual + Yahoo correo/clave + idioma | Worker `donexto-app` (`cd frontend && npm run deploy`) |

## Qué NO está en producción hasta merge a `main`

- Clasificador v4 + catálogo de bancos (Railway publica solo `main`).
- Banamex en el buzón importado de Héctor puede seguir mal hasta merge + “Clasificación inteligente”.

## Publicar de nuevo

```bash
bash landing/donexto/deploy-production.sh
cd frontend && npm run deploy
```

Chrome: Ctrl+Shift+R.

## Prueba

- Yahoo: `hsalcidor@yahoo.com`
- Correo oficial: `support@donexto.com`
- App: https://app.donexto.com
- Landing: https://donexto.com
