import type { AppLanguage } from "@/lib/i18n/languages";
import { MICROSOFT_LOGIN_DOMAINS } from "@/lib/mailboxSignup";

export type LoginMessageKey =
  | "title"
  | "helper"
  | "helperYahoo"
  | "helperMicrosoft"
  | "confirmTitle"
  | "confirmHelper"
  | "emailLabel"
  | "confirmEmailLabel"
  | "continueCta"
  | "subscribeCta"
  | "continuing"
  | "openingMailbox"
  | "confirming"
  | "confirmCta"
  | "confirmBack"
  | "confirmYahoo"
  | "confirmMicrosoft"
  | "confirmGmail"
  | "confirmOther"
  | "havePassword"
  | "enterWithLink"
  | "forgotPassword"
  | "passwordLabel"
  | "passwordPlaceholder"
  | "showPassword"
  | "hidePassword"
  | "legalBefore"
  | "terms"
  | "legalAnd"
  | "privacy"
  | "legalAfter"
  | "servicesKicker"
  | "servicesActive"
  | "serviceGoogle"
  | "serviceYahoo"
  | "serviceMicrosoftTitle"
  | "serviceMicrosoftDomains"
  | "useSuggested"
  | "invalidEmail"
  | "noAccount"
  | "continueFailed"
  | "confirmFailed"
  | "reviewFailed"
  | "microsoftOpenFailed"
  | "yahooOpenFailed"
  | "googleOpenFailed"
  | "appleOpenFailed"
  | "noActiveService"
  | "passwordMin"
  | "donextoSigninFailed"
  | "resetSent"
  | "recoverNeedEmail"
  | "promise"
  | "wantedToSay"
  | "emailPlaceholder";

const microsoftDomainLine = MICROSOFT_LOGIN_DOMAINS.join(" · ");

const es: Record<LoginMessageKey, string> = {
  title: "Entrar a Donexto",
  helper: "Escribe tu correo. Yahoo u Outlook/Hotmail firman en su sitio.",
  helperYahoo:
    "Te llevamos al sitio de Yahoo para que firmes ahí. Donexto no pide tu clave.",
  helperMicrosoft:
    "Microsoft confirma este correo en su sitio (Outlook, Hotmail, Live, MSN o Microsoft 365). Donexto no te envía otro correo de confirmación.",
  confirmTitle: "Confirma el correo de Donexto",
  confirmHelper:
    "Confirma el correo que vas a utilizar para el servicio Donexto. Revísalo antes de seguir.",
  emailLabel: "Correo",
  confirmEmailLabel: "Confirma o corrige el correo",
  continueCta: "Continuar",
  subscribeCta: "Suscribirse",
  continuing: "Continuando…",
  openingMailbox: "Abriendo tu correo…",
  confirming: "Confirmando…",
  confirmCta: "Sí, este es el correo de mi cuenta Donexto",
  confirmBack: "Usar otro correo",
  confirmYahoo:
    "Al confirmar, Donexto usará este correo. Después firmas en el sitio de Yahoo.",
  confirmMicrosoft:
    "Al confirmar, Donexto usará este correo. Después firmas en el sitio de Microsoft. No te enviamos un correo de confirmación aparte: Microsoft ya identifica la cuenta.",
  confirmGmail:
    "Al confirmar, Donexto usará este correo. Después Google te identifica.",
  confirmOther:
    "Al confirmar, Donexto usará este correo para tu cuenta y para vigilar ese mismo buzón.",
  havePassword: "Tengo contraseña de Donexto",
  enterWithLink: "Entrar con enlace al correo",
  forgotPassword: "Olvidé mi contraseña",
  passwordLabel: "Contraseña de Donexto",
  passwordPlaceholder: "Solo si ya la definiste aquí",
  showPassword: "Mostrar contraseña",
  hidePassword: "Ocultar contraseña",
  legalBefore: "Al continuar aceptas los",
  terms: "Términos",
  legalAnd: "y la",
  privacy: "Privacidad",
  legalAfter: "de Donexto.",
  servicesKicker: "Servicios en Donexto",
  servicesActive: "Activos",
  serviceGoogle: "Google (Gmail) — acceso en revisión",
  serviceYahoo: "Yahoo",
  serviceMicrosoftTitle: "Outlook, Hotmail, Live, MSN y Microsoft 365",
  serviceMicrosoftDomains: microsoftDomainLine,
  useSuggested: "Usar este correo",
  invalidEmail:
    "Escribe un correo válido, con @ y un dominio real (ejemplo: nombre@hotmail.com).",
  noAccount: "Ese correo no tiene cuenta Donexto. Pulsa Suscribirse.",
  continueFailed: "No fue posible continuar con ese correo.",
  confirmFailed: "No fue posible confirmar ese correo.",
  reviewFailed: "No fue posible revisar ese correo.",
  microsoftOpenFailed: "No fue posible abrir el inicio de sesión de Microsoft.",
  yahooOpenFailed: "No fue posible abrir Yahoo.",
  googleOpenFailed: "No fue posible abrir el inicio de sesión de Google.",
  appleOpenFailed: "No fue posible abrir el inicio de sesión de Apple.",
  noActiveService:
    "Ese correo no usa un servicio activo en Donexto. Activos: Yahoo y Outlook/Hotmail (y los dominios Microsoft de la lista).",
  passwordMin: "La contraseña de Donexto usa al menos 8 caracteres.",
  donextoSigninFailed: "No fue posible iniciar sesión en Donexto.",
  resetSent: "Enviamos un enlace para restablecer la contraseña de Donexto.",
  recoverNeedEmail: "Escribe primero el correo de tu cuenta Donexto.",
  promise: "Do Next To…\nLo siguiente que sí importa. El resto espera.",
  wantedToSay: "Ese dominio no es un correo activo. ¿Quisiste decir",
  emailPlaceholder: "tu@correo.com",
};

