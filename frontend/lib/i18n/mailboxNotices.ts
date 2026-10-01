import type { AppLanguage } from "@/lib/i18n/languages";

export type MailboxNoticeKey =
  | "yahooTitle"
  | "yahooIntro"
  | "yahooStep1"
  | "yahooStep2"
  | "yahooStep3"
  | "yahooStep4"
  | "yahooEmail"
  | "yahooPassword"
  | "yahooPasswordPlaceholder"
  | "yahooShow"
  | "yahooHide"
  | "yahooSubmit"
  | "yahooSubmitting"
  | "yahooPrivacy"
  | "yahooBack"
  | "gmailTitle"
  | "gmailIntro"
  | "gmailStep1"
  | "gmailStep2"
  | "gmailStep3"
  | "gmailStep4"
  | "gmailEarly"
  | "gmailPrivacy"
  | "gmailSubmit"
  | "gmailSubmitting"
  | "gmailBack"
  | "gmailSetupLead"
  | "wrong_password"
  | "app_password_required"
  | "invalid_address"
  | "network"
  | "email_mismatch"
  | "imap_failed"
  | "rate_limited"
  | "yahoo_credentials_missing";

const es: Record<MailboxNoticeKey, string> = {
  yahooTitle: "Conecta Yahoo",
  yahooIntro:
    "Conexión directa con Yahoo mediante contraseña de app, en espera de la autorización oficial de Yahoo. Solo lectura y revocable cuando quieras.",
  yahooStep1: "Entra a la seguridad de tu cuenta Yahoo.",
  yahooStep2: "Elige Generar contraseña de app. Hace falta la verificación en dos pasos.",
  yahooStep3: "Copia la contraseña de app (16 letras o números).",
  yahooStep4: "Pégala aquí con tu correo Yahoo completo.",
  yahooEmail: "Correo Yahoo",
  yahooPassword: "Contraseña de app",
  yahooPasswordPlaceholder: "xxxx xxxx xxxx xxxx",
  yahooShow: "Mostrar",
  yahooHide: "Ocultar",
  yahooSubmit: "Conectar Yahoo",
  yahooSubmitting: "Conectando Yahoo…",
  yahooPrivacy:
    "Donexto solo lee este buzón. No marca leído, no mueve y no borra. Puedes revocar la contraseña de app en Yahoo cuando quieras y desconectar el buzón aquí.",
  yahooBack: "Cambiar correo",
  gmailTitle: "Conecta Gmail",
  gmailIntro:
    "Gmail se abre con Google, en solo lectura. La app de Donexto todavía no está verificada por Google.",
  gmailStep1: "Google puede decir «Google no ha verificado esta app».",
  gmailStep2: "Toca Avanzado.",
  gmailStep3: "Toca Ir a Donexto (no seguro).",
  gmailStep4:
    "Es normal mientras Google revisa Donexto. El acceso es solo lectura y se revoca en myaccount.google.com/permissions.",
  gmailEarly:
    "Gmail está en acceso anticipado, con lugares limitados. Google limita las apps no verificadas a 100 usuarios.",
  gmailPrivacy:
    "Donexto pide el permiso gmail.readonly. No marca leído, no mueve y no borra. Después llega un correo de Donexto para confirmar la cuenta.",
  gmailSubmit: "Continuar a Google",
  gmailSubmitting: "Abriendo Google…",
  gmailBack: "Cambiar correo",
  gmailSetupLead:
    "Gmail todavía no está configurado en el servidor. En Railway hacen falta estas variables, sin inventar valores:",
  wrong_password:
    "Yahoo no aceptó esa contraseña de app. Revísala o genera otra en la seguridad de la cuenta.",
  app_password_required:
    "Yahoo no acepta la contraseña de la cuenta. Genera una contraseña de app en la seguridad de Yahoo.",
  invalid_address: "Usa un correo Yahoo (@yahoo.com, @yahoo.com.mx, @ymail.com o @rocketmail.com).",
  network: "Yahoo no respondió. Revisa la red e inténtalo de nuevo.",
  email_mismatch: "Donexto solo lee el correo de esta cuenta. Usa el mismo Yahoo con el que entraste.",
  imap_failed: "No fue posible conectar Yahoo. Inténtalo de nuevo.",
  rate_limited: "Demasiados intentos seguidos. Espera un momento.",
  yahoo_credentials_missing: "Vuelve a conectar Yahoo. Donexto ya no tiene la contraseña de app.",
};

