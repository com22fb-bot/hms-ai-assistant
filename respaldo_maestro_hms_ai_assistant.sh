#!/usr/bin/env bash
set -Eeuo pipefail
cd /workspaces/hms-ai-assistant || exit 1

STAMP="$(date +%Y%m%d-%H%M%S)"
CURRENT_BRANCH="$(git branch --show-current)"
BACKUP_BRANCH="backup/hms-communications-vision-${STAMP}"
BACKUP_TAG="restorepoint-hms-communications-${STAMP}"
DOC_DIR="docs/restorepoints/${STAMP}"
BACKUP_DIR="/workspaces/backups"
mkdir -p "$DOC_DIR" "$BACKUP_DIR"

VISION_DOC="$DOC_DIR/VISION_ESTRATEGICA_HMS_COMMUNICATIONS_AI.md"
TECH_DOC="$DOC_DIR/RESTOREPOINT_TECNICO.md"
LITERAL_DOC="$DOC_DIR/REGISTRO_LITERAL_CAMBIO_DE_PERSPECTIVA.md"
LOG_DOC="$DOC_DIR/VALIDACIONES.log"
BUNDLE_FILE="$BACKUP_DIR/hms-ai-assistant-${STAMP}.bundle"
CHECKSUM_FILE="${BUNDLE_FILE}.sha256"

echo "============================================================"
echo "RESPALDO MAESTRO — HMS AI ASSISTANT"
echo "============================================================"
echo "Fecha: $(date)"
echo "Rama actual: $CURRENT_BRANCH"
echo "Rama de respaldo: $BACKUP_BRANCH"
echo "Etiqueta: $BACKUP_TAG"
echo

git rev-parse --is-inside-work-tree >/dev/null
git remote get-url origin >/dev/null

if [ -z "$CURRENT_BRANCH" ]; then
  echo "ERROR: No se pudo determinar la rama actual."
  exit 1
fi

if [ -d .git/rebase-merge ] || [ -d .git/rebase-apply ] || [ -f .git/MERGE_HEAD ]; then
  echo "ERROR: Existe un merge o rebase pendiente."
  exit 1
fi

echo "Estado inicial:"
git status --short
echo

cat > "$VISION_DOC" <<'EOF'
# Visión estratégica maestra — HMS Communications AI

## Decisión estratégica

El proyecto deja de concebirse como un cliente de correo electrónico.

La nueva perspectiva es construir un:

> **Monitor inteligente de información y Centro de Operaciones de Comunicaciones.**

La aplicación no debe competir contra Gmail, Outlook, WhatsApp, Microsoft Teams, Slack ni otros clientes de mensajería. Las personas ya tienen herramientas para leer mensajes. El problema real es evitar que se escape una solicitud, obligación, pago, compromiso, oportunidad, riesgo o conversación importante.

## Cambio de perspectiva

### Antes

- Mostrar bandejas de entrada.
- Desplegar listas completas de correos.
- Abrir y leer mensajes.
- Replicar funciones de Gmail u Outlook.

### Ahora

- Leer y almacenar comunicaciones autorizadas.
- Analizarlas con inteligencia artificial.
- Detectar lo importante.
- Priorizar.
- Convertir mensajes en avisos, tareas, compromisos, riesgos y oportunidades.
- Mostrar solamente lo que requiere atención.
- Facilitar respuestas, delegación y seguimiento.

Flujo:

```text
Canales de comunicación
        ↓
Ingesta y sincronización
        ↓
Base de datos
        ↓
Análisis mediante IA
        ↓
Clasificación y priorización
        ↓
Monitor inteligente
        ↓
Acciones y seguimiento
```

## Principio fundamental

La pantalla principal no debe ser una bandeja de entrada. Debe ser un centro de operaciones que responda:

> **¿Qué requiere mi atención en este momento?**

Ejemplo:

