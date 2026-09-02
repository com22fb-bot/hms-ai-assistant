# Matriz P1 de buzones — personal, empresa, gobierno México

**Fecha:** 2 sep 2026  
**Producto:** Donexto  
**Dueño:** Héctor M. Salcido Roacho  
**Para no perder:** P1 no es “nunca corporativo ni gobierno”. Es *quién firma y cómo se lee el buzón*.  
**Detalle operativo también en:** `docs/ops/DONEX-SEPTEMBER.md` (Pendientes actualizados 2 sep). Puntero en `docs/ops/PLAN-ORIGINAL-PASOS.md` (P1).

No inventar otros dominios MX. Esta lista es la que Héctor pidió dejar por escrito.

---

## Regla de oro: el TLD no es el proveedor

`.mx` / `.gob.mx` / `.com.mx` dicen **país o tipo de dominio**, no quién da el correo.

El usuario escribe el correo y pulsa **Continuar**. El backend mira los **MX**, no el sufijo del dominio.

Ejemplos (no generalizar a todo México):

| Correo / dominio | Qué parece | Qué es de verdad (MX) |
|------------------|------------|------------------------|
| `alguien@televisa.com.mx` | “empresa .com.mx” | Outlook / Microsoft 365 |
| `alguien@cfe.mx` | “.mx” | Outlook / Microsoft 365 |
| `alguien@liverpool.com.mx` | “empresa .com.mx” | Google Workspace |
| `alguien@televisa.com` | “.com” | Google Workspace |
| `alguien@cdmx.gob.mx` | “gobierno .gob.mx” | Google Workspace |
| `alguien@tvazteca.com.mx` | “empresa .com.mx” | Proofpoint (`pphosted`) |
| `hsalcidor@mail.telcel.com` | “mail. = Gmail?” | **No.** `mail.telcel.com` MX `pphosted`. El subdominio `mail.` no lo vuelve Gmail. `@telcel.com` igual. |

Firma siempre en el sitio del proveedor (Microsoft / Google / el que autoricen). **Donexto no pide la contraseña del buzón.** No activar `YAHOO_MAIL_READ_ENABLED`.

---

## Qué significa P1

| P1 **sí** es | P1 **no** es |
|--------------|--------------|
| Microsoft 365 / Outlook / Hotmail **ya** | “Nunca empresa” |
| Google Workspace / Gmail **pronto** (cuando Google suelte la app; hoy Testing) | “Nunca gobierno” |
| Proofpoint, Trend Micro o servidores propios = **waitlist** (o más adelante IMAP/OAuth que **ellos** autoricen) | Pedir clave de Outlook/Gmail/Yahoo/IMAP en el gate |
| Muchas dependencias **prohíben** apps de terceros aunque el MX sea Microsoft | Inventar IMAP “porque es .mx” |

Si el trabajo o el gobierno no dejan conectar el buzón institucional, el usuario puede usar un correo **personal** Outlook/Hotmail.

---

## Disponible ahora — Microsoft 365 / Outlook / Hotmail

Firma en Microsoft (`login.microsoftonline.com`). A veces el **admin de la organización** debe autorizar la app Donexto.

| Tipo | Ejemplos | Notas |
|------|----------|--------|
| Personal Microsoft | Hotmail, Outlook, Live, MSN | Incluye variantes `.com` / `.com.mx` ya cubiertas en OAuth Microsoft |
| Empresa con MX Outlook | `@televisa.com.mx` | MX Outlook. Disponible **ahora** si el admin no bloquea la app |
| Empresa / organismo con MX Outlook | `@cfe.mx` | MX Outlook. Disponible **ahora** si el admin no bloquea la app |

Cuentas de prueba de Héctor (no mezclar; ver también `DONEX-SEPTEMBER.md`):

