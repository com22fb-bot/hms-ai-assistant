# Sprint 4.8 — Estabilización y contención

## Objetivo

Restablecer la confianza en los datos visibles y detener la creación automática de casos falsos mientras se desarrolla el clasificador v2.

## Criterios de aceptación

1. `/cases/dashboard` devuelve conteos exactos, no un máximo de 200.
2. `/cases/process` devuelve HTTP 503 mientras el clasificador v1 está en mantenimiento.
3. La sincronización durable se crea con `process_cases=false` por defecto.
4. El frontend deja de afirmar que la IA está activa.
5. Los botones sin implementación real no aparecen.
6. Lint y build de Next.js terminan sin errores.
7. Frontend y backend responden HTTP 200 después del reinicio.

## Conservación de datos

No se ejecutan migraciones ni operaciones destructivas. Los correos, casos, relaciones y eventos permanecen intactos.
