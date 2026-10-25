# P0 #195 · PR #196 — Corrección de OBS-01 y OBS-02

Fecha: 25-oct-2026 (CDMX, UTC-6). Rama: `fix/audit-phase1-security-case-linking`.
Base `6ff2979` · head anterior `d7c7ed9f5cbfab7d8826e5bb2a22eec5dd2c2768` · corrección `8963784d068e9ef83b136e2e5758544e300ccb75`.
Alcance: solo OBS-01 y OBS-02 del dictamen consolidado de ASTRA (issuecomment-6401608864). OBS-03 a OBS-06 quedan en fase posterior; `find_case_v1` (OBS-04) **no** se modificó.

## Cambios
- `backend/app/services/case_engine.py`
  - Nuevo `_scope_guard()`: rechaza si `message.account_id` (o el de la fila en BD si falta) ≠ cuenta indicada, o si la cuenta (`communication_accounts`) no pertenece al workspace indicado. Si el mensaje ya tiene vínculo en `case_messages`, devuelve ese `case_id`.
  - `process_message()`: llama al guard antes de cualquier escritura. Rechazo → `("", "rejected")` + `logger.warning`, sin escrituras. Ya vinculado → `(case_id, "already_linked")`, sin crear casos ni vínculos (OBS-02). Caso destino de otro workspace → `("", "rejected")` antes de actualizar el caso o insertar el vínculo.
- `backend/tests/test_p0_write_paths_isolation.py` (8 pruebas unitarias, FakeClient en memoria que registra inserciones).
- Sin migraciones, sin cambios de esquema/RLS, sin `BRAIN_V1_ENABLED`, sin ownership-v1, sin B/C/E/G.

## OBS-01 — aislamiento en process_message
| Prueba | Antes (d7c7ed9) | Después (8963784) |
|---|---|---|
| a3: mensaje de A1 procesado como WB/B1 → `rejected`, 0 casos, 0 vínculos | FALLA | PASA |
| b3: mensaje de A2 procesado como A1 (mismo WA) | FALLA | PASA |
| cuenta no pertenece al workspace declarado | FALLA | PASA |
| caso destino en otro workspace (sin escrituras, recuento de casos igual) | FALLA | PASA |
| contexto válido sigue vinculando | PASA | PASA |
| respuesta por In-Reply-To y por References sigue vinculando | PASA | PASA |

Integración local (PostgreSQL 17 + PostgREST, harness `rutas_escritura.py`, base nueva `p0obs`): a3 `rejected`, b3 `rejected` (antes: ligaban a caso de WB / A1). a1, a2, b1, b2 sin cambio (`created` en su propio alcance).

## OBS-02 — sin caso huérfano al reprocesar
| Prueba | Antes | Después |
|---|---|---|
| c1: mensaje ya ligado → `already_linked`, 0 casos nuevos, 0 vínculos nuevos | FALLA | PASA |
| reprocesar mensaje recién creado: 1 caso, 1 vínculo, vínculo original | FALLA | PASA |
| un mensaje nuevo sigue creando caso | — | PASA |

Integración local: c1 `already_linked`, casos 9 → 9 (antes 10 → 11), vínculo original conservado. c2: la BD sigue rechazando un segundo vínculo (23505).

## Comandos (sin secretos)
```
cd backend; export PYTHONPATH=.
E="env -u SUPABASE_URL -u SUPABASE_SECRET_KEY -u SUPABASE_DB_URL -u DATABASE_URL FRONTEND_ORIGINS=https://app.donexto.com"
$E python -m pytest -q tests/test_p0_write_paths_isolation.py            # antes: git stash del fix → 6 failed, 2 passed
$E python -m pytest -q tests/test_p0_reply_ids_isolation.py tests/test_audit_phase1_regression.py
$E python -m pytest -q tests
```
Integración: igual que `integracion_informe.md` (initdb en /tmp, setup_db.sh, seed.sql, PostgREST :3904, gateway :3914, JWT efímero local); URL obligatoriamente 127.0.0.1.

## Resultados
- Unitarias OBS: antes 6 failed / 2 passed; después 8 passed.
- Regresión P0 (aislamiento + fase 1): 34 passed, 3 xfailed = regresión fase 1 (26 passed, 3 xfailed, igual que antes) + 8 de aislamiento reply_ids (8 passed, igual que antes). Sin regresión.
- Backend completo: 789 passed, 1 skipped, 7 xfailed (antes 779 passed + 2 fallos OAuth por falta de FRONTEND_ORIGINS; con la variable pasan; +8 nuevas).

## Limitaciones y riesgos
- Integración solo local; no se probó el proyecto remoto ni OAuth end-to-end. Entorno con 5 migraciones fallidas por deriva y columna `triage_category` añadida (OBS-06).
- El harness no mide recuentos en a3/b3; los recuentos sin escritura se verifican en las unitarias.
- Los llamadores cuentan cualquier estado ≠ `created` como "linked"; `rejected`/`already_linked` pueden inflar ese contador informativo (no afecta datos).
- `_apply_rule_to_message` marca `case_processed=True` aunque `process_message` rechace (OBS-05, fase posterior).
- c3 (UPDATE directo) y v1 (`find_case_v1`) siguen igual: OBS-03/OBS-04, fase posterior; V1 apagado.

## Limpieza
Clúster local, base `p0obs`, PostgREST, gateway y secretos efímeros eliminados. Logs en `cerebro/.../integracion/logs/obs_*`.

PR #196 en draft, sin merge ni despliegue.
