# Bitácora de eventos en /admin

Pestaña **Bitácora** del panel /admin: caídas de proveedores, despliegues, respaldos,
alertas del monitor y notas manuales. Incluye la tarjeta **Respaldos** (último diario,
último semanal, resultado, tamaño, duración, verificación, enlace a la corrida y próxima
ejecución programada).

## Datos
- Tabla `public.admin_events` (migración `20261021_001_admin_events_bitacora.sql`).
- Campos: `occurred_at`, `ended_at`, `source`, `severity` (info/aviso/grave/critico),
  `title`, `detail`, `status` (abierto/resuelto), `created_by`, `meta` (jsonb), `external_id` (único).
- Respaldos: `meta = {kind: diario|semanal, result: ok|fallido, size_bytes, duration_s, verified, run_url}`.
- RLS: solo usuarios en `public.admin_allowlist` (función `is_donexto_admin()`) leen, crean y
  cierran eventos. No hay borrado desde el panel.
- `admin_allowlist` se carga fuera del repositorio a partir de `ADMIN_EMAILS` (no se publican
  correos ni IDs). Si cambia `ADMIN_EMAILS`, agrega al usuario en el SQL Editor:
  `insert into public.admin_allowlist(user_id) select id from auth.users where lower(email)=lower('<correo>') on conflict do nothing;`

## No requiere backend
El panel lee y escribe directo en Supabase con la sesión del administrador; funciona aunque
Railway no pueda desplegar.

## Respaldos automáticos
`.github/workflows/bitacora-respaldos.yml` corre con `workflow_run` al terminar
"Donexto backup daily" o "Donexto backup weekly" y ejecuta `scripts/backup_event_from_run.py`.
No modifica los workflows de respaldo ni su cobertura. Ejecutarlo a mano (Run workflow)
hace backfill de las últimas N corridas. Es idempotente (`external_id = gh-run-<id>`).
Tamaño: se lee del log (`size ...`). Verificado: el respaldo terminó ok y reportó el tamaño
del objeto en R2 (diario: `head-object`; semanal: `sha256sum -c`).

## Otros eventos desde workflows o scripts
`scripts/log_admin_event.sh <source> <severity> "<título>" ["<detalle>"] [abierto|resuelto]`
Usa `SUPABASE_URL` y `SUPABASE_SECRET_KEY`. Nunca hace fallar el job.

Ejemplo para el monitor (pendiente; no aplicado para no generar un evento cada 15 min):

```yaml
      - name: Bitácora (solo caída o recuperación)
        if: steps.check.outputs.changed == 'true'
        continue-on-error: true
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_SECRET_KEY: ${{ secrets.SUPABASE_SECRET_KEY }}
        run: scripts/log_admin_event.sh monitor grave "Donexto caído" "Run ${{ github.run_id }}"
```

## Pedidos de Héctor
Cada pedido se registra como evento `source=manual`, `created_by=pedido`,
`meta = {kind: pedido, estado: pendiente|en_curso|hecho, historial: [...]}` y
`external_id = pedido-<clave>` (idempotente). En el panel: filtro **Tipo › Pedidos de Héctor**
y columna Estado con Pendiente / En curso / Hecho. Sin migración.

```bash
doppler run -p donexto -c prd -- scripts/bitacora_pedido.sh <clave> <pendiente|en_curso|hecho> "<título>" ["<detalle>"] ["<fecha ISO>"]
```
Repetir con la misma clave actualiza el estado (y cierra el evento cuando es `hecho`).
Orden de la vista: Pendientes, luego En curso, al final Realizados (más reciente primero en cada grupo).
Eventos sin `meta.estado`: abierto = Pendiente, resuelto = Realizado. Para marcar un evento cualquiera
como En curso basta con `meta.estado = en_curso`.
