# CHECKPOINT DOCUMENTAL
## HMS AI Assistant — Intelligent Case Engine

**Fecha:** 2026-07-31  
**Versión conceptual:** 2.1  
**Estado:** Aprobado para implementación  
**Propósito:** Preservar las decisiones arquitectónicas, funcionales y comerciales tomadas antes del Sprint 4.3.

---

## 1. Decisión principal

HMS AI Assistant deja de concebirse como un cliente o gestor de correo electrónico.

El producto pasa a ser una **Plataforma de Inteligencia Operacional basada en Casos Inteligentes**.

El correo electrónico es la primera fuente de información, pero no es la unidad principal del producto.

La unidad principal es:

> **CASO INTELIGENTE**

Un caso representa una necesidad, obligación, solicitud, problema, compromiso o resultado de negocio que requiere seguimiento.

---

## 2. Principio rector

> HMS AI Assistant no administra correos. Administra trabajo representado mediante Casos Inteligentes.

Los mensajes son evidencia.  
Los hilos son agrupaciones técnicas.  
Las conversaciones son contexto.  
Los eventos representan cambios relevantes.  
Los casos representan trabajo real.

---

## 3. Definición de Caso Inteligente

Un Caso Inteligente puede contener:

- múltiples mensajes;
- múltiples hilos;
- múltiples participantes;
- archivos y documentos;
- solicitudes;
- tareas;
- compromisos;
- recordatorios;
- delegaciones;
- respuestas parciales;
- fechas límite;
- evidencia de cumplimiento;
- riesgos;
- prioridad;
- responsable actual;
- historial de eventos;
- estado operativo.

Un caso no equivale a un correo, un hilo ni una conversación.

---

## 4. Ejemplo de correlación

Mensajes recibidos:

1. Lunes: “Favor de enviar la factura 5”.
2. Miércoles: “Solo como recordatorio”.
3. Viernes: “Segundo recordatorio”.

Resultado esperado:

- No se crean tres pendientes.
- No se crean tres notificaciones aisladas.
- Se crea un solo Caso Inteligente.
- Los tres mensajes se incorporan como evidencia.
- El caso aumenta su nivel de riesgo y prioridad conforme pasa el tiempo.

---

## 5. Diferencia entre mensaje, evento y caso

### Mensaje

Es una pieza de evidencia proveniente de una fuente externa.

### Evento

Es un cambio de negocio relevante detectado por el sistema.

Ejemplos:

- nuevo caso;
- recordatorio importante;
- fecha límite próxima;
- delegación;
- escalación;
- respuesta del cliente;
- caso reabierto;
- caso resuelto.

### Caso

Es la unidad de trabajo completa que agrupa evidencia, participantes, obligaciones, estados, riesgos y resultados.

---

## 6. Carpetas y fuentes que deben sincronizarse

El sistema deberá poder ingerir información de:

- Inbox;
- Sent;
- Archive;
- etiquetas del usuario;
- borradores, al menos en metadatos;
- Trash, de forma controlada;
- Spam, de forma controlada.

El análisis no puede limitarse a Inbox porque el estado real de un caso depende también de lo enviado, delegado, reenviado o respondido.

---

## 7. Correlación de mensajes

El motor de correlación utilizará, entre otros:

- `threadId`;
- `Message-ID`;
- `References`;
- `In-Reply-To`;
- asunto normalizado;
- participantes;
- fechas;
- entidades extraídas;
- similitud semántica;
- relaciones de reenvío;
- cronología;
- contexto organizacional.

La correlación debe poder unir mensajes relacionados incluso cuando no pertenecen al mismo hilo técnico.

---

## 8. Lógica de enviados y resolución

Enviar un mensaje no significa resolver un caso.

Ejemplo:

Cliente → Héctor → Contabilidad → Contabilidad responde a Héctor → Héctor no responde al cliente.

Resultado:

- El caso permanece abierto.
- Existe avance interno, pero no cumplimiento frente al solicitante original.

Otro ejemplo:

Cliente → Héctor → Contabilidad → Contabilidad responde copiando directamente al cliente.

Resultado:

- El sistema puede considerar que el cliente recibió el resultado.
- El caso puede proponerse como resuelto, sujeto a reglas y evidencia.

El motor deberá distinguir entre:

- acuse de recibo;
- respuesta parcial;
- delegación;
- escalación;
- avance interno;
- entrega real;
- cierre efectivo.

---

## 9. Motor de Aprendizaje Organizacional

Se incorpora un componente denominado:

> **Organizational Learning Engine**

Su función será aprender gradualmente:

- quién suele atender facturas;
- quién responde cotizaciones;
- quién autoriza compras;
- quién resuelve incidencias;
- tiempos habituales de respuesta;
- patrones de delegación;
- rutas operativas;
- responsables frecuentes;
- riesgos recurrentes;
- relaciones entre áreas.

El aprendizaje deberá apoyar la clasificación y recomendación, pero no reemplazar automáticamente decisiones humanas críticas.

---

## 10. Política de notificaciones

Decisión aprobada:

> HMS AI Assistant no notifica correos; notifica eventos de negocio.

No se deben generar alertas como:

- “Nuevo correo recibido”.

Sí se deben generar alertas como:

