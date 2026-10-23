# Migración versionada de OAUTH_ENCRYPTION_KEY y separación de /asistencia (PROPUESTA, no ejecutada)

Solo nombres de variables. Ningún paso se ejecuta sin aprobación de Héctor y ASTRA.

## Usos de OAUTH_ENCRYPTION_KEY (código)
- **Cifrado** (`app/services/oauth_storage.py`): `_get_encryption_secret` → `_derive_fernet` → `_encrypt` (en `save_credentials`) / `_decrypt` (en `get_credentials`). Tabla `oauth_credentials` (access_token, refresh_token). Si cambia sin llavero: las credenciales existentes no se descifran → reconectar buzones.
- **Firma /asistencia** (`app/services/assist.py`): solo si falta `ASSIST_TOKEN_SECRET`, `_legacy_key()` deriva HMAC de OAUTH_ENCRYPTION_KEY para `sign_token`/`read_token`/`_code_digest`. Si cambia: enlaces (7 días), sesiones (24 h) y códigos (10 min) emitidos dejan de validar.

## Fase 0 — separar /asistencia (antes de tocar la llave OAuth)
1. Definir `ASSIST_TOKEN_SECRET` (≥32) y `ASSIST_LEGACY_VERIFY_UNTIL` = ahora + 7 días (TTL del enlace).
2. Efecto: se firma solo con ASSIST_TOKEN_SECRET; los tokens viejos se aceptan hasta la fecha.
3. Al vencer, quitar `ASSIST_LEGACY_VERIFY_UNTIL`. Rollback: quitar `ASSIST_TOKEN_SECRET` (vuelve al histórico; tokens firmados con la dedicada dejan de validar).

## Fase 1 — llavero (coexistencia vieja + nueva)
1. `OAUTH_ENCRYPTION_KEYRING=k2:<nueva>`; `OAUTH_ENCRYPTION_ACTIVE_KEY_ID` vacío (aún cifra con legado). Desplegar: verifica que todas las instancias leen k2.
2. `OAUTH_ENCRYPTION_ACTIVE_KEY_ID=k2`. Lo nuevo se guarda `k2$<fernet>`; lo viejo se sigue leyendo con `OAUTH_ENCRYPTION_KEY`.
3. Rollback de 1–2: dejar `ACTIVE_KEY_ID` vacío; **mantener k2 en el llavero** mientras existan valores `k2$`.

## Fase 2 — re-cifrado
1. `python -m scripts.reencrypt_oauth_credentials` (dry-run: conteos, indescifrables, último cursor).
2. Respaldo previo verificado. `--apply` (reanudable con `--after <cursor>`). UPDATE optimista; vacío se reclasifica (carrera / eliminada / sin confirmar).
3. Indescifrables: se reportan y no se tocan; la decisión (reconectar) es manual.
4. Auditoría final con dry-run: `ya_en_llave_activa` = filas con datos, 0 `por_recifrar`.

## Fase 3 — retiro de la llave vieja
- La llave vieja sigue en `OAUTH_ENCRYPTION_KEY` (y en la SD) mientras haya respaldos que la contengan (retención de respaldos). Nunca borrar antes.

## Formato
`<id>$<token>`; id `[a-z0-9]{1,16}`. Fernet legado es base64url (`gAAAA…`) y no contiene `$`: no hay ambigüedad. Prefijo inválido → se trata como legado y falla controlado (`OAuthCredentialError`).
