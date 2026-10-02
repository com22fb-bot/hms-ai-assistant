import type { AppLanguage } from "@/lib/i18n/languages";

export type IcloudCopyKey =
  | "title"
  | "intro"
  | "step1"
  | "step2"
  | "step3"
  | "step4"
  | "emailLabel"
  | "passwordLabel"
  | "passwordPlaceholder"
  | "submit"
  | "submitting"
  | "back"
  | "privacy"
  | "showPassword"
  | "hidePassword"
  | "wrong_password"
  | "two_factor_required"
  | "app_password_required"
  | "invalid_address"
  | "network"
  | "email_mismatch"
  | "imap_failed"
  | "rate_limited"
  | "icloud_credentials_missing";

const es: Record<IcloudCopyKey, string> = {
  title: "Conecta iCloud",
  intro: "Donexto lee solo este correo, en solo lectura.",
  step1: "En la cuenta Apple, activa la verificación en dos pasos si aún no está.",
  step2:
    "Entra a account.apple.com → Inicio de sesión y seguridad → Contraseñas específicas de app.",
  step3:
    "Crea una contraseña con el nombre Donexto y cópiala. No es la contraseña de tu Apple ID.",
  step4: "Pégala aquí junto con tu correo iCloud completo (@icloud.com, @me.com o @mac.com).",
  emailLabel: "Correo iCloud",
  passwordLabel: "Contraseña específica de app",
  passwordPlaceholder: "xxxx-xxxx-xxxx-xxxx",
  submit: "Conectar iCloud",
  submitting: "Conectando iCloud…",
  back: "Cambiar correo",
  privacy:
    "Donexto solo lee este correo. No lo marca como leído, no lo mueve ni lo borra. Puedes revocar la contraseña de app en Apple cuando quieras y desconectar el buzón aquí.",
  showPassword: "Mostrar",
  hidePassword: "Ocultar",
  wrong_password:
    "iCloud no aceptó esa contraseña de app. Revísala o genera otra en account.apple.com.",
  two_factor_required:
    "La cuenta Apple necesita la verificación en dos pasos para crear la contraseña de app. Actívala en account.apple.com y vuelve a intentar.",
  app_password_required:
    "iCloud no acepta la contraseña del Apple ID. Usa una contraseña específica de app. Para crearla hace falta la verificación en dos pasos.",
  invalid_address:
    "Usa el correo completo de iCloud: @icloud.com, @me.com o @mac.com.",
  network: "iCloud no respondió. Revisa la red e inténtalo de nuevo.",
  email_mismatch:
    "Donexto solo lee el correo de esta cuenta. Usa el mismo iCloud con el que entraste.",
  imap_failed: "No fue posible conectar iCloud. Inténtalo de nuevo.",
  rate_limited: "Demasiados intentos seguidos. Espera un momento.",
  icloud_credentials_missing:
    "Vuelve a conectar iCloud. Donexto ya no tiene la contraseña de app.",
};

const en: Record<IcloudCopyKey, string> = {
  title: "Connect iCloud",
  intro: "Donexto reads only this mailbox, and only to look.",
  step1: "On your Apple Account, turn on two-factor authentication if it is off.",
  step2:
    "Open account.apple.com → Sign-In and Security → App-Specific Passwords.",
  step3:
    "Create a password named Donexto and copy it. It is not your Apple ID password.",
  step4: "Paste it here with your full iCloud email (@icloud.com, @me.com, or @mac.com).",
  emailLabel: "iCloud email",
  passwordLabel: "App-specific password",
  passwordPlaceholder: "xxxx-xxxx-xxxx-xxxx",
  submit: "Connect iCloud",
  submitting: "Connecting iCloud…",
  back: "Change email",
  privacy:
    "Donexto only reads this mailbox. It does not mark mail as read, move it, or delete it. You can revoke the app-specific password at Apple anytime and disconnect the mailbox here.",
  showPassword: "Show",
  hidePassword: "Hide",
  wrong_password:
    "iCloud rejected that app-specific password. Check it or create a new one at account.apple.com.",
  two_factor_required:
    "This Apple Account needs two-factor authentication before you can create an app-specific password. Turn it on at account.apple.com and try again.",
  app_password_required:
    "iCloud does not accept your Apple ID password. Use an app-specific password. Two-factor authentication has to be on to create one.",
  invalid_address: "Use the full iCloud email: @icloud.com, @me.com, or @mac.com.",
  network: "iCloud did not respond. Check the network and try again.",
  email_mismatch:
    "Donexto only reads this account’s mailbox. Use the same iCloud address you signed in with.",
  imap_failed: "iCloud could not be connected. Try again.",
  rate_limited: "Too many attempts. Wait a moment.",
  icloud_credentials_missing:
    "Connect iCloud again. Donexto no longer has the app-specific password.",
};

