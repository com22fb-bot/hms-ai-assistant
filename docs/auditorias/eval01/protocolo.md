# EVAL-01 — Protocolo previo (fijado antes de importar)

Fecha de fijación: 29-oct-2026, antes de cualquier importación. Responde a OBS-EVAL-01 (dictamen ASTRA). Cualquier cambio posterior a este archivo debe quedar en el historial de git y justificarse; los umbrales **no** se modifican tras ver resultados.

## 1. Cuenta y periodo
- Usuario independiente de Donexto: **hsalcidor@yahoo.com** (no hmcelinfo, para no desactivar su Gmail).
- Buzón: Yahoo IMAP, conectado con contraseña de aplicación.
- Periodo: **últimos 90 días** desde el inicio de la importación (se reportan fechas exactas inicio/fin en UTC y CDMX).
- BRAIN_V1_ENABLED permanece `false`. IMPORT_PUSH_NOTIFICATIONS_ENABLED permanece `false`.

## 2. Conteos a reportar
Examinados (UIDs en el rango), importados, excluidos (por motivo: lista/boletín, dominio excluido, duplicado, otro) y fallidos (por error). Debe cumplirse examinados = importados + excluidos + fallidos.

## 3. Muestra etiquetada independiente
- Muestra aleatoria **estratificada de 150 mensajes** de los examinados (semilla fija registrada), estratos: importados / excluidos, y por remitente (personal, comercial, institucional).
- Etiquetado manual por Grok **sin ver la salida del sistema** (sin caso, categoría ni prioridad asignados), usando solo remitente, asunto y cuerpo. Héctor revisa las etiquetas; discrepancias se resuelven por Héctor y se registran.
- Las etiquetas se guardan (hash del archivo en el informe) antes de cruzarlas con la salida.

## 4. Definición de caso positivo
Positivo = mensaje **accionable** para el usuario: requiere respuesta, pago, trámite, entrega, fecha límite o seguimiento de un asunto propio. Negativo = boletín, promoción, notificación automática sin acción, spam.
Asociación correcta = el mensaje queda ligado al caso que corresponde al mismo asunto del mismo usuario.

## 5. Matriz y métricas
TP, FP, FN, TN sobre la muestra; precisión = TP/(TP+FP), recall = TP/(TP+FN), F1. Además: duplicados (mismo asunto en >1 caso) y asociaciones incorrectas.

## 6. Umbrales de aprobación (fijos)
| Métrica | Umbral |
|---|---|
| Precisión (accionables) | ≥ 0.85 |
| Recall (accionables) | ≥ 0.80 |
| Asociaciones a caso de otro usuario | **0** |
| Casos duplicados | ≤ 5 % |
| Fallidos de importación | reportados con causa (sin umbral) |

No se declara aprobado por solo terminar la importación sin errores.

## 7. Evidencia de no modificar originales
- Código verificado (commit 57a836d): `yahoo_import._select_folder` usa `select(..., readonly=True)` (EXAMINE); descargas con `BODY.PEEK[]` (`imap_provider.PEEK_FULL_SPEC`) y cabeceras con `BODY.PEEK[HEADER.FIELDS ...]`; `yahoo_imap.py` e `import_preview.py` también `readonly=True`. No hay `STORE`, `COPY`, `MOVE` ni `EXPUNGE` en los módulos IMAP. Resultado: **sin hallazgo**.
- Evidencia empírica: antes y después de importar, conteo de no leídos (`STATUS INBOX (UNSEEN MESSAGES)`) igual, y FLAGS de 10 UIDs de muestra sin cambio.

## 8. Evidencia de 0 push
- Logs de Railway del periodo con la línea `guided_import push suppressed` (guided_import_job_service.py) y 0 envíos push registrados para el usuario; confirmación de Héctor de no haber recibido notificaciones.