- “Nuevo caso detectado”.
- “Cliente esperando respuesta”.
- “Factura pendiente desde hace cinco días”.
- “Solicitud vence mañana”.
- “Delegación sin seguimiento”.
- “Caso crítico reabierto”.
- “Caso resuelto”.

### Niveles

- **Nivel 0:** sin notificación; solo registro.
- **Nivel 1:** visible en dashboard.
- **Nivel 2:** notificación normal.
- **Nivel 3:** importante.
- **Nivel 4:** crítica.

La prioridad pertenece al caso o evento, no al correo aislado.

---

## 11. Política de sincronización

El motor de sincronización será independiente del motor de casos.

### Responsabilidad del motor de sincronización

- obtener mensajes y metadatos;
- mantener el repositorio actualizado;
- ejecutar sincronización incremental;
- registrar errores y cursores;
- no tomar decisiones de negocio.

### MVP

- sincronización automática aproximada cada cinco minutos;
- botón “Actualizar ahora”;
- procesamiento incremental.

### Evolución posterior

- Gmail push notifications;
- History API;
- sincronización cercana a tiempo real;
- conectores adicionales.

---

## 12. Estrategia para buzones grandes

Para buzones con 10,000, 50,000 o más mensajes:

1. sincronización inicial de los últimos 30 días;
2. expansión en segundo plano:
   - 31–60 días;
   - 61–90 días;
   - 91–120 días;
   - periodos posteriores;
3. profundidad configurable por workspace o buzón.

Esto permite mostrar valor rápidamente sin esperar a importar todo el historial.

---

## 13. Separación entre inteligencia y administración

El producto principal será de inteligencia operacional.

La administración del correo será un módulo independiente y opcional.

### Funciones futuras del módulo administrativo

- archivar;
- etiquetar;
- marcar leído o no leído;
- mover;
- restaurar desde Trash cuando sea posible;
- crear borradores;
- responder;
- reenviar.

### Restricciones iniciales

- no eliminar permanentemente;
- no enviar automáticamente sin autorización;
- no ejecutar acciones destructivas autónomas;
- toda acción debe quedar auditada.

---

## 14. Favoritos

Los favoritos pertenecerán a la base de datos de HMS AI Assistant, no a Gmail.

Esto permite conservar el criterio del usuario independientemente del proveedor de correo.

---

## 15. Correo eliminado

Si un mensaje fue sincronizado previamente, el sistema podrá conservar metadatos y evidencia histórica según la política de retención.

Si el mensaje permanece en Trash, puede ser recuperable mediante el proveedor.

Si fue eliminado permanentemente, no debe prometerse recuperación desde Gmail.

---

## 16. Modelo SaaS

La estructura comercial y técnica será:

Workspace  
↓  
Monitored Assets / Mailboxes  
↓  
Messages  
↓  
Cases  
↓  
Events  
↓  
Learning  
↓  
Dashboard

La monetización podrá considerar:

- cantidad de buzones monitoreados;
- retención;
- volumen de casos;
- capacidad de IA;
- automatizaciones;
- integraciones;
- nivel de auditoría.

El precio no deberá depender únicamente del número de usuarios.

---

## 17. Posicionamiento del producto

HMS AI Assistant evoluciona hacia una:

> **Operational Intelligence Platform**

El correo es la primera fuente.

Fuentes futuras posibles:

- Microsoft Outlook;
- Teams;
- Slack;
- WhatsApp Business;
- otros sistemas operativos y documentales.

El producto no debe convertirse en otro cliente de Gmail u Outlook.

---

## 18. Redefinición del Sprint 4.3

El Sprint 4.3 deja de ser “construir el dashboard”.

Su objetivo será construir las bases del:

> **Intelligent Case Engine**

### Orden de implementación aprobado

1. Synchronization Engine.
2. Message Repository.
3. Correlation Engine.
4. Case Engine.
5. Event Engine.
6. Dashboard.
7. Notifications.
8. Statistics.
9. Organizational Learning incremental.

---

## 19. Estado técnico conocido al momento del checkpoint

Repositorio:

`com22fb-bot/hms-ai-assistant`

Rama de trabajo conocida:

`sprint-4.1-ui`

Stack:

- FastAPI;
- Next.js;
- Gmail OAuth;
- sincronización Gmail existente;
- tema Fado Black.

Endpoints conocidos:

- `GET /gmail/messages`
- `POST /gmail/sync`

Pendiente confirmado antes del nuevo Sprint:

- repositorio persistente de mensajes;
- endpoint de mensajes almacenados;
- modelo formal de casos;
- correlación;
- eventos;
- dashboard de casos.

---

## 20. Regla para decisiones futuras

Toda funcionalidad nueva deberá responder:

> ¿Aporta valor al Caso Inteligente?

Si la respuesta es no, deberá reconsiderarse.

Además:

- las decisiones importantes deberán documentarse de inmediato;
- cada sesión arquitectónica deberá generar un checkpoint documental;
- el repositorio será la fuente oficial;
- el toolkit respaldará únicamente material ya incorporado físicamente al repositorio.

---

## 21. Decisión final

Este checkpoint establece formalmente el cambio de producto:

**De asistente de correo a plataforma de inteligencia operacional basada en Casos Inteligentes.**

Cualquier implementación posterior deberá respetar esta decisión salvo que exista un nuevo ADR que la modifique explícitamente.
