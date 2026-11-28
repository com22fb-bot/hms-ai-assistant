# Índice de auditorías DONEXTO

| Fecha (UTC-6) | Auditoría | Base | Archivos | Estado |
|---|---|---|---|---|
| 24-oct-2026 | Fase 1: identificación de casos, remitentes y asociación (reglas A–G) | `09f8ab0` (rama local integracion/candidato-v1-dashboard; no está en main) | [fase1/informe_fase1.md](fase1/informe_fase1.md), [fase1/escenarios_fase1.py](fase1/escenarios_fase1.py), [fase1/salida_escenarios.json](fase1/salida_escenarios.json) | Diagnóstico entregado |
| 24-oct-2026 | Fase 1, P0: alertas de seguridad (P0.1), asociación por evidencia (P0.2) e identidad propia (H4) | origin/main `6ff2979` | [fase1/p0_resultados.md](fase1/p0_resultados.md), `backend/tests/test_audit_phase1_regression.py` | LISTO PARA REVISIÓN (PR vinculado a #195) |
| 27-nov-2026 | CONTACTS_V1 F0+F1: interfaz de identidad y modelo canónico de participantes | origin/main `9ee269e` | [contactos/F0_F1.md](contactos/F0_F1.md), `backend/tests/test_contacts_f0_identity.py`, `backend/tests/test_contacts_f1_registry.py`, `backend/tests/db/test_contacts_f1_schema.py` | LISTO PARA REVISIÓN (sin fusionar) |

Registro central: issue #195. Todas las pruebas son unitarias con un cliente Supabase falso. Ninguna se ejecuta contra servicios reales.
