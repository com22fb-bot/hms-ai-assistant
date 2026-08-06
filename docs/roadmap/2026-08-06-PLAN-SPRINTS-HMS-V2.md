# Plan de Sprints — HMS AI Assistant V2

**Inicio:** 2026-08-06
**Cadencia:** 14 días
**Rama base:** `feature/logistica-1`

## Resumen

| Sprint | Fechas | Objetivo | Gate |
|---|---|---|---|
| 1 | 6–19 ago 2026 | Estabilizar HMS Profesional y cerrar Logística 1 | Servicios, métricas, robot, Push y pruebas estables |
| 2 | 20 ago–2 sep | Clasificación y alertas confiables | Dedupe, explicación, feedback y precisión |
| 3 | 3–16 sep | Multicuenta Gmail | Varias cuentas aisladas e idempotentes |
| 4 | 17–30 sep | Seguridad SaaS | RLS, auditoría, retención y cero cruces |
| 5 | 1–14 oct | Microsoft 365 | Microsoft Graph funcional |
| 6 | 15–28 oct | Preparar piloto empresarial | Onboarding, métricas y soporte |
| 7 | 29 oct–11 nov | Piloto 3–5 empresas | Evidencia de utilidad y pago |
| 8 | 12–25 nov | Modelo común Profesional/Family | Arquitectura aprobada |
| 9 | 26 nov–9 dic | Fundación HMS Family | Hogares, permisos, Gmail y shell móvil |
| 10 | 10–23 dic | Alertas familiares | Categorías, Push, digest y explicación |
| 11 | 7–20 ene 2027 | Piloto 5–10 hogares | Precisión, privacidad, retención y precio |
| 12 | 21 ene–3 feb | Marca y comercialización | Go/no-go y planes |

# Sprint 1 — Estabilización y baseline profesional

**Fechas:** 6–19 de agosto de 2026
**Estado:** iniciado
**Rama recomendada:** `sprint/01-estabilizacion-alertas-20260806`

## Objetivo

Dejar HMS Profesional reproducible, estable y medible antes de añadir nuevas capacidades.

## Alcance

### Respaldo

- guardar Prompt Maestro V2;
- registrar Decisión Estratégica;
- guardar este roadmap;
- registrar estado del working tree;
- crear commit, push y tag;
- iniciar rama del Sprint 1.

### Backend

- `/health` estable;
- arranque reproducible en 8000;
- clasificador seguro sin errores;
- categorías y pendientes coherentes;
- sin reclasificación global accidental.

### Frontend

- arranque reproducible en 3000;
- no 404;
- diseño aprobado intacto;
- escritorio/tableta/móvil;
- panel, búsqueda, categorías y robot.

### Push/VAPID

- cargar VAPID sin exponer privada;
- estado real del servidor;
- registro de dispositivo;
- permiso Push;
- prueba habilitada;
- dedupe básico.

### Calidad

- Python compile;
- TypeScript;
- build;
- endpoints;
- puertos 3000/8000;
- bitácora y evidencia.

## No incluido

Microsoft 365, HMS Family, migraciones destructivas, facturación, WhatsApp, reclasificación total ni envío automático.

## Definition of Done

- frontend/backend reproducibles;
- ambos puertos 200;
- sin errores de compilación;
- métricas coherentes;
- robot correcto;
- Push activable y prueba funcional;
- sin duplicados evidentes;
- sin secretos en Git;
- documentación y tag publicados;
- validación visual del propietario.

## Reglas de los sprints

1. Cada sprint tiene rama, DoD, evidencia, commit y tag.
2. No mezclar dos sprints en el mismo commit.
3. No hacer commit funcional antes de validación visual.
4. No modificar datos productivos sin autorización.
5. El instalador se detiene ante cualquier error.
6. Todo instalador debe ser idempotente.
