# EVAL-01: por qué solo se creó 1 caso a partir de 500 mensajes identificados

Fecha: 30 oct 2026 (hora de Ciudad de México). Modo: **solo lectura** (solo SELECT; no hubo importación, reclasificación, escrituras, reinicio, despliegue ni push, y no se accedió al buzón original).
Alcance: job `99b1445c-370f-486f-841a-8144d9592748`, workspace `15c1e9b8-…5798`, cuenta Yahoo `d493c747-…9fba`.
Código revisado: `origin/main`, `backend/app/services/safe_case_classifier.py` (`CLASSIFIER_VERSION = logistica1-triage-v5`). BRAIN_V1 está APAGADO, así que corre la ruta heredada (`classify_pending_messages`, línea 547).

## 1. Método (reproducible)

```sql
-- Q1: distribución por categoría
select triage_category, case_processed, count(*), round(avg(actionability_score))
from communication_messages where account_id='d493c747-c49c-4b8c-882a-5238a3079fba'
group by 1,2 order by 3 desc;

-- Q2: candidatos por asunto (los dígitos se enmascaran con #)
select id, triage_category, actionability_score,
       lower(split_part(regexp_replace(sender,'.*<|>.*','','g'),'@',2)) dom,
       left(regexp_replace(subject,'[0-9]','#','g'),70) subj, left(triage_reason,50)
from communication_messages
where account_id='d493c747-c49c-4b8c-882a-5238a3079fba' and case_processed
  and lower(subject) ~ '(vence|vencimiento|l[ií]mite|pago|pagar|adeudo|factura|recibo|cargo|compra|pedido|env[ií]o|entreg|lleg|cita|reserv|vuelo|fuiste|inicio de sesi|sign|dispositivo|contrase|password|c[oó]digo|seguridad|security|alerta|bloque|rechaz|declin|suspend|renov|estado de cuenta|transfer|spei|dep[oó]sito|retiro|confirm|verific|acci[oó]n|urgente|recordatorio|aviso)';
-- 214 filas

-- Q3: remitentes de crédito, gobierno y personas (complementa Q2)
-- mismo SELECT, con filtro de dominio ~ '(bbva|issste|liverpool|costco|shopify|amazon.com.mx|mercadolibre.com$|dif.gob|alsuper|remify|clipcuenta|gmail.com)'

-- Q4: casos existentes y visibilidad
select c.id, c.status, c.created_at,
       (select count(*) from case_messages cm where cm.case_id=c.id)
from intelligent_cases c where c.workspace_id='15c1e9b8-4f53-4492-84f3-21771ba15798';
```

Etiquetado esperado: lo hice yo leyendo el asunto y el dominio, con la razón registrada como apoyo. No leí los cuerpos completos. Los mensajes repetidos del mismo remitente y tema se agrupan en **un solo caso esperado**.
Confianza: **A** = obligación o riesgo explícito en el asunto; **M** = probable, pero falta leer el cuerpo o confirmarlo con el usuario; **B** = informativo o estado de cuenta.

## 2. Resultados

Q1 (500 procesados + 50 pendientes):

| triage_category | n | ¿crea caso? |
|---|---|---|
| notice | 268 | **No** (actionable=False) |
| review | 133 | No |
| automated | 69 | No |
| informational | 19 | No |
| promotional | 10 | No |
| action_required | 1 | Sí → 1 caso |
| unreviewed (case_processed=false) | 50 | (pendientes CONC-01) |

Q4: hay **1 caso** (`103d0bec-…`, status `new`, 1 case_message → `7cd8c3d5-…`, BBVA). **No existen casos ocultos.** En `intelligent_cases` no hay más filas del workspace, así que el problema no está en un filtro del dashboard. Falla la creación del caso.

## 3. Causas raíz (por impacto)

