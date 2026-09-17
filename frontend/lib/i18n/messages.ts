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
  | "confirmGateSecure";

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
  confirmGateHelper: "Abre el enlace que enviamos a {email}. Eso te identifica; no es la contraseña del buzón.",
  confirmGateSpam: "Revisa Spam o Correo no deseado: Donexto puede ser un remitente desconocido.",
  confirmGateResent: "Listo. Revisa la bandeja y Spam de ese mismo correo.",
  confirmGateResendError: "No fue posible reenviar el correo.",
  confirmGateRefreshError: "Aún no vemos la confirmación. Abre el enlace del correo.",
  confirmGateChecking: "Comprobando…",
  confirmGateSending: "Enviando…",
  confirmGateRefresh: "Ya confirmé mi correo",
  confirmGateResend: "Reenviar correo",
  confirmGateSignOut: "Cerrar sesión",
  confirmGateSecure: "Al continuar, Donexto solo confirma que ese correo es tuyo.",
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
  confirmGateHelper: "Open the link we sent to {email}. It identifies you; it is not your mailbox password.",
  confirmGateSpam: "Check Spam or Junk: Donexto may be an unfamiliar sender.",
  confirmGateResent: "Done. Check the inbox and Spam folder for that email.",
  confirmGateResendError: "We could not resend the email.",
  confirmGateRefreshError: "We do not see confirmation yet. Open the link in the email.",
  confirmGateChecking: "Checking…",
  confirmGateSending: "Sending…",
  confirmGateRefresh: "I confirmed my email",
  confirmGateResend: "Resend email",
  confirmGateSignOut: "Sign out",
  confirmGateSecure: "Donexto only confirms that this email belongs to you.",
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
  confirmGateHelper: "Ouvrez le lien envoyé à {email}. Il vous identifie et n’est pas le mot de passe de votre boîte.",
  confirmGateSpam: "Vérifiez les spams ou courriers indésirables : Donexto peut être un expéditeur inconnu.",
  confirmGateResent: "C’est fait. Vérifiez la boîte de réception et les spams.",
  confirmGateResendError: "Impossible de renvoyer l’e-mail.",
  confirmGateRefreshError: "La confirmation n’est pas encore visible. Ouvrez le lien reçu.",
  confirmGateChecking: "Vérification…",
  confirmGateSending: "Envoi…",
  confirmGateRefresh: "J’ai confirmé mon e-mail",
  confirmGateResend: "Renvoyer l’e-mail",
  confirmGateSignOut: "Se déconnecter",
  confirmGateSecure: "Donexto confirme seulement que cette adresse vous appartient.",
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
  confirmGateHelper: "Apri il link inviato a {email}. Ti identifica; non è la password della tua casella.",
  confirmGateSpam: "Controlla Spam o Posta indesiderata: Donexto potrebbe essere un mittente sconosciuto.",
  confirmGateResent: "Fatto. Controlla la posta in arrivo e Spam.",
  confirmGateResendError: "Non è stato possibile inviare di nuovo l’e-mail.",
  confirmGateRefreshError: "La conferma non è ancora visibile. Apri il link ricevuto.",
  confirmGateChecking: "Verifica…",
  confirmGateSending: "Invio…",
  confirmGateRefresh: "Ho confermato la mia e-mail",
  confirmGateResend: "Invia di nuovo l’e-mail",
  confirmGateSignOut: "Esci",
  confirmGateSecure: "Donexto conferma solo che questo indirizzo ti appartiene.",
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
  confirmGateHelper: "Abra o link enviado para {email}. Ele identifica você; não é a senha da sua caixa de correio.",
  confirmGateSpam: "Verifique Spam ou Lixo eletrônico: Donexto pode ser um remetente desconhecido.",
  confirmGateResent: "Pronto. Verifique a caixa de entrada e o Spam.",
  confirmGateResendError: "Não foi possível reenviar o e-mail.",
  confirmGateRefreshError: "Ainda não vemos a confirmação. Abra o link recebido.",
  confirmGateChecking: "Verificando…",
  confirmGateSending: "Enviando…",
  confirmGateRefresh: "Confirmei o meu e-mail",
  confirmGateResend: "Reenviar e-mail",
  confirmGateSignOut: "Terminar sessão",
  confirmGateSecure: "O Donexto apenas confirma que este e-mail pertence a você.",
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
