import type { AppLanguage } from "@/lib/i18n/languages";
import { MICROSOFT_LOGIN_DOMAINS } from "@/lib/mailboxSignup";

export type LoginMessageKey =
  | "title"
  | "helper"
  | "body"
  | "noPasswordNote"
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
  | "yesContinue"
  | "changeEmail"
  | "later"
  | "changeEmailExplain"
  | "icloudUnavailable"
  | "mustUseKnownMailbox"
  | "gmailPending"
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
  | "networkFailed"
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
  | "emailPlaceholder"
  | "availableNow"
  | "comingSoonBadge"
  | "chipOutlook"
  | "chipHotmail"
  | "chipLive"
  | "chipMsn"
  | "chipM365"
  | "chipGmail"
  | "chipWorkspace"
  | "chipYahoo"
  | "chipIcloud"
  | "waitlistTitle"
  | "waitlistBody"
  | "waitlistNotify"
  | "waitlistLater"
  | "waitlistThanks"
  | "companyImapWaitlist"
  | "languageLabel";

const microsoftDomainLine = MICROSOFT_LOGIN_DOMAINS.join(" · ");

const es: Record<LoginMessageKey, string> = {
  title: "Entrar a Donexto",
  helper: "Escribe el correo del buzón que quieres monitorear.",
  body: "Escribe el correo del buzón que quieres monitorear.",
  noPasswordNote:
    "Al continuar, firmarás en Microsoft. Donexto no pide la contraseña de Outlook ni de Hotmail.",
  helperYahoo:
    "Te llevamos al sitio de Yahoo para que firmes ahí. Donexto no pide tu clave.",
  helperMicrosoft:
    "Microsoft identifica el correo en su sitio. Donexto no pide la contraseña de Outlook.",
  confirmTitle: "¿Usamos este correo en Donexto?",
  confirmHelper:
    "Ese correo es el buzón que Donexto va a monitorear. Hoy leemos Outlook, Hotmail, Live, MSN y Microsoft 365.",
  emailLabel: "Correo del buzón",
  confirmEmailLabel: "Correo que Donexto va a monitorear",
  continueCta: "Continuar",
  subscribeCta: "Continuar",
  continuing: "Continuando…",
  openingMailbox: "Abriendo tu correo…",
  confirming: "Continuando…",
  confirmCta: "Sí, continuar",
  confirmBack: "Cambiar correo",
  yesContinue: "Sí, continuar",
  changeEmail: "Cambiar correo",
  later: "Más tarde",
  changeEmailExplain:
    "El correo tiene que ser el buzón que Donexto puede leer ahora: Outlook, Hotmail, Live, MSN o Microsoft 365.",
  icloudUnavailable:
    "iCloud aún no está disponible. Si quieres, te avisamos a este correo cuando Donexto pueda monitorearlo.",
  mustUseKnownMailbox:
    "Hoy Donexto lee Outlook, Hotmail, Live, MSN y Microsoft 365. Gmail, Yahoo e iCloud van a llegar.",
  gmailPending:
    "Gmail aún no se puede monitorear. Si ya entras a Donexto con este Gmail, Continuar te identifica. Si es la primera vez, te podemos avisar cuando esté listo.",
  confirmYahoo:
    "Ese correo es el buzón que Donexto va a monitorear. Al continuar, firmas en Yahoo. Donexto no pide la contraseña de tu correo.",
  confirmMicrosoft:
    "Ese correo es el buzón que Donexto va a monitorear. Al continuar, firmas en Microsoft. Donexto no pide la contraseña de Outlook.",
  confirmGmail:
    "Ese correo es el buzón que Donexto va a monitorear. Al continuar, Google te identifica. Donexto no pide la contraseña de Gmail.",
  confirmOther:
    "Ese correo es el buzón que Donexto va a monitorear. Hoy tiene que ser Outlook, Hotmail o Microsoft 365.",
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
  servicesKicker: "Qué buzones puede leer Donexto",
  servicesActive: "Disponible ahora",
  serviceGoogle: "Gmail — Próximamente",
  serviceYahoo: "Yahoo — Próximamente",
  serviceMicrosoftTitle: "Outlook, Hotmail, Live, MSN y Microsoft 365",
  serviceMicrosoftDomains: microsoftDomainLine,
  useSuggested: "Usar este correo",
  invalidEmail:
    "Escribe un correo válido, con @ y un dominio real (ejemplo: nombre@hotmail.com).",
  noAccount: "Ese correo no tiene cuenta Donexto todavía. Confirma si es el buzón a monitorear.",
  continueFailed: "No fue posible continuar con ese correo.",
  confirmFailed: "No fue posible continuar con ese correo.",
  networkFailed:
    "No hay conexión con Donexto. Revisa la red e inténtalo de nuevo.",
  reviewFailed: "No fue posible revisar ese correo.",
  microsoftOpenFailed: "No fue posible abrir el inicio de sesión de Microsoft.",
  yahooOpenFailed: "No fue posible abrir Yahoo.",
  googleOpenFailed: "No fue posible abrir el inicio de sesión de Google.",
  appleOpenFailed: "iCloud aún no está disponible.",
  noActiveService:
    "Hoy Donexto lee Outlook, Hotmail, Live, MSN y Microsoft 365.",
  passwordMin: "La contraseña de Donexto usa al menos 8 caracteres.",
  donextoSigninFailed: "No fue posible iniciar sesión en Donexto.",
  resetSent: "Enviamos un enlace para restablecer la contraseña de Donexto.",
  recoverNeedEmail: "Escribe primero el correo de tu cuenta Donexto.",
  promise: "Do Next To…\nLo siguiente que sí importa. El resto espera.",
  wantedToSay: "Ese dominio no es un correo que podamos leer ahora. ¿Quisiste decir",
  emailPlaceholder: "tu@hotmail.com",
  availableNow: "Disponible ahora",
  comingSoonBadge: "Pronto",
  chipOutlook: "Outlook",
  chipHotmail: "Hotmail",
  chipLive: "Live",
  chipMsn: "MSN",
  chipM365: "Microsoft 365",
  chipGmail: "Gmail",
  chipWorkspace: "Google Workspace",
  chipYahoo: "Yahoo",
  chipIcloud: "iCloud",
  waitlistTitle: "Próximamente",
  waitlistBody:
    "Próximamente. Si quieres, te avisamos a este correo cuando Donexto pueda monitorear {provider}.",
  waitlistNotify: "Avísame",
  waitlistLater: "Ahora no",
  waitlistThanks: "Listo. Te avisamos a este correo cuando el buzón esté disponible.",
  companyImapWaitlist:
    "Donexto solo monitorea Microsoft 365 y (pronto) Google Workspace. Otros servidores de empresa aún no se pueden leer. Si quieres, te avisamos a este correo.",
  languageLabel: "Idioma",
};

