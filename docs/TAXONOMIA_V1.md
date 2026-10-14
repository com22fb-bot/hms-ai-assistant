# Taxonomía v1 de Donexto

Aprobada por Héctor el 13 de octubre de 2026, a propuesta de ASTRA.

## Regla general
Cada correo recibe **un área principal** y puede llevar **etiquetas secundarias**. Hay 16 áreas base, que coinciden con `import_categories.CATEGORY_IDS`:

| id | Área |
|---|---|
| security | Seguridad y cuentas |
| bills | Facturas y vencimientos (obligaciones) |
| money | Dinero (movimientos: cargos, depósitos, transferencias) |
| orders | Compras y pedidos |
| subscriptions | Suscripciones y servicios |
| work | Trabajo y negocios |
| home | Hogar y familia |
| health | Salud y bienestar |
| travel | Viajes (vuelos, hoteles, itinerarios) |
| agenda | Eventos y citas (separada de Viajes) |
| insurance | Seguros (área propia) |
| government | Gobierno y documentos |
| education | Educación |
| social | Social: solo redes sociales y comunidades |
| promos | Promociones: es un área visible y también una etiqueta de triage |
| other | Otros: solo correos analizados con baja confianza. No es lo mismo que "pendiente" |

## Criterios
- Los boletines se clasifican por su tema. Social **no** incluye boletines.
- Dinero registra movimientos de dinero. Facturas y vencimientos registra obligaciones. El pago de una factura se queda con la factura, y Dinero puede aparecer como etiqueta secundaria.
- Seguros es un área propia. Una factura de póliza tiene `bills` como área principal y `insurance` como etiqueta.
- Seguridad y Facturas nunca se ocultan ni se reemplazan por otra área.
- Las categorías creadas por el usuario se suman a estas áreas y nunca pueden ocultar Seguridad ni Facturas. Son una función futura y no forman parte del cerebro v1.

## Implementación
- `backend/app/services/brain_v1/taxonomy.py` se usa solo con `BRAIN_V1_ENABLED`. La regla del cerebro determina el área principal; si la regla no la determina, se usa `import_category` por tema.
- Las señales `brain_signals.area` y `brain_signals.area_tags` se guardan solo cuando la bandera está encendida. Con la bandera apagada, el resultado no cambia.
