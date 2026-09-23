import type { AppLanguage } from "@/lib/i18n/languages";

export type MessageKey =
  | "settingsTitle"
  | "settingsKicker"
  | "settingsLanguage"
  | "settingsLanguageHelp"
  | "settingsSaved"
  | "settingsClose"
  | "settingsAccount"
  | "navHome"
  | "navMail"
  | "navAlerts"
  | "navCases"
  | "navTasks"
  | "navActivity"
  | "navReports"
  | "navMetrics"
  | "navSettings"
  | "navMenu"
  | "profileSettings"
  | "profileSignOut"
  | "closeMenu"
  | "language"
  | "searchPlaceholder"
  | "confirmGateTitle"
  | "confirmGateHelper"
  | "confirmGateSpam"
  | "confirmGateResent"
  | "confirmGateResendError"
  | "confirmGateRefreshError"
  | "confirmGateChecking"
  | "confirmGateSending"
  | "confirmGateRefresh"
  | "confirmGateResend"
  | "confirmGateSignOut"
  | "confirmGateSecure"
  | "confirmGateLinkInvalid"
  | "confirmGateLinkNetwork"
  | "confirmGateSignInAgain";

const es: Record<MessageKey, string> = {
  settingsTitle: "Ajustes",
  settingsKicker: "Tu cuenta Donexto",
  settingsLanguage: "Idioma",
  settingsLanguageHelp:
    "Donexto se muestra en este idioma. Lo guardamos en este dispositivo y en tu cuenta.",
  settingsSaved: "Idioma guardado",
  settingsClose: "Cerrar",
  settingsAccount: "Cuenta",
  navHome: "Inicio",
  navMail: "Correos",
  navAlerts: "Avisos",
  navCases: "Casos",
  navTasks: "Tareas",
  navActivity: "Actividad",
  navReports: "Reportes",
  navMetrics: "Métricas",
  navSettings: "Ajustes",
  navMenu: "Menú",
  profileSettings: "Ajustes e idioma",
  profileSignOut: "Cerrar sesión",
  closeMenu: "Cerrar menú",
  language: "Idioma",
  searchPlaceholder: "Buscar correos, personas o avisos…",
  confirmGateTitle: "Confirma tu correo",
  confirmGateHelper: "Pulsa Verificar en el correo que enviamos a {email}. Ese clic abre Donexto y confirma la cuenta, aunque esta pestaña no tenga sesión.",
  confirmGateSpam: "Revisa Spam o Correo no deseado: Donexto puede ser un remitente desconocido.",
  confirmGateResent: "Listo. Revisa la bandeja y Spam de ese mismo correo.",
  confirmGateResendError: "No fue posible reenviar el correo.",
  confirmGateRefreshError: "Este botón no confirma la cuenta. Abre Verificar en el correo; con un clic entras a Donexto.",
  confirmGateChecking: "Comprobando…",
  confirmGateSending: "Enviando…",
  confirmGateRefresh: "Ya abrí el enlace",
  confirmGateResend: "Reenviar correo",
  confirmGateSignOut: "Cerrar sesión",
  confirmGateSecure: "Donexto confirma el correo solo con el enlace. El botón de esta pantalla no basta.",
  confirmGateLinkInvalid: "Ese enlace ya se usó o expiró. Pulsa Reenviar y abre Verificar una sola vez.",
  confirmGateLinkNetwork: "No pudimos abrir el enlace. Revisa la red y vuelve a pulsar Verificar en el correo.",
  confirmGateSignInAgain: "El correo ya quedó confirmado. Entra de nuevo con el mismo proveedor para abrir Donexto.",
};

