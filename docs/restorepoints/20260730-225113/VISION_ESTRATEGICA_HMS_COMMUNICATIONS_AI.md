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
