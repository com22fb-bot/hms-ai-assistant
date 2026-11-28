# Recuperación de la BD de Donexto desde respaldo

Prueba real más reciente: 28-nov-2026 ~04:07–04:10 hora del centro de México, en Postgres 17.12 efímero (127.0.0.1:5433) en la caja. Nunca se tocó producción. Base efímera, volcados descifrados y clúster local se borraron al terminar.

## Resultado de la prueba del 28-nov-2026

Dictamen: **COMPROBADA CON LIMITACIONES**. La base de datos diaria se restauró bien en un Postgres aislado. Storage no se pudo demostrar (no hay archivos que restaurar). La configuración queda cubierta solo en parte por el respaldo semanal.

### Base de datos (comprobada)

- Respaldo: `r2://donexto-backups/db/donexto-db-20261128T090032Z-r46128389947-a1.dump.gpg` (28-nov 03:01 hora del centro de México; 09:01 UTC).
- Tamaño: 6,157,524 bytes cifrado; 6,571,338 bytes descifrado. Caduca el 28-dic-2026 (regla `delete-30d` de R2).
- Integridad: sha256 local = sha256 en metadatos del objeto = `c9b289f6c1c6c66b80006233539fbfbdc6a5b69226c52dd0eb8f6d04ccfeea80`.
- Tiempos: descarga 0.846 s, descifrado 0.164 s, `pg_restore` 0.851 s.
- Restauración: 864 entradas en la lista; 3 errores, todos de `supabase_vault` (extensión exclusiva de Supabase; no existe en Postgres estándar). Cero advertencias. En un proyecto Supabase destino esa extensión ya existe.
- Estructura restaurada: esquemas `auth`, `extensions`, `graphql`, `graphql_public`, `public`, `realtime`, `storage`, `supabase_migrations`, `vault`; tablas public 49; claves foráneas 78; políticas RLS 13; índices 142; funciones public 73; RLS activo en las 49 tablas public; `auth.users` 2; `storage.objects` 0; `storage.buckets` 0; migraciones registradas 36.
- El volcado **ya no incluye** los esquemas `hms_backup_*` de agosto (0 entradas).
- Las tablas de CONTACTS_V1 (`message_participants`, `contact_addresses`, `own_address_aliases`) no están en el volcado: la migración no se ha aplicado en producción.
- `admin_events`: 194 filas, de 2026-10-21 19:22 a 2026-11-27 19:10 (hora del centro de México). Otras tablas con datos (conteo exacto, sin contenido): `communication_messages` 1633, `communication_threads` 1495, `account_cleanup_runs` 50, `admin_expenses` 18, `workspaces` 2, `profiles` 2.
- Permisos: la prueba usó `--no-privileges`, así que no se restauraron GRANT. El rol `anon` recibió "permission denied" al leer `admin_events`, coherente con ese modo. En un destino Supabase hay que apoyarse en los privilegios que ya trae el proyecto.
- No se consultó el esquema ni los datos de producción en esta corrida. No se afirma igualdad bit a bit con el estado en vivo posterior al volcado.

### Storage (no comprobado)

- El bucket `donexto-backups` no tiene prefijo `storage/`. Un listado completo del bucket (67 objetos) no encontró ninguna clave con "storage".
- El volcado diario tiene `storage.objects` = 0 y `storage.buckets` = 0. También `attachments` = 0 y `emails` = 0.
- Conclusión: no hay archivos que restaurar, así que esta prueba **no** demuestra recuperación de Storage. El respaldo diario y el semanal tampoco incluyen un archivo de objetos de Storage.

### Configuración (comprobada en parte, con el semanal del 22-nov)

