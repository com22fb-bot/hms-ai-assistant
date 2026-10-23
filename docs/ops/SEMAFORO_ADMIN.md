# Semáforo de salud de /admin (evaluación única)

Fuente única: `backend/app/services/health_eval.py` → `GET /admin/health`. También la usan `GET /admin/health-extended`
(compatibilidad) y `GET /admin/performance` (`health`), y cada tarjeta muestra su insignia desde ahí. Está pensada para
ser reutilizada por el futuro «Centro de control».

## Estados
- **VERIFICANDO**: interfaz, mientras llega la primera evaluación.
- **VERDE**: todos los chequeos (críticos y no críticos) en `ok` y frescos.
- **AMARILLO**: sin fallas críticas propias, pero algo está degradado o sin verificar: permisos de monitoreo,
  proveedor externo caído, timeout, datos vencidos o insuficientes.
- **ROJO**: falla propia en un componente crítico (base, configuración/auth, app, respaldo > 54 h o fallido, cuota ≥ 95 %, 5xx > 10 %).
- La interfaz nunca muestra verde si la evaluación tiene más de 180 s o si la última actualización falló.

## Categorías
`falla_propia` · `proveedor_caido` (5xx/red/52x) · `permiso` (401/403/«Not Authorized»: NO es caída) ·
`monitoreo` (la herramienta falló; p. ej. desafío de Cloudflare al monitor) · `timeout` · `vencido` · `sin_datos`.

## Umbrales y justificación
| Chequeo | Umbral | Por qué |
|---|---|---|
| Base (select 1 fila) | > 1500 ms degradado | Desde Railway la consulta normal tarda 150–400 ms; 1,5 s ya se nota en la app |
| Cuota base | ≥ 80 % degradado, ≥ 95 % falla | Plan Free (verificado con la API de Supabase): 500 MB; al llenarse, la base pasa a solo lectura |
| Respaldo diario | ≤ 30 h ok; > 30 h degradado; > 54 h o fallido = falla | Cron diario (24 h) + 6 h de margen; 54 h = dos ciclos perdidos |
| 5xx últimos 15 min | > 2 % degradado, > 10 % falla (mín. 20 peticiones) | Con pocas peticiones un solo error distorsiona; < 20 = «Sin datos» |
| Memoria Railway | ≥ 90 % del límite | Margen antes de OOM/reinicio |
| Cada chequeo | 9 s de tiempo límite | Por debajo del timeout del proxy; si no responde = `timeout`, nunca ok |

## Incidentes
Se guardan en la Bitácora (`admin_events`, `source=monitor`): uno por componente mientras esté abierto (deduplicado).
Ciclo de vida: `abierto` (con transiciones falla/degradado/sin verificar) → `recuperando` → `resuelto`.
**Recuperación:** 3 evaluaciones OK seguidas que abarquen ≥ 2 min. Si recae, la racha se reinicia.
Las evaluaciones ocurren cuando un administrador abre /admin (polling cada 60 s, caché 30 s).

## Railway «Not Authorized» (23-oct-2026)
Causa raíz: el `RAILWAY_API_TOKEN` cargado en el servicio era un token viejo sin acceso. Corrección: token de **proyecto**
(`RAILWAY_METRICS_TOKEN`, solo grand-nourishment/production) con su cabecera `Project-Access-Token`. Limitación:
Railway no ofrece tokens de solo lectura; el de proyecto es el de menor alcance disponible.
