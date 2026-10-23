# donexto-backup-cron (EN ESPERA — crons = [])

Dispara los respaldos de GitHub Actions desde el cron de Cloudflare (Workers gratis: 5 crons por cuenta, 100k req/día; este usa 1 invocación/día).

```mermaid
flowchart LR
  CF["Cloudflare cron 09:00 UTC<br/>(03:00 CDMX, sin horario de verano)"] -->|workflow_dispatch<br/>GH_DISPATCH_TOKEN, 3 intentos| D[backup-daily.yml]
  CF -->|solo domingo| W[backup-weekly.yml]
  GHD["GitHub schedule 12:00 UTC<br/>(06:00 CDMX) respaldo"] --> GD{guard: ¿éxito/en curso hoy?}
  GHW["GitHub schedule dom 12:00 UTC"] --> GW{guard semanal}
  GD -->|no| D
  GD -->|sí| SK[salta; bitácora lo ignora]
  GW -->|no| W
  D --> R2[(R2 donexto-backups cifrado GPG)]
  W --> R2
  D -->|workflow_run| B[bitacora-respaldos.yml → admin_events]
  W --> B
  D -->|falla| A[Slack #alertas + correo Resend]
```

- El Worker no hace pg_dump/gpg/R2 (necesita runner con binarios y >30 s CPU): solo dispara.
- Diario y semanal son independientes (grupos de concurrencia distintos; la falla de uno no frena al otro).
- Activar (con aprobación): `crons = ["0 9 * * *"]` y `wrangler deploy`. Secreto: `GH_DISPATCH_TOKEN` (nombre; valor solo en Cloudflare).
- Pruebas: `node --test index.test.mjs` y `python3 -m unittest scripts/tests/test_backup_guard.py`.
