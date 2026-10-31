# Validación complementaria de la auditoría maestra (4d30e18)

**Fecha:** 30 oct 2026, hora de Ciudad de México (UTC-6).
**Modo:** solo lectura.
- En producción solo se ejecutaron SELECT, sobre metadatos y campos ya registrados.
- **No se leyeron cuerpos nuevos.**
- Sin cambios de código, datos ni configuración; sin descargas; sin llamadas de pago; sin generar embeddings.
- BRAIN_V1 y push siguen apagados.

**Convenciones:**
- **[HECHO]** = demostrado con código o datos.
- **[HIPÓTESIS]** = no demostrado.
- Rutas relativas a `backend/app/services/`.

**Corrección a la auditoría maestra:**
- La cifra "14 respuestas con el original guardado" salió de una consulta que buscaba el mensaje original **en toda la tabla** (incluidas otras cuentas).
- Limitada a la cuenta de EVAL-01, la cifra correcta es **13**. La coincidencia restante corresponde a otra cuenta de la base.

---

## 1. Yahoo y correos enviados

| Dimensión | Resultado | Evidencia |
|---|---|---|
| **Capacidad implementada** | El snapshot recorre todas las carpetas que devuelve `LIST`, por rol. Importa los roles `inbox` y `sent`. Solo cuenta `draft`, `spam` y `trash`. Ignora `other` (Archivo y carpetas personalizadas) | [HECHO] `yahoo_import.py:_collect_refs:187-207` (`if role not in roles: continue`, `:199`); roles del snapshot `:233-236`; lista elegible `inbox + sent` `:241` |
| Orden | La lista de referencias se arma **primero con todos los recibidos y después con todos los enviados**, y se paginan de forma secuencial | [HECHO] `:241`; `sync_yahoo_page` corta `refs[offset:offset+batch]` (`:495`); la llamada desde el job está en `guided_import_job_service.py:403-419` |
| Rol del mensaje enviado al guardarlo | `classify_yahoo_folder(folder)` → `sent` → `direction="outbound"` | [HECHO] `yahoo_import.py:641-644` |
| **Capacidad ejecutada (job 99b1445c)** | `mode=historical`, `status=cancelled`, `unique_estimate=735`, `messages_inserted=550`, `pages_completed=11`, `batch_size=50`, `next_page_token=550` | [HECHO] SQL V1 |
| **Composición de las 735 referencias** (de `metadata.yahoo_refs`) | **Inbox: 676 (posiciones 1–676). Sent: 59 (posiciones 677–735)** | [HECHO] SQL V2 |
| **Mensajes guardados** | 550, todos de Inbox (posiciones 1–550). Enviados guardados: **0** | [HECHO] |
| Carpetas omitidas | Inbox: quedaron 126 sin descargar (posiciones 551–676). Sent: 59 sin descargar. Borradores, spam y papelera: solo contados. Otras carpetas: no listadas en las referencias (por diseño) | [HECHO]. Qué otras carpetas existen en el buzón no es evaluable: la lista de `LIST` no se guarda |

**Conclusión:**
- Yahoo **sí** implementa la importación de enviados.
- En EVAL-01 los enviados **no se procesaron porque el job se canceló en la posición 550**, antes de llegar a la 677, donde empiezan. **[HECHO]**, ya no hipótesis.
- La única limitación de implementación es que Archivo y las carpetas personalizadas nunca se importan.
- Diferencia con la auditoría maestra: allá lo dejé como hipótesis; aquí queda demostrado con `metadata.yahoo_refs`.

**[HIPÓTESIS]** que siguen abiertas:
- Que los 59 enviados contengan compromisos.
- Que existan carpetas de Archivo con contenido.

Para resolverlas habría que reanudar la importación, que requiere autorización de ASTRA.

**Defecto de diseño:** al colocar los enviados al final, cualquier cancelación o tope sesga la muestra contra los compromisos del usuario. **Propuesta:** intercalar las carpetas o procesarlas por fecha.

## 2. Agrupación de conversaciones

SQL V3/V4. EVAL-01: 550 mensajes, 545 filas en `communication_threads`.