```text
RESUMEN DEL DÍA

4 asuntos urgentes
8 solicitudes pendientes
3 pagos confirmados
2 clientes llevan varios días sin respuesta
7 tareas vencen hoy
1 factura requiere autorización
5 mensajes mencionan directamente al usuario
3 documentos esperan firma
```

## Mensajes completos

Los mensajes completos se conservarán en la base de datos para mantener contexto, trazabilidad, antecedentes, análisis, respuestas y métricas. Sin embargo, no dominarán la interfaz.

Secuencia:

```text
Resumen inteligente
        ↓
Prioridad
        ↓
Motivo de la prioridad
        ↓
Acciones sugeridas
        ↓
Mensaje completo, solo cuando el usuario lo solicite
```

## Información accionable

El sistema deberá detectar:

- asuntos urgentes;
- solicitudes pendientes;
- mensajes que esperan respuesta;
- pagos pendientes o confirmados;
- facturas;
- autorizaciones;
- cotizaciones;
- compromisos;
- tareas;
- fechas límite;
- citas;
- documentos;
- contratos;
- firmas;
- clientes en riesgo;
- oportunidades comerciales;
- quejas;
- incidencias;
- menciones directas;
- conversaciones abandonadas;
- seguimientos incumplidos;
- responsables;
- prioridades;
- riesgos operativos.

## IA como copiloto

La IA no será solamente un chatbot. Trabajará antes que el usuario para:

- revisar;
- resumir;
- clasificar;
- priorizar;
- detectar riesgos y oportunidades;
- identificar solicitudes y compromisos;
- extraer fechas y cantidades;
- identificar responsables;
- sugerir respuestas;
- crear borradores;
- proponer acciones;
- generar tareas;
- recordar seguimientos;
- medir tiempos;
- presentar estadísticas.

> **No es solamente un chatbot. Es un copiloto y monitor inteligente de comunicaciones.**

## Respuestas asistidas

La aplicación podrá ofrecer:

- respuestas sugeridas;
- varios tonos;
- respuestas formales o breves;
- confirmaciones;
- solicitudes de información;
- notificaciones de retraso;
- borradores editables;
- archivos adjuntos;
- envío desde la aplicación cuando la plataforma lo permita.

El usuario conservará el control antes del envío, salvo automatizaciones expresamente configuradas y permitidas.

## Seguimiento y métricas

Las comunicaciones podrán convertirse en pendientes, tareas, compromisos, seguimientos, asuntos delegados, atendidos, descartados, en espera o con fecha límite.

Se medirán:

- mensajes recibidos;
- mensajes atendidos;
- mensajes no atendidos;
- tiempos de respuesta;
- conversaciones vencidas;
- solicitudes abiertas y cerradas;
- desempeño por responsable;
- reincidencias;
- temas frecuentes;
- tendencias.

## Arquitectura multicanal

La arquitectura deberá poder integrar:

- Gmail;
- Outlook y Microsoft 365;
- WhatsApp Business;
- Teams;
- Slack;
- Telegram cuando sea viable;
- formularios;
- CRM;
- sistemas internos;
- otros canales autorizados.

Todos los elementos podrán convertirse en una entidad común llamada `Comunicación`, con canal, remitente, destinatario, conversación, prioridad, resumen, intención, tarea, compromiso, riesgo, acción pendiente, fecha límite, estado y responsable.

## Papel del trabajo actual

El trabajo realizado no se pierde. Gmail OAuth, sincronización, Supabase, frontend y backend forman la capa de ingesta:

```text
Gmail
  ↓
API de Gmail
  ↓
Sincronización
  ↓
Supabase
  ↓
Análisis mediante IA
  ↓
Monitor inteligente de información
```

## Dirección del Dashboard

El Dashboard deberá incluir:

- resumen del día;
- requiere mi atención;
- personas esperando mi respuesta;
- esperando respuesta de otros;
- compromisos y tareas;
- pagos y documentos;
- clientes en riesgo;
- indicadores y métricas.

## Público del proyecto macro

HMS Communications AI estará orientado a empresas, directivos, áreas administrativas, operativas y financieras, despachos, constructoras, equipos de servicio y organizaciones con alto volumen de comunicaciones.