const en: Record<LoginMessageKey, string> = {
  title: "Sign in to Donexto",
  helper: "Enter the mailbox email you want Donexto to monitor.",
  body: "Enter the mailbox email you want Donexto to monitor.",
  noPasswordNote:
    "When you continue, you will sign in at Yahoo, Outlook, or Gmail. Donexto does not ask for your mailbox password.",
  helperYahoo:
    "We take you to Yahoo’s site to sign in. Donexto does not ask for your password.",
  helperMicrosoft:
    "Microsoft identifies the address on its site. Donexto does not ask for your Outlook password.",
  confirmTitle: "Use this email in Donexto?",
  confirmHelper:
    "That address is the mailbox Donexto will monitor. It must be Yahoo, Outlook/Hotmail, or Gmail — not a different login email.",
  emailLabel: "Mailbox email",
  confirmEmailLabel: "Email Donexto will monitor",
  continueCta: "Continue",
  subscribeCta: "Continue",
  continuing: "Continuing…",
  openingMailbox: "Opening your mailbox…",
  confirming: "Continuing…",
  confirmCta: "Yes, continue",
  confirmBack: "Change email",
  yesContinue: "Yes, continue",
  changeEmail: "Change email",
  later: "Later",
  changeEmailExplain:
    "The email has to be the mailbox (Yahoo, Outlook, or Gmail) that Donexto will monitor. If you enter another address, we cannot serve the inbox that matters to you.",
  icloudUnavailable:
    "iCloud is not available yet. For now use Yahoo, Outlook/Hotmail, or Gmail.",
  mustUseKnownMailbox:
    "For now the mailbox has to be Yahoo, Outlook/Hotmail, or Gmail. If you enter another address, we cannot serve the inbox that matters to you.",
  gmailPending:
    "New Gmail accounts are still under Google review. If you already use this Gmail in Donexto, Continue takes you to Google. If this is the first time, use Yahoo or Outlook/Hotmail.",
  confirmYahoo:
    "That address is the mailbox Donexto will monitor. When you continue, you sign in at Yahoo. Donexto does not ask for your mailbox password.",
  confirmMicrosoft:
    "That address is the mailbox Donexto will monitor. When you continue, you sign in at Microsoft. Donexto does not ask for your Outlook password.",
  confirmGmail:
    "That address is the mailbox Donexto will monitor. When you continue, Google identifies you. Donexto does not ask for your Gmail password.",
  confirmOther:
    "That address is the mailbox Donexto will monitor. It must be Yahoo, Outlook/Hotmail, or Gmail.",
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
  noAccount: "That email has no Donexto account yet. Confirm it is the mailbox to monitor.",
  continueFailed: "We could not continue with that email.",
  confirmFailed: "We could not continue with that email.",
  networkFailed: "No connection to Donexto. Check the network and try again.",
  reviewFailed: "We could not check that email.",
  microsoftOpenFailed: "We could not open Microsoft sign-in.",
  yahooOpenFailed: "We could not open Yahoo.",
  googleOpenFailed: "We could not open Google sign-in.",
  appleOpenFailed: "iCloud is not available yet.",
  noActiveService:
    "For now the mailbox has to be Yahoo, Outlook/Hotmail, or Gmail.",
  passwordMin: "The Donexto password uses at least 8 characters.",
  donextoSigninFailed: "We could not sign you in to Donexto.",
  resetSent: "We sent a link to reset your Donexto password.",
  recoverNeedEmail: "Enter your Donexto account email first.",
  promise: "Do Next To…\nThe next thing that actually matters. Everything else waits.",
  wantedToSay: "That domain is not a mailbox we can read yet. Did you mean",
  emailPlaceholder: "you@hotmail.com",
  availableNow: "Available now",
  comingSoonBadge: "Soon",
  chipOutlook: "Outlook",
  chipHotmail: "Hotmail",
  chipLive: "Live",
  chipMsn: "MSN",
  chipM365: "Microsoft 365",
  chipGmail: "Gmail",
  chipWorkspace: "Google Workspace",
  chipYahoo: "Yahoo",
  chipIcloud: "iCloud",
  waitlistTitle: "Coming soon",
  waitlistBody:
    "Coming soon. If you want, we will email this address when Donexto can monitor {provider}.",
  waitlistNotify: "Notify me",
  waitlistLater: "Not now",
  waitlistThanks: "Done. We will email you when that mailbox is available.",
  companyImapWaitlist:
    "Donexto only monitors Microsoft 365 and (soon) Google Workspace. Other company servers cannot be read yet. We can notify this address if you want.",
  languageLabel: "Language",
};