| Medida | Valor | Explicación |
|---|---|---|
| Hilos / mensajes | 545 / 550 | casi uno por mensaje |
| Mensajes con In-Reply-To | 24 | 11 apuntan a mensajes no guardados (fuera del periodo, en Enviados o en otro buzón) |
| Respuestas cuyo original está guardado | **13** | – |
| …en el mismo hilo que su original | **3** | el original **no** era a su vez una respuesta |
| …en un hilo distinto | **10** | en los 10 casos el original **sí** era una respuesta |
| Hilos con más de un mensaje | 5 | 3 son pares respuesta–original; 2 agrupan respuestas que citan el mismo `In-Reply-To` sin que el original esté guardado |

**Mecanismo [HECHO]:**
- `yahoo_import.py:_external_thread_id:463-471` elige como clave In-Reply-To, luego Message-ID y luego References[0].
- La clave de una respuesta es **el ID de su padre**. La de un original que no es respuesta es **su propio Message-ID**, y por eso coinciden en los 3 casos.
- Cuando el padre es a su vez una respuesta, su clave es la del **abuelo**, mientras que el hijo usa la del **padre**. Resultado: hilos distintos, que es lo que pasa en los 10 casos.
- Las 13 respuestas tienen References (de 1 a 10 elementos), pero **References[0] (la raíz) nunca se usa primero**.

**Defectos:**
- **D2-1:** orden de las claves (`:466-468`).
- **D2-2:** no hay unión posterior cuando llega un mensaje anterior.
- **D2-3:** `case_engine._find_case_for_message` busca el caso primero por `thread_id` (`case_engine.py:384`), así que hereda la fragmentación. In-Reply-To y References la mitigan solo si el caso existe (`:398-406`).
- **D2-4:** Graph no guarda In-Reply-To ni References (`microsoft_import.py:511-512`).

**Pruebas reproducibles [PROPUESTA]**, con fixtures RFC822 sintéticos:
1. Cadena A → B (In-Reply-To A, References [A]) → C (In-Reply-To B, References [A, B]). Las tres deben compartir `external_thread_id = A`. Hoy: A y B comparten, C queda aparte.
2. Llegada desordenada: C antes que A. Al terminar, deben unirse.
3. Respuesta cuyo original no está guardado: la clave debe ser References[0].
4. Dos conversaciones distintas con el mismo asunto: **no** deben unirse.
5. Mismo Message-ID en Inbox y Archivo: un solo mensaje.
6. Equivalente para Graph: `conversationId` presente e In-Reply-To desde `internetMessageHeaders`.

## 3. Referencia de casos reales (8 A + 11 M = 19)

Solo con campos ya registrados (asunto, dominio, razón registrada).

**Criterio:**
- **Confirmado:** el asunto y el dominio bastan por sí mismos para demostrar un hecho con obligación o riesgo, y el remitente es institucional y verificable.
- **Potencial:** probable, pero falta el cuerpo o la confirmación del usuario.
- **Info:** hecho real sin acción.
- **No evaluable:** faltan datos.

