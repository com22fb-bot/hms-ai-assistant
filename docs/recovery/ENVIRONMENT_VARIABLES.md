# HMS AI Assistant

# Variables de Entorno

---

# Objetivo

Este documento registra las variables de entorno requeridas por el proyecto.

**No deben almacenarse aquí contraseñas, tokens, secretos ni claves reales.**

Los valores sensibles deben mantenerse en:

- GitHub Codespaces Secrets
- Variables del servicio de despliegue
- Supabase Secrets
- Un gestor de contraseñas seguro

---

# Backend

Archivo esperado:

```text
backend/.env
```

Variables conocidas:

```env
SUPABASE_URL=
SUPABASE_SECRET_KEY=

GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=

FRONTEND_ORIGINS=

AI_PROVIDER=mock
OPENAI_API_KEY=
OPENAI_MODEL=
CONTACT_AI_PROVIDER=
CONTACT_AI_MODEL=
```

---

# Frontend

Archivo esperado:

```text
frontend/.env.local
```

Variables conocidas:

```env
NEXT_PUBLIC_API_BASE_URL=
```

---

# Descripción de Variables

## `SUPABASE_URL`

URL del proyecto Supabase utilizado por el backend.

## `SUPABASE_SECRET_KEY`

Clave privada utilizada por el backend para comunicarse con Supabase,
incluida la Admin API de Auth.

Debe permanecer únicamente del lado del servidor.

En Railway (servicio `hms-ai-assistant`) vale la clave secret
(`sb_secret_…`) o el JWT legacy con rol `service_role`. No uses la clave
publishable ni el JWT `anon`. El código no lee `SUPABASE_SERVICE_ROLE_KEY`.

## `GOOGLE_CLIENT_ID`

Identificador OAuth de la aplicación configurada en Google Cloud.

## `GOOGLE_CLIENT_SECRET`

Secreto OAuth de Google.

No debe exponerse en el frontend ni almacenarse en Git.

## `GOOGLE_REDIRECT_URI`

URL a la que Google redirige después del proceso de autenticación.

Debe coincidir exactamente con la URL registrada en Google Cloud.

## `FRONTEND_ORIGINS`

Lista de orígenes autorizados por la configuración CORS del backend.

Puede incluir:

- URL de desarrollo
- URL de Codespaces
- URL de producción

## `AI_PROVIDER`

Proveedor del análisis de correos del usuario (`app/services/ai_analyzer.py`).

En producción se deja en `mock`: el análisis es por reglas y no llama a OpenAI.
No controla el borrador de respuestas del formulario de contacto.

## `OPENAI_API_KEY`

Clave de OpenAI. El análisis de correos no la usa mientras `AI_PROVIDER=mock`.
El botón **Redactar con IA** del panel de mensajes sí la usa, si el borrador
de contacto está habilitado.

## `OPENAI_MODEL`

Modelo del análisis de correos cuando `AI_PROVIDER=openai`.
Si `CONTACT_AI_MODEL` no está puesta, el borrador de contacto también la toma
como respaldo.

## `CONTACT_AI_PROVIDER`

Proveedor solo del borrador de respuestas en `/admin` (Mensajes).

- Vacía: `openai` si hay `OPENAI_API_KEY`; si no, queda apagado.
- `off` o `mock`: no redacta, aunque exista la clave. La respuesta se escribe a mano.
- `openai`: redacta al pulsar **Redactar con IA**.

No dispara un borrador al llegar el mensaje. No cambia `AI_PROVIDER`.

## `CONTACT_AI_MODEL`

Modelo de ese borrador. Si está vacía, se usa `OPENAI_MODEL` y, si esa
también está vacía, `gpt-5-mini`. La llamada limita la salida
(`max_output_tokens`) para no gastar de más.

## `NEXT_PUBLIC_API_BASE_URL`

Dirección pública del backend utilizada por el frontend.

Al comenzar con `NEXT_PUBLIC_`, esta variable puede quedar expuesta en el navegador y no debe contener información sensible.

---

# Reglas de Seguridad

1. No subir archivos `.env` al repositorio.

2. No copiar secretos en documentación, capturas o auditorías.

3. No colocar claves privadas en variables `NEXT_PUBLIC_*`.

4. Verificar que `.gitignore` excluya:

```text
.env
.env.*
!.env.example
```

5. Cambiar cualquier secreto que haya sido expuesto accidentalmente.

6. Mantener valores diferentes para desarrollo, pruebas y producción.

---

# Archivo de Ejemplo

Se recomienda mantener archivos sin secretos:

```text
backend/.env.example
frontend/.env.local.example
```

Estos archivos deben contener únicamente los nombres de las variables:

```env
VARIABLE=
```

---

# Respaldo Privado

Los valores reales deben conservarse fuera del repositorio en un respaldo privado y seguro.

El respaldo debe indicar:

- Nombre de la variable
- Entorno al que pertenece
- Fecha de actualización
- Servicio donde está configurada

Nunca debe incluirse en la documentación pública del proyecto.

---

# Última actualización

1 de octubre de 2026