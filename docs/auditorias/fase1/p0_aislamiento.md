# P0 — Aislamiento en la vinculación por In-Reply-To/References (issue #195, PR #196)

- Estado: LISTO PARA REVISIÓN
- Rama: `fix/audit-phase1-security-case-linking`
- Commit auditado (padre): `4d540e5415d9c9a7bc4c640c1c49589e5ec3a000`
- Base: `origin/main` `6ff29794ce34b163e09a1c32646e5f70a0c70464`

## Defecto
`_find_case_by_reply_ids()` consultaba `intelligent_cases` solo por `id IN (case_ids)` y estado abierto,
sin restringir por `workspace_id` / `account_id`. Una fila de `case_messages` que apuntara a un caso de
otro workspace o cuenta permitía recuperarlo.

## Corrección (solo `backend/app/services/case_engine.py`)
- `_find_case_for_message()` propaga `workspace_id` a `_find_case_by_reply_ids()`.
- `_find_case_by_reply_ids()` usa el mismo criterio de alcance: `workspace_id` si existe, si no `account_id`.
- La consulta a `intelligent_cases` añade `.eq(scope_column, scope_value)` y conserva el filtro de estados abiertos.
- Defensa en profundidad: se verifica en la fila devuelta que su alcance y estado coinciden; si no, `None`.
- Esquema (migraciones, solo lectura): `intelligent_cases.workspace_id NOT NULL`, `account_id` nullable;
  `case_messages(case_id, message_id)`. No se requiere migración.

## Pruebas (`backend/tests/test_p0_reply_ids_isolation.py`, unitarias, cliente falso)
| Prueba | 4d540e5 | Corrección |
|---|---|---|
| positivo mismo workspace | pasa | pasa |
| negativo entre workspaces | **FALLA** | pasa |
| negativo entre cuentas (sin workspace) | **FALLA** | pasa |
| caso cerrado no se recupera | pasa | pasa |
| regresión In-Reply-To / References × entrante / saliente (4) | pasa | pasa |

- Regresión P0 `test_audit_phase1_regression.py`: 26 passed, 3 xfailed (igual que antes).
- Suite backend: 779 passed, 2 failed, 7 xfailed. Los 2 fallos son preexistentes (`test_microsoft_oauth`, ya en 4d540e5 y main). +8 pruebas nuevas, 0 fallos nuevos.

## Limitaciones
- No se accedió a producción ni a Supabase real; no se probaron políticas RLS ni relaciones reales.
- La búsqueda del mensaje padre en `communication_messages` sigue limitada a `account_id` (sin cambio).
- No se resuelven los pendientes C, E, B o G. La auditoría completa no queda cerrada.