| # | id | dominio | Evidencia que lo confirmaría | Clasificación |
|---|---|---|---|---|
| 1 | 7cd8c3d5 | bbva.com | cuerpo: estatus y adeudo; confirmación del usuario | **Potencial** (detectado; el asunto no basta para afirmar que el adeudo existe) |
| 2 | c48c5ec6 (81 mensajes) | bazdigital.com | asunto explícito "rechazo por saldo insuficiente", repetido 81 veces en 2 meses | **Confirmado** (hecho: cargos rechazados; la obligación concreta requiere el cuerpo) |
| 3 | cbd449cd | cfe.mx | "aviso de cobro" + "comprobante de pago" en otro mensaje: ¿pagado? | **Potencial** (podría estar cerrado; hace falta comparar importe y periodo) |
| 4 | 85ef9461 | cleverbridge.com | asunto "pago no autorizado" de una renovación | **Confirmado** (hecho); acción: decisión del usuario |
| 5 | fbe0b47a | accountprotection.microsoft.com | asunto "acción requerida" sobre 2FA | **Confirmado** (alerta de seguridad) |
| 6 | d9d641aa | envio.santander.com.mx | asunto "no fue posible entregar tu tarjeta" | **Confirmado** |
| 7 | 9d3c640e (11) | dif.gob.mx | hilo humano: hace falta el cuerpo para saber quién debe actuar | **Potencial** |
| 8 | 55ba15ce | dif.gob.mx | asunto de un trámite con obligación legal; hace falta saber la fecha límite y si ya se presentó | **Potencial** |
| 9 | 0375affd (14) | bbva.mx | "mantener al corriente": ¿recordatorio genérico o atraso? | **Potencial** |
| 10 | cac8f07b | sempraglobal.com.mx | facturas mensuales más "pago aplicado" | **Información solamente** (es probable que esté pagado; se confirma al comparar periodos) |
| 11 | 494d9103 | totalplay.com.mx | estado de cuenta: ¿saldo pendiente? | **Potencial** |
| 12 | 4476d616 (19) | accounts.google.com | alertas de otra cuenta propia: ¿actividad del usuario (conexión de Donexto)? | **No evaluable** sin el cuerpo y la cronología de conexión |
| 13 | 1e68d74a (~17) | cc.yahoo.com | contraseñas de aplicación creadas o eliminadas: coincide con la conexión de Donexto | **Información solamente** (probable actividad propia; falta confirmación del usuario) |
| 14 | 8234e9d4 | issste.gob.mx | asunto de un préstamo personal | **Potencial** |
| 15 | 17a0249e | mercadolibre.com.mx | "en camino" seguido de "llegó tu compra" | **Información solamente** (acontecimiento real ya cerrado) |
| 16 | 8d11e901 | alsuper.com | hilo humano de postulación | **Potencial** |
| 17 | b1b7fa0d | indeed.com | "invitaciones que vencerán": correo masivo de plataforma | **Información solamente** |
| 18 | 1b0094ea | amazon.com.mx | "aviso importante sobre tu suscripción" | **Potencial** |
| 19 | aa6bed50 | mercadolibre.com | "mensaje nuevo" de vendedor | **No evaluable** |