| # | Causa | Código | Mensajes afectados |
|---|---|---|---|
| RC1 | Toda la categoría `notice` sale con `actionable=False`. Aplica a remitentes conocidos (banco, comercio, viaje), a avisos por NOTICE_TERMS ("sin convertirlo automáticamente en caso") y a avisos de seguridad. "acción requerida", "pago rechazado" o "factura vencida" se reconocen, pero nunca abren caso. | `safe_case_classifier.py` L309-314, L375-381, L386-387 | 268 |
| RC2 | Solo crean caso DIRECT_ACTION_TERMS y PAYMENT_ACTION_TERMS, que son frases conversacionales. Faltan obligaciones transaccionales: "rechazo por saldo insuficiente", "pago no autorizado", "aviso de cobro", "al corriente", "no fue posible entregar", "declaración patrimonial", "invitaciones vencerán". | L152-193, L278-281 | ~90 |
| RC3 | `_sender_is_automated` (no-reply, notifications@…) se evalúa antes que el contenido y devuelve `automated` sin caso. Eso incluye fallos de cobro y cambios de credenciales. | L82-95, L390-391 | 69 |
| RC4 | `review` es el valor por omisión de casi todo: `_sender_email(sender)` siempre es verdadero, L437. Por eso caen igual en `review` campañas (remify, teatrix, sanborns, wrangler) e hilos humanos reales (DIF, Alsuper). `review` nunca crea caso y además mezcla el ruido. | L437-438 | 133 |
| RC5 | No hay agregación de alertas repetidas. Hay ~60 rechazos idénticos (bazdigital) y 16 alertas de Google sin una regla de "N repeticiones = 1 caso". | (ausente) | ~80 |
| RC6 | SECURITY_NOTICE_TERMS también coincide con el pie de página. Por eso los rechazos de Baz se etiquetan como "Aviso de seguridad". | `taxonomy.py` L204; L375 | ~60 |
| RC7 | Las promociones de bancos (BBVA "OFERTA ESPECIAL", "liquidar con descuento") quedan como `notice`: el marketing se detecta por la parte local del remitente, no por el contenido. Esto no genera falsos positivos hoy, pero lo hará si se corrige RC1 sin filtrar. | L277, L287 | ~10 |

BRAIN_V1 APAGADO: el motor nuevo no participa (L547). Todos los resultados vienen de las reglas heredadas v5.

## 4. Tabla de evidencia (casos esperados)

Los UUID son de un mensaje representativo; el grupo completo se obtiene con Q2/Q3 filtrando por el dominio. No se incluye contenido sensible.