const fr: Record<LoginMessageKey, string> = {
  title: "Connexion à Donexto",
  helper: "Saisissez l’e-mail de la boîte que Donexto doit surveiller.",
  body: "Saisissez l’e-mail de la boîte que Donexto doit surveiller.",
  noPasswordNote:
    "En continuant, vous vous connecterez sur Yahoo, Outlook ou Gmail. Donexto ne demande pas le mot de passe de votre messagerie.",
  helperYahoo:
    "Nous vous emmenons sur le site Yahoo pour vous connecter. Donexto ne demande pas votre mot de passe.",
  helperMicrosoft:
    "Microsoft identifie l’adresse sur son site. Donexto ne demande pas le mot de passe Outlook.",
  confirmTitle: "Utiliser cet e-mail dans Donexto ?",
  confirmHelper:
    "Cette adresse est la boîte que Donexto va surveiller. Ce doit être Yahoo, Outlook/Hotmail ou Gmail, pas un autre e-mail de connexion.",
  emailLabel: "E-mail de la boîte",
  confirmEmailLabel: "E-mail que Donexto va surveiller",
  continueCta: "Continuer",
  subscribeCta: "Continuer",
  continuing: "Suite…",
  openingMailbox: "Ouverture de votre messagerie…",
  confirming: "Suite…",
  confirmCta: "Oui, continuer",
  confirmBack: "Changer d’e-mail",
  yesContinue: "Oui, continuer",
  changeEmail: "Changer d’e-mail",
  later: "Plus tard",
  changeEmailExplain:
    "L’e-mail doit être la boîte (Yahoo, Outlook ou Gmail) que Donexto va surveiller. Si vous en mettez un autre, nous ne pouvons pas servir la messagerie qui vous importe.",
  icloudUnavailable:
    "iCloud n’est pas encore disponible. Pour l’instant, utilisez Yahoo, Outlook/Hotmail ou Gmail.",
  mustUseKnownMailbox:
    "Pour l’instant, la boîte doit être Yahoo, Outlook/Hotmail ou Gmail. Si vous en mettez une autre, nous ne pouvons pas servir la messagerie qui vous importe.",
  gmailPending:
    "Les nouveaux comptes Gmail sont encore en revue chez Google. Si vous utilisez déjà ce Gmail dans Donexto, Continuer ouvre Google. Sinon, utilisez Yahoo ou Outlook/Hotmail.",
  confirmYahoo:
    "Cette adresse est la boîte que Donexto va surveiller. En continuant, vous vous connectez sur Yahoo. Donexto ne demande pas le mot de passe.",
  confirmMicrosoft:
    "Cette adresse est la boîte que Donexto va surveiller. En continuant, vous vous connectez chez Microsoft. Donexto ne demande pas le mot de passe Outlook.",
  confirmGmail:
    "Cette adresse est la boîte que Donexto va surveiller. En continuant, Google vous identifie. Donexto ne demande pas le mot de passe Gmail.",
  confirmOther:
    "Cette adresse est la boîte que Donexto va surveiller. Ce doit être Yahoo, Outlook/Hotmail ou Gmail.",
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
  noAccount: "Cet e-mail n’a pas encore de compte Donexto. Confirmez que c’est la boîte à surveiller.",
  continueFailed: "Impossible de continuer avec cet e-mail.",
  confirmFailed: "Impossible de continuer avec cet e-mail.",
  networkFailed:
    "Pas de connexion à Donexto. Vérifiez le réseau et réessayez.",
  reviewFailed: "Impossible de vérifier cet e-mail.",
  microsoftOpenFailed: "Impossible d’ouvrir la connexion Microsoft.",
  yahooOpenFailed: "Impossible d’ouvrir Yahoo.",
  googleOpenFailed: "Impossible d’ouvrir la connexion Google.",
  appleOpenFailed: "iCloud n’est pas encore disponible.",
  noActiveService:
    "Pour l’instant, la boîte doit être Yahoo, Outlook/Hotmail ou Gmail.",
  passwordMin: "Le mot de passe Donexto comporte au moins 8 caractères.",
  donextoSigninFailed: "Impossible de vous connecter à Donexto.",
  resetSent: "Nous avons envoyé un lien pour réinitialiser le mot de passe Donexto.",
  recoverNeedEmail: "Saisissez d’abord l’e-mail de votre compte Donexto.",
  promise: "Do Next To…\nLa prochaine chose qui compte vraiment. Le reste attend.",
  wantedToSay: "Ce domaine n’est pas une boîte que nous pouvons lire. Vouliez-vous dire",
  emailPlaceholder: "vous@hotmail.com",
  availableNow: "Disponible maintenant",
  comingSoonBadge: "Bientôt",
  chipOutlook: "Outlook",
  chipHotmail: "Hotmail",
  chipLive: "Live",
  chipMsn: "MSN",
  chipM365: "Microsoft 365",
  chipGmail: "Gmail",
  chipWorkspace: "Google Workspace",
  chipYahoo: "Yahoo",
  chipIcloud: "iCloud",
  waitlistTitle: "Bientôt",
  waitlistBody:
    "Bientôt. Si vous voulez, nous préviendrons cet e-mail lorsque Donexto pourra surveiller {provider}.",
  waitlistNotify: "Prévenez-moi",
  waitlistLater: "Pas maintenant",
  waitlistThanks: "C’est noté. Nous vous préviendrons lorsque cette boîte sera disponible.",
  companyImapWaitlist:
    "Donexto ne surveille que Microsoft 365 et (bientôt) Google Workspace. Les autres serveurs d’entreprise ne peuvent pas encore être lus. Nous pouvons prévenir cet e-mail si vous voulez.",
  languageLabel: "Langue",
};