const en: Record<LoginMessageKey, string> = {
  title: "Sign in to Donexto",
  helper: "Enter your email. Yahoo or Outlook/Hotmail sign in on their own site.",
  helperYahoo:
    "We take you to Yahoo’s site to sign in. Donexto does not ask for your password.",
  helperMicrosoft:
    "Microsoft confirms this address on its site (Outlook, Hotmail, Live, MSN, or Microsoft 365). Donexto does not send a separate confirmation email.",
  confirmTitle: "Confirm your Donexto email",
  confirmHelper:
    "Confirm the address you will use for Donexto. Check it before you continue.",
  emailLabel: "Email",
  confirmEmailLabel: "Confirm or correct the email",
  continueCta: "Continue",
  subscribeCta: "Subscribe",
  continuing: "Continuing…",
  openingMailbox: "Opening your mailbox…",
  confirming: "Confirming…",
  confirmCta: "Yes, this is my Donexto email",
  confirmBack: "Use another email",
  confirmYahoo:
    "After you confirm, Donexto will use this address. Then you sign in on Yahoo’s site.",
  confirmMicrosoft:
    "After you confirm, Donexto will use this address. Then you sign in on Microsoft’s site. We do not send a separate confirmation email: Microsoft already identifies the account.",
  confirmGmail:
    "After you confirm, Donexto will use this address. Then Google identifies you.",
  confirmOther:
    "After you confirm, Donexto will use this address for your account and to watch that same mailbox.",
  havePassword: "I have a Donexto password",
  enterWithLink: "Sign in with an email link",
  forgotPassword: "Forgot my password",
  passwordLabel: "Donexto password",
  passwordPlaceholder: "Only if you already set one here",
  showPassword: "Show password",
  hidePassword: "Hide password",
  legalBefore: "By continuing you accept Donexto’s",
  terms: "Terms",
  legalAnd: "and",
  privacy: "Privacy",
  legalAfter: ".",
  servicesKicker: "Services in Donexto",
  servicesActive: "Active",
  serviceGoogle: "Google (Gmail) — access under review",
  serviceYahoo: "Yahoo",
  serviceMicrosoftTitle: "Outlook, Hotmail, Live, MSN, and Microsoft 365",
  serviceMicrosoftDomains: microsoftDomainLine,
  useSuggested: "Use this email",
  invalidEmail:
    "Enter a valid email, with @ and a real domain (example: name@hotmail.com).",
  noAccount: "That email has no Donexto account. Tap Subscribe.",
  continueFailed: "We could not continue with that email.",
  confirmFailed: "We could not confirm that email.",
  reviewFailed: "We could not check that email.",
  microsoftOpenFailed: "We could not open Microsoft sign-in.",
  yahooOpenFailed: "We could not open Yahoo.",
  googleOpenFailed: "We could not open Google sign-in.",
  appleOpenFailed: "We could not open Apple sign-in.",
  noActiveService:
    "That email is not an active Donexto service. Active: Yahoo and Outlook/Hotmail (and the Microsoft domains listed).",
  passwordMin: "The Donexto password uses at least 8 characters.",
  donextoSigninFailed: "We could not sign you in to Donexto.",
  resetSent: "We sent a link to reset your Donexto password.",
  recoverNeedEmail: "Enter your Donexto account email first.",
  promise: "Do Next To…\nThe next thing that actually matters. Everything else waits.",
  wantedToSay: "That domain is not an active mailbox. Did you mean",
  emailPlaceholder: "you@email.com",
};

