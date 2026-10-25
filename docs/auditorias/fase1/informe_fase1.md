> **Nota de registro (24-oct-2026, issue #195):** este informe se generó sobre el commit `09f8ab0`, que **no está en origin/main**. Solo existe en la rama local `integracion/candidato-v1-dashboard` (incluye ownership-v1, ausente en main). La línea base de producción se repitió sobre origin/main `6ff2979` con `backend/tests/test_audit_phase1_regression.py`: ver `fase1/p0_resultados.md`. Las direcciones personales se reemplazaron por marcadores. `escenarios_fase1.py` usa `resolve_ownership`, que solo existe en `09f8ab0`; para main y la rama usa la prueba de regresión.

# DONEXTO: auditoría técnica, fase 1 (solo lectura)
24-oct-2026, hora de Chihuahua (UTC-6). Commit auditado: `09f8ab0fc39e7d980c20b2b0eff0c925e35fa34c` (main, 24-oct-2026 11:33 UTC-6). Clasificador `logistica1-triage-v4`. BRAIN_V1_ENABLED=0.
Sin cambios en el código del motor ni en main, sin push, PR, despliegue, migraciones ni acceso a Supabase. Se usó un worktree desechable (`fase1/wt`, detached), un cliente Supabase **falso en memoria** y datos sintéticos.

Antecedentes reutilizados (no se rehicieron): `politica_correos_propios.md` (NC1, commit 8053ef67), `auditoria_motor_casos.md`, `identificacion_casos/decisiones_hector_v1.md`. Desde 8053ef67, ownership-v1 ya está en main (commit 30d2086 y siguientes). Por eso NC1 se volvió a verificar: el auto-enviado ahora resuelve a `nota_propia` y no crea caso (escenario 9b).

## I. Resumen ejecutivo
**Estado general: REQUIERE CORRECCIONES.** Pruebas: 7 APROBADAS, 11 FALLIDAS, 0 NO EJECUTADAS, 0 BLOQUEADAS. Escenario 7 evaluado en los días 2, 3 y 4.

Riesgos críticos y altos:
1. **Alto (A/F):** las alertas de seguridad nunca crean caso. Un "¿Fuiste tú?" (esc. 1) queda como `notice`, y una actividad sospechosa de Google (esc. 12) queda como `automated`, sin caso.
2. **Alto (asociación):** `_find_case_for_message` asocia por `normalized_subject` como último recurso, sin comparar entidad, factura, referencia, importe ni fecha. Facturas distintas, cancelaciones ajenas y asuntos genéricos ("Hola") se pegan a casos abiertos (esc. 5, 14, 15, 18). Además, la clasificación sube el mensaje a `action_required` ("Continuación de una conversación con un caso abierto").
3. **Alto (D):** la identidad propia se calcula por cuenta y no por usuario. Un correo de propia-1@yahoo.example que llega al buzón propia2@gmail.com se trata como externo y crea caso (esc. 9a).
4. **Alto (C):** la regla de 3 días no existe. Los enviados nunca crean caso, sin importar la petición ni los días.
5. **Medio (E/B/G):** no hay bandeja técnica: un respaldo fallido crea caso de usuario (esc. 10). No existe cierre automático por recibo ni por cancelación. Un recibo o cancelación con caso abierto lo mantiene en `action_required`, en vez de tratarse como informativo.

Hechos verificados: los resultados vienen de ejecución real y se pueden reproducir (ver comandos). Un caso cerrado no se reasocia porque solo se buscan estados abiertos. Un enviado no crea caso. El auto-enviado con mayúsculas y espacios se reconoce como propio.
Pendiente: el comportamiento con datos reales de producción (no se accedió a la BD), los flujos de importación por proveedor de punta a punta y la muestra etiquetada (EVAL-01, bloqueada por Héctor).

## II. Matriz de hallazgos
| ID | Regla | Archivo:función | Líneas | Observado | Esperado | Sev. | Prueba | Corrección recomendada | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| H1 | A, F | safe_case_classifier.py:classify_message / _classify_known_vertical | 324-330 (SECURITY_NOTICE_TERMS→notice, actionable=False); 339-340 (automated) | "¿Fuiste tú?" queda en notice sin caso; la actividad sospechosa queda en automated sin caso | Caso de seguridad si pide confirmar o hay evidencia sospechosa | Alta | esc. 1, 12 | Detector explícito de "confirmar actividad / sospechoso" antes de las reglas informativas | VERIFICADO (ejecutado) |
| H2 | Asociación, B, G | case_engine.py:_find_case_for_message | 359-442 (orden: hilo → event_key → normalized_subject l.427-440) | Mismo asunto basta para asociar dentro del workspace | Asunto nunca suficiente; exigir hilo, Message-ID o identificadores (factura, ref., importe, entidad) | Alta | esc. 5, 14, 15, 18 | Quitar el fallback por asunto o exigirle un identificador coincidente; si no hay evidencia, "Requiere revisión" | VERIFICADO |
| H3 | Asociación, capas | safe_case_classifier.py:classify_message | 341-342 | Con existing_case, cualquier entrante no clasificado pasa a action_required (incluye recibo pagado y cancelación) | Clasificación independiente del caso; un informativo no reactiva ni cierra | Alta | esc. 4a, 13a | Separar las capas: clasificar primero sin existing_case y decidir la vinculación después | VERIFICADO |
| H4 | D | mail_direction.py:account_identity; safe_case_classifier.py:481 | 80-89 | La identidad = email de la cuenta + identity_aliases; la otra dirección propia de Héctor es "entrante" | Ambas direcciones propias a nivel usuario | Alta | esc. 9a | Identidad por workspace con las 2 direcciones confirmadas (requiere decisión y dato de Héctor) | VERIFICADO |
| H5 | D | mail_direction.py:normalize_address | 63-75 | En gmail.com quita puntos y +etiqueta (p.ropia2+x → propia2) | "Sin alias" salvo confirmación | Baja | esc. 9c | Documentar como equivalencia del proveedor o decidir si se acepta | VERIFICADO |
| H6 | C | safe_case_classifier.py:classify_message | 312-315 | propio_enviado sin caso → informational, siempre; no hay temporizador (rg "days/timedelta" sin lógica de seguimiento) | Caso con petición explícita + externo + 3 días sin respuesta | Alta | esc. 7 | Implementar el job de seguimiento con reloj inyectable | VERIFICADO (no implementado) |
| H7 | E | safe_case_classifier.py (sin ruta técnica) | 337-371 | Railway→automated, GitHub CI→notice, respaldo "urgente"→action_required con caso | Bandeja técnica del admin, sin caso de usuario | Media | esc. 10 | Clasificación "técnica" por remitente/dominio antes del puntaje | VERIFICADO |
| H8 | B, G | case_engine.py, case_repository.py:267-296 | — | No existe cierre automático; los cambios de estado son solo acciones de usuario | Cerrar solo con evidencia de la misma entidad/transacción | Media | esc. 4b, 13b | Implementar el cierre por evidencia solo después de H2 | VERIFICADO (no implementado) |
| H9 | Asociación | case_engine.py:_find_case_for_message | 383-389 | In-Reply-To/References solo se usan en mensajes propios; un entrante sin thread_id no se vincula por Message-ID | Usar In-Reply-To también en entrantes | Baja | esc. 17 | Extender `_find_case_by_reply_ids` a entrantes | VERIFICADO |
| H10 | D | — | — | GPT-6 escribió "no-confirmada@gmail.example"; en el repo aparece propia2@gmail.com (tests/test_protected_history_window.py:38). Probable errata | Confirmar | Info | esc. 9d | — | Documentado |

## III. Resultados de pruebas
Salida completa: `salida_escenarios.json`. "Caso" = actionable=True o vinculado a un caso.
| # | Entrada (sintética) | Esperado | Observado | Estado |
|---|---|---|---|---|
| 1 | Google: "¿Fuiste tú? Confirma la actividad" | Caso de seguridad | notice/80, sin caso | FALLIDA |
| 2 | Google: acceso informativo | Aviso sin caso | notice, sin caso | APROBADA |
| 3 | Recibo "Pagada, saldo $0.00" sin caso | Informativo, sin caso | review/30, sin caso | APROBADA (con nota: queda en revisión, no en informativo) |
| 4 | Recibo con caso de cargo fallido abierto | Informativo; cierre solo con evidencia | action_required (continuación); no hay cierre; el asunto distinto no asocia | FALLIDA |
| 5 | "Pago" de otra entidad, mismo asunto que el caso abierto | No asociar | Asociado a C-f2 | FALLIDA |
| 6 | Enviado con petición y respuesta antes de 2 días | Sin caso | informational, sin caso (no existe temporizador) | APROBADA (trivial: no hay lógica) |
| 7 | Enviado con petición externa a los días 2, 3 y 4 | Día 2 sin caso; días 3 y 4 con caso | Los 3 días: informational, sin caso; no hay lógica de días | FALLIDA |
| 8 | Enviado sin petición | Sin caso | informational, sin caso | APROBADA |
| 9 | a) yahoo→buzón gmail, b) "  Propia-1@YAHOO.example " a sí mismo, c) alias gmail, d) apropia2 | Propio en todos | a) entrante + action_required (caso); b) nota_propia sin caso; c) se normaliza a propia2; d) entrante | FALLIDA (por a) |
| 10 | Railway / GitHub CI / respaldo fallido | Bandeja técnica, sin caso | automated / notice / **action_required con caso** | FALLIDA |
| 11 | Login informativo de Google | Aviso, no phishing | notice, sin caso | APROBADA |
| 12 | Intento de login sospechoso, cambiar contraseña | Caso | automated/10, sin caso | FALLIDA |
| 13 | Cancelación confirmada con caso de suscripción abierto | Informativo; cierre solo verificable | action_required (continuación); sin cierre | FALLIDA |
| 14 | Cancelación de otra empresa, mismo asunto | No asociar | Asociada a C-gym | FALLIDA |
| 15 | Factura B, mismo asunto que factura A, otro hilo | No asociar | Asociada a C-A | FALLIDA |
| 16 | "Re: Factura disponible" contra un caso **cerrado** | No reabrir | Sin asociar (solo _OPEN_STATUSES, l.20-27) | APROBADA |
| 17 | Respuesta en el mismo hilo; propio con In-Reply-To | Asociar | Asociado (C-h, C-r); un entrante sin hilo con In-Reply-To no se asocia (H9) | APROBADA |
| 18 | "Hola"/"ok" sin datos, caso "Hola" abierto | No asociar; revisión | Clasificación review, pero asociado a C-g por asunto | FALLIDA |

