/**
 * Guía canónica para pedir a Yahoo el código IMAP de 16 dígitos.
 * Yahoo no deja usar la clave de mail.yahoo.com en clientes de terceros.
 * Fuente: https://es.ayuda.yahoo.com/kb/SLN15241.html
 */

export const YAHOO_ACCOUNT_SECURITY_URL =
  "https://login.yahoo.com/account/security";

export const YAHOO_APP_PASSWORD_HELP_URL =
  "https://es.ayuda.yahoo.com/kb/SLN15241.html";

export const YAHOO_APP_PASSWORD_NAME = "Donexto";

export const YAHOO_CONNECT_TITLE = "Conecta tu correo Yahoo";

export const YAHOO_CONNECT_LEAD =
  "Te llevamos a Yahoo para que inicies sesión con tu clave. Yahoo te da un código de 16 dígitos para Donexto. Solo una vez.";

export const YAHOO_OPEN_SECURITY_CTA = "Abrir Yahoo e iniciar sesión";

export const YAHOO_STEPS: { title: string; detail: string }[] = [
  {
    title: "Inicia sesión en Yahoo",
    detail:
      "En la pestaña nueva entra con este mismo correo y tu clave de Yahoo (la de siempre, o una que hayas creado tú).",
  },
  {
    title: "Abre Seguridad",
    detail:
      "Si no se abrió Seguridad, en Yahoo ve a Información de la cuenta y luego Seguridad.",
  },
  {
    title: "Conexiones externas",
    detail:
      "Baja hasta «Conexiones externas» y pulsa «Crear contraseña de aplicación».",
  },
  {
    title: "Nómbrala Donexto",
    detail:
      "En el nombre escribe Donexto y pulsa «Generar contraseña».",
  },
  {
    title: "Copia el código de 16 dígitos",
    detail:
      "Yahoo muestra algo como xxxx xxxx xxxx xxxx. Solo se ve una vez: cópialo y pégalo abajo.",
  },
];

export const YAHOO_TWO_STEP_TIP =
  "Si no aparece «Conexiones externas», activa primero «Verificación en dos pasos» en esa misma página de Seguridad y vuelve a intentar.";

export const YAHOO_PASTE_LABEL = "Pega aquí el código de 16 dígitos";

export const YAHOO_CONNECT_CTA = "Ya lo pegué — conectar Yahoo";

export const YAHOO_CODE_TOO_SHORT =
  "El código de Yahoo tiene exactamente 16 letras o números. Pégalo tal como lo muestra Yahoo, con o sin espacios.";

export const YAHOO_CODE_TOO_LONG =
  "Eso no es el código de Yahoo. El código tiene 16 caracteres. No pegues tu clave de mail.yahoo.com.";

export function formatYahooAppPassword(raw: string): string {
  const chars = raw.replace(/[^a-zA-Z0-9]/g, "").slice(0, 24);
  if (chars.length <= 16) {
    return chars.replace(/(.{4})/g, "$1 ").trim();
  }
  return chars;
}

export function yahooAppPasswordCharCount(raw: string): number {
  return raw.replace(/[^a-zA-Z0-9]/g, "").length;
}
