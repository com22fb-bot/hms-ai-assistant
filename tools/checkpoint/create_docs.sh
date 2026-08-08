#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; source "$SCRIPT_DIR/lib.sh"
ROOT="$(repo_root)"; cd "$ROOT"; TODAY="${1:-$(date +%Y-%m-%d)}"
mkdir -p docs/{vision,architecture,adr,roadmap,project-book,restorepoints,changelog}
cat > "docs/vision/${TODAY}_VISION_2_HMS_AI_PLATFORM.md" <<'EOF'
# Visión estratégica 2.0 — HMS AI Assistant

HMS AI Assistant será una plataforma SaaS de inteligencia para comunicaciones empresariales.

No será otro cliente de correo. Su propósito será responder:

> ¿Qué requiere mi atención en este momento?

## Principios

- Panel de Control Inteligente como pantalla principal.
- IA como copiloto operativo, no solo chatbot.
- Plataforma web responsiva, PWA y aplicaciones futuras sobre el mismo backend.
- Arquitectura multi-tenant.
- Mercado principal: Estados Unidos.
- Cuatro temas configurables; el primero será **Fado Black**.
- WhatsaPilot queda como posible producto futuro, no como prioridad actual.

## Prioridad de ejecución

1. Sincronización incremental de Gmail.
2. Lectura paginada desde Supabase.
3. Motor de análisis y clasificación.
4. Dashboard Inteligente.
5. Tareas y seguimientos.
6. Temas configurables.
7. Arquitectura comercial multi-tenant.
EOF
cat > docs/project-book/PRODUCT_BOOK.md <<'EOF'
# Libro del Proyecto — HMS AI Assistant

## Problema

Las empresas reciben más comunicaciones de las que pueden procesar oportunamente. Solicitudes, pagos, documentos, compromisos y riesgos quedan ocultos dentro del volumen.

## Propuesta de valor

HMS AI Assistant convierte comunicaciones en prioridades, tareas, compromisos, alertas, riesgos, oportunidades, acciones sugeridas e indicadores.

## Lo que no construiremos

- Una copia de Gmail u Outlook.
- Una bandeja de entrada sin inteligencia.
- Un chatbot aislado del flujo operativo.
- Aplicaciones separadas con lógica duplicada.
- Automatizaciones sin control del usuario.

## Estado actual

El proyecto utiliza FastAPI, Next.js, Gmail OAuth y Supabase. El siguiente paso funcional es completar la sincronización progresiva y alimentar el Dashboard Inteligente.
EOF
cat > docs/roadmap/ROADMAP.md <<'EOF'
# Roadmap — HMS AI Assistant

## Fase 1 — Ingesta y almacenamiento
- [x] FastAPI
- [x] Next.js
- [x] Gmail OAuth
- [x] Supabase
- [x] Sincronización inicial
- [ ] Paginación de Gmail
- [ ] Sincronización incremental
- [ ] Endpoint de mensajes almacenados
- [ ] Indicador de progreso y recuperación

## Fase 2 — Inteligencia
- [ ] Resúmenes y clasificación
- [ ] Detección de solicitudes, compromisos, fechas y cantidades
- [ ] Puntaje y explicación de prioridad
- [ ] Acciones sugeridas

## Fase 3 — Dashboard
- [ ] Requiere mi atención
- [ ] Esperando mi respuesta
- [ ] Esperando respuesta de terceros
- [ ] Tareas, vencimientos, riesgos e indicadores

## Fase 4 — Plataforma comercial
- [ ] Organizations, memberships, roles y permisos
- [ ] Aislamiento multi-tenant
- [ ] Planes, límites, facturación y auditoría
EOF
cat > docs/architecture/PLATFORM_ARCHITECTURE.md <<'EOF'
# Arquitectura de plataforma

Gmail/Microsoft 365 → OAuth → sincronización incremental → Supabase/PostgreSQL → IA → prioridades/tareas/alertas → Dashboard Inteligente.

- Frontend: Next.js, diseño responsivo, temas y PWA.
- Backend: FastAPI, OAuth, sincronización, análisis, tareas y preferencias.
- Persistencia: Supabase/PostgreSQL con evolución multi-tenant.
- IA: clasificación, extracción, priorización y acciones sugeridas.
- Tema inicial: **Fado Black** mediante tokens de diseño.
EOF
cat > docs/adr/ADR-001-CENTRO-INTELIGENTE.md <<'EOF'
# ADR-001 — Centro Inteligente de Comunicaciones
Estado: Aprobada

HMS AI Assistant será un Centro Inteligente de Operaciones de Comunicaciones. El mensaje completo será contexto; la experiencia principal mostrará prioridades, tareas, riesgos y acciones.
EOF
cat > docs/adr/ADR-002-MERCADO-USA.md <<'EOF'
# ADR-002 — Mercado principal: Estados Unidos
Estado: Aprobada

La plataforma se diseñará como SaaS para el mercado estadounidense, con soporte progresivo para inglés, español, Gmail, Microsoft 365, suscripciones y seguridad empresarial.
EOF
cat > docs/adr/ADR-003-SAAS-MULTITENANT.md <<'EOF'
# ADR-003 — SaaS multi-tenant
Estado: Aprobada

La arquitectura evolucionará hacia organizaciones, usuarios, memberships, roles, cuentas conectadas, preferencias y aislamiento lógico de datos.
EOF
cat > docs/adr/ADR-004-DASHBOARD.md <<'EOF'
# ADR-004 — Dashboard Inteligente
Estado: Aprobada

El Dashboard Inteligente será la pantalla principal y no una bandeja de entrada tradicional.
EOF
cat > docs/adr/ADR-005-FADO-BLACK.md <<'EOF'
# ADR-005 — Temas configurables
Estado: Aprobada

Existirán cuatro temas configurables. El primero será Fado Black. La preferencia deberá guardarse por usuario.
EOF
cat > docs/adr/ADR-006-IA-COPILOTO.md <<'EOF'
# ADR-006 — IA como copiloto
Estado: Aprobada

La IA analizará proactivamente comunicaciones, resumirá, clasificará, priorizará y propondrá acciones y respuestas.
EOF
cat > docs/adr/ADR-007-RESPONSIVA.md <<'EOF'
# ADR-007 — Plataforma responsiva
Estado: Aprobada

La misma aplicación funcionará en móvil, tablet y escritorio, compartiendo backend, datos y preferencias.
EOF
cat > docs/adr/ADR-008-WHATSAPILOT-FUTURO.md <<'EOF'
# ADR-008 — WhatsaPilot queda para una fase futura
Estado: Aprobada

WhatsaPilot no recibirá recursos del sprint actual. La prioridad es HMS AI Assistant.
EOF
cat > docs/vision/DECISION_LOG.md <<EOF
# Registro de decisiones

| ADR | Fecha | Decisión | Estado |
|---|---|---|---|
| ADR-001 | $TODAY | Centro Inteligente de Comunicaciones | Aprobada |
| ADR-002 | $TODAY | Mercado principal: Estados Unidos | Aprobada |
| ADR-003 | $TODAY | SaaS multi-tenant | Aprobada |
| ADR-004 | $TODAY | Dashboard Inteligente | Aprobada |
| ADR-005 | $TODAY | Fado Black y cuatro temas | Aprobada |
| ADR-006 | $TODAY | IA como copiloto | Aprobada |
| ADR-007 | $TODAY | Plataforma responsiva | Aprobada |
| ADR-008 | $TODAY | WhatsaPilot queda para el futuro | Aprobada |
EOF
log "Documentación estratégica creada"
