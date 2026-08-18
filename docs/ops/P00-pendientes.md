# P00 — Pendientes de atención (18 ago 2026)

**Prioridad:** por encima de P0–P12.

**Dueño:** Héctor M. Salcido Roacho · prueba Yahoo: `hsalcidor@yahoo.com`

## Qué quedó de la jornada

1. Banamex no puede ir a redes sociales.
2. Catálogo banco / pedido / reserva / social / publicidad.
3. Bases de bancos MX, US, CA, UE, LATAM.
4. Idioma en ajustes: ES, EN, FR, IT, PT.
5. Yahoo: **correo + clave**, sin guía de 16 dígitos ni 2FA en Donexto.
6. Landing y app: H1 **Donexto**. Producto = criterio (qué sí requiere acción). Cuatro frentes al **mismo peso**: Dinero · Seguridad · Pedidos · Familia. Hogar no es titular; pedidos no es “envíos”. Publicar landing siempre a Pages **Production / `main`**.

## Estado

| Pieza | Dónde | Prod |
| --- | --- | --- |
| Landing (criterio + 4 frentes) | Pages `donexto` Production `main` | Este deploy |
| Yahoo correo + clave | Worker `donexto-app` + backend IMAP | Worker: este deploy. Railway: al mergear a `main` |
| Idioma ES/EN/FR/IT/PT | Worker ajustes | Este deploy |
| Clasificador v4 + catálogo bancos | `backend` `logistica1-triage-v4` | **Railway solo tras merge a `main`** |

## P00.1 — Bancos ≠ redes

Causa: `x.com` coincidía como substring dentro de `citibanamex.com`. Ahora el match es por sufijo de dominio.

- [x] Código y tests (`backend/tests/test_classification_catalog.py`).
- [ ] Merge a `main` → Railway publica `logistica1-triage-v4`.
- [ ] En la app: **Clasificación inteligente** sobre el buzón de Héctor.
- [ ] Citibanamex / Banamex → **Avisos (N1)**, no Social.
- [ ] LinkedIn / X digest → Social. `offers@` de banco → Publicidad.

## P00.2 — Catálogo

`docs/ops/CLASIFICACION_CATALOGO.md` y `backend/app/services/classification_catalog/`.

## P00.3 — Bases de bancos

MX, US, CA (listo, no a la venta), UE, LATAM en `banks.py`. Pedidos en `commerce.py`. Reservas en `travel.py`.

## P00.4 — Idioma

Selector en Ajustes y tira en el login. Chrome de menú/perfil. El resto de la app sigue en español hasta ampliar traducciones.

## P00.5 — Yahoo

No hay wizard de Seguridad Yahoo ni código de 16 dígitos. En Donexto: correo y la misma clave de Yahoo.

## Landing (por qué “no quedaba”)

Los deploys de Pages desde una rama feature van a **Preview**. `www.donexto.com` y `donexto.com` solo cambian con:

```bash
cd landing/donexto && bash deploy-production.sh
```

Eso usa `--branch main`. Chrome: **Ctrl+Shift+R** si la pestaña es vieja.

## Definición de hecho

1. donexto.com: H1 Donexto; kicker **no** es “Correo del hogar”; pilar 03 = **Pedidos**; prototipo A = **Prioridad**.
2. App login: “Cargos, pedidos, seguridad y familia. El resto espera.” Yahoo pide correo + clave.
3. Merge a `main` + Railway v4 + reclasificar buzón de Héctor.
4. Héctor confirma Banamex en Avisos.