**Totales:**
- Confirmado: **4** (#2, #4, #5, #6).
- Potencial: **9**.
- Información solamente: **4**.
- Falso positivo: **0**.
- No evaluable: **2**.
- Detectados por Donexto entre los confirmados: **0 de 4**. El único caso detectado (#1) es Potencial.

**Conjunto de referencia confiable [PROPUESTA]:**
- **Datos:**
  - Los 550 mensajes más los 185 no descargados (126 de Inbox y 59 de Sent), lo que requiere reanudar el job con autorización.
  - Lectura de los cuerpos solo por la persona etiquetadora autorizada (Héctor), en una herramienta local sin enviar datos a terceros.
- **Protocolo:**
  - (1) Unidad = acontecimiento; cada uno se liga a sus mensajes.
  - (2) Etiquetas: tipo (taxonomía A–J), estado, responsable (user / third party / unknown), fecha, importe enmascarado y evidencia.
  - (3) Dos pasadas: Grok propone y la persona confirma o corrige. Se mide el acuerdo sobre un 20% revisado dos veces, idealmente por un segundo revisor.
  - (4) Guía escrita de casos límite (avisos repetidos, actividad propia, pagados).
- **Tamaño de muestra:**
  - EVAL-01 completo (735) para el primer usuario.
  - Para generalizar, **al menos 3 buzones de perfiles distintos y unos 2,000 mensajes**.
  - Con una prevalencia esperada del 5–10% de mensajes con acontecimientos, eso da unos 100–200 mensajes positivos, suficientes para un intervalo de confianza de ±0.07 en el recall (aproximación binomial al 95%).
  - **[ESTIMADO]**: la prevalencia real se mide en la fase 1.

## 4. Banco Azteca (bazdigital.com)

SQL V5. **[HECHO]**

| Corte | Valor |
|---|---|
| Total | **168** de 550 (30.5%), 1 dirección remitente, 48 días distintos, de agosto a octubre de 2026 (agosto 18, septiembre 75, octubre 75) |
| Por asunto | "Notificación Banco Azteca" 84 · "Rechazo por saldo insuficiente" 81 · "Estado de Cuenta Banca Digital" 3 |
| Procesados / pendientes | 149 procesados (todos `notice`) / 19 pendientes (`case_processed=false`, dentro de los 50) |
| Razón registrada | "Aviso de seguridad o verificación…" 123 (incluye los 71 rechazos procesados) · "Aviso importante para revisión…" 26 · nula 19 (pendientes) |
| `security_flag` | **la columna no existe** en `communication_messages` |
| Casos | 0 |

**Efecto en las métricas** (sin excluirlos):
- **Micro, a nivel mensaje:** Banco Azteca pesa el 29.8% de los 500 procesados (149). Si se etiquetan los 71 rechazos como mensajes relevantes, cualquier recall micro queda dominado por un solo remitente: con 0 detectados, la cobertura relevante baja 71 puntos de golpe.
- **Macro, a nivel acontecimiento o remitente:** Banco Azteca cuenta como **1 acontecimiento** (cargo recurrente rechazado), con el mismo peso que el de CFE o Santander.
- **Recomendación:** reportar **las dos métricas** y como métrica principal la del **acontecimiento**, con una tabla por remitente y por categoría.

Rendimiento actual por remitente o categoría (referencia del §3; confirmados + potenciales = 13):

| Corte | Esperados | Detectados | Recall |
|---|---|---|---|
| Banco Azteca (1 acontecimiento, 168 mensajes) | 1 | 0 | 0.00 |
| Bancos (BBVA ×2, Baz, Santander, ISSSTE) | 5 | 1 | 0.20 |
| Servicios del hogar (CFE, Totalplay) | 2 | 0 | 0.00 |
| Seguridad (Microsoft) | 1 | 0 | 0.00 |
| Compras / suscripciones (Cleverbridge, Amazon) | 2 | 0 | 0.00 |
| Trabajo / trámites (DIF ×2, Alsuper) | 3 | 0 | 0.00 |
| **Macro (promedio por categoría)** | – | – | **0.04** |
| **Micro (por acontecimiento)** | 13 | 1 | **0.08** |

Las cifras son **indicativas**: la referencia todavía no es un conjunto oro.

## 5. Costos: hoja de supuestos reproducible

El archivo `costos-supuestos.csv` tiene cada parámetro con su tipo (calculado, estimado o pendiente) y su fuente.

- **Tipo de cambio:** FIX de Banxico del 30/10/2026 = 18.7962 MXN/US$ (https://www.banxico.org.mx/tipcamb/tipCamMIAction.do).
- **Precios:** https://docs.x.ai/developers/pricing y https://developers.openai.com/api/docs/pricing, consultados el 30 oct 2026.

**Fórmulas** (por 1,000 mensajes después del filtro; precios por 1M tokens):

```
Triage   = 1000·(P5·R1 + P6·R2 + P7·R3)/1e6
         = (1.5·1.25 + 0.8·0.20 + 0.2·2.50) = 2.535 US$
Profunda = 1000·P8·(P9·R4 + P10·R5)/1e6
         = 0.30·(4.5·2.00 + 0.5·6.00)       = 3.600 US$
Embeds   = 1000·P5·R7/1e6
         = 1.5·0.02                         = 0.030 US$
TR       = Triage + Profunda + Embeds       = 6.165 US$  (MXN 115.88)
Batch    = (Triage + Profunda)·(1−R6) + Embeds = 4.938 US$ (MXN 92.82)
Inicial  = P1·P2·(1−P4)/1000·Batch
Mensual  = P1·P3·(1−P4)/1000·TR
```

| Concepto | US$ | MXN | Tipo |
|---|---|---|---|
| Precio por token (xAI, OpenAI) | – | – | **calculado** (oficial) |
| Por 1,000 mensajes, en tiempo real | 6.17 | 115.88 | **estimado** (tokens supuestos) |
| Por 1,000 mensajes, con Batch | 4.94 | 92.82 | estimado |
| Inicial para 3,000 usuarios (1,000 a 3,000 mensajes por usuario; filtro de 0 a 50%) | 7,407 a 44,442 | 139,223 a 835,341 | estimado |
| Mensual para 3,000 usuarios (500 mensajes por usuario; filtro de 0 a 50%) | 4,624 a 9,248 | 86,909 a 173,818 | estimado |
| Embeddings de xAI | – | – | **pendiente** (precio no publicado) |
| Supabase (pgvector, cómputo), Railway (cola de Batch), horas de etiquetado | – | – | **pendiente de cotización** |

**Sensibilidad:** el costo escala casi linealmente con P5, P8 y P9. Duplicar P8 (del 30% al 60%) suma unos US$3.60 por cada 1,000 mensajes. Los parámetros P4, P5 y P8 se **miden** en la fase 0/1 con datos de EVAL-01, sin llamadas de pago: P5 se calcula contando tokens localmente.

## Dictamen

**SÍ hay evidencia suficiente para iniciar la fase de fundamentos y etiquetado humano**, con estas condiciones:
1. Autorización expresa de Héctor y ASTRA para cada acción.
2. Fusionar CONC-01 (#214) antes de cualquier escritura.
3. Corregir D2-1 (clave de hilo) y el orden de las carpetas, con las pruebas del §2 antes de reimportar.
4. Reanudar EVAL-01 solo con autorización, para recuperar los 126 mensajes de Inbox y los 59 de Sent.
5. Etiquetado humano con el protocolo del §3, sin enviar datos a terceros y sin llamadas de pago hasta que se apruebe el presupuesto.
6. Mantener BRAIN_V1 y push apagados.

**NO** hay evidencia todavía para autorizar la arquitectura de IA completa ni fijar umbrales de métricas: falta el conjunto oro y medir P4, P5 y P8.

### Limitaciones

- La clasificación del §3 se basa en asuntos y dominios; 9 casos Potenciales y 2 No evaluables necesitan los cuerpos y la confirmación del usuario.
- Las carpetas reales del buzón Yahoo (más allá de las referencias) no se pueden conocer sin un nuevo `LIST`.
- Los costos son estimaciones.
- La columna `security_flag` no existe.

### Anexo SQL (solo SELECT)

```sql
-- V1: contadores del job
select mode,status,query,messages_found,messages_inserted,unique_estimate,pages_completed,batch_size,next_page_token
from gmail_sync_jobs where id='99b1445c-370f-486f-841a-8144d9592748';
-- V2: composición de las referencias por carpeta (el separador es chr(31))
with r as (select e.v,e.ord from gmail_sync_jobs j, jsonb_array_elements_text(j.metadata->'yahoo_refs') with ordinality e(v,ord)
           where j.id='99b1445c-370f-486f-841a-8144d9592748')
select split_part(replace(v,chr(31),'|'),'|',1) folder, count(*), min(ord), max(ord),
       count(*) filter (where ord<=550)
from r group by 1 order by 3;
-- V3: pares respuesta–original dentro de la cuenta
with m as (select * from communication_messages where account_id='d493c747-c49c-4b8c-882a-5238a3079fba')
select a.id, a.thread_id=b.thread_id same_thread, b.in_reply_to is not null parent_is_reply,
       ta.external_thread_id=tb.external_thread_id same_key,
       jsonb_array_length(coalesce(to_jsonb(a.references_header),'[]')) nrefs
from m a join m b on b.internet_message_id=a.in_reply_to
join communication_threads ta on ta.id=a.thread_id join communication_threads tb on tb.id=b.thread_id;
-- V4: hilos con más de un mensaje
select thread_id, count(*) from communication_messages
where account_id='d493c747-c49c-4b8c-882a-5238a3079fba' group by 1 having count(*)>1;
-- V5: Banco Azteca
select left(subject,30), case_processed, triage_category, left(triage_reason,30), count(*),
       min(received_at), max(received_at)
from communication_messages
where account_id='d493c747-c49c-4b8c-882a-5238a3079fba' and lower(sender) like '%bazdigital.com%'
group by 1,2,3,4;
```
