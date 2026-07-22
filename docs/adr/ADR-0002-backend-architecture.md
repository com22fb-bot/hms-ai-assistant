# ADR-0002 — Evolución de la arquitectura del backend

**Estado:** Aprobado

**Fecha:** 2026-07-21

---

## Contexto

El backend comenzó con una estructura tradicional basada en capas:

```
app/
├── api/
├── services/
├── database/
└── core/
```

Esta estructura es adecuada para un MVP, pero el proyecto evolucionará para soportar:

- múltiples proveedores de correo;
- múltiples workspaces;
- IA;
- auditoría;
- dispositivos;
- permisos;
- notificaciones;
- tareas.

Conforme el sistema crezca, una organización por capas hará más difícil localizar y mantener el código.

---

## Decisión

La arquitectura evolucionará gradualmente hacia una organización por dominios de negocio.

La estructura objetivo será:

```
app/
├── auth/
├── profiles/
├── workspaces/
├── mail/
├── ai/
├── tasks/
├── alerts/
├── audit/
├── devices/
├── notifications/
├── common/
├── database/
└── core/
```

Cada dominio contendrá su propia API, servicios, modelos y esquemas.

---

## Estrategia de migración

No se realizará una refactorización masiva.

La migración será incremental:

### Sprint 0

- Documentación.
- Modelo de datos.
- ADRs.

### Sprint 1

- Crear `workspaces`.
- Migrar `gmail` al dominio `mail`.

### Sprint 2

- Incorporar `audit`.
- Incorporar `devices`.
- Incorporar `notifications`.

---

## Consecuencias

### Ventajas

- Mayor cohesión.
- Mejor mantenibilidad.
- Facilita pruebas unitarias.
- Reduce dependencias entre módulos.
- Facilita agregar nuevos proveedores.

### Desventajas

- Incremento inicial en el número de carpetas.
- Requiere disciplina para mantener los límites entre dominios.

---

## Estado

Esta decisión queda aprobada y servirá como guía para todas las refactorizaciones futuras del backend.