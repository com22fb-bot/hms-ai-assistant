# Logística 1 — Bloque A implementado

## Alcance funcional

Este bloque implementa el flujo operativo principal acordado:

1. El robot HMS aparece en el lado izquierdo del acceso.
2. Al entrar con una cuenta de correo conectada y sin primera importación,
   HMS abre automáticamente la pantalla inicial.
3. El inventario inicial se limita a los últimos seis meses.
4. Se excluyen Spam, Papelera y Borradores.
5. El total se calcula mediante IDs únicos.
6. El usuario confirma una sola descarga inicial.
7. HMS descarga automáticamente en lotes internos de 100.
8. La pantalla muestra el maletero, los papeles decrecientes y el traslado
   hacia la laptop.
9. La clasificación se ejecuta durante la descarga.
10. Los mensajes promocionales, sociales, automáticos e informativos no
    crean un caso por defecto.
11. Los mensajes con solicitud, urgencia, fecha límite, recordatorio o riesgo
    pueden crear un caso.
12. Al concluir, HMS vuelve al dashboard.
13. Después de la primera carga, el control se llama
    **Descargar correos nuevos**.
14. Los textos principales son neutrales respecto al proveedor.

## Seguridad

- Gmail continúa con alcance `gmail.readonly`.
- El proceso no borra, archiva, etiqueta ni marca mensajes.
- El modo de contención global permanece activo para las rutas anteriores.
- Solo el flujo autenticado de importación guiada puede escribir mensajes,
  clasificación y casos.
- El trabajo guarda progreso en `gmail_sync_jobs`.
- Si el backend reinicia, consultar el estado intenta reanudar el trabajo.

## Pendiente posterior

Las notificaciones push, la instalación PWA y el método de pago se trabajarán
después de validar con datos reales que esta primera descarga y clasificación
terminen correctamente.
