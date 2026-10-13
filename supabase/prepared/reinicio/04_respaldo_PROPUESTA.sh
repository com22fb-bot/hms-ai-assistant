#!/bin/bash
# RESPALDO ACOTADO (PROPUESTA, NO EJECUTADA). Solo lectura: COPY (SELECT ...) TO STDOUT.
# El plan es Free: no hay PITR ni respaldos descargables desde el panel. Este respaldo propio es OBLIGATORIO antes de la fase 1.
# DSN: pedírselo a Héctor en el momento. Nunca guardarlo en un archivo ni imprimirlo.
#   read -s DB_URL; export DB_URL
# oauth_credentials NO se respalda: son tokens cifrados que no deben circular. Al restaurar, el buzón se reconecta.
# Columnas con cuerpo de mensaje: van dentro del respaldo (son datos del propio Héctor), pero el archivo es cifrado y no se lee.
set -euo pipefail
OUT=/workspace/cerebro/respaldo-reinicio-$(date +%Y%m%d-%H%M); mkdir -p "$OUT"; chmod 700 "$OUT"
E="array['hmcelinfo@gmail.com','hsalcidor@yahoo.com']"
ACC="select id from public.communication_accounts where lower(email)=any($E)"
WS="select workspace_id from public.communication_accounts where lower(email)=any($E)"
CASES="select id from public.intelligent_cases where account_id in ($ACC) or workspace_id in ($WS)"
RUNS="select id from public.case_reclassification_runs where account_id in ($ACC) or workspace_id in ($WS)"
NOTIF="select id from public.hms_notifications where account_id in ($ACC) or workspace_id in ($WS)"
declare -A Q=(
 [01_workspaces]="select * from public.workspaces where id in ($WS)"
 [02_workspace_members]="select * from public.workspace_members where workspace_id in ($WS)"
 [03_communication_accounts]="select * from public.communication_accounts where id in ($ACC)"
 [04_communication_threads]="select * from public.communication_threads where account_id in ($ACC)"
 [05_communication_messages]="select * from public.communication_messages where account_id in ($ACC)"
 [06_message_classification_rules]="select * from public.message_classification_rules where account_id in ($ACC) or workspace_id in ($WS)"
 [07_message_watch_rules]="select * from public.message_watch_rules where account_id in ($ACC) or workspace_id in ($WS)"
 [08_gmail_sync_jobs]="select * from public.gmail_sync_jobs where account_id in ($ACC) or workspace_id in ($WS)"
 [09_intelligent_cases]="select * from public.intelligent_cases where id in ($CASES)"
 [10_case_messages]="select * from public.case_messages where case_id in ($CASES)"
 [11_case_events]="select * from public.case_events where case_id in ($CASES)"
 [12_case_participants]="select * from public.case_participants where case_id in ($CASES)"
 [13_case_notifications]="select * from public.case_notifications where case_id in ($CASES)"
 [14_case_reclassification_runs]="select * from public.case_reclassification_runs where id in ($RUNS)"
 [15_reclassification_backup_rows]="select * from public.reclassification_backup_rows where run_id in ($RUNS)"
 [16_hms_notifications]="select * from public.hms_notifications where id in ($NOTIF)"
 [17_push_delivery_log]="select * from public.push_delivery_log where notification_id in ($NOTIF)"
 [18_organizational_patterns]="select * from public.organizational_patterns where workspace_id in ($WS)"
 [19_push_subscriptions]="select id,workspace_id,profile_id,device_label,is_active,created_at from public.push_subscriptions where workspace_id in ($WS)"
 [20_donexto_preferences]="select * from public.donexto_preferences where workspace_id in ($WS)"
 [21_system_incidents_ids]="select id,account_id,workspace_id,sync_job_id from public.system_incidents where account_id in ($ACC) or workspace_id in ($WS)"
)
for k in $(printf '%s\n' "${!Q[@]}" | sort); do
  psql "$DB_URL" -v ON_ERROR_STOP=1 -Atc "set default_transaction_read_only=on; copy (${Q[$k]}) to stdout with csv header" > "$OUT/$k.csv"
done
( cd "$OUT" && sha256sum *.csv > SHA256SUMS && wc -l *.csv )
tar -C "$OUT" -czf - . | gpg --symmetric --cipher-algo AES256 -o "$OUT.tgz.gpg"   # la frase de paso la guarda Héctor
rm -rf "$OUT"
echo "Respaldo cifrado: $OUT.tgz.gpg"
# RESTAURACIÓN (solo si hace falta revertir):
#  1) gpg -d respaldo.tgz.gpg | tar xz -C /tmp/rest ; sha256sum -c SHA256SUMS
#  2) En una transacción, en este orden: 01→20 con "\copy tabla from 'NN_tabla.csv' csv header"
#     (los workspaces primero; los hijos después). push_subscriptions no se restaura (el navegador se vuelve a suscribir).
#  3) system_incidents: update ... set account_id/workspace_id/sync_job_id desde 21_*.csv.
#  4) Reconectar los buzones desde la app; las credenciales no se restauran.
#  5) Comparar los conteos con wc -l y ejecutar 01_dry_run_select.sql: deben salir los mismos números de antes.
