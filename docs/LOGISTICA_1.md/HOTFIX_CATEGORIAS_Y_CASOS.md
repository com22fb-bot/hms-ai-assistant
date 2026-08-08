# Logística 1 — Hotfix de categorías y casos

## Problemas corregidos

1. El dashboard mostraba como máximo siete casos aunque existieran más.
2. Una búsqueda sin coincidencias mostraba “No hay casos pendientes”, lo que
   parecía indicar que los casos habían desaparecido.
3. No existía un área visible para Social, Publicidad, Avisos, Automatizados e
   Informativos.
4. La restricción de base de datos no aceptaba la categoría Social.
5. El clasificador anterior interpretaba boletines y notificaciones automáticas
   como casos accionables.

## Nuevo comportamiento

- El bloque de casos muestra todos los casos devueltos por el dashboard.
- La búsqueda tiene botón para limpiarse y un mensaje correcto cuando no hay
  coincidencias.
- Se incorpora **Clasificación del correo** con categorías expandibles.
- Los avisos automáticos importantes se muestran en **Avisos importantes** y no
  crean un caso por defecto.
- Social, publicidad y automatizados permanecen visibles, pero separados de los
  casos.
- Solo solicitudes humanas claras o seguimientos de un caso abierto pueden
  generar un caso.

## Respaldo

Antes de reclasificar se creó en Supabase:

`hms_backup_logistica1_triage_20260804_2155_mx`

El correo original en Gmail no se modifica.