- Respaldo: `r2://donexto-backups/weekly/donexto-weekly-20261122T090048Z-r45005402587-a1.tar.gpg` (22-nov 03:01 hora del centro de México).
- Integridad: sha256 local = metadatos = `586c819978c43a0208f10f01f509fddcdfcd41e9e0db6f44390887e705f613d8`. Los 10 checksums internos de `SHA256SUMS` coincidieron.
- Tiempos: descarga 1.753 s, descifrado 0.260 s.
- Contenido verificado (nombres y tamaños, sin copiar secretos): `db.dump`, `auth_data.dump`, `roles.sql` (15 roles de Supabase, sin contraseñas), `repo.bundle`, `worker.multipart`, `worker_settings.json` (8 bindings: ASSETS, URLs públicas, `HMS_PROXY_SECRET` como `secret_text` sin el valor), `rulesets.json`, `zone_settings.json`, `dns.bind` (SOA, NS, CNAME, MX, TXT), `env_names_inventory.txt` (solo apunta a Doppler `donexto/prd`).
- El `db.dump` semanal tiene las mismas 864 entradas de lista que el diario.
- El `repo.bundle` se clonó bien, pero su `main` apunta a `28a5b8ba` (31-oct-2026, merge de #214). No es una copia actualizada del repositorio; la fuente de verdad del código sigue siendo GitHub.
- **No está en el respaldo:** configuración del panel de Auth de Supabase (URLs del sitio, redirecciones, plantillas de correo, límites), secretos de `supabase_vault`, inventario de Railway más allá del texto, ni objetos de Storage.
- Recuperación completa sobre un proyecto Supabase real (nuevo o de producción): **no probada**.

## Qué se probó / qué NO (28-nov-2026)

**Probado:** descarga y verificación sha256 de los respaldos diario y semanal; descifrado; restauración de la BD diaria en Postgres 17 efímero; conteos de estructura y filas; listado del bucket R2; integridad y listado del tar semanal; clonación de prueba del `repo.bundle`.

**NO probado:** recuperación de archivos de Storage (no hay ninguno en el respaldo); restauración sobre un proyecto Supabase; `supabase_vault` y sus secretos; reconfiguración del panel de Auth; login, /admin o advisors contra un destino real.

## Advertencia sobre volcados antiguos

Los respaldos anteriores al retiro de los esquemas de agosto (23-oct-2026) pueden incluir `hms_backup_*`. El volcado diario del 28-nov ya no los trae. Antes de restaurar un volcado viejo: `pg_restore -l b.dump > lista.txt`, identificar esas entradas, decidir con Héctor su trato y, si se excluyen, restaurar con `pg_restore -L lista_filtrada.txt …`.

## Postgres estándar vs proyecto Supabase

- **Postgres estándar (lo probado):** restaura tablas, datos, funciones, políticas e índices del volcado. No existen `supabase_vault`, Auth, PostgREST ni Storage como servicios; los roles `anon/authenticated/service_role` hay que crearlos a mano, y con `--no-privileges` los GRANT no se restauran.
- **Proyecto Supabase (NO probado):** ya trae roles, extensiones (incl. `supabase_vault`) y servicios. Hay que restaurar sobre esquemas que ya existen (auth, storage) sin pisar lo administrado, reconfigurar Auth (proveedores OAuth, URLs, plantillas) y recuperar Storage por separado si algún día hay archivos.

## Validación post-restauración (obligatoria)

1. `pg_restore` sin errores fuera de la lista esperada (`supabase_vault` en Postgres estándar).
2. Conteos de tablas, FK, políticas, índices y funciones vs referencia; RLS activo en todas las tablas public.
3. Conteo de filas por tabla y `admin_events` hasta la hora del respaldo.
4. Permisos efectivos: en un destino Supabase, anon sin acceso a tablas sin políticas; authenticated solo lo suyo; service_role operativo. Una prueba con `--no-privileges` en Postgres estándar no demuestra esos GRANT.
5. Login, /admin, Bitácora y advisors de Supabase, solo cuando el destino sea un proyecto Supabase autorizado.

> **Autorización:** restaurar sobre producción requiere autorización expresa de Héctor, por escrito, y un respaldo inmediato previo.

## Procedimiento (pasos)

1. Congelar escrituras: pausar workers/sync (auto-sync ya está apagado) y avisar a Héctor.
2. Elegir el respaldo: `aws s3 ls s3://donexto-backups/db/ --endpoint-url https://<ACCOUNT>.r2.cloudflarestorage.com` (credenciales desde Doppler `donexto/prd`; nunca imprimirlas). Para configuración, usar además `s3://donexto-backups/weekly/`.
3. Descargar y verificar: `aws s3 cp …`; comparar `sha256sum` con `aws s3api head-object … --query Metadata.sha256`.
4. Descifrar en carpeta 700: `gpg --batch --pinentry-mode loopback --passphrase-fd 3 -d -o b.dump b.gpg 3<<<"$BACKUP_PASSPHRASE"`.
5. Ensayo obligatorio en Postgres 17 efímero: crear roles `anon authenticated service_role`, luego `pg_restore --no-owner --no-privileges -d <efímera> b.dump`. Aceptable: solo errores de `supabase_vault`.
6. Verificar: tablas, FK, políticas, índices, funciones y conteos vs lo esperado.
7. Restaurar en destino (solo con autorización expresa de Héctor): preferir un proyecto Supabase NUEVO y cambiar variables; restaurar sobre prod solo si no hay alternativa, tras otro respaldo inmediato.
8. Revisar después: login, /admin, Bitácora, advisors; registrar en la Bitácora.
9. Borrar volcados descifrados y bases efímeras.

## Prueba anterior (23-oct-2026)

Prueba de solo BD, ~16:55 hora del centro de México, documentada en el PR #192.

- Respaldo: `r2://donexto-backups/db/donexto-db-20261023T0411Z.dump.gpg` (22-oct 22:11), 17.9 MB cifrado, 18.4 MB descifrado. sha256 local = metadatos.
- Restauración: 914 entradas en 1.9 s; 3 errores, todos de `supabase_vault`.
- Entonces sí se comparó en solo lectura con producción: tablas public 49 = 49, FK 78, políticas 13, índices 142, RLS en las 49, `auth.users` 2, `storage.objects` 0. Funciones 71 vs 72: faltaba `admin_mailbox_stats` (migración posterior al volcado). `admin_events` 23 coincidía con producción hasta la hora del respaldo.
- Ese volcado todavía incluía los 2 esquemas de respaldo de agosto.
