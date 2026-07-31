# Sistema Operativo del Proyecto
## HMS AI Assistant

**Documento:** HMS-POS-001  
**Versión:** 1.0  
**Fecha de aprobación:** 2026-07-31  
**Estado:** OBLIGATORIO  
**Propietario del producto:** Héctor M. Salcido Roacho

---

## 1. Propósito

Este documento define cómo se trabaja en HMS AI Assistant. Su objetivo es evitar pérdida de contexto, decisiones sin registrar, trabajo repetido, respuestas improvisadas y sesiones sin entregables verificables.

Cuando una conversación o sugerencia contradiga este documento, prevalece este documento.

## 2. Fuente oficial de verdad

Orden de autoridad:

1. Código y documentos vigentes en la rama activa.
2. ADR aprobados.
3. Checkpoint documental más reciente.
4. Roadmap y sprint activo.
5. Bitácoras.
6. Conversaciones del chat.

El chat es una mesa de trabajo. No sustituye al repositorio.

## 3. Inicio obligatorio de sesión

Antes de modificar código o arquitectura se revisan:

1. Este documento.
2. El checkpoint más reciente.
3. El sprint activo.
4. `git status`.
5. Rama activa.
6. Último commit.

No se reconstruye el proyecto solo desde memoria conversacional.

## 4. Regla de ejecución

Cuando el propietario solicite “hazlo”, se produce un entregable o se ejecuta una acción disponible.

No se debe:

- repetir el plan varias veces;
- prometer capacidades no disponibles;
- presentar una opción hipotética como disponible;
- detener la ejecución para explicar otra vez lo acordado;
- pedir confirmaciones innecesarias cuando el objetivo es claro.

Una limitación real se informa una sola vez y se continúa con la alternativa ejecutable más directa.

## 5. Registro inmediato de decisiones

Toda decisión que cambie producto, arquitectura, seguridad, datos, experiencia, modelo comercial o alcance se registra antes de continuar con desarrollo dependiente.

Según importancia, produce:

- actualización documental;
- registro de decisión;
- ADR;
- checkpoint documental.

Las decisiones críticas no pueden permanecer solo en el chat.

## 6. Checkpoint documental

Debe incluir:

- ID único;
- fecha;
- hora;
- zona horaria;
- sprint;
- rama;
- decisiones;
- estado técnico;
- pendientes;
- commit de snapshot;
- tag;
- rama de respaldo;
- bundle.

Convención:

`HMS-CP-YYYYMMDD-HHMMSS`

## 7. Relación con Git

Cada checkpoint genera:

1. Commit de snapshot.
2. Documento de trazabilidad.
3. Commit de registro.
4. Tag.
5. Rama de respaldo.
6. Bundle.
7. SHA-256 del bundle.

El tag y la rama de respaldo apuntan al commit de registro.

## 8. Uso del toolkit

```bash
cd /workspaces/hms-ai-assistant
./tools/checkpoint/checkpoint.sh "4.3"
```

El argumento indica el sprint.

El toolkit valida y respalda el estado actual. No crea ni sobrescribe estrategia automáticamente.

## 9. Bitácora de tiempo

Cada proceso guiado en el chat usa:

```text
[AAAA-MM-DD HH:MM] INICIO — Proceso
[AAAA-MM-DD HH:MM] FIN — Proceso
Duración: N minutos
```

El toolkit registra segundos y zona horaria del Codespace.

## 10. Regla de productividad

Cada sesión termina con al menos uno:

- funcionalidad;
- corrección;
- prueba;
- decisión registrada;
- checkpoint;
- despliegue;
- bloqueo probado con evidencia.

La documentación sirve al desarrollo; no lo sustituye.

## 11. Entregables completos

No se pide al propietario reconstruir archivos desde fragmentos dispersos cuando puede entregarse un archivo completo, ZIP o automatización.

## 12. Seguridad

Antes del checkpoint:

- validaciones;
- revisión de secretos;
- exclusión de ZIP locales;
- confirmación de rama;
- ninguna acción destructiva sin autorización.

## 13. Cierre

1. `git status --short` limpio o explicado.
2. Cambios importantes en GitHub.
3. Siguiente paso concreto.
4. Detener Codespaces con `stopcs`.

## 14. Perspectiva vigente

HMS AI Assistant es una Plataforma de Inteligencia Operacional basada en Casos Inteligentes.

La unidad principal es el Caso, no el correo.

El sistema notifica eventos de negocio, no mensajes entrantes.

El Sprint 4.3 construye el Intelligent Case Engine.

## 15. Recuperación ante desviaciones

1. Detener explicaciones repetitivas.
2. Consultar este documento y el checkpoint vigente.
3. Recuperar el último estado verificable.
4. Generar el entregable faltante.
5. Continuar.

No se reinicia el proyecto ni se abre otro chat únicamente por pérdida de contexto.