Limitaciones: el cliente falso no reproduce RLS, triggers ni el orden real de la BD. En los escenarios 4a y 13a, existing_case se inyectó directamente. No se ejecutó `classify_pending_messages` ni `process_message` de punta a punta (escriben en la BD). No se verificaron importadores por proveedor (E: "distintos proveedores").

### Reproducir
```
cd /workspace/hms-ai-assistant && git worktree add --detach /workspace/cerebro/auditoria_forense/fase1/wt 09f8ab0
cd /workspace/cerebro/auditoria_forense/fase1/wt/backend
env -i PATH=/usr/bin:/bin HOME=/tmp BRAIN_V1_ENABLED=0 SUPABASE_URL=http://127.0.0.1:9 SUPABASE_SECRET_KEY=dummy PYTHONPATH=. \
  /workspace/venv-audit/bin/python ../../escenarios_fase1.py
```

## IV. Correcciones priorizadas (todas son RECOMENDACIÓN; ninguna está implementada)
- **P0:** H1, detección de alertas que piden confirmar o reportan actividad sospechosa → caso de seguridad, antes de cualquier regla informativa. H2, eliminar la asociación solo por asunto.
- **P1:** H3, separar las 3 capas (hoy, la clasificación depende de existing_case). H4, identidad propia por usuario con las 2 direcciones. H6, regla C con reloj inyectable y pruebas de los días 2, 3 y 4. H7, bandeja técnica.
- **P2:** H8, cierre por evidencia (después de H2). H9, In-Reply-To en entrantes. H5, documentar la normalización de Gmail. Pruebas de regresión con estos 18 escenarios.

## V. Decisiones pendientes de Héctor
1. Confirmar la dirección exacta: ¿propia2@gmail.com (la del repo) o no-confirmada@gmail.example (la del texto de GPT-6)?
2. Autorizar que la identidad propia se configure a nivel usuario (las 2 direcciones) y no por buzón.
3. ¿Se acepta que en Gmail los puntos y el "+etiqueta" se consideren la misma dirección?
4. Autorización para pasar de auditoría a cambios (ningún cambio se hizo).