const en: Record<MailboxNoticeKey, string> = {
  yahooTitle: "Connect Yahoo",
  yahooIntro:
    "Direct Yahoo connection with an app password, while Yahoo’s official mail permission is still pending. Read-only, and you can revoke it anytime.",
  yahooStep1: "Open Yahoo Account Security.",
  yahooStep2: "Choose Generate app password. Two-step verification has to be on.",
  yahooStep3: "Copy the app password (16 letters or numbers).",
  yahooStep4: "Paste it here with your full Yahoo email.",
  yahooEmail: "Yahoo email",
  yahooPassword: "App password",
  yahooPasswordPlaceholder: "xxxx xxxx xxxx xxxx",
  yahooShow: "Show",
  yahooHide: "Hide",
  yahooSubmit: "Connect Yahoo",
  yahooSubmitting: "Connecting Yahoo…",
  yahooPrivacy:
    "Donexto only reads this mailbox. It does not mark mail as read, move it, or delete it. You can revoke the app password at Yahoo anytime and disconnect the mailbox here.",
  yahooBack: "Change email",
  gmailTitle: "Connect Gmail",
  gmailIntro:
    "Gmail opens with Google, read-only. Google has not verified the Donexto app yet.",
  gmailStep1: "Google may say “Google hasn’t verified this app”.",
  gmailStep2: "Tap Advanced.",
  gmailStep3: "Tap Go to Donexto (unsafe).",
  gmailStep4:
    "That is normal while Google reviews Donexto. Access is read-only and you can revoke it at myaccount.google.com/permissions.",
  gmailEarly:
    "Gmail is in early access with limited spots. Google caps unverified apps at 100 users.",
  gmailPrivacy:
    "Donexto asks for the gmail.readonly permission. It does not mark mail as read, move it, or delete it. A Donexto email still has to confirm the account.",
  gmailSubmit: "Continue to Google",
  gmailSubmitting: "Opening Google…",
  gmailBack: "Change email",
  gmailSetupLead:
    "Gmail is not configured on the server yet. Railway needs these variables. Do not invent values:",
  wrong_password:
    "Yahoo rejected that app password. Check it or create a new one in Yahoo Account Security.",
  app_password_required:
    "Yahoo does not accept your account password. Generate an app password in Yahoo Account Security.",
  invalid_address: "Use a Yahoo email (@yahoo.com, @yahoo.com.mx, @ymail.com, or @rocketmail.com).",
  network: "Yahoo did not respond. Check the network and try again.",
  email_mismatch: "Donexto only reads this account’s mailbox. Use the same Yahoo address you signed in with.",
  imap_failed: "Yahoo could not be connected. Try again.",
  rate_limited: "Too many attempts. Wait a moment.",
  yahoo_credentials_missing: "Connect Yahoo again. Donexto no longer has the app password.",
};