| Cuenta | Uso |
|--------|-----|
| `donexto@hotmail.com` | Entra / Hotmail |
| `hsalcidolapdell@outlook.com` | Outlook de prueba (verify a veces en basura) |
| `hsalcidor@yahoo.com` | Buzón de prueba personal (Yahoo: identidad sí, inbox no) |
| `donexto@yahoo.com` | Empresa / YDN / solicitud mail-r |
| `hmcelinfo@gmail.com` | Cloudflare + Cursor + `ADMIN_EMAILS` |

---

## Próximamente — Google Workspace / Gmail

Misma fila de producto cuando Google suelte la app (consentimiento en **Testing** hoy). No pedir contraseña. No fingir lectura.

| Tipo | Ejemplos | MX |
|------|----------|----|
| Gmail personal | `@gmail.com` / `@googlemail.com` | Google |
| Empresa | `@liverpool.com.mx` | Google Workspace |
| Empresa | `@televisa.com` | Google Workspace |
| Gobierno | `@cdmx.gob.mx` | Google Workspace |

Hasta que Google suelte la app: waitlist / “Próximamente”, **sin OAuth** de lectura para altas nuevas.

---

## Hoy no — waitlist, sin pedir contraseña

No hay IMAP con password en Donexto. No hay “pon tu clave de Telcel”. Lista de espera (`mailbox_waitlist` u equivalente): correo + proveedor + fecha.

| Caso | Ejemplo | Por qué no |
|------|---------|------------|
| Proofpoint | `@tvazteca.com.mx` | MX `pphosted` |
| Proofpoint | `@telcel.com` y `hsalcidor@mail.telcel.com` | MX `pphosted`. `mail.` **no** es Gmail |
| Servidores propios | SAT, IMSS, Hacienda, Función Pública | No Microsoft ni Google de consumo |
| Trend Micro | ISSSTE / SEGOB | Gateway propio, no OAuth Donexto |
| Servidores propios | Banxico | No Microsoft ni Google de consumo |

Gobierno: aunque el MX sea Microsoft, **muchas dependencias prohíben apps de terceros**. En ese caso: waitlist del institucional + ofrecer correo personal Outlook/Hotmail.

Más adelante, solo si **ellos** autorizan: IMAP u OAuth de esa org. Nunca password de buzón en el formulario Donexto.

---

## Yahoo e iCloud (ya documentado; no se pierde)

No forman parte de la lista de dominios MX de esta nota, pero P1 sigue cargándolos:

- **Yahoo / ymail / rocketmail:** firma en Yahoo (identidad). Lectura del inbox **no** (`mail-r` pendiente). **No** poner `YAHOO_MAIL_READ_ENABLED=true`.
- **iCloud / me.com / mac.com:** decisión abierta; no pedir contraseña.

---

## Cómo debe comportarse Continuar

1. El usuario escribe el correo (personal, `@empresa.com.mx`, `@cfe.mx`, `@algo.gob.mx`, etc.).
2. Donexto **normaliza** y consulta MX (no decide por `.mx` / `.gob.mx` / `.com.mx`).
3. MX Microsoft → flujo Outlook/Hotmail/Microsoft 365 (si la org no bloquea la app).
4. MX Google → misma fila Gmail/Workspace cuando la app esté suelta; hoy próximamente.
5. Proofpoint / Trend Micro / servidores propios → waitlist. **No** pedir contraseña.
6. Yahoo nuevo → no lectura; no activar mail-r a escondidas.

---

## Anti-patrones

- Tratar `.gob.mx` como “todo gobierno igual”.
- Tratar `.com.mx` como “todo empresa IMAP”.
- Decir que `mail.telcel.com` es Gmail.
- Pedir la clave del buzón “mientras tanto”.
- Activar `YAHOO_MAIL_READ_ENABLED`.
- Prometer SAT / IMSS / Banxico / Telcel / TV Azteca como si ya se leyeran.
- Borrar las cuentas de prueba de Héctor de `DONEX-SEPTEMBER.md`.