const fr: Record<IcloudCopyKey, string> = {
  title: "Connecter iCloud",
  intro: "Donexto lit seulement cette boîte, en lecture seule.",
  step1:
    "Sur le compte Apple, activez la validation en deux étapes si elle est coupée.",
  step2:
    "Ouvrez account.apple.com → Connexion et sécurité → Mots de passe pour application.",
  step3:
    "Créez un mot de passe nommé Donexto et copiez-le. Ce n’est pas le mot de passe de l’identifiant Apple.",
  step4:
    "Collez-le ici avec l’adresse iCloud complète (@icloud.com, @me.com ou @mac.com).",
  emailLabel: "Adresse iCloud",
  passwordLabel: "Mot de passe pour application",
  passwordPlaceholder: "xxxx-xxxx-xxxx-xxxx",
  submit: "Connecter iCloud",
  submitting: "Connexion à iCloud…",
  back: "Changer d’adresse",
  privacy:
    "Donexto lit seulement cette boîte. Il ne marque pas les messages comme lus, ne les déplace pas et ne les supprime pas. Vous pouvez révoquer le mot de passe pour application chez Apple à tout moment et déconnecter la boîte ici.",
  showPassword: "Afficher",
  hidePassword: "Masquer",
  wrong_password:
    "iCloud a refusé ce mot de passe pour application. Vérifiez-le ou créez-en un autre sur account.apple.com.",
  two_factor_required:
    "Le compte Apple doit avoir la validation en deux étapes pour créer un mot de passe pour application. Activez-la sur account.apple.com et réessayez.",
  app_password_required:
    "iCloud n’accepte pas le mot de passe de l’identifiant Apple. Utilisez un mot de passe pour application. La validation en deux étapes doit être active pour le créer.",
  invalid_address:
    "Utilisez l’adresse iCloud complète : @icloud.com, @me.com ou @mac.com.",
  network: "iCloud n’a pas répondu. Vérifiez le réseau et réessayez.",
  email_mismatch:
    "Donexto lit seulement la boîte de ce compte. Utilisez la même adresse iCloud.",
  imap_failed: "Impossible de connecter iCloud. Réessayez.",
  rate_limited: "Trop de tentatives. Patientez un instant.",
  icloud_credentials_missing:
    "Reconnectez iCloud. Donexto n’a plus le mot de passe pour application.",
};

const it: Record<IcloudCopyKey, string> = {
  title: "Collega iCloud",
  intro: "Donexto legge solo questa casella, in sola lettura.",
  step1:
    "Nell’account Apple, attiva l’autenticazione a due fattori se non è già attiva.",
  step2:
    "Apri account.apple.com → Accesso e sicurezza → Password specifiche per le app.",
  step3:
    "Crea una password chiamata Donexto e copiala. Non è la password dell’ID Apple.",
  step4:
    "Incollala qui con l’indirizzo iCloud completo (@icloud.com, @me.com o @mac.com).",
  emailLabel: "Email iCloud",
  passwordLabel: "Password specifica per l’app",
  passwordPlaceholder: "xxxx-xxxx-xxxx-xxxx",
  submit: "Collega iCloud",
  submitting: "Collegamento a iCloud…",
  back: "Cambia email",
  privacy:
    "Donexto legge solo questa casella. Non segna i messaggi come letti, non li sposta e non li elimina. Puoi revocare la password dell’app su Apple in qualsiasi momento e scollegare la casella qui.",
  showPassword: "Mostra",
  hidePassword: "Nascondi",
  wrong_password:
    "iCloud non ha accettato questa password per l’app. Controllala o creane un’altra su account.apple.com.",
  two_factor_required:
    "L’account Apple deve avere l’autenticazione a due fattori per creare la password dell’app. Attivala su account.apple.com e riprova.",
  app_password_required:
    "iCloud non accetta la password dell’ID Apple. Usa una password specifica per l’app. Serve l’autenticazione a due fattori per crearla.",
  invalid_address:
    "Usa l’indirizzo iCloud completo: @icloud.com, @me.com o @mac.com.",
  network: "iCloud non ha risposto. Controlla la rete e riprova.",
  imap_failed: "Non è stato possibile collegare iCloud. Riprova.",
  email_mismatch:
    "Donexto legge solo la casella di questo account. Usa lo stesso indirizzo iCloud.",
  rate_limited: "Troppi tentativi. Attendi un momento.",
  icloud_credentials_missing:
    "Ricollega iCloud. Donexto non ha più la password dell’app.",
};