const fr: Record<MailboxNoticeKey, string> = {
  yahooTitle: "Connecter Yahoo",
  yahooIntro:
    "Connexion directe à Yahoo avec un mot de passe d’application, en attendant l’autorisation officielle de Yahoo. Lecture seule, révocable quand vous voulez.",
  yahooStep1: "Ouvrez la sécurité du compte Yahoo.",
  yahooStep2: "Choisissez Générer un mot de passe d’application. La validation en deux étapes doit être active.",
  yahooStep3: "Copiez le mot de passe d’application (16 lettres ou chiffres).",
  yahooStep4: "Collez-le ici avec l’adresse Yahoo complète.",
  yahooEmail: "Adresse Yahoo",
  yahooPassword: "Mot de passe d’application",
  yahooPasswordPlaceholder: "xxxx xxxx xxxx xxxx",
  yahooShow: "Afficher",
  yahooHide: "Masquer",
  yahooSubmit: "Connecter Yahoo",
  yahooSubmitting: "Connexion à Yahoo…",
  yahooPrivacy:
    "Donexto lit seulement cette boîte. Il ne marque pas comme lu, ne déplace pas et ne supprime pas. Vous pouvez révoquer le mot de passe chez Yahoo et déconnecter la boîte ici.",
  yahooBack: "Changer d’adresse",
  gmailTitle: "Connecter Gmail",
  gmailIntro:
    "Gmail s’ouvre avec Google, en lecture seule. Google n’a pas encore vérifié l’app Donexto.",
  gmailStep1: "Google peut afficher « Google n’a pas validé cette appli ».",
  gmailStep2: "Touchez Paramètres avancés.",
  gmailStep3: "Touchez Accéder à Donexto (non sécurisé).",
  gmailStep4:
    "C’est normal pendant l’examen de Google. L’accès est en lecture seule et se révoque sur myaccount.google.com/permissions.",
  gmailEarly:
    "Gmail est en accès anticipé, avec des places limitées. Google limite les apps non vérifiées à 100 utilisateurs.",
  gmailPrivacy:
    "Donexto demande l’autorisation gmail.readonly. Il ne marque pas comme lu, ne déplace pas et ne supprime pas. Un e-mail Donexto confirme encore le compte.",
  gmailSubmit: "Continuer vers Google",
  gmailSubmitting: "Ouverture de Google…",
  gmailBack: "Changer d’adresse",
  gmailSetupLead:
    "Gmail n’est pas encore configuré sur le serveur. Railway a besoin de ces variables, sans inventer de valeurs :",
  wrong_password:
    "Yahoo a refusé ce mot de passe d’application. Vérifiez-le ou créez-en un autre.",
  app_password_required:
    "Yahoo n’accepte pas le mot de passe du compte. Générez un mot de passe d’application.",
  invalid_address: "Utilisez une adresse Yahoo (@yahoo.com, @yahoo.com.mx, @ymail.com ou @rocketmail.com).",
  network: "Yahoo n’a pas répondu. Vérifiez le réseau et réessayez.",
  email_mismatch: "Donexto lit seulement la boîte de ce compte. Utilisez la même adresse Yahoo.",
  imap_failed: "Impossible de connecter Yahoo. Réessayez.",
  rate_limited: "Trop de tentatives. Attendez un moment.",
  yahoo_credentials_missing: "Reconnectez Yahoo. Donexto n’a plus le mot de passe d’application.",
};

