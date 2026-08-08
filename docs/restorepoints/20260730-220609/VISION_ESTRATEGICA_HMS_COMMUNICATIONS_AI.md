# Visión estratégica maestra — HMS Communications AI

## Decisión estratégica

El proyecto deja de concebirse como un cliente de correo electrónico.

La nueva perspectiva es construir un:

> **Monitor inteligente de información y Centro de Operaciones de Comunicaciones.**

La aplicación no debe competir contra Gmail, Outlook, WhatsApp, Microsoft Teams, Slack ni otros clientes de mensajería.

Las personas ya disponen de aplicaciones para leer mensajes. El problema que se busca resolver no es la falta de otra bandeja de entrada.

El problema real es:

> **Que no se escape ninguna solicitud, obligación, pago, compromiso, oportunidad, riesgo o conversación importante.**

---

# 1. Perspectiva anterior

La perspectiva anterior se concentraba en:

- desplegar correos electrónicos;
- mostrar una bandeja de entrada;
- consultar listas completas de mensajes;
- abrir mensajes;
- sincronizar mensajes con Gmail;
- construir funciones similares a las de un cliente de correo.

Ese enfoque tenía una limitación estratégica:

> Si la persona ya ve sus correos en Gmail o Outlook, una aplicación que solamente vuelve a mostrar los mismos correos no aporta suficiente valor.

El usuario no necesita otro lugar para leer todos sus mensajes.

---

# 2. Nueva perspectiva

El producto debe trabajar como una capa inteligente colocada por encima de los canales de comunicación.

La aplicación deberá:

1. Leer y almacenar las comunicaciones autorizadas.
2. Analizarlas con inteligencia artificial.
3. Detectar información importante.
4. Priorizarla.
5. Convertirla en avisos, tareas, compromisos, riesgos y oportunidades.
6. Presentar únicamente lo que requiere atención.
7. Permitir que el usuario decida qué atender.
8. Facilitar las acciones posteriores.

El flujo conceptual será:

```text
Canales de comunicación
        ↓
Ingesta y sincronización
        ↓
Base de datos
        ↓
Análisis mediante inteligencia artificial
        ↓
Clasificación y priorización
        ↓
Monitor de información
        ↓
Acciones y seguimiento
3. Principio fundamental

La pantalla principal no debe ser una bandeja de entrada.

Debe ser un centro de operaciones.

No debe comenzar mostrando:

Correo 1
Correo 2
Correo 3
Correo 4
Correo 5

Debe mostrar algo equivalente a:

RESUMEN DEL DÍA

4 asuntos urgentes
8 solicitudes pendientes
3 pagos confirmados
2 clientes llevan varios días sin respuesta
7 tareas vencen hoy
1 factura requiere autorización
5 mensajes mencionan directamente al usuario
3 documentos esperan firma

La pregunta principal de la aplicación será:

¿Qué requiere mi atención en este momento?

4. Los mensajes completos siguen siendo necesarios

Los correos y mensajes completos deben almacenarse porque son necesarios para:

conservar el contexto;
ejecutar análisis posteriores;
revisar antecedentes;
detectar compromisos;
elaborar respuestas;
crear métricas;
dar seguimiento;
comprobar lo ocurrido;
mantener trazabilidad.

Sin embargo, el contenido completo no debe dominar la experiencia principal.

La secuencia correcta será:

Resumen inteligente
        ↓
Prioridad
        ↓
Motivo de la prioridad
        ↓
Acciones sugeridas
        ↓
Mensaje completo, solamente cuando el usuario lo solicite
5. Ejemplo de información accionable

En lugar de mostrar solamente un correo, el sistema deberá producir una ficha como:

PRIORIDAD ALTA

Remitente:
Juan Pérez

Necesidad detectada:
Requiere el pago de la nómina.

Fecha límite:
Hoy antes de las 15:00 horas.

Riesgo:
El pago podría retrasarse.

Acciones disponibles:
- Ver mensaje original
- Responder con ayuda de IA
- Crear tarea
- Delegar
- Marcar como atendido
- Programar seguimiento

Otro ejemplo:

CLIENTE SIN RESPUESTA

Empresa:
Constructora ABC

Situación:
Solicitó una cotización hace ocho días.

Respuesta detectada:
No existe respuesta enviada.

Riesgo:
Posible pérdida del cliente.

Acciones disponibles:
- Revisar conversación
- Generar respuesta
- Asignar responsable
- Establecer fecha de seguimiento
6. Funciones centrales del monitor de información

El producto deberá detectar y organizar, entre otras cosas:

asuntos urgentes;
solicitudes pendientes;
mensajes que esperan respuesta;
pagos pendientes;
pagos confirmados;
solicitudes de autorización;
facturas;
cotizaciones;
compromisos;
tareas;
fechas límite;
citas;
documentos solicitados;
contratos pendientes;
firmas;
clientes en riesgo;
oportunidades comerciales;
quejas;
incidencias;
menciones directas;
conversaciones abandonadas;
seguimientos incumplidos;
mensajes sin contestar;
mensajes enviados sin respuesta;
tiempo transcurrido desde la última interacción;
responsables;
prioridades;
riesgos operativos;
indicadores de atención.
7. La inteligencia artificial no será solamente un chatbot

La inteligencia artificial no debe limitarse a esperar preguntas.

La IA deberá trabajar antes que el usuario.

Debe comportarse como un copiloto que:

revisa;
resume;
clasifica;
prioriza;
detecta riesgos;
detecta oportunidades;
identifica solicitudes;
identifica compromisos;
extrae fechas;
extrae cantidades;
identifica responsables;
identifica personas mencionadas;
sugiere respuestas;
crea borradores;
propone acciones;
genera tareas;
recuerda seguimientos;
mide tiempos;
presenta estadísticas.

Principio:

No es solamente un chatbot. Es un copiloto y monitor inteligente de comunicaciones.

8. Respuestas asistidas

Cuando el usuario decida atender una comunicación, la aplicación podrá ofrecer:

respuesta sugerida;
varias opciones de tono;
respuesta formal;
respuesta breve;
solicitud de información adicional;
confirmación de pago;
confirmación de recepción;
notificación de retraso;
promesa de seguimiento;
respuesta basada en documentos;
borrador editable;
inclusión de archivos adjuntos;
envío desde la aplicación cuando la plataforma lo permita.

La inteligencia artificial deberá preparar la respuesta, pero el usuario conservará el control antes del envío, salvo que configure expresamente automatizaciones permitidas.

9. Seguimiento

El sistema deberá permitir que el usuario determine cuáles comunicaciones atender y cuáles no.

Las comunicaciones importantes podrán convertirse en:

pendiente;
tarea;
compromiso;
seguimiento;
asunto delegado;
asunto atendido;
asunto descartado;
asunto en espera;
asunto con fecha límite.

El sistema deberá medir:

correos recibidos;
correos atendidos;
correos no atendidos;
tiempo promedio de respuesta;
tiempo máximo de respuesta;
conversaciones vencidas;
solicitudes abiertas;
solicitudes cerradas;
responsables;
desempeño por periodo;
reincidencias;
temas frecuentes.
10. Arquitectura multicanal futura

La arquitectura general deberá permitir conectar diferentes fuentes:

Gmail;
Outlook y Microsoft 365;
WhatsApp Business;
Microsoft Teams;
Slack;
Telegram, cuando sea viable;
formularios web;
sistemas internos;
CRM;
otros canales autorizados.

El origen de la comunicación no debe determinar la lógica del sistema.

Todos los elementos podrán convertirse en una entidad común:

Comunicación

A partir de ella se podrá determinar:

canal;
remitente;
destinatario;
conversación;
prioridad;
resumen;
intención;
tarea;
compromiso;
riesgo;
acción pendiente;
fecha límite;
estado;
responsable.
11. Papel de la sincronización actual de Gmail

El trabajo realizado hasta ahora no se pierde.

La sincronización de Gmail y el almacenamiento en Supabase constituyen la capa de ingesta del sistema.

Arquitectura actual:

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
Monitor de información

La decisión estratégica no elimina la necesidad de almacenar los mensajes.

Cambia la forma en que se presentan y utilizan.

12. Dirección del Dashboard

El Dashboard debe diseñarse como un centro de control y no como una bandeja de entrada.

Secciones previstas:

Resumen del día
asuntos urgentes;
vencimientos;
solicitudes importantes;
pagos;
documentos;
clientes en riesgo;
menciones;
tareas.
Requiere mi atención
elementos ordenados por prioridad;
explicación de la prioridad;
fecha límite;
acciones rápidas.
Esperando respuesta
mensajes enviados;
destinatario;
tiempo transcurrido;
seguimiento recomendado.
Personas esperando mi respuesta
remitente;
tema;
tiempo de espera;
riesgo;
respuesta sugerida.
Compromisos y tareas
compromiso detectado;
responsable;
fecha;
conversación de origen;
estado.
Indicadores
tiempo medio de respuesta;
pendientes;
asuntos vencidos;
solicitudes atendidas;
volumen por canal;
temas;
remitentes;
tendencias.
13. Público del proyecto macro

HMS Communications AI estará orientado principalmente a:

empresas;
directivos;
administradores;
áreas operativas;
áreas financieras;
equipos de servicio;
despachos;
constructoras;
profesionales que administran múltiples canales;
organizaciones con alto volumen de solicitudes.

Podrá ofrecer planes empresariales y funciones como:

múltiples usuarios;
asignación de responsables;
permisos;
trazabilidad;
indicadores;
auditoría;
integraciones;
automatizaciones;
administración centralizada.
14. Proyecto independiente: WhatsaPilot

Se acuerda iniciar un segundo proyecto completamente independiente, con nombre provisional:

WhatsaPilot

El nombre transmite la idea de:

WhatsApp en piloto automático o con un copiloto inteligente.

WhatsaPilot no deberá mezclarse con el repositorio actual.

Tendrá:

repositorio propio;
documentación propia;
arquitectura propia;
planificación propia;
interfaz propia;
modelo de negocio propio;
conversación de desarrollo propia.

El repositorio hms-ai-assistant quedará como proyecto macro.

15. Visión de WhatsaPilot

WhatsaPilot será un asistente inteligente para ayudar a administrar conversaciones de WhatsApp.

No será solamente:

otro cliente de WhatsApp;
una copia de WhatsApp;
un chatbot tradicional;
una lista de conversaciones.

Su propuesta será:

Mostrar qué mensajes, personas, grupos, solicitudes y compromisos necesitan atención.

Ejemplo:

HOY

189 mensajes recibidos.

Solo 7 requieren atención.

Ejemplo:

Juan espera respuesta desde hace tres días.

Motivo:
Solicitó confirmación de un servicio.

Riesgo:
Puede perderse la venta.

Ejemplo de grupo:

Grupo Construcción

248 mensajes.

Resumen:
- Se aprobó la compra de cemento.
- Se cambió la fecha de entrega.
- Héctor debe confirmar al proveedor.
- Falta comprobar un pago.
16. Mercado de WhatsaPilot

WhatsaPilot buscará atender a:

usuarios personales;
profesionistas independientes;
prestadores de servicios;
vendedores;
pequeños negocios;
personas con muchas conversaciones;
personas que olvidan responder;
personas que participan en muchos grupos;
usuarios de WhatsApp Business;
empresas pequeñas que aún no necesitan un CRM completo.

El producto deberá explorar planes diferenciados:

personal;
profesional;
WhatsApp Business;
empresarial.

El objetivo comercial inicial planteado es ofrecer una membresía accesible, posiblemente cercana a:

$50 MXN mensuales;
$100 MXN mensuales;
o niveles superiores según funciones y costos.

El precio final deberá determinarse después de estudiar:

costos de inteligencia artificial;
infraestructura;
almacenamiento;
APIs;
comisiones de las tiendas;
soporte;
viabilidad técnica;
disposición de pago.
17. Restricción crítica de WhatsApp personal

Antes de programar WhatsaPilot deberán investigarse formalmente:

API oficial de WhatsApp Business;
restricciones de WhatsApp personal;
políticas de Meta;
políticas de Google Play;
políticas de Apple;
privacidad;
consentimiento;
lectura de notificaciones;
accesibilidad en Android;
cifrado;
grupos;
estados de lectura;
envío de respuestas;
riesgos de bloqueo;
soluciones permitidas y no permitidas.

No se deberá construir un negocio estable sobre técnicas frágiles, ingeniería inversa o mecanismos que puedan provocar el bloqueo de cuentas.

Se debe separar claramente:

Lo que es posible mediante APIs oficiales.
Lo que es técnicamente posible en Android con autorización del usuario.
Lo que está permitido por las tiendas.
Lo que puede violar términos de servicio.
Lo que no debe implementarse.
18. Lectura sin marcar como visto

Se registró como posible atractivo comercial la capacidad de conocer el contenido de mensajes sin cambiar inmediatamente su estado de lectura.

Esta posibilidad deberá investigarse con especial cuidado.

No debe prometerse hasta comprobar:

viabilidad técnica;
consentimiento;
funcionamiento real;
políticas de WhatsApp;
políticas de Android;
políticas de las tiendas;
implicaciones de privacidad;
riesgos para la cuenta.

La función no debe utilizarse para engaño, vigilancia no consentida ni acceso a comunicaciones ajenas.

19. Modelo de distribución y cobro

WhatsaPilot deberá considerar:

aplicación Android;
publicación en Google Play;
posteriormente iOS;
versión web cuando sea viable;
suscripción;
Google Play Billing;
Apple In-App Purchase;
cobro web mediante proveedor adecuado;
administración de planes;
periodo de prueba;
cancelación;
facturación;
comisiones;
recepción de pagos en una cuenta del propietario.

También se deberán investigar opciones como:

Mercado Pago;
Stripe;
proveedores disponibles en México;
comisiones;
impuestos;
políticas para productos digitales.
20. Promoción

El producto no deberá promocionarse solamente como “inteligencia artificial”.

Debe promocionarse por el beneficio concreto.

Mensajes posibles:

¿Tienes demasiados WhatsApps sin contestar?

Descubre quién necesita tu atención hoy.

Deja de perder clientes por olvidar responder un mensaje.

La IA resume tus grupos y detecta tus pendientes.

Menos tiempo leyendo. Más tiempo resolviendo.

Tu WhatsApp, con copiloto.

La promoción podrá contemplar:

Facebook;
Instagram;
contenido orgánico;
videos demostrativos;
anuncios;
página de aterrizaje;
prueba gratuita;
testimonios;
estrategia de lanzamiento.
21. Relación entre ambos proyectos
HMS Communications AI

Proyecto macro empresarial y multicanal.

Correo + WhatsApp Business + Teams + Slack + otros canales
                            ↓
                Centro inteligente de comunicaciones
WhatsaPilot

Producto independiente enfocado inicialmente en WhatsApp y usuarios individuales, profesionales y pequeños negocios.

WhatsApp autorizado
        ↓
Copiloto personal
        ↓
Prioridades, resúmenes, pendientes y acciones

En el futuro, ambos proyectos podrán compartir conceptos o componentes del motor de inteligencia artificial, pero no deberán mezclarse prematuramente.

22. Principio de conservación del trabajo

Nada de lo desarrollado hasta ahora debe descartarse.

El trabajo actual aporta:

autenticación;
OAuth;
integración con Gmail;
sincronización;
almacenamiento;
Supabase;
estructura de comunicaciones;
procesamiento con IA;
frontend;
backend;
experiencia arquitectónica.

El cambio consiste en orientar el valor del producto hacia:

Información accionable, no acumulación de mensajes.

23. Libro del proyecto

A partir de este punto, el proyecto deberá mantener un Libro del Proyecto que documente:

por qué existe el producto;
qué problema resuelve;
qué no pretende hacer;
decisiones estratégicas;
decisiones técnicas;
alternativas descartadas;
riesgos;
cambios de rumbo;
arquitectura;
modelo de negocio;
avances;
puntos de restauración;
instrucciones de recuperación;
siguientes pasos.

El documento debe permitir que un futuro:

desarrollador;
colaborador;
socio;
auditor;
inversionista;
responsable de soporte;

pueda comprender el proyecto sin depender exclusivamente de la memoria de las conversaciones.

24. Declaración final de visión

El producto macro no será otro cliente de correo.

Será un sistema que observa comunicaciones autorizadas, comprende su contenido, identifica lo importante y ayuda al usuario a actuar.

Su razón de existir es:

Reducir el ruido, evitar olvidos y convertir mensajes dispersos en decisiones y acciones concretas.

WhatsaPilot llevará ese mismo principio al entorno de WhatsApp:

No mostrar todo. Mostrar lo que importa.
