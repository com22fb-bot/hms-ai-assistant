# Estado antes del Sprint 1

Fecha: 2026-08-06
Rama: feature/logistica-1
HEAD: fc73abab3be596d4e0b5a085ecdec52a52ba98c1

## git status --short
```text
 M .gitignore
 M backend/app/api/guided_import.py
 M backend/app/api/messages.py
 M backend/app/core/config.py
 M backend/app/middleware/authentication_context.py
 M backend/app/services/case_engine.py
 M backend/app/services/case_repository.py
 M backend/app/services/gmail_full_sync.py
 M backend/app/services/gmail_import_inventory.py
 M backend/app/services/message_repository.py
 M backend/main.py
 M frontend/app/approved-ui.css
 M frontend/app/layout.tsx
 M frontend/app/page.tsx
 M frontend/components/GuidedImportWizard.tsx
 M frontend/components/guided-import.css
 M frontend/hooks/useCases.ts
?? .hms-logs/
?? HMS_V2_MASTER_20260806.zip
?? HMS_V2_MASTER_20260806.zip.sha256
?? backend/app/api/push_notifications.py
?? backend/app/api/reclassification.py
?? backend/app/services/automatic_mail_scheduler.py
?? backend/app/services/guided_import_job_service.py
?? backend/app/services/message_rules_service.py
?? backend/app/services/message_triage_repository.py
?? backend/app/services/message_watch_service.py
?? backend/app/services/push_service.py
?? backend/app/services/reclassification_service.py
?? backend/app/services/safe_case_classifier.py
?? backend/app/services/web_push_sender.py
?? docs/LOGISTICA_1.md/BLOQUE_B_BUSQUEDA_PUSH.md
?? docs/LOGISTICA_1.md/CORREOS_RECLASIFICACION_FAVORITOS.md
?? docs/LOGISTICA_1.md/HOTFIX_CATEGORIAS_Y_CASOS.md
?? docs/LOGISTICA_1.md/IMPLEMENTACION_BLOQUE_A.md
?? docs/history/2026-08-06-ESTADO-ANTES-SPRINT-1.md
?? frontend/components/MailCategoriesPanel.tsx
?? frontend/components/MailInbox.tsx
?? frontend/components/PushNotificationsPanel.tsx
?? frontend/components/SmartClassificationPanel.tsx
?? frontend/components/logistica-responsive.css
?? frontend/components/mail-categories.css
?? frontend/components/mail-inbox.css
?? frontend/components/push-notifications.css
?? frontend/components/smart-classification.css
?? frontend/public/hms-sw.js
?? frontend/public/manifest.webmanifest
?? scripts/generate_vapid_keys.py
?? scripts/reclassify_logistica1.py
?? supabase/migrations/20260805040500_logistica1_triage_categories.sql
?? supabase/migrations/20260805044000_logistica1_reclassification_favorites_mailbox.sql
?? supabase/migrations/20260805113000_logistica1_search_rules_push.sql
```

## git diff --stat
```text
 .gitignore                                       |   2 +
 backend/app/api/guided_import.py                 |  83 +--
 backend/app/api/messages.py                      | 147 ++++-
 backend/app/core/config.py                       |   4 +
 backend/app/middleware/authentication_context.py |   1 +
 backend/app/services/case_engine.py              |  13 +-
 backend/app/services/case_repository.py          |   4 +-
 backend/app/services/gmail_full_sync.py          |  14 +-
 backend/app/services/gmail_import_inventory.py   | 424 +++++-------
 backend/app/services/message_repository.py       | 260 ++++++--
 backend/main.py                                  |  10 +
 frontend/app/approved-ui.css                     | 334 ++++++++++
 frontend/app/layout.tsx                          |   5 +-
 frontend/app/page.tsx                            | 267 ++++++--
 frontend/components/GuidedImportWizard.tsx       | 803 ++++++++++++-----------
 frontend/components/guided-import.css            | 644 +++++++++++++++++-
 frontend/hooks/useCases.ts                       |  19 +
 17 files changed, 2211 insertions(+), 823 deletions(-)
```