const it: Record<MailboxNoticeKey, string> = {
  yahooTitle: "Collega Yahoo",
  yahooIntro:
    "Connessione diretta a Yahoo con una password per l’app, in attesa dell’autorizzazione ufficiale di Yahoo. Sola lettura, revocabile quando vuoi.",
  yahooStep1: "Apri la sicurezza dell’account Yahoo.",
  yahooStep2: "Scegli Genera password per l’app. Serve la verifica in due passaggi.",
  yahooStep3: "Copia la password per l’app (16 lettere o numeri).",
  yahooStep4: "Incollala qui con l’indirizzo Yahoo completo.",
  yahooEmail: "Email Yahoo",
  yahooPassword: "Password per l’app",
  yahooPasswordPlaceholder: "xxxx xxxx xxxx xxxx",
  yahooShow: "Mostra",
  yahooHide: "Nascondi",
  yahooSubmit: "Collega Yahoo",
  yahooSubmitting: "Collegamento a Yahoo…",
  yahooPrivacy:
    "Donexto legge solo questa casella. Non segna come letto, non sposta e non elimina. Puoi revocare la password su Yahoo e scollegare la casella qui.",
  yahooBack: "Cambia email",
  gmailTitle: "Collega Gmail",
  gmailIntro:
    "Gmail si apre con Google, in sola lettura. Google non ha ancora verificato l’app Donexto.",
  gmailStep1: "Google può dire «Google non ha verificato questa app».",
  gmailStep2: "Tocca Avanzate.",
  gmailStep3: "Tocca Vai a Donexto (non sicuro).",
  gmailStep4:
    "È normale mentre Google esamina Donexto. L’accesso è in sola lettura e si revoca su myaccount.google.com/permissions.",
  gmailEarly:
    "Gmail è in accesso anticipato, con posti limitati. Google limita le app non verificate a 100 utenti.",
  gmailPrivacy:
    "Donexto chiede il permesso gmail.readonly. Non segna come letto, non sposta e non elimina. Un’email Donexto conferma ancora l’account.",
  gmailSubmit: "Continua su Google",
  gmailSubmitting: "Apertura di Google…",
  gmailBack: "Cambia email",
  gmailSetupLead:
    "Gmail non è ancora configurato sul server. Su Railway servono queste variabili, senza inventare valori:",
  wrong_password:
    "Yahoo non ha accettato questa password per l’app. Controllala o creane un’altra.",
  app_password_required:
    "Yahoo non accetta la password dell’account. Genera una password per l’app.",
  invalid_address: "Usa un indirizzo Yahoo (@yahoo.com, @yahoo.com.mx, @ymail.com o @rocketmail.com).",
  network: "Yahoo non ha risposto. Controlla la rete e riprova.",
  email_mismatch: "Donexto legge solo la casella di questo account. Usa lo stesso indirizzo Yahoo.",
  imap_failed: "Non è stato possibile collegare Yahoo. Riprova.",
  rate_limited: "Troppi tentativi. Attendi un momento.",
  yahoo_credentials_missing: "Ricollega Yahoo. Donexto non ha più la password dell’app.",
};

const pt: Record<MailboxNoticeKey, string> = {
  yahooTitle: "Conectar o Yahoo",
  yahooIntro:
    "Conexão direta com o Yahoo por senha de app, enquanto a autorização oficial do Yahoo não chega. Somente leitura e revogável quando quiser.",
  yahooStep1: "Abra a segurança da conta Yahoo.",
  yahooStep2: "Escolha Gerar senha de app. A verificação em duas etapas precisa estar ativa.",
  yahooStep3: "Copie a senha de app (16 letras ou números).",
  yahooStep4: "Cole aqui com o e-mail Yahoo completo.",
  yahooEmail: "E-mail Yahoo",
  yahooPassword: "Senha de app",
  yahooPasswordPlaceholder: "xxxx xxxx xxxx xxxx",
  yahooShow: "Mostrar",
  yahooHide: "Ocultar",
  yahooSubmit: "Conectar o Yahoo",
  yahooSubmitting: "Conectando o Yahoo…",
  yahooPrivacy:
    "A Donexto só lê esta caixa. Não marca como lido, não move e não apaga. Você pode revogar a senha no Yahoo e desconectar a caixa aqui.",
  yahooBack: "Trocar e-mail",
  gmailTitle: "Conectar o Gmail",
  gmailIntro:
    "O Gmail abre com o Google, em somente leitura. O Google ainda não verificou o app Donexto.",
  gmailStep1: "O Google pode dizer «O Google não verificou este app».",
  gmailStep2: "Toque em Avançado.",
  gmailStep3: "Toque em Ir para Donexto (não seguro).",
  gmailStep4:
    "É normal enquanto o Google analisa a Donexto. O acesso é somente leitura e se revoga em myaccount.google.com/permissions.",
  gmailEarly:
    "O Gmail está em acesso antecipado, com vagas limitadas. O Google limita apps não verificados a 100 usuários.",
  gmailPrivacy:
    "A Donexto pede a permissão gmail.readonly. Não marca como lido, não move e não apaga. Um e-mail da Donexto ainda confirma a conta.",
  gmailSubmit: "Continuar para o Google",
  gmailSubmitting: "Abrindo o Google…",
  gmailBack: "Trocar e-mail",
  gmailSetupLead:
    "O Gmail ainda não está configurado no servidor. No Railway faltam estas variáveis, sem inventar valores:",
  wrong_password:
    "O Yahoo não aceitou essa senha de app. Confira ou gere outra na segurança da conta.",
  app_password_required:
    "O Yahoo não aceita a senha da conta. Gere uma senha de app na segurança do Yahoo.",
  invalid_address: "Use um e-mail Yahoo (@yahoo.com, @yahoo.com.mx, @ymail.com ou @rocketmail.com).",
  network: "O Yahoo não respondeu. Verifique a rede e tente de novo.",
  email_mismatch: "A Donexto só lê o e-mail desta conta. Use o mesmo Yahoo com o qual entrou.",
  imap_failed: "Não foi possível conectar o Yahoo. Tente de novo.",
  rate_limited: "Muitas tentativas seguidas. Espere um momento.",
  yahoo_credentials_missing: "Conecte o Yahoo de novo. A Donexto já não tem a senha de app.",
};

