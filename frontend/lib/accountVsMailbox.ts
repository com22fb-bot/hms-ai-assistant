/**
 * Copy canónico: Cuenta Donexto ≠ buzón a vigilar.
 * Una sola fuente para login, onboarding y conexión de mailbox.
 */
export const ACCOUNT_VS_MAILBOX = {
  /** Frase de producto: por qué el email de login puede diferir del buzón */
  oneLiner:
    "La cuenta Donexto es tu acceso a la app; el buzón es el correo (Gmail, Yahoo u otro) que vigilamos y puede ser distinto.",

  loginEyebrow: "Cuenta Donexto",
  loginTitleSignIn: "Login",
  loginTitleSignUp: "Crear cuenta",
  loginEmailLabel: "Correo de tu cuenta",
  loginPasswordLabel: "Contraseña",
  signupFullNameLabel: "Nombre completo",
  loginHelper: "Esta es tu cuenta de Donexto.",
  loginFoot: "Esta es tu cuenta de Donexto.",
  signupChooserBody:
    "Elige el correo que vas a vigilar. Te llevamos al inicio de sesión de ese proveedor.",
  signupHaveAccount: "Ya tengo cuenta — Entrar",
  signupYahooTitle: "Yahoo",
  signupYahooBody:
    "Yahoo no tiene OAuth en Supabase. Te llevamos a Yahoo para crear la contraseña de aplicación; con eso conectamos el buzón en el Paso 2.",
  signupYahooCta: "Te llevamos a Yahoo para crear la contraseña de aplicación",
  signupYahooContinue:
    "Cuando tengas la contraseña de aplicación, continúa: te enviamos un enlace a ese correo Yahoo para entrar a Donexto.",
  signupHotmailPending:
    "Te llevamos al inicio de sesión de Microsoft.",
  signupApplePending:
    "Te llevamos al inicio de sesión de Apple.",
  signupOtherPrompt:
    "Escribe la cuenta de correo que quieres vigilar. Si reconocemos el dominio, te llevamos a ese proveedor.",
  signupOtherContinue: "Continuar",
  signupOtherUnrecognized:
    "No hay un portal OAuth de Donexto para ese dominio. Te enviamos un enlace mágico a ese correo para crear la cuenta; el buzón lo conectamos con IMAP en el Paso 2.",
  signupOtherMagicLink: "Enviar enlace de acceso",
  brandSub:
    "Prioridades y respuestas, sin el caos de la bandeja. Gmail o Yahoo se conectan en un paso aparte, después de entrar.",

  step2Title: "Paso 2: Conecta el buzón a vigilar",
  step2Body:
    "Ya entraste con tu cuenta Donexto. Ahora elige el buzón que Donexto leerá. Puede ser un correo distinto al de tu login.",
  step2Cta: "Conectar Gmail o Yahoo",
  step2EmptyLead:
    "Sin buzón conectado no hay bandeja que clasificar. Esto no pide de nuevo tu contraseña Donexto.",

  connectBanner: "Esto no es tu login de Donexto · solo lee el buzón",
  connectChooserTitle: "Paso 2: Conecta el buzón a vigilar",
  connectChooserBody:
    "Elige Gmail o Yahoo. Puede ser cualquier buzón; no tiene que ser el correo de tu cuenta Donexto.",
  connectYahooTitle: "Conectar buzón Yahoo",
  connectYahooBody:
    "Correo Yahoo + contraseña de aplicación (IMAP). No uses la contraseña de tu cuenta Donexto.",
  connectYahooAppPasswordLabel: "Contraseña de aplicación Yahoo",
  connectGoogleHint:
    "Te llevamos a la página oficial de Google para autorizar lectura del buzón (no es el login de Donexto).",
  connectYahooChooserHint:
    "Luego pedimos correo Yahoo y contraseña de aplicación IMAP (no la de mail.yahoo.com ni la de Donexto).",

  changeMailboxLabel: "Cambiar buzón",
  connectMailboxLabel: "Conectar buzón",
  mailboxConnected: "Buzón conectado",
  mailboxMissing: "Sin buzón",
  mailboxMissingHint: "Paso 2: conecta Gmail o Yahoo (distinto del login Donexto)",
} as const;
