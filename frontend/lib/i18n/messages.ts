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
  | "language";

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
