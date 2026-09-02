/**
 * Copy canónico: el correo de la cuenta Donexto ES el buzón a monitorear.
 * Una sola fuente para login, onboarding y conexión de mailbox.
 */
export const ACCOUNT_VS_MAILBOX = {
  oneLiner:
    "El correo con el que entras a Donexto es el mismo buzón que monitoreamos. Nunca te pedimos la contraseña de Outlook ni de Hotmail aquí.",

  loginEyebrow: "Cuenta Donexto",
  loginTitleSignIn: "Entrar a Donexto",
  loginTitleSignUp: "Crear cuenta",
  loginTitleYahoo: "Entrar con Yahoo",
  loginEmailLabel: "Correo",
  loginPasswordLabel: "Contraseña de Donexto",
  signupFullNameLabel: "Nombre completo",
  loginHelper: "Escribe el correo del buzón que quieres monitorear.",
  loginContinueCta: "Continuar",
  loginSubscribeCta: "Continuar",
  signupConfirmTitle: "¿Usamos este correo en Donexto?",
  signupConfirmHelper:
    "Ese correo es el buzón que Donexto va a monitorear. Hoy leemos Outlook, Hotmail y Microsoft 365.",
  signupConfirmCta: "Sí, continuar",
  signupConfirmBack: "Cambiar correo",
  signupConfirmYahooNote:
    "Ese correo es el buzón que Donexto va a monitorear. Al continuar, firmas en Yahoo. Donexto no pide la contraseña de tu correo.",
  signupConfirmMicrosoftNote:
    "Ese correo es el buzón que Donexto va a monitorear. Al continuar, firmas en Microsoft. Donexto no pide la contraseña de Outlook.",
  signupConfirmGmailNote:
    "Ese correo es el buzón que Donexto va a monitorear. Al continuar, Google te identifica. Donexto no pide la contraseña de Gmail.",
  signupConfirmOtherNote:
    "Ese correo es el buzón que Donexto va a monitorear. Hoy tiene que ser Outlook, Hotmail o Microsoft 365.",
  loginHelperYahoo:
    "Te llevamos al sitio de Yahoo para que firmes ahí. Donexto no pide tu clave.",
  servicesActiveLabel: "Servicios en Donexto",
  servicesActiveBadge: "Activos",
  servicesMicrosoftTitle: "Outlook, Hotmail, Live, MSN y Microsoft 365",
  servicesPendingLabel: "En revisión",
  useSuggestedEmail: "Usar este correo",
  domainFixFallback:
    "Ese dominio no está activo. Ahora leemos Outlook, Hotmail, Live, MSN y Microsoft 365. Gmail, Yahoo e iCloud: Pronto.",
  domainPendingFallback:
    "Gmail, Yahoo e iCloud: Pronto. Ahora leemos Outlook, Hotmail, Live, MSN y Microsoft 365.",
  domainUnsupportedFallback:
    "Donexto solo monitorea Microsoft 365 y (pronto) Google Workspace. Otros servidores de empresa aún no se pueden leer. Ahora leemos Outlook, Hotmail, Live, MSN y Microsoft 365.",
  yahooWaitingMailTitle: "Ya firmaste en Yahoo",
  yahooWaitingMailBody:
    "Tu cuenta Donexto está lista. Yahoo todavía no autoriza a esta app a leer el buzón. No te volvemos a mandar a Yahoo: cuando Yahoo apruebe el permiso, Actualizar buzón traerá los correos.",
  yahooGrantMailReadTitle: "Autoriza la lectura del buzón",
  yahooGrantMailReadBody:
    "Yahoo ya aprobó el permiso de correo para Donexto. Firma una sola vez en Yahoo para autorizar la lectura. Después no te volvemos a mandar.",
  updateMailboxLabel: "Actualizar buzón",
  yahooSignInNext:
    "Firma en el sitio de Yahoo. Donexto no pide la clave de ningún buzón.",
  yahooMagicLinkSent:
    "Te llevamos a Yahoo para firmar. No usamos un enlace ni tu clave aquí.",
  loginFoot: "Esta es tu cuenta de Donexto.",
  signupChooserBody:
    "Elige el correo que vas a monitorear: será el mismo de tu cuenta Donexto. Te llevamos al inicio de sesión de ese proveedor.",
  authSecurityTitle: "Seguridad y responsabilidad",
  authSecurityBody:
    "Donexto nunca te pide la contraseña de Gmail aquí. Si te das de alta con Gmail, te escribimos a ese mismo correo. Sin clic en ese mail no entras ni leemos el buzón. Las pantallas de Google son de Google; la confirmación de Donexto es el correo que nosotros enviamos.",
  confirmGateTitle: "Revisa tu correo",
  confirmGateBody:
    "Te escribimos a ese mismo correo. Sin el clic en ese mail no entras a Donexto.",
  confirmGateResend: "Reenviar correo de confirmación",
  confirmGateRefresh: "Ya hice clic — continuar",
  confirmGateSignOut: "Cerrar sesión",
  signupHaveAccount: "Ya tengo cuenta — Entrar",
  signupYahooTitle: "Yahoo",
  signupYahooBody:
    "Te llevamos al sitio de Yahoo para que firmes. Donexto no pide tu clave.",
  signupYahooCta: "Continuar con Yahoo",
  signupYahooContinue:
    "Yahoo te identifica en su sitio. Si autorizas la lectura, el buzón queda conectado.",
  signupHotmailPending:
    "Te llevamos al inicio de sesión de Microsoft.",
  signupApplePending:
    "Te llevamos al inicio de sesión de Apple.",
  signupOtherPrompt:
    "Escribe la cuenta de correo que quieres monitorear. Si reconocemos el dominio, te llevamos a ese proveedor.",
  signupOtherContinue: "Continuar",
  signupOtherUnrecognized:
    "No hay un portal OAuth de Donexto para ese dominio. Te enviamos un enlace mágico a ese mismo correo para crear la cuenta; luego autorizamos la lectura de ese buzón.",
  signupOtherMagicLink: "Enviar enlace de acceso",
  brandSub:
    "Primero confirmas tu correo de Donexto; después autorizas la lectura de ese mismo buzón. No es otra bandeja: es una capa de atención.",

  step2Title: "Autoriza la lectura de tu correo",
  step2Body:
    "Donexto leerá el mismo correo de tu cuenta. No es un buzón distinto ni un segundo login.",
  step2Cta: "Autorizar este correo",
  step2EmptyLead:
    "Sin autorizar la lectura no hay bandeja que clasificar. Donexto no pide de nuevo tu contraseña de Gmail.",

  connectBanner: "Esto no pide tu contraseña de Gmail · solo autoriza la lectura",
  connectChooserTitle: "Autoriza la lectura de tu correo",
  connectChooserBody:
    "El buzón es el mismo correo de tu cuenta Donexto. Outlook y Hotmail autorizan lectura en Microsoft. Gmail y Yahoo, cuando estén listos. Donexto no pide claves de buzón.",
  connectGmailBody:
    "Donexto nunca te pidió la contraseña de Gmail. Esta pantalla de Google es solo para autorizar la lectura de este mismo buzón.",
  connectGmailCta: "Autorizar lectura de este Gmail",
  connectYahooTitle: "Conecta tu correo Yahoo",
  connectYahooBody:
    "Te llevamos al sitio de Yahoo para autorizar la lectura. Donexto no pide tu clave.",
  connectGoogleHint:
    "Te llevamos a la página oficial de Google para autorizar la lectura de este mismo Gmail (no es el login de Donexto y no pedimos tu contraseña).",
  connectYahooChooserHint:
    "Yahoo te identifica y autoriza la lectura en su propio sitio. Sin clave en Donexto.",
  connectMicrosoftTitle: "Conecta Outlook, Hotmail o Microsoft 365",
  connectMicrosoftBody:
    "Te llevamos al sitio de Microsoft para firmar. Donexto no pide la clave de Outlook.",
  connectMicrosoftCta: "Continuar con Microsoft",

  changeMailboxLabel: "Volver a autorizar buzón",
  connectMailboxLabel: "Autorizar buzón",
  mailboxConnected: "Buzón conectado",
  mailboxMissing: "Sin buzón",
  mailboxMissingHint: "Autoriza la lectura de este mismo correo",
  gmailReadPendingTitle: "Gmail aún no se puede leer",
  gmailReadPendingBody:
    "Ya puedes entrar a Donexto con este Gmail, pero Google todavía no autoriza la lectura del buzón. Te avisamos cuando se pueda monitorear.",
  planNormalTitle: "Plan Normal",
  planNormalPrice: "$19.99 / mes",
  planNormalBody:
    "Cuando tu Outlook o Hotmail está conectado, el Plan Normal cubre la atención del buzón. Checkout en Stripe Test.",
  planNormalCta: "Contratar Plan Normal $19.99",
  planNormalMissingKey:
    "Falta configurar Stripe Test en Railway (STRIPE_SECRET_KEY y STRIPE_PRICE_NORMAL_MONTHLY).",
  quickConnectHint: "Outlook o Hotmail",
  quickChangeHint: "Otro Outlook o Hotmail",
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
      return "Outlook / Hotmail";
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
      return "contraseña de Yahoo";
    case "hotmail":
    case "microsoft":
      return "contraseña de Outlook";
    case "apple":
      return "contraseña de iCloud";
    default:
      return "contraseña de ese correo";
  }
}