const fr: Record<LoginMessageKey, string> = {
  title: "Connexion à Donexto",
  helper:
    "Saisissez votre e-mail. Yahoo ou Outlook/Hotmail se connectent sur leur site.",
  helperYahoo:
    "Nous vous emmenons sur le site Yahoo pour vous connecter. Donexto ne demande pas votre mot de passe.",
  helperMicrosoft:
    "Microsoft confirme cette adresse sur son site (Outlook, Hotmail, Live, MSN ou Microsoft 365). Donexto n’envoie pas d’e-mail de confirmation séparé.",
  confirmTitle: "Confirmez l’e-mail Donexto",
  confirmHelper:
    "Confirmez l’adresse que vous utiliserez pour Donexto. Vérifiez-la avant de continuer.",
  emailLabel: "E-mail",
  confirmEmailLabel: "Confirmez ou corrigez l’e-mail",
  continueCta: "Continuer",
  subscribeCta: "S’inscrire",
  continuing: "Suite…",
  openingMailbox: "Ouverture de votre messagerie…",
  confirming: "Confirmation…",
  confirmCta: "Oui, c’est l’e-mail de mon compte Donexto",
  confirmBack: "Utiliser un autre e-mail",
  confirmYahoo:
    "Après confirmation, Donexto utilisera cette adresse. Ensuite vous vous connectez sur le site Yahoo.",
  confirmMicrosoft:
    "Après confirmation, Donexto utilisera cette adresse. Ensuite vous vous connectez chez Microsoft. Nous n’envoyons pas d’e-mail de confirmation séparé : Microsoft identifie déjà le compte.",
  confirmGmail:
    "Après confirmation, Donexto utilisera cette adresse. Ensuite Google vous identifie.",
  confirmOther:
    "Après confirmation, Donexto utilisera cette adresse pour le compte et pour surveiller cette même boîte.",
  havePassword: "J’ai un mot de passe Donexto",
  enterWithLink: "Connexion par lien e-mail",
  forgotPassword: "Mot de passe oublié",
  passwordLabel: "Mot de passe Donexto",
  passwordPlaceholder: "Uniquement si vous l’avez déjà défini ici",
  showPassword: "Afficher le mot de passe",
  hidePassword: "Masquer le mot de passe",
  legalBefore: "En continuant, vous acceptez les",
  terms: "Conditions",
  legalAnd: "et la",
  privacy: "Confidentialité",
  legalAfter: "de Donexto.",
  servicesKicker: "Services dans Donexto",
  servicesActive: "Actifs",
  serviceGoogle: "Google (Gmail) — accès en revue",
  serviceYahoo: "Yahoo",
  serviceMicrosoftTitle: "Outlook, Hotmail, Live, MSN et Microsoft 365",
  serviceMicrosoftDomains: microsoftDomainLine,
  useSuggested: "Utiliser cet e-mail",
  invalidEmail:
    "Saisissez un e-mail valide, avec @ et un vrai domaine (exemple : nom@hotmail.com).",
  noAccount: "Cet e-mail n’a pas de compte Donexto. Appuyez sur S’inscrire.",
  continueFailed: "Impossible de continuer avec cet e-mail.",
  confirmFailed: "Impossible de confirmer cet e-mail.",
  reviewFailed: "Impossible de vérifier cet e-mail.",
  microsoftOpenFailed: "Impossible d’ouvrir la connexion Microsoft.",
  yahooOpenFailed: "Impossible d’ouvrir Yahoo.",
  googleOpenFailed: "Impossible d’ouvrir la connexion Google.",
  appleOpenFailed: "Impossible d’ouvrir la connexion Apple.",
  noActiveService:
    "Cet e-mail n’est pas un service actif Donexto. Actifs : Yahoo et Outlook/Hotmail (et les domaines Microsoft listés).",
  passwordMin: "Le mot de passe Donexto comporte au moins 8 caractères.",
  donextoSigninFailed: "Impossible de vous connecter à Donexto.",
  resetSent: "Nous avons envoyé un lien pour réinitialiser le mot de passe Donexto.",
  recoverNeedEmail: "Saisissez d’abord l’e-mail de votre compte Donexto.",
  promise: "Do Next To…\nLa prochaine chose qui compte vraiment. Le reste attend.",
  wantedToSay: "Ce domaine n’est pas une boîte active. Vouliez-vous dire",
  emailPlaceholder: "vous@email.com",
};

