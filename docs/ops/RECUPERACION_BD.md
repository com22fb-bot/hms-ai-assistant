# Recuperación de la BD de Donexto desde respaldo

Prueba real: 23-oct-2026 ~16:55 CDMX, en Postgres 17 efímero en la caja (nunca en prod). Base efímera y archivos borrados al terminar.

## Resultado de la prueba
- Respaldo: `r2://donexto-backups/db/donexto-db-20261023T0411Z.dump.gpg` (22-oct 22:11 CDMX), 17.9 MB cifrado, 18.4 MB descifrado.
- Integridad: sha256 local = sha256 guardado en los metadatos del objeto (coinciden).
- Restauración: 914 entradas en 1.9 s; 3 errores, todos de `supabase_vault` (extensión exclusiva de Supabase; no existe en Postgres estándar). En un proyecto Supabase destino la extensión ya existe.
- Estructura vs prod (leída en solo lectura): tablas public 49 = 49, claves foráneas 78 = 78, políticas RLS 13 = 13, índices 142 = 142, RLS activo en las 49, auth.users 2 = 2, storage.objects 0 = 0. Funciones 71 vs 72: la que falta es `admin_mailbox_stats`, creada después del respaldo (migración 20261023_001).
- Filas: `admin_events` del respaldo = 23 = eventos de prod con fecha ≤ hora del respaldo (coincide exacto). El resto de diferencias son actividad posterior al respaldo (borrado de buzones de prueba y nuevas entradas de Bitácora del 23-oct).
- El volcado aún incluía los 2 esquemas de respaldo de agosto, que se archivaron y quitaron de prod el 23-oct.

## Qué se probó / qué NO
**Probado:** restauración de la BD (volcado `pg_dump -Fc`) solo en Postgres 17 efímero en la caja; verificación de estructura y conteos contra prod en solo lectura.

**NO probado:**
- Recuperación completa de Supabase: servicios administrados (Auth, Realtime, PostgREST, Edge), extensión `supabase_vault` y sus secretos, configuración de Auth (proveedores, URLs, plantillas, límites).
- Storage: prod tiene 0 objetos, así que no se demostró recuperar archivos.
- Restauración sobre un proyecto Supabase real (ni nuevo ni prod).

> ⚠️ **Advertencia: esquemas de agosto en el volcado.** Los respaldos de este periodo incluyen 2 esquemas de respaldo de agosto (`hms_backup_*`) que ya se retiraron de prod el 23-oct-2026. Restaurar tal cual los volvería a introducir. Antes de restaurar en cualquier destino: `pg_restore -l b.dump > lista.txt`, identificar las entradas de esos esquemas, decidir con Héctor su trato (excluir o restaurar aparte) y restaurar con la lista filtrada: `pg_restore -L lista_filtrada.txt …`.

## Postgres estándar vs proyecto Supabase
- **Postgres estándar (lo probado):** solo restaura tablas, datos, funciones, políticas e índices del volcado. No existen `supabase_vault`, Auth, PostgREST ni Storage como servicios; los roles `anon/authenticated/service_role` hay que crearlos a mano, y con `--no-privileges` los GRANT no se restauran.
- **Proyecto Supabase (NO probado):** ya trae roles, extensiones (incl. `supabase_vault`) y servicios. Hay que restaurar sobre esquemas que ya existen (auth, storage) sin pisar lo administrado, reconfigurar Auth (proveedores OAuth, URLs, plantillas) y recuperar Storage por separado.

## Diferencias esperadas al restaurar este respaldo
- 3 errores de `supabase_vault` (exclusiva de Supabase) en Postgres estándar: esperados.
- `admin_mailbox_stats` no está: se creó después del respaldo (migración 20261023_001); reaplicar migraciones posteriores.
- 2 esquemas de respaldo de agosto incluidos (ver advertencia).
- Storage con 0 objetos: la prueba **no** demuestra recuperación de archivos.

## Validación post-restauración (obligatoria)
1. `pg_restore` sin errores fuera de la lista esperada.
2. Conteos de tablas, FK, políticas, índices y funciones vs referencia; RLS activo en todas las tablas public.
3. Conteo de filas por tabla y `admin_events` hasta la hora del respaldo.
4. Permisos efectivos: anon sin acceso a tablas sin políticas; authenticated solo lo suyo; service_role operativo.
5. Login, /admin, Bitácora y advisors de Supabase.

> **Autorización:** restaurar sobre producción requiere autorización expresa de Héctor, por escrito, y un respaldo inmediato previo.

## Procedimiento (pasos)
1. Congelar escrituras: pausar workers/sync (auto-sync ya está apagado) y avisar a Héctor.
2. Elegir el respaldo: `aws s3 ls s3://donexto-backups/db/ --endpoint-url https://<ACCOUNT>.r2.cloudflarestorage.com` (credenciales desde Doppler `donexto/prd`; nunca imprimirlas).
3. Descargar y verificar: `aws s3 cp …`; comparar `sha256sum` con `aws s3api head-object … --query Metadata.sha256`.
4. Descifrar en carpeta 700: `gpg --batch --pinentry-mode loopback --passphrase-fd 3 -d -o b.dump b.gpg 3<<<"$BACKUP_PASSPHRASE"`.
5. Ensayo obligatorio en Postgres 17 efímero: crear roles `anon authenticated service_role`, luego `pg_restore --no-owner --no-privileges -d <efímera> b.dump`. Aceptable: solo errores de `supabase_vault`.
6. Verificar: tablas, FK, políticas, índices, funciones y conteos vs lo esperado.
7. Restaurar en destino (solo con autorización expresa de Héctor): preferir un proyecto Supabase NUEVO y cambiar variables; restaurar sobre prod solo si no hay alternativa, tras otro respaldo inmediato.
8. Revisar después: login, /admin, Bitácora, advisors; registrar en la Bitácora.
9. Borrar volcados descifrados y bases efímeras.
