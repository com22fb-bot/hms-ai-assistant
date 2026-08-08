# Sprint 1 — Tablero de pendientes (HMS V2)

**Actualizado:** 2026-08-07  
**Rama:** `sprint/01-estabilizacion-alertas-20260806`  
**HEAD remoto de referencia:** `e017f11` — *fix: mobile viewport responsive layout and device-targeted push test*  
**Ventana del sprint:** 6–19 de agosto de 2026  
**Siguiente decisión de producto:** rediseño completo (post–punto de restauración)

---

## Resumen del estado

| Área | Estado |
|------|--------|
| Prompt Maestro V2 + plan 12 sprints | Hecho (docs en Git) |
| Logística 1 en GitHub | Hecho (`2dea5d9`) |
| Hotfix clasificador + path VAPID | Hecho (`ea863f9`) |
| Viewport móvil + Push solo a este dispositivo | Hecho (`e017f11`) |
| Backend `/health` + frontend 3000 (Codespace) | Validado en sesión |
| Push en laptop | Validado |
| Push en celular | Validado (tras permisos del SO) |
| Puerto 3000 público en Codespace | Hecho |
| Tag / restorepoint pre-rediseño | **Pendiente** |
| Cierre formal DoD Sprint 1 | **Pendiente** |
| Rediseño de producto/UI | **Pendiente** (fuera del DoD técnico actual; decisión del propietario) |

---

## Hecho en esta línea de trabajo

### A. Gobierno y respaldo histórico
- [x] Respaldo maestro V2 leído y alineado
- [x] Repo clonado / conectado (`com22fb-bot/hms-ai-assistant`)
- [x] Rama Sprint 1 activa
- [x] Docs V2: Prompt Maestro, decisión Profesional/Family, plan de sprints
- [x] Logística 1 commiteada y pusheada (ya no solo en working tree)
- [x] `.hms-secrets/` en `.gitignore`
- [x] Firma GPG desactivada **solo en repo local Codespace** (`commit.gpgsign=false`) por 403 Author invalid
- [x] Tar WIP Codespace (~289 MB) generado en su momento

### B. Backend / Logística 1
- [x] APIs y servicios: push, reclass, clasificador seguro, reglas, triage, watch, schedule, etc.
- [x] Router Push registrado en `main.py`
- [x] Modo `data_mutations_enabled=false` / `inventory_read_only` por defecto
- [x] Fix: `direction` no definido en `safe_case_classifier`
- [x] Fix: `generate_vapid_keys.py` usa `parents[1]` (repo root)
- [x] `push.env` / pem en `/workspaces/hms-ai-assistant/.hms-secrets` (no en Git)
- [x] Health OK en Codespace (v0.4.0)

### C. Frontend / Logística 1
- [x] Mail inbox, categorías, clasificación inteligente, panel Push, SW, manifest
- [x] Importación guiada actualizada
- [x] Viewport `width=device-width` + ajustes responsive
- [x] Push panel: lista dispositivos, re-suscripción, prueba **solo a este endpoint**

### D. Push operativo
- [x] VAPID configurado y carga de env
- [x] Activar en dispositivo + prueba laptop
- [x] Activar en celular + permisos del SO + recepción OK
- [x] Codespace port 3000 public:  
  `https://stunning-potato-r45467jvg69gh5p4x-3000.app.github.dev`

### E. No hecho / no cerrado aún
- [ ] Tag formal **pre-rediseño** + rama `backup/*` + bundle (script preparado, ejecución no confirmada en remoto)
- [ ] Checklist completo del DoD Sprint 1 (build TS, sin duplicados métricos, robot visual formal, commits limpios de logs/zips)
- [ ] Migraciones Logística 1 aplicadas y verificadas en Supabase (documentar evidencia)
- [ ] Validación visual formal de todo el dashboard (inicio, correos, categorías, pendientes, robot, búsqueda, breakpoints)
- [ ] Bitácora de cierre Sprint 1 + tag de cierre
- [ ] Rediseño completo de producto (decisión: empieza **después** del restore point)

---

## Tablero de pendientes (Sprint 1)

### Prioridad P0 — Anclar el estado (antes de rediseñar)

| ID | Pendiente | Criterio de hecho | Dueño |
|----|-----------|-------------------|-------|
| S1-P0-01 | Ejecutar restorepoint pre-rediseño | Tag + rama backup en origin; doc en `docs/checkpoints/` | Codespace / Héctor |
| S1-P0-02 | Confirmar que no hay WIP sensible sin commit | `git status` limpio salvo ignorados (logs/zips) | Codespace |
| S1-P0-03 | Sincronizar clone local Windows con remoto | Local en `e017f11` sin diffs basura | Cursor PC |