| # | id (representativo) | dominio | categoría genérica | n msgs | esperado | obtenido | conf. | motivo | corrección |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 7cd8c3d5-08f6-447a-9c2f-b611bf90c199 | bbva.com | estatus de crédito / adeudo | 1 (+1) | caso pago | action_required → **caso** | A | OK | – |
| 2 | c48c5ec6 (grupo Q2) | bazdigital.com | cargo rechazado por saldo | ~60 | 1 caso pago (agregado) | notice | A | RC1, RC2, RC5, RC6 | regla "cargo rechazado" → action_required + agregación |
| 3 | cbd449cd | cfe.mx | aviso de cobro de luz | 4 (+2 notas propias) | caso pago | review | A | RC2, RC4 | término "aviso de cobro"/"aviso de factura" de servicios |
| 4 | 85ef9461 | cleverbridge.com | renovación con pago no autorizado | 2 | caso pago | automated | A | RC3, RC2 | revisar contenido antes que remitente automatizado |
| 5 | fbe0b47a | accountprotection.microsoft.com | acción requerida en seguridad de cuenta | 1 | caso seguridad | notice | A | RC1 | "acción requerida" → action_required |
| 6 | d9d641aa | envio.santander.com.mx | tarjeta no entregada | 1 | caso entrega | notice | A | RC1, RC2 | término "no fue posible entregar" |
| 7 | 9d3c640e-def5-428d-8e3e-8ee718030963 | dif.gob.mx | hilo laboral: prestaciones | 11 | caso seguimiento | notice/review | A | RC4 (hilo humano sin frase listada) | hilo humano con respuestas (RE:) de terceros → candidato a caso |
| 8 | 55ba15ce-79ec-45bf-a835-402a501908f6 | dif.gob.mx | trámite de declaración patrimonial | 1 | caso trámite/vencimiento | review | A | RC2, RC4 | término de obligación legal |
| 9 | 0375affd-13b2-4329-a93b-fec0a7d24ccd | bbva.mx | crédito de auto: mantener al corriente | 14 | caso pago (¿vincular a #1?) | notice | M | RC1, RC2, RC5 | "al corriente" + agregación |
| 10 | cac8f07b | sempraglobal.com.mx | factura mensual de gas | 7 (+7 pagos aplicados) | caso pago recurrente | informational/review | M | RC2 | factura de servicio → caso; "pago aplicado" lo cierra |
| 11 | 494d9103 | totalplay.com.mx | estado de cuenta de servicio | 1 | caso pago | notice | M | RC1 | estado de cuenta de servicio con saldo → caso |
| 12 | 4476d616 | accounts.google.com | alertas de seguridad de otra cuenta | 16 | 1 caso seguridad (agregado) | notice | M | RC1, RC5 | agregación de alertas; ¿actividad propia? |
| 13 | 1e68d74a | cc.yahoo.com | cambios de contraseña / app password / 2FA | ~17 | 1 caso seguridad | automated/notice | M | RC3, RC5 | cambio de credenciales → caso "revisar si fuiste tú" |
| 14 | 8234e9d4-d534-4ff6-b03c-b9229d16e11e | issste.gob.mx | préstamo personal | 1 | caso pago | notice | M | RC1 | – |
| 15 | 17a0249e | mercadolibre.com.mx | compra en camino / entregada | 4 | caso compra (cerrado al entregar) | notice | M | RC1 | ciclo de pedido → caso con cierre automático |
| 16 | 8d11e901-e0e6-4b3a-b4a9-0a7882eebdbf | alsuper.com | seguimiento de postulación (hilo humano) | 2 | caso seguimiento | review | M | RC4 | ver #7 |
| 17 | b1b7fa0d | indeed.com | invitaciones que vencen | 1 | caso vencimiento | automated | M | RC3, RC2 | "vencerán" a DEADLINE_TERMS |
| 18 | 1b0094ea-148a-4399-85d3-690f9bf21e85 | amazon.com.mx | aviso de suscripción | 1 | caso suscripción | notice | M | RC1 | – |
| 19 | aa6bed50-d35d-4ccd-9580-e83bad7e3920 | mercadolibre.com | mensaje de vendedor | 1 | caso seguimiento | notice | M | RC1 | – |
| 20 | 4d1c7c5a / 8ac35855 / d5e0d028 / ade8b88e | spinbyoxxo, payclip, banamex, profuturo | estados de cuenta | ~9 | sin caso (informativo) | notice | B | correcto | – |

Los IDs de 8 caracteres son prefijos; el UUID completo sale de Q2.

Bien descartados (muestra): campañas (remify, teatrix, sanborns, wrangler, beehiiv), códigos de un solo uso, enlaces de inicio de sesión de Donexto, CFDI de Costco, promociones de BBVA. Problema: muchas campañas quedaron en `review` y no en `promotional` (RC4).

## 5. Conteos

| | casos |
|---|---|
| Casos reales esperados, confianza A | **8** (incluye el detectado) |
| Casos reales esperados, A + M | **19** |
| Detectados por Donexto | **1** (#1) |
| Omitidos | **7 (A)**, o **18 (A+M)** |
| Casos creados pero ocultos | **0** |
| Mensajes detrás de los omitidos | ~220 de 500 |

Lo que falta para un conteo definitivo:
1. Lectura de cuerpos o confirmación del usuario para los 11 casos M: ¿son actividad propia? ¿ya están pagados?
2. Etiquetas oro humanas según `protocolo.md` (precision/recall).
3. Los 50 mensajes `case_processed=false` (bloqueados por CONC-01) no entran en este conteo.

## 6. Correcciones propuestas (sin implementar)

1. **P1 (RC1):** separar `notice` en `notice_actionable` (crea caso: rechazo o declinación de pago, acción requerida, factura o cobro de servicio, entrega fallida, cambio de credenciales) y `notice_info` (estado de cuenta sin saldo, ticket, CFDI, código OTP).
2. **P2 (RC2):** ampliar la taxonomía con términos transaccionales en español de México (lista en la tabla) y sumar "vencerán" a DEADLINE_TERMS.
3. **P3 (RC3):** evaluar contenido y obligaciones **antes** de `_sender_is_automated`. "Automatizado" solo debe aplicarse si no hay señal de obligación.
4. **P4 (RC4):** `review` solo para correos humanos reales (no-marketing, sin List-Unsubscribe). Mandar a `promotional` los remitentes con patrón de campaña. Un hilo humano con respuestas de terceros → caso de seguimiento.
5. **P5 (RC5):** agregación por (remitente, tipo de aviso) en una ventana de N días → 1 caso con contador; el resto, como case_messages.
6. **P6 (RC6, RC7):** aplicar SECURITY_NOTICE_TERMS solo al asunto y a los primeros ~300 caracteres, y detectar marketing por el contenido ("oferta especial", "descuento").
7. **Validación:** usar esta tabla como conjunto oro inicial y medir con `protocolo.md` (≥0.85/≥0.80) en una copia aislada antes de cualquier reclasificación en producción, que requiere autorización de ASTRA.
