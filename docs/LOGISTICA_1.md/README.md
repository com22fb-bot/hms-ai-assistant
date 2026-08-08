# Logística 1 — Incorporación inicial y operación de correo

## Objetivo

Definir e implementar la primera experiencia completa de HMS desde el acceso
del usuario hasta la presentación de pendientes clasificados en el dashboard.

## Flujo aprobado

1. El usuario crea su cuenta HMS.
2. La pantalla de acceso muestra el robot HMS en el lado izquierdo.
3. El método de pago queda preparado visualmente, pero no se activa hasta que
   el programa funcione correctamente.
4. El usuario conecta una cuenta de correo mediante el proveedor disponible.
5. Al regresar de OAuth, HMS no muestra un dashboard vacío ni exige pulsar
   “Sincronizar Gmail”.
6. HMS inicia automáticamente el inventario inicial de los últimos seis meses.
7. La importación inicial incluye recibidos, enviados y archivados; excluye
   Spam, Papelera y Borradores.
8. HMS muestra el total exacto que se descargará.
9. El usuario confirma la importación.
10. HMS congela los identificadores exactos de la selección.
11. La descarga continúa automáticamente en lotes internos de hasta 100.
12. La pantalla muestra progreso real mediante el robot, la laptop y el
    maletero antiguo cuyos papeles disminuyen.
13. La descarga y la clasificación se muestran como etapas independientes.
14. Cada mensaje se guarda una sola vez.
15. Todos los mensajes importados se clasifican; no todos se convierten en caso.
16. Los mensajes relacionados pueden agruparse en un mismo caso.
17. Al completar descarga y clasificación, HMS abre automáticamente el dashboard.
18. El dashboard separa mensajes, casos, tareas y mensajes no accionables.
19. Durante la primera descarga y clasificación, el botón de actualización queda
    deshabilitado.
20. Después de completar la primera carga, el botón se llama
    “Descargar correos nuevos”.
21. La interfaz no utiliza el nombre de un proveedor como texto general del botón.
22. Las sincronizaciones posteriores descargan solamente mensajes nuevos.

## Notificaciones

HMS deberá incorporar:

- notificaciones push en celular, tablet, laptop y PC;
- avisos internos cuando la aplicación esté abierta;
- centro de notificaciones con campana y contador;
- avisos únicamente para pendientes, riesgos, fechas límite o seguimiento;
- ninguna notificación push para promociones, sociales o mensajes no accionables;
- apertura directa del caso al tocar la notificación.

## Reglas de seguridad

- La importación no modifica el correo original.
- No borra, archiva, etiqueta ni marca mensajes sin autorización explícita.
- El progreso se conserva aunque el usuario cierre o actualice la página.
- La primera importación no puede ejecutarse dos veces accidentalmente.
