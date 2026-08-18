# P00 — Pendientes de atención (18 ago 2026)

**Prioridad:** por encima de P0–P12. No se abre Stripe, Free plan ni P2 de verify hasta que esto esté **validado por Héctor** en `https://app.donexto.com`.

**Dueño:** Héctor M. Salcido Roacho · **Cuenta de prueba Yahoo:** `hsalcidor@yahoo.com`

**Por qué existe este punto.** En la misma jornada quedó claro que:

1. Un correo de **Banamex / Citibanamex** se iba a **redes sociales**.
2. Falta un **catálogo explícito** de qué es banco, pedido, reserva, social y publicidad (MX y US).
3. Hay que tener **bases de bancos** de México, EU, Canadá, UE y Latinoamérica aunque Canadá aún no se venda.
4. Hace falta **idioma** en ajustes: español, inglés, francés, italiano y portugués.
5. Conectar Yahoo con el código de 16 dígitos tiene que ser una **guía clic a clic**, no un párrafo.

---

## Estado de código vs producción

| Pieza | PR | Frontend Worker | Backend Railway | Validado por Héctor |
| --- | --- | --- | --- | --- |
| Guía Yahoo (16 dígitos) | [#4](https://github.com/com22fb-bot/hms-ai-assistant/pull/4) | Desplegado | N/A | Pendiente |
| Clasificador v4 + catálogo + bancos | [#5](https://github.com/com22fb-bot/hms-ai-assistant/pull/5) | Copy de avisos desplegado | **Falta merge a `main`** | Pendiente |
| Idioma en ajustes ES/EN/FR/IT/PT | [#6](https://github.com/com22fb-bot/hms-ai-assistant/pull/6) | Desplegado | N/A (metadata Auth) | Pendiente |

Sin merge de **#5**, Banamex en un buzón ya importado **sigue mal clasificado**. Hay que mergear, dejar que Railway publique, y correr **Clasificación inteligente**.

---

## P00.1 — Bancos nunca son redes sociales

- [ ] Merge PR #5 a `main` y confirmar deploy Railway (`logistica1-triage-v4`).
- [ ] En la app: **Clasificación inteligente** sobre el buzón de Héctor.
- [ ] Comprobar que Citibanamex / Banamex / `estadosdecuenta@banamex.com` van a **Avisos (N1)**, no a Social (N3).
- [ ] Un like de LinkedIn / digest de X sigue en **Social**.
- [ ] Oferta `offers@` de un banco sí puede ser **Publicidad**.

Causa del bug: se buscaba `x.com` como substring; `citibanamex.com` lo contiene. El arreglo compara el dominio por sufijo real (`mail.x.com` sí, Banamex no).

---

## P00.2 — Catálogo de clasificación (MX y US)

Documento de producto: `docs/ops/CLASIFICACION_CATALOGO.md` (entra con PR #5).

Hay que poder decir, sin ambigüedad:

| Clave | Nivel | Qué entra | Qué no entra |
| --- | --- | --- | --- |
| `action_required` | N1 | Te piden enviar, confirmar o **pagar tú** | El aviso automático de un cargo ya hecho |
| `notice` | N1 | **Bancos**, **pedidos/compras**, **reservas**, 2FA, fraude, plazos | “Hasta 40% off”, millas, newsletter |
| `review` | N1 | Correo personal ambiguo | Banco, Amazon o LinkedIn ya identificados |
| `waiting_external` | N2 | Tú ya contestaste | Correo nuevo de banco o tienda |
| `informational` | N2 | Útil, sin plazo | Estado de cuenta, guía, boarding pass |
| `social` | N3 | LinkedIn, Instagram, X, TikTok, YouTube (likes, follows, digest) | Citibanamex, Chase, Amazon, vuelos |
| `promotional` | N3 | Campañas, `offers@`, `newsletter@` | Pedido enviado, cargo, check-in |
| `automated` | N3 | no-reply genérico de un SaaS | `noreply@banamex.com` con un cargo → aviso de banco |

- [ ] El catálogo vive en código (`backend/app/services/classification_catalog/`) y en el doc.
- [ ] MX y US son los ejemplos de entrenamiento y QA.
- [ ] Sombreros hogar / oficio / personal **no** son claves de triage; no inventar un cuarto sombrero.

---

## P00.3 — Bases de bancos (MX, US, CA, UE, LATAM)

Aunque el producto **aún no entra a Canadá**, las bases ya deben clasificar si el correo llega.

- [ ] MX: Citibanamex/Banamex, BBVA, Banorte, Santander, HSBC, Scotiabank, Nu, Mercado Pago, Amex, etc.
- [ ] US: Chase, BofA, Wells Fargo, Citi, Capital One, Discover, Amex, PayPal, Chime, etc.
- [ ] CA (listo, no a la venta): RBC, TD, Scotiabank, BMO, CIBC, Desjardins, Tangerine.
- [ ] UE: Santander, BBVA, CaixaBank, Barclays, HSBC UK, Deutsche Bank, BNP, Revolut, N26, ING.
- [ ] LATAM: Bancolombia, Nubank, Itaú, Galicia, BCP, BAC, Banreservas, Banco de Chile.

También pedidos (Amazon, Mercado Libre, Liverpool, DHL…) y reservas (Aeroméxico, Delta, Booking, Airbnb…).

- [ ] Si Héctor reporta un banco que cae mal: **agregar el dominio** en `banks.py`, no meterlo a social.
- [ ] Pedidos y reservas → `notice`, salvo remitente claramente de marketing.

---

## P00.4 — Idioma de la interfaz (ES, EN, FR, IT, PT)

Selector en **Ajustes** (menú, avatar, y tira en el login). PR #6.

- [ ] Validar que se guarda en el dispositivo y en la cuenta.
- [ ] El menú / perfil / cerrar sesión cambian al elegir idioma.
- [ ] **Pendiente de producto:** traducir el resto (login, guía Yahoo, Inicio, categorías, conectar buzón, clasificador). Hoy solo chrome + ajustes.

Idiomas: Español (`es-MX`), English (`en-US`), Français (`fr-FR`), Italiano (`it-IT`), Português (`pt-BR`).

---

## P00.5 — Guía Yahoo, código de 16 dígitos

PR #4 en el Worker. Yahoo no deja IMAP con la clave de mail.yahoo.com.

- [ ] Abrir Yahoo e iniciar sesión → `https://login.yahoo.com/account/security`
- [ ] Conexiones externas → Crear contraseña de aplicación → nombre **Donexto** → pegar `xxxx xxxx xxxx xxxx`
- [ ] Probar con `hsalcidor@yahoo.com` de punta a punta.
- [ ] Si no aparece Conexiones externas: verificación en dos pasos en esa misma página.

---

## Cómo cerrar P00 (definición de hecho)

1. PR #4, #5 y #6 en `main` (o equivalentes mergeados).
2. Railway con clasificador **v4**.
3. Buzón de Héctor **reclasificado**.
4. Héctor confirma: Banamex en Avisos; LinkedIn en Social; Yahoo se conecta con la guía; el idioma se puede cambiar en Ajustes.
5. Solo entonces se retoma P2 (verify buzón) del plan P0–P12.

---

## PRs de esta jornada

- https://github.com/com22fb-bot/hms-ai-assistant/pull/4 — guía Yahoo  
- https://github.com/com22fb-bot/hms-ai-assistant/pull/5 — clasificación + bancos  
- https://github.com/com22fb-bot/hms-ai-assistant/pull/6 — idioma en ajustes  