const pt: Record<IcloudCopyKey, string> = {
  title: "Conectar iCloud",
  intro: "O Donexto lê só esta caixa, em somente leitura.",
  step1: "Na conta Apple, ative a verificação em duas etapas se ainda não estiver.",
  step2:
    "Abra account.apple.com → Início de sessão e segurança → Senhas específicas de app.",
  step3:
    "Crie uma senha com o nome Donexto e copie. Não é a senha do ID Apple.",
  step4:
    "Cole aqui junto com o e-mail iCloud completo (@icloud.com, @me.com ou @mac.com).",
  emailLabel: "E-mail iCloud",
  passwordLabel: "Senha específica de app",
  passwordPlaceholder: "xxxx-xxxx-xxxx-xxxx",
  submit: "Conectar iCloud",
  submitting: "Conectando o iCloud…",
  back: "Mudar e-mail",
  privacy:
    "O Donexto só lê esta caixa. Não marca as mensagens como lidas, não as move nem as apaga. Você pode revogar a senha de app na Apple quando quiser e desconectar a caixa aqui.",
  showPassword: "Mostrar",
  hidePassword: "Ocultar",
  wrong_password:
    "O iCloud não aceitou essa senha de app. Confira ou gere outra em account.apple.com.",
  two_factor_required:
    "A conta Apple precisa da verificação em duas etapas para criar a senha de app. Ative em account.apple.com e tente de novo.",
  app_password_required:
    "O iCloud não aceita a senha do ID Apple. Use uma senha específica de app. A verificação em duas etapas precisa estar ativa para criá-la.",
  invalid_address:
    "Use o e-mail iCloud completo: @icloud.com, @me.com ou @mac.com.",
  network: "O iCloud não respondeu. Verifique a rede e tente de novo.",
  email_mismatch:
    "O Donexto só lê a caixa desta conta. Use o mesmo iCloud com que entrou.",
  imap_failed: "Não foi possível conectar o iCloud. Tente de novo.",
  rate_limited: "Tentativas demais. Espere um momento.",
  icloud_credentials_missing:
    "Conecte o iCloud de novo. O Donexto já não tem a senha de app.",
};

const COPY: Record<AppLanguage, Record<IcloudCopyKey, string>> = {
  es,
  en,
  fr,
  it,
  pt,
};

export function icloudText(language: AppLanguage, key: IcloudCopyKey): string {
  return COPY[language][key] || COPY.es[key];
}

export function icloudSteps(language: AppLanguage): string[] {
  return [
    icloudText(language, "step1"),
    icloudText(language, "step2"),
    icloudText(language, "step3"),
    icloudText(language, "step4"),
  ];
}

const FAILURE_KEYS = new Set<IcloudCopyKey>([
  "wrong_password",
  "two_factor_required",
  "app_password_required",
  "invalid_address",
  "network",
  "email_mismatch",
  "imap_failed",
  "rate_limited",
  "icloud_credentials_missing",
]);

export function icloudFailureText(
  language: AppLanguage,
  code: string | undefined,
  fallback: string,
): string {
  if (code && FAILURE_KEYS.has(code as IcloudCopyKey)) {
    return icloudText(language, code as IcloudCopyKey);
  }
  return fallback;
}

export function icloudErrorCode(payload: unknown): string | undefined {
  if (!payload || typeof payload !== "object") {
    return undefined;
  }
  const detail = (payload as { detail?: unknown }).detail;
  if (detail && typeof detail === "object") {
    const code = (detail as { code?: unknown }).code;
    return typeof code === "string" ? code : undefined;
  }
  const code = (payload as { code?: unknown }).code;
  return typeof code === "string" ? code : undefined;
}

export function icloudErrorMessage(payload: unknown): string {
  if (!payload || typeof payload !== "object") {
    return "";
  }
  const detail = (payload as { detail?: unknown }).detail;
  if (typeof detail === "string") {
    return detail;
  }
  if (detail && typeof detail === "object") {
    const message = (detail as { message?: unknown }).message;
    return typeof message === "string" ? message : "";
  }
  const message = (payload as { message?: unknown }).message;
  return typeof message === "string" ? message : "";
}