Podrá ofrecer múltiples usuarios, responsables, permisos, trazabilidad, auditoría, indicadores, integraciones y automatizaciones.

# Proyecto independiente: WhatsaPilot

Se acuerda iniciar un segundo proyecto independiente:

> **WhatsaPilot**

El nombre transmite:

> **WhatsApp en piloto automático o con un copiloto inteligente.**

WhatsaPilot tendrá repositorio, documentación, arquitectura, planificación, interfaz, modelo de negocio y conversación de desarrollo propios. No se mezclará con `hms-ai-assistant`.

## Visión de WhatsaPilot

WhatsaPilot no será otro cliente de WhatsApp ni un chatbot tradicional. Será un asistente que muestre qué mensajes, personas, grupos, solicitudes y compromisos necesitan atención.

Ejemplos:

```text
HOY

189 mensajes recibidos.
Solo 7 requieren atención.
```

```text
Juan espera respuesta desde hace tres días.

Motivo:
Solicitó confirmación de un servicio.

Riesgo:
Puede perderse la venta.
```

```text
Grupo Construcción

248 mensajes.

Resumen:
- Se aprobó la compra de cemento.
- Se cambió la fecha de entrega.
- Héctor debe confirmar al proveedor.
- Falta comprobar un pago.
```

## Mercado

WhatsaPilot buscará atender usuarios personales, profesionistas, prestadores de servicios, vendedores, pequeños negocios, personas con muchas conversaciones, usuarios de WhatsApp Business y empresas pequeñas que aún no necesitan un CRM.

Se estudiarán planes personal, profesional, Business y empresarial. Los precios de $50 o $100 MXN mensuales son hipótesis iniciales que deberán validarse contra costos, comisiones y disposición de pago.

## Restricciones críticas

Antes de programar se investigarán:

- API oficial de WhatsApp Business;
- restricciones de WhatsApp personal;
- políticas de Meta;
- políticas de Google Play y Apple;
- privacidad y consentimiento;
- lectura de notificaciones;
- accesibilidad en Android;
- grupos;
- estados de lectura;
- respuestas;
- riesgos de bloqueo.

No se construirá un negocio sobre ingeniería inversa o técnicas frágiles.

Se separará claramente:

1. Lo permitido por APIs oficiales.
2. Lo técnicamente posible con autorización del usuario.
3. Lo permitido por las tiendas.
4. Lo que podría violar términos.
5. Lo que no debe implementarse.

## Lectura sin marcar como visto

La posibilidad de leer mensajes sin cambiar inmediatamente su estado de lectura queda registrada como idea para investigación. No deberá prometerse hasta verificar viabilidad técnica, privacidad, consentimiento, políticas de WhatsApp, Android y tiendas.

## Distribución, cobro y promoción

Se investigarán Android, Google Play, iOS, suscripciones, Google Play Billing, Apple In-App Purchase, Mercado Pago, Stripe, comisiones, impuestos y recepción de pagos.

La promoción deberá comunicar beneficios concretos:

- ¿Tienes demasiados WhatsApps sin contestar?
- Descubre quién necesita tu atención hoy.
- Deja de perder clientes por olvidar responder.
- La IA resume tus grupos y detecta tus pendientes.
- Menos tiempo leyendo. Más tiempo resolviendo.
- Tu WhatsApp, con copiloto.

## Relación entre proyectos

HMS Communications AI será el proyecto macro empresarial y multicanal.

WhatsaPilot será un producto independiente centrado inicialmente en WhatsApp.

Podrán compartir conceptos y componentes del motor de IA en el futuro, pero no se mezclarán prematuramente.

## Libro del proyecto

A partir de este punto se documentarán:

- propósito;
- problema;
- alcance;
- exclusiones;
- decisiones estratégicas;
- decisiones técnicas;
- alternativas descartadas;
- riesgos;
- cambios de rumbo;
- arquitectura;
- modelo de negocio;
- avances;
- puntos de restauración;
- instrucciones de recuperación;
- siguientes pasos.

