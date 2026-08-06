# Logística 1 — Correos, reclasificación y favoritos

## Cambios de esta entrega

- Retira del dashboard la franja **Laboratorio de controles**.
- Convierte **Clasificación inteligente** en un botón funcional de prueba.
- La prueba crea un respaldo interno de los casos y relaciones actuales.
- Conserva todos los mensajes descargados y reconstruye únicamente los casos.
- Agrega el módulo **Correos** con bandeja, filtros, búsqueda y paginación.
- Cada fila muestra remitente, asunto, resumen, fecha, categoría y dirección.
- Al abrir un mensaje se muestra el correo completo dentro de HMS.
- El HTML se presenta en un iframe aislado, sin scripts ni recursos externos.
- Agrega el corazón de favoritos con vigilancia por remitente, tema o ambos.
- Las reglas se guardan por usuario y cuenta de correo.
- Los mensajes nuevos que coincidan se registran como coincidencias para las
  futuras notificaciones internas y push.

## Seguridad

- Gmail continúa en modo de solo lectura.
- La reclasificación no borra mensajes descargados.
- Antes de reconstruir casos se guardan copias JSON de las tablas relacionadas.
- Solo propietarios o administradores pueden iniciar la reclasificación total.
- El proceso continúa aunque el usuario cierre sesión o cierre la ventana.

## Separación funcional

- **Correos:** todo el inventario descargado.
- **Casos:** únicamente mensajes que requieren atención.
- **Favoritos:** remitentes o temas que el usuario desea vigilar.
