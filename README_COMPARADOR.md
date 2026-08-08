# HMS Comparador Gmail ↔ HMS (solo lectura)

Este parche agrega un comparador por `external_message_id`.

## Qué hace

- Enumera todos los IDs actuales de Gmail con `in:anywhere`.
- Lee los IDs almacenados en `communication_messages` para la cuenta activa.
- Calcula:
  - IDs presentes en ambos;
  - IDs faltantes en HMS;
  - IDs que solo existen en HMS;
  - duplicados por ID externo.
- Permite guardar el resultado como JSON desde el asistente visual.

## Qué NO hace

- No importa mensajes.
- No elimina mensajes.
- No archiva ni etiqueta Gmail.
- No modifica Supabase.
- No procesa ni crea casos.
- No desactiva el modo `inventory_read_only`.

## Instalación

Desde la raíz del repositorio:

```bash
cd /workspaces/hms-ai-assistant
tar -xzf HMS_COMPARADOR_INVENTARIO_3.tar.gz
cd backend
python3 -m py_compile app/api/guided_import.py app/services/gmail_import_inventory.py
```

Reinicia backend y frontend para cargar los archivos nuevos.

## Uso

1. Abre **Revisar Gmail**.
2. Pulsa **Contar mi buzón**.
3. Pulsa **Comparar Gmail con HMS**.
4. Revisa los conteos y guarda el reporte JSON.
