# ADR-0001 — Adoptar el modelo de Workspaces

**Estado:** Aprobado  
**Fecha:** 2026-07-21

## Contexto

La plataforma debe atender tanto a usuarios particulares como a empresas.

Existen empresas donde varias personas trabajan sobre un mismo buzón de correo (por ejemplo, ventas@empresa.com), mientras que los usuarios particulares administran únicamente sus cuentas personales.

Era necesario definir una arquitectura que permitiera soportar ambos escenarios sin mantener dos aplicaciones distintas.

## Decisión

La plataforma adoptará el concepto de **Workspace** como unidad principal de aislamiento.

Se definen dos tipos:

- Personal
- Organization

Todo usuario tendrá automáticamente un Workspace Personal al registrarse.

Un usuario podrá pertenecer además a uno o más Workspaces Organization mediante invitación o asignación.

## Consecuencias

### Ventajas

- Una sola plataforma para todos los tipos de clientes.
- Escalabilidad.
- Multiempresa.
- Multiusuario.
- Soporte para buzones compartidos.
- Aislamiento de información.
- Facilita el crecimiento futuro.

### Desventajas

- Mayor complejidad inicial del modelo de datos.
- Requiere tablas adicionales para membresías y permisos.

## Estado

Esta decisión queda adoptada como base de la arquitectura de HMS AI Assistant.