## Declaración final

El producto macro no será otro cliente de correo.

Será un sistema que observa comunicaciones autorizadas, comprende su contenido, identifica lo importante y ayuda al usuario a actuar.

> **Reducir el ruido, evitar olvidos y convertir mensajes dispersos en decisiones y acciones concretas.**

WhatsaPilot aplicará el mismo principio:

> **No mostrar todo. Mostrar lo que importa.**
EOF

cat > "$LITERAL_DOC" <<'EOF'
# Registro literal del cambio de perspectiva

Este documento conserva las expresiones que originaron el cambio estratégico.

## Proyecto de correo

> “¿De qué me sirve si en mi aplicación yo realmente despliego los correos? ¿Qué no se supone que la gente de todos modos ve sus correos en su correo normal?”

> “Este aplicativo debería ser más como un panel de avisos, de notificaciones, de cosas interesantes que podamos hacer sobre esos correos electrónicos.”

> “No es lo mismo decir correos urgentes y que los detallemos. Por ejemplo: te escribió Juan Pérez, que requiere el pago de la nómina.”

> “De ahí poder crear la estructura para poder responder desde la misma aplicación.”

> “Darle un reply para contar tiempos de respuesta, cuántos correos no se han recibido, para dar seguimiento a los correos.”

> “Cuando las personas ya lo vieron en el panel principal, ellos van a decidir cuáles correos atender y cuáles no.”

> “¿De qué sirve que les despleguemos toda la información, es decir, todos los correos?”

> “Entiendo que los debemos tener en nuestra base de datos, pero yo preferiría trabajar única y exclusivamente con el que el usuario le gustaría verificar y checar.”

> “Podríamos hacerlo con inteligencia artificial.”

> “Presentar opciones: ¿quieres responderlo?, y ayudarle a responder.”

> “Ponerle ya el texto para responderle conforme a si le están solicitando un pago.”

> “Ayudarle para crear ahí un formato de correo, ponerle el texto y ya que él modifique lo que guste.”

> “Que nada más suba el attachment y pueda enviarlo directamente.”

## WhatsApp

> “Quería yo ver qué tan prudente sería hacer esto, pero para WhatsApp.”

> “Un aplicativo donde va y te lea tus WhatsApps y te diga exactamente quién te escribió y qué es lo que necesita.”

> “Muchas veces las personas en WhatsApp tienen grupos que a lo mejor no checan, que a lo mejor no interesan.”

> “Poner un módulo de grupos y poner ahí las principales acciones por tomar en determinado momento en cualquier grupo.”

> “Hay grupos que te dicen: oye, no has hecho el pago; a ver quién falta: Héctor.”

> “En ese momento poner una notificación: oye, en este grupo están diciendo que hace falta un pago.”

> “Una aplicación como un panel de control de WhatsApp.”

> “Dependiendo de las acciones a tomar, podemos responder un WhatsApp o podemos reenviar ese WhatsApp a otra persona.”

> “Hay miles de cosas, pero creo que estamos equivocándonos en el diseño.”

## Diferencia frente a un chatbot

> “Me dijo un amigo que él se dedica a dar servicios. Entonces recibe muchos WhatsApp y no tiene tiempo de contestarlos.”

> “Me decía que le creara un bot, un chatbot, pero muchas veces también los chatbots reciben y reciben información. A veces la gente tampoco lo ve.”

> “Me gustaría crear una herramienta.”

> “Que funcione como un chatbot, exactamente, sin hacer un chatbot.”

> “Cualquier mensaje que llegue, ponerlo en el panel de control.”

> “Dejar eso como pendiente para que a la gente no se le olvide responder los WhatsApps.”

## Mercado y suscripción

> “Ese es mi mercado nicho que yo quiero tomar.”

> “Que una persona pueda pagar una suscripción de 50 o 100 pesos.”