const COPY: Record<AppLanguage, Record<MailboxNoticeKey, string>> = {
  es,
  en,
  fr,
  it,
  pt,
};

const GOOGLE_ENV_NAMES = [
  "GOOGLE_CLIENT_ID",
  "GOOGLE_CLIENT_SECRET",
  "GOOGLE_REDIRECT_URI",
] as const;

const FAILURE_KEYS = new Set<MailboxNoticeKey>([
  "wrong_password",
  "app_password_required",
  "invalid_address",
  "network",
  "email_mismatch",
  "imap_failed",
  "rate_limited",
  "yahoo_credentials_missing",
]);

export function mailboxNoticeText(
  language: AppLanguage,
  key: MailboxNoticeKey,
): string {
  return COPY[language][key] || COPY.es[key];
}

export function yahooSteps(language: AppLanguage): string[] {
  return [
    mailboxNoticeText(language, "yahooStep1"),
    mailboxNoticeText(language, "yahooStep2"),
    mailboxNoticeText(language, "yahooStep3"),
    mailboxNoticeText(language, "yahooStep4"),
  ];
}

export function gmailSteps(language: AppLanguage): string[] {
  return [
    mailboxNoticeText(language, "gmailStep1"),
    mailboxNoticeText(language, "gmailStep2"),
    mailboxNoticeText(language, "gmailStep3"),
    mailboxNoticeText(language, "gmailStep4"),
  ];
}

export function yahooFailureText(
  language: AppLanguage,
  code: string | undefined,
  fallback: string,
): string {
  if (code && FAILURE_KEYS.has(code as MailboxNoticeKey)) {
    return mailboxNoticeText(language, code as MailboxNoticeKey);
  }
  return fallback;
}

export function noticeErrorCode(payload: unknown): string | undefined {
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

export function noticeErrorMessage(payload: unknown): string {
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

export function missingGoogleEnvNames(payload: unknown): string[] {
  if (!payload || typeof payload !== "object") {
    return [...GOOGLE_ENV_NAMES];
  }
  const detail = (payload as { detail?: unknown }).detail;
  const source = detail && typeof detail === "object" ? detail : payload;
  const listed = (source as { missing_variables?: unknown }).missing_variables;
  if (!Array.isArray(listed)) {
    return [...GOOGLE_ENV_NAMES];
  }
  const names = listed.filter(
    (item): item is string =>
      typeof item === "string" && GOOGLE_ENV_NAMES.includes(item as (typeof GOOGLE_ENV_NAMES)[number]),
  );
  return names.length > 0 ? names : [...GOOGLE_ENV_NAMES];
}

export function gmailSetupText(language: AppLanguage, missing: string[]): string {
  const names = (missing.length > 0 ? missing : [...GOOGLE_ENV_NAMES]).join(", ");
  return [
    mailboxNoticeText(language, "gmailSetupLead"),
    names,
    "Google Cloud: OAuth consent screen published In production; scope https://www.googleapis.com/auth/gmail.readonly; authorized JavaScript origin https://app.donexto.com; authorized redirect URI = GOOGLE_REDIRECT_URI (Railway callback /auth/google/callback).",
  ].join(" ");
}