const it: Record<LoginMessageKey, string> = {
  title: "Accedi a Donexto",
  helper: "Scrivi la tua email. Yahoo o Outlook/Hotmail accedono sul loro sito.",
  helperYahoo:
    "Ti portiamo sul sito Yahoo per accedere. Donexto non chiede la password.",
  helperMicrosoft:
    "Microsoft conferma questo indirizzo sul suo sito (Outlook, Hotmail, Live, MSN o Microsoft 365). Donexto non invia un’email di conferma a parte.",
  confirmTitle: "Conferma l’email Donexto",
  confirmHelper:
    "Conferma l’indirizzo che userai per Donexto. Controllalo prima di continuare.",
  emailLabel: "Email",
  confirmEmailLabel: "Conferma o correggi l’email",
  continueCta: "Continua",
  subscribeCta: "Iscriviti",
  continuing: "Attendi…",
  openingMailbox: "Apertura della casella…",
  confirming: "Conferma…",
  confirmCta: "Sì, questa è l’email del mio account Donexto",
  confirmBack: "Usa un’altra email",
  confirmYahoo:
    "Dopo la conferma, Donexto userà questo indirizzo. Poi accedi sul sito Yahoo.",
  confirmMicrosoft:
    "Dopo la conferma, Donexto userà questo indirizzo. Poi accedi sul sito Microsoft. Non inviamo un’email di conferma a parte: Microsoft identifica già l’account.",
  confirmGmail:
    "Dopo la conferma, Donexto userà questo indirizzo. Poi Google ti identifica.",
  confirmOther:
    "Dopo la conferma, Donexto userà questo indirizzo per l’account e per sorvegliare la stessa casella.",
  havePassword: "Ho una password Donexto",
  enterWithLink: "Accedi con link email",
  forgotPassword: "Password dimenticata",
  passwordLabel: "Password Donexto",
  passwordPlaceholder: "Solo se l’hai già impostata qui",
  showPassword: "Mostra password",
  hidePassword: "Nascondi password",
  legalBefore: "Continuando accetti i",
  terms: "Termini",
  legalAnd: "e la",
  privacy: "Privacy",
  legalAfter: "di Donexto.",
  servicesKicker: "Servizi in Donexto",
  servicesActive: "Attivi",
  serviceGoogle: "Google (Gmail) — accesso in revisione",
  serviceYahoo: "Yahoo",
  serviceMicrosoftTitle: "Outlook, Hotmail, Live, MSN e Microsoft 365",
  serviceMicrosoftDomains: microsoftDomainLine,
  useSuggested: "Usa questa email",
  invalidEmail:
    "Scrivi un’email valida, con @ e un dominio reale (esempio: nome@hotmail.com).",
  noAccount: "Questa email non ha un account Donexto. Tocca Iscriviti.",
  continueFailed: "Impossibile continuare con questa email.",
  confirmFailed: "Impossibile confermare questa email.",
  reviewFailed: "Impossibile verificare questa email.",
  microsoftOpenFailed: "Impossibile aprire l’accesso Microsoft.",
  yahooOpenFailed: "Impossibile aprire Yahoo.",
  googleOpenFailed: "Impossibile aprire l’accesso Google.",
  appleOpenFailed: "Impossibile aprire l’accesso Apple.",
  noActiveService:
    "Questa email non è un servizio attivo Donexto. Attivi: Yahoo e Outlook/Hotmail (e i domini Microsoft in elenco).",
  passwordMin: "La password Donexto ha almeno 8 caratteri.",
  donextoSigninFailed: "Impossibile accedere a Donexto.",
  resetSent: "Abbiamo inviato un link per reimpostare la password Donexto.",
  recoverNeedEmail: "Inserisci prima l’email del tuo account Donexto.",
  promise: "Do Next To…\nLa prossima cosa che conta davvero. Il resto aspetta.",
  wantedToSay: "Quel dominio non è una casella attiva. Intendevi",
  emailPlaceholder: "tu@email.com",
};

