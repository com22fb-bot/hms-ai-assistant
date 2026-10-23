# donexto-backup-watch — 2º canal de alertas (independiente de GitHub)
Cron diario 15:00 UTC (09:00 CDMX). Lista `donexto-backups/db/` (binding R2 de solo lectura en la práctica:
solo `list()`), y si el último objeto tiene más de `MAX_AGE_HOURS` (30 h), no hay objetos o R2 no responde,
avisa por Slack `#alertas` **y** por Resend (cada canal por separado; basta con que uno entregue; si
ninguno, el Worker falla y queda en los logs de Workers). Secrets: `SLACK_BOT_TOKEN`, `RESEND_API_KEY`.
Pruebas: `node --test index.test.mjs` (fresco, viejo, sin objetos, R2 ilegible, Slack caído, Resend caído, ambos).
Limitación: comparte proveedores de entrega (Slack/Resend) con las alertas de GitHub; lo independiente es el
disparador y la verificación (Cloudflare + R2, sin runner de GitHub).