const en: Record<MessageKey, string> = {
  settingsTitle: "Settings",
  settingsKicker: "Your Donexto account",
  settingsLanguage: "Language",
  settingsLanguageHelp:
    "Donexto uses this language. We save it on this device and on your account.",
  settingsSaved: "Language saved",
  settingsClose: "Close",
  settingsAccount: "Account",
  navHome: "Home",
  navMail: "Mail",
  navAlerts: "Alerts",
  navCases: "Cases",
  navTasks: "Tasks",
  navActivity: "Activity",
  navReports: "Reports",
  navMetrics: "Metrics",
  navSettings: "Settings",
  navMenu: "Menu",
  profileSettings: "Settings & language",
  profileSignOut: "Sign out",
  closeMenu: "Close menu",
  language: "Language",
  searchPlaceholder: "Search mail, people, or alerts…",
  confirmGateTitle: "Confirm your email",
  confirmGateHelper: "Click Verify in the email we sent to {email}. That one click opens Donexto and confirms the account, even in a new tab with no session.",
  confirmGateSpam: "Check Spam or Junk: Donexto may be an unfamiliar sender.",
  confirmGateResent: "Done. Check the inbox and Spam folder for that email.",
  confirmGateResendError: "We could not resend the email.",
  confirmGateRefreshError: "This button does not confirm the account. Open Verify in the email; one click signs you in.",
  confirmGateChecking: "Checking…",
  confirmGateSending: "Sending…",
  confirmGateRefresh: "I opened the link",
  confirmGateResend: "Resend email",
  confirmGateSignOut: "Sign out",
  confirmGateSecure: "Donexto confirms the email only from that link. This screen's button is not enough.",
  confirmGateLinkInvalid: "That link was already used or it expired. Resend the email and open Verify once.",
  confirmGateLinkNetwork: "We could not open the link. Check your connection and click Verify in the email again.",
  confirmGateSignInAgain: "The email is already confirmed. Sign in again with the same provider to open Donexto.",
};

const fr: Record<MessageKey, string> = {
  settingsTitle: "Réglages",
  settingsKicker: "Votre compte Donexto",
  settingsLanguage: "Langue",
  settingsLanguageHelp:
    "Donexto s’affiche dans cette langue. Nous l’enregistrons sur cet appareil et dans votre compte.",
  settingsSaved: "Langue enregistrée",
  settingsClose: "Fermer",
  settingsAccount: "Compte",
  navHome: "Accueil",
  navMail: "Courrier",
  navAlerts: "Alertes",
  navCases: "Dossiers",
  navTasks: "Tâches",
  navActivity: "Activité",
  navReports: "Rapports",
  navMetrics: "Indicateurs",
  navSettings: "Réglages",
  navMenu: "Menu",
  profileSettings: "Réglages et langue",
  profileSignOut: "Se déconnecter",
  closeMenu: "Fermer le menu",
  language: "Langue",
  searchPlaceholder: "Rechercher courrier, personnes ou alertes…",
  confirmGateTitle: "Confirmez votre e-mail",
  confirmGateHelper: "Cliquez sur Vérifier dans l’e-mail envoyé à {email}. Ce clic ouvre Donexto et confirme le compte, même dans un nouvel onglet sans session.",
  confirmGateSpam: "Vérifiez les spams ou courriers indésirables : Donexto peut être un expéditeur inconnu.",
  confirmGateResent: "C’est fait. Vérifiez la boîte de réception et les spams.",
  confirmGateResendError: "Impossible de renvoyer l’e-mail.",
  confirmGateRefreshError: "Ce bouton ne confirme pas le compte. Ouvrez Vérifier dans l’e-mail : un clic vous fait entrer.",
  confirmGateChecking: "Vérification…",
  confirmGateSending: "Envoi…",
  confirmGateRefresh: "J’ai ouvert le lien",
  confirmGateResend: "Renvoyer l’e-mail",
  confirmGateSignOut: "Se déconnecter",
  confirmGateSecure: "Donexto confirme l’e-mail seulement avec ce lien. Le bouton de cet écran ne suffit pas.",
  confirmGateLinkInvalid: "Ce lien a déjà été utilisé ou il a expiré. Renvoyez l’e-mail et ouvrez Vérifier une seule fois.",
  confirmGateLinkNetwork: "Nous n’avons pas pu ouvrir le lien. Vérifiez le réseau et cliquez de nouveau sur Vérifier dans l’e-mail.",
  confirmGateSignInAgain: "L’e-mail est déjà confirmé. Reconnectez-vous avec le même fournisseur pour ouvrir Donexto.",
};