> “Que su WhatsApp sea realmente un módulo de asistencia.”

> “Cualquier usuario común que tenga una cuenta de WhatsApp lo pueda usar.”

> “Que me pague una membresía de 100 pesos al mes.”

> “Quisiera hacer una prueba porque quiero investigar cómo se sube a Play Store.”

> “Que sea descargado y se instale en los celulares.”

> “Ver cómo puedo cobrar.”

> “Ver si realmente los cargos o los cobros se van a mi cuenta.”

> “Qué gestor de banco utilizar.”

> “Cómo se crearía una campaña de promoción dentro de Facebook, Instagram y las redes.”

> “Principalmente WhatsApp.”

> “Me gustaría ya subir un aplicativo para venderlo porque necesito dinero, estoy sin trabajo y no puedo invertir.”

> “WhatsApp la gente lo usa a diario, entonces es un nicho muy importante que me gustaría atacar.”

## WhatsApp personal y Business

> “No sé si distinguirlo, separarlo de WhatsApp normal a WhatsApp Business.”

> “Que WhatsApp Business fuera una licencia más cara.”

> “Dentro del mismo sistema.”

> “A alguien que nos compre una licencia de WhatsApp normal, darle su módulo para un WhatsApp normal.”

> “Para una persona de WhatsApp Business, darle una atención personalizada, sin necesidad de crearle un chatbot.”

> “Ser nosotros la inteligencia artificial que haga ese chatbot.”

> “Que el usuario pueda construir y configurar.”

## Lectura y vistos

> “Muchas veces en las redes sociales las personas dejan en visto a las personas.”

> “¿Habría la posibilidad de leer todos los WhatsApps sin que realmente cambie el estatus de leído?”

> “¿Quién no quisiera ver lo que te escriben sin que se den cuenta de que ya lo leíste y que te tomes el tiempo para responderlo?”

La función queda registrada como idea para investigación técnica, legal, de privacidad y de políticas. No se considera aprobada ni viable todavía.

## Nombre

> “Me agrada el nombre WhatsaPilot, como si dijera WhatsApp a piloto automático.”

Nombre provisional:

> **WhatsaPilot**

## Decisión final

```text
De:
Cliente de correo y visualización de mensajes.

A:
Monitor inteligente de información y Centro de Operaciones de Comunicaciones.
```

Nuevo proyecto separado:

```text
WhatsaPilot
```
EOF

cat > "$TECH_DOC" <<EOF
# Punto de restauración técnico — HMS AI Assistant

Fecha: $(date)