const it: Record<LoginMessageKey, string> = {
  title: "Accedi a Donexto",
  helper: "Scrivi l’email della casella che Donexto deve monitorare.",
  body: "Scrivi l’email della casella che Donexto deve monitorare.",
  noPasswordNote:
    "Continuando, accederai su Yahoo, Outlook o Gmail. Donexto non chiede la password della casella.",
  helperYahoo:
    "Ti portiamo sul sito Yahoo per accedere. Donexto non chiede la password.",
  helperMicrosoft:
    "Microsoft identifica l’indirizzo sul suo sito. Donexto non chiede la password di Outlook.",
  confirmTitle: "Usiamo questa email in Donexto?",
  confirmHelper:
    "Quell’indirizzo è la casella che Donexto monitorerà. Deve essere Yahoo, Outlook/Hotmail o Gmail, non un’altra email di login.",
  emailLabel: "Email della casella",
  confirmEmailLabel: "Email che Donexto monitorerà",
  continueCta: "Continua",
  subscribeCta: "Continua",
  continuing: "Attendi…",
  openingMailbox: "Apertura della casella…",
  confirming: "Attendi…",
  confirmCta: "Sì, continua",
  confirmBack: "Cambia email",
  yesContinue: "Sì, continua",
  changeEmail: "Cambia email",
  later: "Più tardi",
  changeEmailExplain:
    "L’email deve essere la casella (Yahoo, Outlook o Gmail) che Donexto monitorerà. Se ne inserisci un’altra, non possiamo servire la casella che ti importa.",
  icloudUnavailable:
    "iCloud non è ancora disponibile. Per ora usa Yahoo, Outlook/Hotmail o Gmail.",
  mustUseKnownMailbox:
    "Per ora la casella deve essere Yahoo, Outlook/Hotmail o Gmail. Se ne inserisci un’altra, non possiamo servire la casella che ti importa.",
  gmailPending:
    "I nuovi account Gmail sono ancora in revisione da Google. Se usi già questo Gmail in Donexto, Continua apre Google. Altrimenti usa Yahoo o Outlook/Hotmail.",
  confirmYahoo:
    "Quell’indirizzo è la casella che Donexto monitorerà. Continuando, accedi su Yahoo. Donexto non chiede la password.",
  confirmMicrosoft:
    "Quell’indirizzo è la casella che Donexto monitorerà. Continuando, accedi su Microsoft. Donexto non chiede la password di Outlook.",
  confirmGmail:
    "Quell’indirizzo è la casella che Donexto monitorerà. Continuando, Google ti identifica. Donexto non chiede la password di Gmail.",
  confirmOther:
    "Quell’indirizzo è la casella che Donexto monitorerà. Deve essere Yahoo, Outlook/Hotmail o Gmail.",
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
  noAccount: "Questa email non ha ancora un account Donexto. Conferma che è la casella da monitorare.",
  continueFailed: "Impossibile continuare con questa email.",
  confirmFailed: "Impossibile continuare con questa email.",
  networkFailed:
    "Nessuna connessione a Donexto. Controlla la rete e riprova.",
  reviewFailed: "Impossibile verificare questa email.",
  microsoftOpenFailed: "Impossibile aprire l’accesso Microsoft.",
  yahooOpenFailed: "Impossibile aprire Yahoo.",
  googleOpenFailed: "Impossibile aprire l’accesso Google.",
  appleOpenFailed: "iCloud non è ancora disponibile.",
  noActiveService:
    "Per ora la casella deve essere Yahoo, Outlook/Hotmail o Gmail.",
  passwordMin: "La password Donexto ha almeno 8 caratteri.",
  donextoSigninFailed: "Impossibile accedere a Donexto.",
  resetSent: "Abbiamo inviato un link per reimpostare la password Donexto.",
  recoverNeedEmail: "Inserisci prima l’email del tuo account Donexto.",
  promise: "Do Next To…\nLa prossima cosa che conta davvero. Il resto aspetta.",
  wantedToSay: "Quel dominio non è una casella che possiamo leggere ora. Intendevi",
  emailPlaceholder: "tu@hotmail.com",
  availableNow: "Disponibile ora",
  comingSoonBadge: "Presto",
  chipOutlook: "Outlook",
  chipHotmail: "Hotmail",
  chipLive: "Live",
  chipMsn: "MSN",
  chipM365: "Microsoft 365",
  chipGmail: "Gmail",
  chipWorkspace: "Google Workspace",
  chipYahoo: "Yahoo",
  chipIcloud: "iCloud",
  waitlistTitle: "Prossimamente",
  waitlistBody:
    "Prossimamente. Se vuoi, ti avvisiamo a questa email quando Donexto potrà monitorare {provider}.",
  waitlistNotify: "Avvisami",
  waitlistLater: "Adesso no",
  waitlistThanks: "Fatto. Ti avvisiamo quando quella casella sarà disponibile.",
  companyImapWaitlist:
    "Donexto monitora solo Microsoft 365 e (presto) Google Workspace. Altri server aziendali non si possono ancora leggere. Possiamo avvisare questa email se vuoi.",
  languageLabel: "Lingua",
};