const it: Record<MessageKey, string> = {
  settingsTitle: "Impostazioni",
  settingsKicker: "Il tuo account Donexto",
  settingsLanguage: "Lingua",
  settingsLanguageHelp:
    "Donexto usa questa lingua. La salviamo su questo dispositivo e nel tuo account.",
  settingsSaved: "Lingua salvata",
  settingsClose: "Chiudi",
  settingsAccount: "Account",
  navHome: "Home",
  navMail: "Posta",
  navAlerts: "Avvisi",
  navCases: "Casi",
  navTasks: "Attività",
  navActivity: "Attività recente",
  navReports: "Report",
  navMetrics: "Metriche",
  navSettings: "Impostazioni",
  navMenu: "Menu",
  profileSettings: "Impostazioni e lingua",
  profileSignOut: "Esci",
  closeMenu: "Chiudi menu",
  language: "Lingua",
  searchPlaceholder: "Cerca posta, persone o avvisi…",
  confirmGateTitle: "Conferma la tua e-mail",
  confirmGateHelper: "Premi Verifica nell’email inviata a {email}. Quel clic apre Donexto e conferma l’account, anche in una scheda nuova senza sessione.",
  confirmGateSpam: "Controlla Spam o Posta indesiderata: Donexto potrebbe essere un mittente sconosciuto.",
  confirmGateResent: "Fatto. Controlla la posta in arrivo e Spam.",
  confirmGateResendError: "Non è stato possibile inviare di nuovo l’e-mail.",
  confirmGateRefreshError: "Questo pulsante non conferma l’account. Apri Verifica nell’email: un clic ti fa entrare.",
  confirmGateChecking: "Verifica…",
  confirmGateSending: "Invio…",
  confirmGateRefresh: "Ho aperto il link",
  confirmGateResend: "Invia di nuovo l’e-mail",
  confirmGateSignOut: "Esci",
  confirmGateSecure: "Donexto conferma l’email solo da quel link. Il pulsante di questa schermata non basta.",
  confirmGateLinkInvalid: "Quel link è già stato usato oppure è scaduto. Invia di nuovo l’email e apri Verifica una sola volta.",
  confirmGateLinkNetwork: "Non siamo riusciti ad aprire il link. Controlla la rete e premi di nuovo Verifica nell’email.",
  confirmGateSignInAgain: "L’email è già confermata. Entra di nuovo con lo stesso provider per aprire Donexto.",
};

const pt: Record<MessageKey, string> = {
  settingsTitle: "Definições",
  settingsKicker: "A sua conta Donexto",
  settingsLanguage: "Idioma",
  settingsLanguageHelp:
    "O Donexto usa este idioma. Guardamos neste dispositivo e na sua conta.",
  settingsSaved: "Idioma guardado",
  settingsClose: "Fechar",
  settingsAccount: "Conta",
  navHome: "Início",
  navMail: "Correio",
  navAlerts: "Avisos",
  navCases: "Casos",
  navTasks: "Tarefas",
  navActivity: "Atividade",
  navReports: "Relatórios",
  navMetrics: "Métricas",
  navSettings: "Definições",
  navMenu: "Menu",
  profileSettings: "Definições e idioma",
  profileSignOut: "Terminar sessão",
  closeMenu: "Fechar menu",
  language: "Idioma",
  searchPlaceholder: "Procurar correio, pessoas ou avisos…",
  confirmGateTitle: "Confirme o seu e-mail",
  confirmGateHelper: "Toque em Verificar no e-mail enviado para {email}. Esse clique abre o Donexto e confirma a conta, mesmo numa aba nova sem sessão.",
  confirmGateSpam: "Verifique Spam ou Lixo eletrônico: Donexto pode ser um remetente desconhecido.",
  confirmGateResent: "Pronto. Verifique a caixa de entrada e o Spam.",
  confirmGateResendError: "Não foi possível reenviar o e-mail.",
  confirmGateRefreshError: "Este botão não confirma a conta. Abra Verificar no e-mail; um clique entra no Donexto.",
  confirmGateChecking: "Verificando…",
  confirmGateSending: "Enviando…",
  confirmGateRefresh: "Já abri o link",
  confirmGateResend: "Reenviar e-mail",
  confirmGateSignOut: "Terminar sessão",
  confirmGateSecure: "O Donexto confirma o e-mail só com esse link. O botão desta tela não basta.",
  confirmGateLinkInvalid: "Esse link já foi usado ou expirou. Reenvie o e-mail e abra Verificar uma só vez.",
  confirmGateLinkNetwork: "Não conseguimos abrir o link. Verifique a rede e toque de novo em Verificar no e-mail.",
  confirmGateSignInAgain: "O e-mail já está confirmado. Entre de novo com o mesmo provedor para abrir o Donexto.",
};

export const MESSAGES: Record<AppLanguage, Record<MessageKey, string>> = {
  es,
  en,
  fr,
  it,
  pt,
};

export function translate(
  language: AppLanguage,
  key: MessageKey,
): string {
  return MESSAGES[language][key] || MESSAGES.es[key];
}

export function verifyLinkErrorText(
  language: AppLanguage,
  code: string,
): string {
  const key: MessageKey = code === "invalid"
    ? "confirmGateLinkInvalid"
    : code === "retry"
      ? "confirmGateLinkNetwork"
      : code === "sign_in_again"
        ? "confirmGateSignInAgain"
        : "confirmGateRefreshError";
  return translate(language, key);
}