### Prioridad P1 — Cerrar DoD técnico Sprint 1

| ID | Pendiente | Criterio de hecho | Dueño |
|----|-----------|-------------------|-------|
| S1-P1-01 | Arranque reproducible documentado | Backend 8000 + frontend 3000 + VAPID en runbook 1 página | Docs |
| S1-P1-02 | Python compile + endpoints críticos | compileall + `/health` + `/push/*` autenticados | Backend |
| S1-P1-03 | TypeScript / build frontend | `npm run build` OK | Frontend |
| S1-P1-04 | Validación visual propietaria | Checklist firmado: login, home, correos, categorías, pendientes, push, móvil | Héctor |
| S1-P1-05 | Robot / catálogo de controles | Estados coherentes con lo realmente activo | Frontend |
| S1-P1-06 | Deduplicación básica de avisos | No spam de push de prueba / casos evidentes | Push |
| S1-P1-07 | Migraciones Supabase Logística 1 | 3 migraciones aplicadas o plan de aplicación documentado | Datos |
| S1-P1-08 | Sin secretos en Git | Escaneo `.pem` / env / tokens | Repo |
| S1-P1-09 | Tag y documentación de cierre Sprint 1 | `checkpoint-sprint1-close-…` + nota de restore | Gobierno |

### Prioridad P2 — Mejoras recomendadas (aún Sprint 1 si cabe)

| ID | Pendiente | Notas |
|----|-----------|--------|
| S1-P2-01 | UX móvil post-viewport | Revisar bandeja/correo y paneles densos en 390px |
| S1-P2-02 | UI Push: desactivar por dispositivo remoto | Hoy desactiva “aquí”; falta listado con desactivar remoto |
| S1-P2-03 | i18n/copy de prueba Push | Mensajes claros dispositivo actual vs todos |
| S1-P2-04 | Integrar VAPID en `./hms` CLI | Hoy backend se arranca a mano con `source push.env` |
| S1-P2-05 | Limpiar artefactos locales | `.hms-logs/`, zips master no deben commitearse |

### Prioridad P3 — Fuera de Sprint 1 (roadmap)

| ID | Tema | Sprint planificado |
|----|------|--------------------|
| S2+ | Motor clasificación/alertas confiable | Sprint 2 |
| S3+ | Multicuenta Gmail | Sprint 3 |
| S4+ | Seguridad SaaS / RLS | Sprint 4 |
| S5+ | Microsoft 365 | Sprint 5 |
| S8+ | Modelo Profesional/Family | Sprint 8 |
| RD-01 | **Rediseño completo de producto/UI** | A decidir post–restorepoint (puede redefinir sprints) |

---

## Deuda técnica conocida

1. Desarrollo 100 % Codespace: clone Windows sin identidad Git para commits; GPG 403 en Codespace sin `commit.gpgsign=false`.
2. CLI `./hms` no arranca backend (solo frontend / status).
3. Push requiere sesión HMS + cuenta Google (`require_google_account` en prueba).
4. Two key dirs históricos: `/workspaces/.hms-secrets` (viejo) vs repo `.hms-secrets` (correcto) — mantener una sola fuente.
5. `page.tsx` monolítico (~1.8k+ líneas) dificulta rediseño — candidato natural al rediseño.
6. DoD incluye build/TS/validación formal que **aún no hay evidencia documentada** en repo.

---

## Checklist operativo “continuar mañana”

1. Codespace open → `git pull` en `sprint/01-estabilizacion-alertas-20260806`
2. Confirmar HEAD = `e017f11` o posterior
3. Cargar VAPID + backend + `bash ./hms start|repair frontend`
4. Ejecutar restorepoint pre-rediseño (**S1-P0-01**)
5. Decidir: (A) cerrar DoD Sprint 1 técnico, o (B) saltar a discovery de rediseño con el tag ya creado

---

## Definición de Done Sprint 1 (recordatorio)

Ver `docs/roadmap/2026-08-06-PLAN-SPRINTS-HMS-V2.md` sección Definition of Done.  
**Estado actual estimado:** ~70–75 % del DoD (funcional crítico de Push/Logística sí; cierre formal/build/tag final no).

---

## Commits clave de la línea

| Commit | Descripción |
|--------|-------------|
| `07a894a` | Prompt Maestro V2 + inicio Sprint 1 |
| `2dea5d9` | Logística 1 end-to-end |
| `ea863f9` | VAPID path + direction clasificador |
| `e017f11` | Viewport móvil + push por dispositivo |

Tag histórico previo: `checkpoint-hms-v2-master-20260806`