const pt: Record<LoginMessageKey, string> = {
  title: "Entrar no Donexto",
  helper: "Escreva o seu correio. Yahoo ou Outlook/Hotmail entram no próprio site.",
  helperYahoo:
    "Levamo-lo ao site da Yahoo para entrar. O Donexto não pede a palavra-passe.",
  helperMicrosoft:
    "A Microsoft confirma este correio no respectivo site (Outlook, Hotmail, Live, MSN ou Microsoft 365). O Donexto não envia outro e-mail de confirmação.",
  confirmTitle: "Confirme o correio Donexto",
  confirmHelper:
    "Confirme o endereço que vai usar no Donexto. Reveja-o antes de continuar.",
  emailLabel: "Correio",
  confirmEmailLabel: "Confirme ou corrija o correio",
  continueCta: "Continuar",
  subscribeCta: "Subscrever",
  continuing: "A continuar…",
  openingMailbox: "A abrir o correio…",
  confirming: "A confirmar…",
  confirmCta: "Sim, este é o correio da minha conta Donexto",
  confirmBack: "Usar outro correio",
  confirmYahoo:
    "Ao confirmar, o Donexto usa este endereço. Depois entra no site da Yahoo.",
  confirmMicrosoft:
    "Ao confirmar, o Donexto usa este endereço. Depois entra no site da Microsoft. Não enviamos um e-mail de confirmação à parte: a Microsoft já identifica a conta.",
  confirmGmail:
    "Ao confirmar, o Donexto usa este endereço. Depois o Google identifica-o.",
  confirmOther:
    "Ao confirmar, o Donexto usa este endereço para a conta e para vigiar a mesma caixa.",
  havePassword: "Tenho palavra-passe Donexto",
  enterWithLink: "Entrar com ligação no correio",
  forgotPassword: "Esqueci a palavra-passe",
  passwordLabel: "Palavra-passe Donexto",
  passwordPlaceholder: "Só se já a definiu aqui",
  showPassword: "Mostrar palavra-passe",
  hidePassword: "Ocultar palavra-passe",
  legalBefore: "Ao continuar aceita os",
  terms: "Termos",
  legalAnd: "e a",
  privacy: "Privacidade",
  legalAfter: "do Donexto.",
  servicesKicker: "Serviços no Donexto",
  servicesActive: "Ativos",
  serviceGoogle: "Google (Gmail) — acesso em revisão",
  serviceYahoo: "Yahoo",
  serviceMicrosoftTitle: "Outlook, Hotmail, Live, MSN e Microsoft 365",
  serviceMicrosoftDomains: microsoftDomainLine,
  useSuggested: "Usar este correio",
  invalidEmail:
    "Escreva um correio válido, com @ e um domínio real (exemplo: nome@hotmail.com).",
  noAccount: "Esse correio não tem conta Donexto. Toque em Subscrever.",
  continueFailed: "Não foi possível continuar com esse correio.",
  confirmFailed: "Não foi possível confirmar esse correio.",
  reviewFailed: "Não foi possível verificar esse correio.",
  microsoftOpenFailed: "Não foi possível abrir o início de sessão da Microsoft.",
  yahooOpenFailed: "Não foi possível abrir a Yahoo.",
  googleOpenFailed: "Não foi possível abrir o início de sessão do Google.",
  appleOpenFailed: "Não foi possível abrir o início de sessão da Apple.",
  noActiveService:
    "Esse correio não é um serviço ativo no Donexto. Ativos: Yahoo e Outlook/Hotmail (e os domínios Microsoft da lista).",
  passwordMin: "A palavra-passe Donexto tem pelo menos 8 caracteres.",
  donextoSigninFailed: "Não foi possível iniciar sessão no Donexto.",
  resetSent: "Enviámos uma ligação para repor a palavra-passe Donexto.",
  recoverNeedEmail: "Escreva primeiro o correio da sua conta Donexto.",
  promise: "Do Next To…\nO que segue e importa. O resto espera.",
  wantedToSay: "Esse domínio não é um correio ativo. Quis dizer",
  emailPlaceholder: "voce@email.com",
};

export const LOGIN_MESSAGES: Record<
  AppLanguage,
  Record<LoginMessageKey, string>
> = {
  es,
  en,
  fr,
  it,
  pt,
};

export function loginText(
  language: AppLanguage,
  key: LoginMessageKey,
): string {
  return LOGIN_MESSAGES[language][key] || LOGIN_MESSAGES.es[key];
}