const pt: Record<LoginMessageKey, string> = {
  title: "Entrar no Donexto",
  helper: "Escreva o correio da caixa que o Donexto deve monitorizar.",
  body: "Escreva o correio da caixa que o Donexto deve monitorizar.",
  noPasswordNote:
    "Ao continuar, entra na Yahoo, Outlook ou Gmail. O Donexto não pede a palavra-passe do correio.",
  helperYahoo:
    "Levamo-lo ao site da Yahoo para entrar. O Donexto não pede a palavra-passe.",
  helperMicrosoft:
    "A Microsoft identifica o correio no respectivo site. O Donexto não pede a palavra-passe do Outlook.",
  confirmTitle: "Usamos este correio no Donexto?",
  confirmHelper:
    "Esse endereço é a caixa que o Donexto vai monitorizar. Tem de ser Yahoo, Outlook/Hotmail ou Gmail, não outro correio de início de sessão.",
  emailLabel: "Correio da caixa",
  confirmEmailLabel: "Correio que o Donexto vai monitorizar",
  continueCta: "Continuar",
  subscribeCta: "Continuar",
  continuing: "A continuar…",
  openingMailbox: "A abrir o correio…",
  confirming: "A continuar…",
  confirmCta: "Sim, continuar",
  confirmBack: "Mudar correio",
  yesContinue: "Sim, continuar",
  changeEmail: "Mudar correio",
  later: "Mais tarde",
  changeEmailExplain:
    "O correio tem de ser a caixa (Yahoo, Outlook ou Gmail) que o Donexto vai monitorizar. Se puser outro, não podemos servir a caixa que lhe importa.",
  icloudUnavailable:
    "O iCloud ainda não está disponível. Por agora use Yahoo, Outlook/Hotmail ou Gmail.",
  mustUseKnownMailbox:
    "Por agora a caixa tem de ser Yahoo, Outlook/Hotmail ou Gmail. Se puser outra, não podemos servir a caixa que lhe importa.",
  gmailPending:
    "Novas contas Gmail ainda estão em revisão da Google. Se já usa este Gmail no Donexto, Continuar abre a Google. Se é a primeira vez, use Yahoo ou Outlook/Hotmail.",
  confirmYahoo:
    "Esse endereço é a caixa que o Donexto vai monitorizar. Ao continuar, entra na Yahoo. O Donexto não pede a palavra-passe.",
  confirmMicrosoft:
    "Esse endereço é a caixa que o Donexto vai monitorizar. Ao continuar, entra na Microsoft. O Donexto não pede a palavra-passe do Outlook.",
  confirmGmail:
    "Esse endereço é a caixa que o Donexto vai monitorizar. Ao continuar, o Google identifica-o. O Donexto não pede a palavra-passe do Gmail.",
  confirmOther:
    "Esse endereço é a caixa que o Donexto vai monitorizar. Tem de ser Yahoo, Outlook/Hotmail ou Gmail.",
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
  noAccount: "Esse correio ainda não tem conta Donexto. Confirme se é a caixa a monitorizar.",
  continueFailed: "Não foi possível continuar com esse correio.",
  confirmFailed: "Não foi possível continuar com esse correio.",
  networkFailed:
    "Sem ligação ao Donexto. Verifique a rede e tente novamente.",
  reviewFailed: "Não foi possível verificar esse correio.",
  microsoftOpenFailed: "Não foi possível abrir o início de sessão da Microsoft.",
  yahooOpenFailed: "Não foi possível abrir a Yahoo.",
  googleOpenFailed: "Não foi possível abrir o início de sessão do Google.",
  appleOpenFailed: "O iCloud ainda não está disponível.",
  noActiveService:
    "Por agora a caixa tem de ser Yahoo, Outlook/Hotmail ou Gmail.",
  passwordMin: "A palavra-passe Donexto tem pelo menos 8 caracteres.",
  donextoSigninFailed: "Não foi possível iniciar sessão no Donexto.",
  resetSent: "Enviámos uma ligação para repor a palavra-passe Donexto.",
  recoverNeedEmail: "Escreva primeiro o correio da sua conta Donexto.",
  promise: "Do Next To…\nO que segue e importa. O resto espera.",
  wantedToSay: "Esse domínio não é um correio que possamos ler agora. Quis dizer",
  emailPlaceholder: "voce@hotmail.com",
  availableNow: "Disponível agora",
  comingSoonBadge: "Em breve",
  chipOutlook: "Outlook",
  chipHotmail: "Hotmail",
  chipLive: "Live",
  chipMsn: "MSN",
  chipM365: "Microsoft 365",
  chipGmail: "Gmail",
  chipWorkspace: "Google Workspace",
  chipYahoo: "Yahoo",
  chipIcloud: "iCloud",
  waitlistTitle: "Em breve",
  waitlistBody:
    "Em breve. Se quiser, avisamos neste correio quando o Donexto puder monitorizar {provider}.",
  waitlistNotify: "Avise-me",
  waitlistLater: "Agora não",
  waitlistThanks: "Feito. Avisamos quando essa caixa estiver disponível.",
  companyImapWaitlist:
    "O Donexto só monitoriza Microsoft 365 e (em breve) Google Workspace. Outros servidores da empresa ainda não se podem ler. Podemos avisar este correio se quiser.",
  languageLabel: "Idioma",
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

export function loginTextReplace(
  language: AppLanguage,
  key: LoginMessageKey,
  vars: Record<string, string>,
): string {
  let text = loginText(language, key);
  for (const [name, value] of Object.entries(vars)) {
    text = text.replaceAll(`{${name}}`, value);
  }
  return text;
}