export function signupConfirmNote(email: string): string {
  const provider = resolveMailboxProviderFromEmail(email);
  if (provider === "hotmail") {
    return ACCOUNT_VS_MAILBOX.signupConfirmMicrosoftNote;
  }
  if (provider === "gmail") {
    return ACCOUNT_VS_MAILBOX.signupConfirmGmailNote;
  }
  if (provider === "yahoo") {
    return ACCOUNT_VS_MAILBOX.signupConfirmYahooNote;
  }
  return ACCOUNT_VS_MAILBOX.signupConfirmOtherNote;
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
  if (provider === "yahoo") {
    return (
      "Donexto nunca te pide la clave de Yahoo aquí. Firmas en el sitio de " +
      "Yahoo y después te escribimos a ese mismo correo. Sin el clic no entras."
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
  const provider = email
    ? resolveMailboxProviderFromEmail(email)
    : "other";
  if (provider === "yahoo") {
    return (
      "Firma en el sitio de Yahoo. Donexto no pide tu clave: ese correo " +
      "es el buzón que monitoreamos."
    );
  }
  const password = mailboxPasswordPhrase(provider);
  return (
    "El correo con el que entras a Donexto es el mismo buzón que monitoreamos. " +
    `Nunca te pedimos la ${password} aquí.`
  );
}

export function connectBannerFor(email?: string): string {
  const provider = email
    ? resolveMailboxProviderFromEmail(email)
    : "other";
  if (provider === "yahoo") {
    return "Te llevamos al sitio de Yahoo para autorizar la lectura. Donexto no pide tu clave.";
  }
  if (provider === "gmail") {
    return ACCOUNT_VS_MAILBOX.connectBanner;
  }
  return "Esto no pide la contraseña de tu buzón · solo autoriza la lectura";
}

export function step2EmptyLeadFor(email?: string): string {
  const provider = email
    ? resolveMailboxProviderFromEmail(email)
    : "other";
  if (provider === "yahoo") {
    return (
      "Sin autorizar Yahoo no hay bandeja que clasificar. Firma en el sitio " +
      "de Yahoo; Donexto no pide tu clave."
    );
  }
  const password = mailboxPasswordPhrase(provider);
  return (
    `Sin autorizar la lectura no hay bandeja que clasificar. Donexto no pide de nuevo tu ${password}.`
  );
}

export function loginHelperFor(email?: string): string {
  if (!email) {
    return ACCOUNT_VS_MAILBOX.loginHelper;
  }
  if (resolveMailboxProviderFromEmail(email) === "yahoo") {
    return ACCOUNT_VS_MAILBOX.loginHelperYahoo;
  }
  const label = mailboxServiceLabel(resolveMailboxProviderFromEmail(email));
  return (
    `Esta es tu cuenta de Donexto. El buzón a leer es este mismo ${label}.`
  );
}