Rama de trabajo: \`$CURRENT_BRANCH\`

Rama de respaldo: \`$BACKUP_BRANCH\`

Etiqueta: \`$BACKUP_TAG\`

Remoto: \`$(git remote get-url origin)\`

## Estado funcional

- Frontend con Next.js.
- Backend con FastAPI.
- Gmail OAuth funcionando.
- Selección de cuenta Google corregida.
- Consulta directa mediante \`GET /gmail/messages\`.
- Sincronización mediante \`POST /gmail/sync\`.
- Persistencia de mensajes en Supabase.
- Paginación de Gmail disponible.
- Límite actual de sincronización: 500 mensajes por ejecución.

## Tabla principal

\`public.communication_messages\`

Campos relevantes:

- thread_id
- account_id
- provider
- external_message_id
- sender
- recipients
- cc
- bcc
- subject
- body_text
- body_html
- received_at
- has_attachments
- ai_processed
- labels
- is_unread
- snippet

## Migración aplicada

\`supabase/migrations/20260729_001_add_gmail_message_metadata.sql\`

Resultado confirmado:

\`Success. No rows returned.\`

## Gmail Sync

\`backend/app/services/gmail_sync.py\` ya almacena:

- snippet
- labels
- is_unread

## Esquema

\`backend/app/schemas/gmail.py\` contiene los campos necesarios de GmailMessage.

## Siguiente paso pendiente

Crear \`GET /gmail/stored-messages\` para:

1. Obtener la cuenta Gmail activa.
2. Obtener account_id.
3. Consultar communication_messages.
4. Filtrar por account_id.
5. Ordenar por received_at DESC.
6. Aplicar paginación.
7. Responder con GmailMessagesResponse.
8. Mantener temporalmente /gmail/messages.
9. Cambiar después el frontend para leer desde Supabase.

## Cambio estratégico

Los mensajes almacenados alimentarán un monitor inteligente. No se construirá una réplica de la bandeja de entrada.

## Estado antes del commit

\`\`\`text
$(git status --short)
\`\`\`
EOF

: > "$LOG_DOC"
echo "=== git diff --check ===" >> "$LOG_DOC"
git diff --check >> "$LOG_DOC" 2>&1
echo "OK: git diff --check"

echo "=== python compileall ===" >> "$LOG_DOC"
python -m compileall -q backend/app >> "$LOG_DOC" 2>&1
echo "OK: backend Python compila"

git add -A

SENSITIVE_FILES="$(
  git diff --cached --name-only |
  grep -Ei '(^|/)(\.env|\.env\.[^/]+|.*\.pem|.*\.p12|.*\.pfx|.*\.key|credentials\.json|service[_-]?account.*\.json)$' |
  grep -Evi '(\.example|\.sample|\.template)$' || true
)"

if [ -n "$SENSITIVE_FILES" ]; then
  echo "ERROR: Posibles archivos sensibles detectados:"
  echo "$SENSITIVE_FILES"
  git reset
  exit 1
fi

echo "Archivos que se guardarán:"
git status --short

if git diff --cached --quiet; then
  CHECKPOINT_COMMIT="$(git rev-parse HEAD)"
  echo "No había cambios nuevos para confirmar."
else
  git commit -m "checkpoint: respaldo maestro y visión HMS Communications AI"
  CHECKPOINT_COMMIT="$(git rev-parse HEAD)"
fi

git branch "$BACKUP_BRANCH" "$CHECKPOINT_COMMIT"
git tag -a "$BACKUP_TAG" "$CHECKPOINT_COMMIT" -m "Punto de restauración antes de iniciar WhatsaPilot. Incluye el cambio a monitor inteligente de información."

git bundle create "$BUNDLE_FILE" --all
git bundle verify "$BUNDLE_FILE"

if command -v sha256sum >/dev/null 2>&1; then
  sha256sum "$BUNDLE_FILE" > "$CHECKSUM_FILE"
elif command -v shasum >/dev/null 2>&1; then
  shasum -a 256 "$BUNDLE_FILE" > "$CHECKSUM_FILE"
fi

git push origin "$CURRENT_BRANCH"
git push origin "$BACKUP_BRANCH"
git push origin "$BACKUP_TAG"

echo
echo "============================================================"
echo "RESPALDO MAESTRO COMPLETADO"
echo "============================================================"
echo "Commit:               $CHECKPOINT_COMMIT"
echo "Rama de trabajo:      $CURRENT_BRANCH"
echo "Rama de respaldo:     $BACKUP_BRANCH"
echo "Etiqueta:             $BACKUP_TAG"
echo "Documento de visión:  $VISION_DOC"
echo "Registro literal:     $LITERAL_DOC"
echo "Documento técnico:    $TECH_DOC"
echo "Validaciones:         $LOG_DOC"
echo "Git bundle:           $BUNDLE_FILE"
echo "Checksum:             $CHECKSUM_FILE"
echo
git log -1 --oneline
echo
git status --short

if [ -z "$(git status --porcelain)" ]; then
  echo "LIMPIO: No existen cambios pendientes."
fi

echo
echo "Restaurar desde etiqueta:"
echo "git switch -c restauracion-${STAMP} $BACKUP_TAG"
echo
echo "Restaurar desde rama:"
echo "git switch $BACKUP_BRANCH"
echo
echo "Clonar desde bundle:"
echo "git clone $BUNDLE_FILE hms-ai-assistant-restaurado"
echo "============================================================"
