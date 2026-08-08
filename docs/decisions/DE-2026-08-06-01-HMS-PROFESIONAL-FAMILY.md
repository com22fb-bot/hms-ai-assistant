# DE-2026-08-06-01 — Motor común HMS Profesional / HMS Family

**Estado:** aprobada conceptualmente.
**Impacto inmediato:** documentación y planificación; no autoriza desarrollo familiar ni migraciones.

## Decisión

HMS utilizará un motor central compartido y dos experiencias separadas:

- HMS Profesional.
- HMS Family / HMS Hogar.

## Núcleo compartido

Conectores, sincronización, conversaciones, clasificación, extracción, reglas, favoritos, notificaciones, búsqueda, auditoría, explicaciones y acceso al mensaje original.

## Separación

Profesional: workspaces, equipos, casos, responsables, SLA y métricas operativas.

Family: hogares, miembros, privacidad individual, alertas domésticas, agenda y resúmenes.

## Privacidad familiar

El administrador no obtiene acceso automático a todo. Cada cuenta tiene propietario. Las alertas pueden ser privadas o compartidas. Finanzas, salud, viajes y 2FA tendrán protección especial. Todo acceso y compartición será explícito y auditable.

## Condición para comenzar Family

1. HMS Profesional estable.
2. Clasificación y Push confiables.
3. Aislamiento por usuario/workspace.
4. Multicuenta.
5. Microsoft 365.
6. Piloto empresarial.
