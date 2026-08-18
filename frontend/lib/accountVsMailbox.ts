/**
 * Copy canónico: el correo de la cuenta Donexto ES el buzón a vigilar.
 * Una sola fuente para login, onboarding y conexión de mailbox.
 */
export const ACCOUNT_VS_MAILBOX = {
  oneLiner:
    "El correo con el que entras a Donexto es el mismo buzón que vigilamos. Nunca te pedimos la contraseña de Gmail aquí.",

  loginEyebrow: "Cuenta Donexto",
  loginTitleSignIn: "Login",
  loginTitleSignUp: "Crear cuenta",
  loginEmailLabel: "Correo de tu cuenta",
  loginPasswordLabel: "Contraseña",
  signupFullNameLabel: "Nombre completo",
  loginHelper: "Esta es tu cuenta de Donexto. El buzón a leer es este mismo correo.",
  loginFoot: "Esta es tu cuenta de Donexto.",
  signupChooserBody:
    "Elige el correo que vas a vigilar: será el mismo de tu cuenta Donexto. Te llevamos al inicio de sesión de ese proveedor.",
  authSecurityTitle: "Seguridad y responsabilidad",
  authSecurityBody:
    "Donexto nunca te pide la contraseña de Gmail aquí. Si te das de alta con Gmail, te escribimos a ese mismo correo. Sin clic en ese mail no entras ni leemos el buzón. Las pantallas de Google son de Google; la confirmación de Donexto es el correo que nosotros enviamos.",
  confirmGateTitle: "Revisa tu correo",
  confirmGateBody:
    "Te escribimos a ese mismo Gmail. Donexto nunca te pidió la contraseña de Gmail: este correo confirma que autorizas a Donexto a, después, leer ese buzón. Sin el clic no entras.",
  confirmGateResend: "Reenviar correo de confirmación",
  confirmGateRefresh: "Ya hice clic — continuar",
  confirmGateSignOut: "Cerrar sesión",
  signupHaveAccount: "Ya tengo cuenta — Entrar",
  signupYahooTitle: "Yahoo",
  signupYahooBody:
    "Yahoo no tiene OAuth de correo. Te enviamos un enlace a ese Yahoo para crear la cuenta Donexto. La contraseña de aplicación se pide después, al autorizar la lectura.",
  signupYahooCta: "Abrir seguridad de Yahoo (lo usarás al conectar el buzón)",
  signupYahooContinue:
    "Revisa ese Yahoo (y spam). Con el enlace entras a Donexto; después autorizas la lectura con la contraseña de aplicación.",
  signupHotmailPending:
    "Te llevamos al inicio de sesión de Microsoft.",
  signupApplePending:
    "Te llevamos al inicio de sesión de Apple.",
  signupOtherPrompt:
    "Escribe la cuenta de correo que quieres vigilar. Si reconocemos el dominio, te llevamos a ese proveedor.",
  signupOtherContinue: "Continuar",
  signupOtherUnrecognized:
    "No hay un portal OAuth de Donexto para ese dominio. Te enviamos un enlace mágico a ese mismo correo para crear la cuenta; luego autorizamos la lectura de ese buzón.",
  signupOtherMagicLink: "Enviar enlace de acceso",
  brandSub:
    "Prioridades y respuestas, sin el caos de la bandeja. Primero confirmas tu correo; después autorizas la lectura de ese mismo buzón.",

  step2Title: "Autoriza la lectura de tu correo",
  step2Body:
    "Donexto leerá el mismo correo de tu cuenta. No es un buzón distinto ni un segundo login.",
  step2Cta: "Autorizar este correo",
  step2EmptyLead:
    "Sin autorizar la lectura no hay bandeja que clasificar. Donexto no pide de nuevo tu contraseña de Gmail.",

  connectBanner: "Esto no pide tu contraseña de Gmail · solo autoriza la lectura",
  connectChooserTitle: "Autoriza la lectura de tu correo",
  connectChooserBody:
    "El buzón es el mismo correo de tu cuenta Donexto. Gmail autoriza lectura en Google; Yahoo usa contraseña de aplicación IMAP.",
  connectGmailBody:
    "Donexto nunca te pidió la contraseña de Gmail. Esta pantalla de Google es solo para autorizar la lectura de este mismo buzón.",
  connectGmailCta: "Autorizar lectura de este Gmail",
  connectYahooTitle: "Autoriza la lectura de este Yahoo",
  connectYahooBody:
    "Contraseña de aplicación IMAP de este mismo correo Yahoo. No uses la contraseña de mail.yahoo.com ni la de Donexto.",
  connectYahooAppPasswordLabel: "Contraseña de aplicación Yahoo",
  connectGoogleHint:
    "Te llevamos a la página oficial de Google para autorizar la lectura de este mismo Gmail (no es el login de Donexto y no pedimos tu contraseña).",
  connectYahooChooserHint:
    "Pedimos la contraseña de aplicación IMAP de este mismo Yahoo (no la de mail.yahoo.com ni la de Donexto).",

  changeMailboxLabel: "Volver a autorizar buzón",
  connectMailboxLabel: "Autorizar buzón",
  mailboxConnected: "Buzón conectado",
  mailboxMissing: "Sin buzón",
  mailboxMissingHint: "Autoriza la lectura de este mismo correo",
} as const;

