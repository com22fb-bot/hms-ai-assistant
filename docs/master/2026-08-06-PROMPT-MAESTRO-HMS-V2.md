# HMS AI Assistant — Prompt Maestro V2

**Fecha:** 2026-08-06
**Rama:** `feature/logistica-1`
**Estado:** respaldo estratégico; no autoriza cambios de código ni de datos productivos.

## 1. Origen

HMS AI Assistant nació para resolver correos importantes sin atender, solicitudes repetidas, compromisos olvidados, pagos detenidos y falta de visibilidad sobre quién esperaba respuesta. La visión nunca fue construir otro cliente de correo, sino una capa inteligente que detecta, clasifica, resume y convierte mensajes en acciones y seguimiento.

## 2. Evolución aprobada

Se adopta un motor común con dos experiencias:

- **HMS Profesional:** casos operativos, responsables, espera interna/externa, pagos, documentos, tareas y métricas.
- **HMS Family / HMS Hogar:** seguridad, finanzas y logística doméstica a partir de varias cuentas de correo.

No se duplicará el motor y tampoco se mezclarán prematuramente interfaz, lenguaje, permisos ni modelo comercial.

## 3. Prompt Maestro consolidado

### Libro Maestro

Actualizar conceptualmente el Libro Maestro con:

1. visión empresarial original;
2. oportunidad B2C y familiar;
3. motor común y dos experiencias;
4. problemas por modalidad;
5. funciones compartidas;
6. funciones separadas;
7. privacidad familiar;
8. notificaciones inmediata, resumen y silenciosa;
9. riesgos de mezclar mercados;
10. secuencia de desarrollo;
11. hipótesis de precio;
12. datos pendientes de validación.

### MVP HMS Family

Objetivo: supervisar varias cuentas y avisar solo sobre información que afecte seguridad, finanzas y logística del hogar.

Debe contemplar:

- múltiples cuentas;
- Gmail inicialmente;
- panel móvil;
- Push;
- cargos y pagos;
- servicios del hogar;
- entregas;
- escuela;
- salud;
- viajes;
- citas;
- suscripciones;
- favoritos;
- resumen diario;
- privacidad entre miembros;
- explicación de alertas;
- acceso al mensaje original.

Debe definir perfil, problemas, historias, alcance, exclusiones, onboarding, navegación, estados, permisos, métricas, riesgos y piloto con 5–10 familias.

### Motor de notificaciones

No notificar cada correo.

- Nivel 1: inmediata.
- Nivel 2: resumen periódico.
- Nivel 3: silenciosa.

Categorías críticas: seguridad, 2FA, cargos, transferencias, pagos rechazados, facturas, servicios, entregas, escuela, salud, viajes, VIP y temas favoritos.

Debe definir reglas deterministas antes de IA, uso de IA, umbrales, deduplicación, frecuencia, horarios silenciosos, escalamiento, agrupamiento, feedback, auditoría, datos sensibles y pruebas.

### Arquitectura futura

Contexto actual: Next.js, FastAPI, Supabase, Gmail, nube, repositorio `com22fb-bot/hms-ai-assistant`, rama `feature/logistica-1`.

Debe soportar varias cuentas, proveedores, hogares, miembros, roles, workspaces, privacidad, reglas, notificaciones, casos, tareas, eventos, auditoría, RLS, migración, adaptadores, seguridad y retención.

### Mobile-first

No será una bandeja tradicional. La pantalla principal responderá: **¿Qué ocurrió hoy que afecta a mi hogar?**

Tarjetas: cargos, pagos, entregas, escuela, salud, viajes, servicios, citas, suscripciones y documentos. Cada tarjeta mostrará categoría, nivel, resumen, motivo, fecha, cantidad, miembro, acción y enlace al original.

### Investigación competitiva

Investigar asistentes familiares, household management, paquetería, finanzas, suscripciones, escuela, viajes, multi-inbox y AI email triage. Separar directos, parciales, sustitutos y cerrados. Registrar empresa, país, año, estado, precio, compatibilidad, funciones, IA, notificaciones, diferenciación, limitaciones y similitud.

## 4. Protocolo obligatorio de implementación

Antes de modificar archivos:

1. auditar repositorio;
2. confirmar rama;
3. revisar cambios sin commit;
4. identificar archivos;
5. comprobar implementación previa;
6. respaldar;
7. no sobrescribir diseño;
8. no eliminar funciones;
9. no tocar datos productivos sin autorización;
10. no reclasificar globalmente;
11. entregar archivos completos;
12. usar instaladores idempotentes;
13. validar Python, TypeScript, build, endpoints y puertos 3000/8000;
14. detenerse ante errores;
15. no hacer commit funcional antes de validación visual.

Reglas adicionales: desarrollo solo en nube, no exponer secretos, no borrar datos, no declarar terminada una función sin validación, mantener restaurabilidad y tratar datos de mercado no verificados como hipótesis.

## 5. Secuencia aprobada

```text
HMS Profesional estable
        ↓
Motor de clasificación y alertas confiable
        ↓
Multicuenta
        ↓
Microsoft 365
        ↓
Piloto empresarial
        ↓
Prototipo HMS Family
        ↓
Piloto con hogares
        ↓
Decisión de marca y comercialización
```

## 6. Diferencia inicio vs. 2026-08-06

**Inicio:** asistente de pendientes, Gmail, una necesidad empresarial, clasificación básica y prototipo rápido.

**Actual:** SaaS multicuenta/multiproveedor, motor común, casos, espera interna/externa, reglas explicables, Push selectivo, seguridad por workspace, Microsoft 365 futuro, edición familiar futura, auditoría, privacidad y pilotos antes de comercializar.
