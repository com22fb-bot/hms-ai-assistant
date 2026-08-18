# Catálogo de clasificación Donexto

**Interno.** México y Estados Unidos son el producto de ahora.
Canadá, UE y Latinoamérica ya están en las bases de remitentes
aunque el país no esté a la venta.

Clasificador: `logistica1-triage-v4`  
Código: `backend/app/services/classification_catalog/`  
Fuente de verdad: `taxonomy.py` + directorios de dominios.

---

## Cómo se decide (orden)

1. Borrador / spam / papelera → se ignora.
2. Correo que tú enviaste → esperando respuesta o informativo.
3. **Remitente conocido** (banco, pedido, reserva, red social).
   Gmail no manda: un Citibanamex etiquetado “Social” sigue siendo aviso de banco.
4. Código de verificación / nuevo dispositivo / fraude → aviso (N1),
   aunque venga de LinkedIn o Google.
5. Etiqueta Social de Gmail o dominio de red → redes sociales (N3).
6. Publicidad / newsletter → publicidad (N3).
7. Plazos, cortes, facturas vencidas → aviso (N1).
8. no-reply genérico → automatizado (N3), **salvo** que el dominio sea banco/tienda/aerolínea.
9. Persona pidiendo algo o pago a tu cargo → requieren atención (N1).
10. Lo demás ambiguo → revisión humana.

El dominio se compara por **sufijo real** (`mail.x.com` sí, `citibanamex.com` no).
Nunca por substring. Ese era el bug de Banamex en redes sociales:
`x.com` vivía dentro de `citibanamex.com`.

---

## Niveles en Inicio

| Nivel | Claves | Qué hace Donexto |
| --- | --- | --- |
| N1 Ahora | `action_required`, `notice`, `review` | Dinero, seguridad, logística, acción o duda |
| N2 Después | `waiting_external`, `informational` | Útil, no interrumpe |
| N3 Silencio | `social`, `promotional`, `automated` | Sin push |

---

## Qué va en cada clave

### Requieren atención (`action_required`) — N1

Una persona o un trámite te pide **hacer** algo: enviar, confirmar, pagar tú.
No es el aviso automático del banco de que ya se hizo un cargo.

- MX: el colegio pide el comprobante; un cliente pide el CFDI.
- US: “please confirm”, “invoice due — please send payment”.

### Avisos importantes (`notice`) — N1

Aquí viven **bancos, pedidos, reservas y seguridad**.

**Bancos y dinero**

- Sí: cargo, depósito, SPEI, estado de cuenta, 2FA del banco, fraude, cargo no reconocido.
- No: “aumenta tu línea”, millas, Hot Sale de la tarjeta (eso es publicidad).
- MX: Citibanamex, Banamex, BBVA, Banorte, Santander, HSBC, Scotiabank, Nu, Mercado Pago, Amex.
- US: Chase, Bank of America, Wells Fargo, Citi, Capital One, US Bank, Discover, Amex, PayPal, Chime.
- CA (listo, aún no a la venta): RBC, TD, Scotiabank, BMO, CIBC, Desjardins.
- UE: Santander, BBVA, CaixaBank, Barclays, HSBC UK, Deutsche Bank, BNP, Revolut, N26, ING.
- LATAM: Bancolombia, Nubank, Itaú, Galicia, BCP, BAC, Banreservas, Banco de Chile.

**Pedidos y compras**

- Sí: orden confirmada, enviado, en camino, entregado, reembolso, número de guía.
- No: “50% off” / newsletter de la misma tienda.
- MX/US: Amazon, Mercado Libre, Walmart, Liverpool, Coppel, DHL, FedEx, UPS, Rappi, Uber.

**Reservas y viajes**

- Sí: confirmación, check-in abierto, cambio de vuelo, boarding pass, hotel.
- No: “vuela desde $499” / promo de millas.
- MX/US: Aeroméxico, Volaris, Viva, Delta, United, American, Booking, Airbnb, Marriott, Hilton.

**Seguridad de cuentas**

- Código de verificación, nuevo dispositivo, reset de contraseña, fraude.
- Aunque el remitente sea LinkedIn o Google, esto **no** es ruido social.

### Revisión humana (`review`) — N1

Correo personal sin un pedido claro. Donexto no inventa.

### Esperando respuesta (`waiting_external`) — N2

Tú ya contestaste. El siguiente paso es del otro.

### Informativos (`informational`) — N2

Útil, sin plazo ni acción. No meter aquí estados de cuenta ni tracking.

### Redes sociales (`social`) — N3

LinkedIn, Facebook, Instagram, X, TikTok, YouTube, Reddit, Pinterest, Snapchat, Threads, Twitch.
Likes, follows, “people you may know”, digest semanal.

**Nunca:** Citibanamex, Banamex, Chase, Amazon, vuelos, hoteles.

### Publicidad (`promotional`) — N3

Newsletters, campañas, descuentos, vacantes masivas.
Sí puede ser del banco o de Amazon **si** el remitente es `offers@` / `newsletter@` / `marketing@` y el texto no es un cargo ni un envío.

### Automatizados (`automated`) — N3

no-reply genérico de un SaaS. Un `noreply@banamex.com` con un cargo **gana el banco** (notice).

---

## Qué hacer si un banco sigue mal clasificado

En la app: **Clasificación inteligente** (reclasifica el buzón con `logistica1-triage-v4`).

Si el dominio no está en `banks.py` / `commerce.py` / `travel.py`, agrégalo ahí
con región y país; no lo metas a redes sociales.
