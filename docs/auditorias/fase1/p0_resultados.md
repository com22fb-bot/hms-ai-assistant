# Fase 1 P0: resultados antes y después (issue #195)
Fecha: 24-oct-2026 (UTC-6). "Antes" = origin/main `6ff2979`; "después" = rama `fix/audit-phase1-security-case-linking`.
Tipo: **unitarias** con un cliente Supabase falso. Ninguna se ejecuta contra servicios reales ni es end-to-end.
Comando: `cd backend && PYTHONPATH=. BRAIN_V1_ENABLED=0 SUPABASE_URL=http://127.0.0.1:9 SUPABASE_SECRET_KEY=dummy python -m pytest -q tests/test_audit_phase1_regression.py -rA`

Totales: antes **13 failed / 13 passed / 3 xfailed**; después **26 passed / 3 xfailed / 0 failed**.
XFAIL (strict) = regla no implementada y fuera del alcance de P0: C (3 días, días 3 y 4) y E (bandeja técnica, respaldo). Siguen fallando y así lo documentan.

## 18 escenarios
| Escenario | Prueba(s) | Antes | Después |
|---|---|---|---|
| 1 Google pide confirmar actividad | `e01_google_pide_confirmar_actividad_crea_caso` | FAILED | PASSED |
| 2 Google informativa | `e02_google_informativa_queda_aviso` | PASSED | PASSED |
| 3 Recibo pagado sin caso | `e03_recibo_pagado_sin_caso_previo` | PASSED | PASSED |
| 4 Recibo pagado con cargo fallido (misma ref.) | `e04_recibo_pagado_con_caso_de_cargo_fallido_misma_referencia` | FAILED | PASSED |
| 5 Recibo de otra entidad, mismo asunto | `e05_recibo_de_otra_entidad_mismo_asunto_no_se_asocia` | FAILED | PASSED |
| 6 Enviado con petición, respuesta <2 días | `e06_enviado_con_peticion_y_respuesta_antes_de_2_dias` | PASSED | PASSED |
| 7 Enviado sin respuesta días 2/3/4 | `e07_dia2_sin_caso`<br>`e07_dias_3_y_4_crea_caso[3]`<br>`e07_dias_3_y_4_crea_caso[4]` | PASSED<br>XFAIL<br>XFAIL | PASSED<br>XFAIL<br>XFAIL |
| 8 Enviado sin petición | `e08_enviado_sin_peticion` | PASSED | PASSED |
| 9 Dirección propia (a: entre buzones; b: nota propia) | `e09a_entre_buzones_propios_no_es_externo`<br>`e09b_nota_propia_mayusculas_espacios` | FAILED<br>PASSED | PASSED<br>PASSED |
| 10 CI/Railway/respaldo | `e10a_railway_y_ci_no_crean_caso`<br>`e10b_respaldo_fallido_no_crea_caso_de_usuario` | PASSED<br>XFAIL | PASSED<br>XFAIL |
| 11 Login informativo | `e11_login_informativo_no_es_caso_ni_phishing` | PASSED | PASSED |
| 12 Login sospechoso | `e12_login_sospechoso_crea_caso` | FAILED | PASSED |
| 13 Cancelación relacionada | `e13_cancelacion_relacionada_no_es_accion_pendiente` | FAILED | PASSED |
| 14 Cancelación ajena | `e14_cancelacion_ajena_mismo_asunto_no_se_asocia` | FAILED | PASSED |
| 15 Dos facturas mismo asunto | `e15_dos_facturas_distintas_mismo_asunto` | FAILED | PASSED |
| 16 Caso cerrado, coincidencia superficial | `e16_coincidencia_con_caso_cerrado_no_reabre` | PASSED | PASSED |
| 17 Respuesta mismo hilo / In-Reply-To | `e17a_respuesta_mismo_hilo`<br>`e17b_entrante_con_in_reply_to_sin_hilo` | PASSED<br>FAILED | PASSED<br>PASSED |
| 18 Genérico sin datos | `e18_generico_sin_datos_no_se_asocia` | FAILED | PASSED |

## Pruebas adicionales
| Prueba | Antes | Después |
|---|---|---|
| `extra_english_was_this_you` | FAILED | PASSED |
| `extra_gmail_normalizacion_solo_gmail` | FAILED | PASSED |
| `extra_informativo_no_anula_accion` | FAILED | PASSED |
| `extra_misma_factura_mismo_folio_si_se_asocia` | PASSED | PASSED |
| `extra_no_todo_mensaje_de_seguridad_es_caso` | PASSED | PASSED |
| `extra_tercero_no_es_propio` | PASSED | PASSED |

Nota: la versión inicial de `extra_tercero_no_es_propio` usaba un texto que no supera el umbral de solicitud en ningún remitente; no probaba lo que decía probar. Se corrigió el **dato de entrada** (mismo texto que e09a) y se mantuvo la **expectativa** (dirección no confirmada = externa).

## Suite backend completa
- main `6ff2979`: 2 failed, 745 passed, 1 skipped, 4 xfailed.
- rama: 2 failed, 771 passed, 1 skipped, 7 xfailed.
- Las 2 fallas son **preexistentes**: se reproducen idénticas en main (`test_microsoft_oauth.py::test_callback_missing_code_redirects_home` y `::test_callback_used_state_redirects_home`; el redirect apunta a `http://127.0.0.1:3000` por el entorno local). **0 fallas nuevas.**