import type { MailboxSignupProvider } from "@/lib/mailboxSignup";
import { resolveMailboxProviderFromEmail } from "@/lib/mailboxSignup";

export function mailboxServiceLabel(
  provider: MailboxSignupProvider | string,
): string {
  switch (provider) {
    case "gmail":
    case "google":
      return "Gmail";
    case "yahoo":
      return "Yahoo";
    case "hotmail":
    case "microsoft":
      return "Outlook";
    case "apple":
      return "iCloud";
    default:
      return "correo";
  }
}

export function mailboxPasswordPhrase(
  provider: MailboxSignupProvider | string,
): string {
  switch (provider) {
    case "gmail":
    case "google":
      return "contraseña de Gmail";
    case "yahoo":
      return "contraseña de mail.yahoo.com";
    case "hotmail":
    case "microsoft":
      return "contraseña de Outlook";
    case "apple":
      return "contraseña de iCloud";
    default:
      return "contraseña de ese correo";
  }
}

export function authorizeMailboxTitle(email: string): string {
  const label = mailboxServiceLabel(resolveMailboxProviderFromEmail(email));
  return `Autoriza a Donexto a leer este ${label}: ${email}`;
}

export function authorizeGmailTitle(email: string): string {
  return authorizeMailboxTitle(email);
}

export function confirmGateBodyFor(email: string): string {
  const provider = resolveMailboxProviderFromEmail(email);
  const label = mailboxServiceLabel(provider);
  const password = mailboxPasswordPhrase(provider);
  return (
    `Te escribimos a ese mismo ${label}. Donexto nunca te pidió la ${password}: ` +
    "este correo confirma que autorizas a Donexto a, después, leer ese buzón. " +
    "Sin el clic no entras."
  );
}

export function authSecurityBodyFor(email?: string): string {
  const provider = email
    ? resolveMailboxProviderFromEmail(email)
    : "other";
  const label = mailboxServiceLabel(provider);
  const password = mailboxPasswordPhrase(provider);
  if (!email || provider === "other") {
    return (
      "Donexto nunca te pide aquí la contraseña de tu buzón. Te escribimos " +
      "a ese mismo correo. Sin clic en ese mail no entras ni leemos el buzón. " +
      "La confirmación de Donexto es el correo que nosotros enviamos."
    );
  }
  return (
    `Donexto nunca te pide la ${password} aquí. Si te das de alta con ${label}, ` +
    "te escribimos a ese mismo correo. Sin clic en ese mail no entras ni leemos " +
    "el buzón. Las pantallas del proveedor son suyas; la confirmación de " +
    "Donexto es el correo que nosotros enviamos."
  );
}

export function oneLinerFor(email?: string): string {
  const password = mailboxPasswordPhrase(
    email ? resolveMailboxProviderFromEmail(email) : "other",
  );
  return (
    "El correo con el que entras a Donexto es el mismo buzón que vigilamos. " +
    `Nunca te pedimos la ${password} aquí.`
  );
}

export function connectBannerFor(email?: string): string {
  const provider = email
    ? resolveMailboxProviderFromEmail(email)
    : "other";
  if (provider === "yahoo") {
    return (
      "Esto no pide la contraseña de mail.yahoo.com · usa la contraseña de aplicación Yahoo"
    );
  }
  if (provider === "gmail") {
    return ACCOUNT_VS_MAILBOX.connectBanner;
  }
  return "Esto no pide la contraseña de tu buzón · solo autoriza la lectura";
}

export function step2EmptyLeadFor(email?: string): string {
  const password = mailboxPasswordPhrase(
    email ? resolveMailboxProviderFromEmail(email) : "other",
  );
  return (
    `Sin autorizar la lectura no hay bandeja que clasificar. Donexto no pide de nuevo tu ${password}.`
  );
}

export function loginHelperFor(email?: string): string {
  if (!email) {
    return ACCOUNT_VS_MAILBOX.loginHelper;
  }
  const label = mailboxServiceLabel(resolveMailboxProviderFromEmail(email));
  return (
    `Esta es tu cuenta de Donexto. El buzón a leer es este mismo ${label}.`
  );
}
