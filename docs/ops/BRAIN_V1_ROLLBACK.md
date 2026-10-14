# Cerebro v1 — procedimiento de reversión

Volver al código anterior NO deshace los datos que el cerebro ya escribió. Este procedimiento cubre las dos cosas.

## 1. Apagar el cerebro (inmediato, sin despliegue de código)
1. En Railway (servicio hms-ai-assistant, producción), borra la variable `BRAIN_V1_ENABLED` o ponla en `false`. Railway reinicia el servicio.
2. Verifica `GET /health` = 200 y que una clasificación nueva reporta `classifier_version` distinto de `brain-v1-*`.
3. No toques `HMS_AUTO_SYNC_ENABLED`, OAuth ni buzones.

## 2. Volver al despliegue anterior (solo si el código falla con la bandera apagada)
1. Railway → Deployments → el despliegue previo con estado SUCCESS → "Rollback".
2. Repite la verificación de /health, login y tablero.

## 3. Datos ya escritos por el cerebro
Identificación (solo lectura):
```sql
select status, count(*) from public.intelligent_cases
where metadata->>'created_by' like 'brain-v1%' group by status;
select count(*) from public.communication_messages where brain_signals is not null;
```
- Los casos del cerebro quedan visibles y son válidos para el código anterior SALVO los estados nuevos
  (`scheduled`, `no_action`, `needs_review`), que el frontend sin esta versión no etiqueta.
- Opción recomendada (reversible): conservar los casos y dejarlos como están. No borrar nada sin una lista
  mostrada a Héctor y su confirmación explícita.
- Si hay que devolver los estados nuevos a los anteriores (respaldo previo obligatorio):
```sql
create table if not exists ops_brain_v1_rollback_backup as
  select id, status, metadata from public.intelligent_cases where metadata->>'created_by' like 'brain-v1%';
update public.intelligent_cases set status = case status when 'scheduled' then 'new'
  when 'needs_review' then 'new' when 'no_action' then 'archived' end
where metadata->>'created_by' like 'brain-v1%' and status in ('scheduled','needs_review','no_action');
```
- Un caso resuelto por el cerebro (pago confirmado) conserva su evento `payment_confirmed` como evidencia;
  si hubiera duda, se reabre manualmente (`status='new'`) desde la lista de respaldo.
- Para reclasificar con el clasificador anterior: marcar `case_processed=false` solo en los mensajes afectados,
  después de decidir qué hacer con sus casos (si no, se duplican).
- Revertir la migración 005 solo cuando ninguna fila use los estados nuevos (ver comentarios del archivo).
