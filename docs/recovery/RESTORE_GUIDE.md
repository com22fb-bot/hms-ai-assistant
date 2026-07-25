# HMS AI Assistant

# Guía de Restauración del Proyecto

---

# Objetivo

Este documento describe el procedimiento para recuperar completamente el proyecto HMS AI Assistant a partir del repositorio Git.

La restauración incluye:

- Código fuente
- Dependencias
- Variables de entorno
- Base de datos
- Migraciones
- Ejecución del Backend
- Ejecución del Frontend

---

# Requisitos

Antes de comenzar verificar que existan:

- Git
- Python 3.12 o superior
- Node.js LTS
- npm
- Cuenta de Supabase
- Cuenta de Google Cloud (OAuth)

---

# 1. Clonar el repositorio

```bash
git clone <URL_DEL_REPOSITORIO>
cd hms-ai-assistant
```

---

# 2. Cambiar a la rama de desarrollo

```bash
git checkout architecture-v1
```

O, si se desea restaurar un checkpoint específico:

```bash
git checkout <TAG_DEL_CHECKPOINT>
```

---

# 3. Restaurar el Backend

Entrar al directorio:

```bash
cd backend
```

Crear el entorno virtual:

```bash
python -m venv .venv
```

Activarlo:

Linux / macOS

```bash
source .venv/bin/activate
```

Windows

```cmd
.venv\Scripts\activate
```

Instalar dependencias:

```bash
pip install -r requirements.txt
```

---

# 4. Restaurar el Frontend

Entrar al directorio:

```bash
cd ../frontend
```

Instalar dependencias:

```bash
npm install
```

---

# 5. Configurar Variables de Entorno

Crear los archivos correspondientes:

Backend

```
backend/.env
```

Frontend

```
frontend/.env.local
```

Consultar el archivo:

```
docs/recovery/ENVIRONMENT_VARIABLES.md
```

para conocer las variables requeridas.

**Importante:** Los valores de las variables sensibles no se almacenan en el repositorio.

---

# 6. Restaurar Base de Datos

Verificar que el proyecto de Supabase esté disponible.

Aplicar las migraciones del directorio:

```
supabase/migrations/
```

según el procedimiento definido para el proyecto.

---

# 7. Iniciar el Backend

Desde el directorio `backend`:

```bash
uvicorn main:app --reload
```

La API deberá quedar disponible en:

```
http://localhost:8000
```

---

# 8. Iniciar el Frontend

Desde el directorio `frontend`:

```bash
npm run dev
```

La aplicación deberá quedar disponible en:

```
http://localhost:3000
```

---

# 9. Verificaciones

Confirmar que:

- El frontend carga correctamente.
- El backend responde.
- Existe conexión con Supabase.
- El inicio de sesión con Google funciona.
- Se pueden consultar correos de Gmail.

---

# Documentación Relacionada

- PROJECT_STATE.md
- CURRENT_ARCHITECTURE.md
- DECISIONS_AND_PENDING.md
- ENVIRONMENT_VARIABLES.md
- CHECKPOINT_MANIFEST.md
- AI_CONTEXT_HANDOFF.md

---

# Notas

Antes de realizar cambios importantes:

1. Crear un checkpoint.
2. Confirmar que las migraciones estén actualizadas.
3. Realizar commit de la documentación.
4. Verificar que no existan secretos en el repositorio.

---

Última actualización

25 de julio de 2026