# EVAL-01 — Protocolo previo (fijado antes de importar)

Fecha de fijación: 29-oct-2026, antes de cualquier importación. Responde a OBS-EVAL-01 (dictamen ASTRA). Cualquier cambio posterior a este archivo debe quedar en el historial de git y justificarse; los umbrales **no** se modifican tras ver resultados.

## 1. Cuenta y periodo
- Usuario independiente de Donexto: **hsalcidor@yahoo.com** (no hmcelinfo, para no desactivar su Gmail).
- Buzón: Yahoo IMAP, conectado con contraseña de aplicación.
- Periodo: **últimos 180 días** desde el inicio de la importación (se reportan fechas exactas inicio/fin en UTC y CDMX). Excepción única autorizada por Héctor el 29-oct-2026; el límite general del plan (mensual/prueba 90, anual 183) no cambia.
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

## 9. Ventana de 180 días sin cambiar el plan (override puntual)
`history_days_for_workspace` (account_lifecycle.py) consulta primero `admin_settings` con key `history_days_override:<workspace_id>`. Si existe y no ha expirado, usa esos días y deja en log `history_days override applied: workspace=… days=… reason=…`. Al expirar vuelve sola al plan. Pruebas: `backend/tests/test_history_override.py`.

Preparado, **no ejecutado** hasta que la cuenta esté conectada:
1. Héctor entra con hsalcidor@yahoo.com y conecta Yahoo; se obtiene su `workspace_id`.
2. Insertar (service role), con expiración de 48 h:
   ```sql
   insert into public.admin_settings(key, value) values (
     'history_days_override:<workspace_id>',
     '{"days":180,"expires_at":"<ahora+48h ISO UTC>","reason":"EVAL-01","authorized_by":"Héctor 29-oct-2026"}');
   ```
3. Lanzar `/import/start` (modo initial) desde la app; verificar `history_days=180` en el snapshot del job y la línea de log.
4. Al terminar, borrar la fila (`delete from public.admin_settings where key='history_days_override:<workspace_id>'`) y registrarlo en el informe.
