import type { AppLanguage } from "@/lib/i18n/languages";

/** Gmail por IMAP con contraseña de aplicación. Texto corto y funcional. */
export type GmailImapCopyKey =
  | "title"
  | "intro"
  | "step1Title"
  | "step1Body"
  | "step1Cta"
  | "step2Title"
  | "step2Body"
  | "step2Cta"
  | "step3Title"
  | "emailLabel"
  | "passwordLabel"
  | "passwordPlaceholder"
  | "submit"
  | "submitting"
  | "showPassword"
  | "hidePassword"
  | "privacy"
  | "useOauth"
  | "useOauthHint"
  | "back"
  | "wrong_password"
  | "app_password_required"
  | "imap_disabled"
  | "web_login_required"
  | "invalid_characters"
  | "invalid_address"
  | "network"
  | "email_mismatch"
  | "imap_failed"
  | "rate_limited"
  | "gmail_imap_credentials_missing";

const es: Record<GmailImapCopyKey, string> = {
  title: "Conecta Gmail con contraseña de aplicación",
  intro: "Solo lectura. Toma 2 minutos.",
  step1Title: "1. Activa la verificación en dos pasos",
  step1Body: "Da Click en el botón, entra con tu cuenta de Google y actívala. Si ya está activa, sigue al paso 2.",
  step1Cta: "Abrir verificación en dos pasos",
  step2Title: "2. Crea la contraseña de aplicación",
  step2Body: "Da Click en el botón, escribe Donexto como nombre y da Click en Crear. Copia las 16 letras.",
  step2Cta: "Abrir contraseñas de aplicación",
  step3Title: "3. Pégala aquí",
  emailLabel: "Correo de Gmail",
  passwordLabel: "Contraseña de aplicación (16 letras)",
  passwordPlaceholder: "xxxx xxxx xxxx xxxx",
  submit: "Conectar Gmail",
  submitting: "Comprobando con Gmail…",
  showPassword: "Mostrar",
  hidePassword: "Ocultar",
  privacy: "Se guarda cifrada. Puedes revocarla en tu cuenta de Google cuando quieras.",
  useOauth: "Conectar con Google (OAuth)",
  useOauthHint: "Opción alternativa. Google puede mostrar un aviso de app no verificada.",
  back: "Volver",
  wrong_password: "Gmail no aceptó esa contraseña de aplicación para este correo. Créala con la sesión de Google de este mismo correo.",
  web_login_required: "Google pide confirmar el acceso. Entra a tu cuenta de Google, revisa el aviso de seguridad y vuelve a intentar.",
  invalid_characters: "La contraseña de aplicación solo lleva letras. Cópiala otra vez desde Google.",
  app_password_required: "Usa una contraseña de aplicación de 16 letras, no tu contraseña de Google.",
  imap_disabled: "IMAP está desactivado en esta cuenta. Si es de trabajo o escuela, pide al administrador que lo active.",
  invalid_address: "Escribe el correo completo de Gmail.",
  network: "Gmail no respondió. Inténtalo de nuevo.",
  email_mismatch: "Usa el mismo Gmail con el que entraste a Donexto.",
  imap_failed: "No fue posible conectar Gmail. Inténtalo de nuevo.",
  rate_limited: "Demasiados intentos. Espera un momento.",
  gmail_imap_credentials_missing: "Vuelve a conectar Gmail.",
};

const en: Record<GmailImapCopyKey, string> = {
  title: "Connect Gmail with an app password",
  intro: "Read-only. Takes 2 minutes.",
  step1Title: "1. Turn on 2-Step Verification",
  step1Body: "Click the button, sign in to your Google Account and turn it on. If it is already on, go to step 2.",
  step1Cta: "Open 2-Step Verification",
  step2Title: "2. Create the app password",
  step2Body: "Click the button, type Donexto as the name and click Create. Copy the 16 letters.",
  step2Cta: "Open app passwords",
  step3Title: "3. Paste it here",
  emailLabel: "Gmail address",
  passwordLabel: "App password (16 letters)",
  passwordPlaceholder: "xxxx xxxx xxxx xxxx",
  submit: "Connect Gmail",
  submitting: "Checking with Gmail…",
  showPassword: "Show",
  hidePassword: "Hide",
  privacy: "Stored encrypted. You can revoke it in your Google Account at any time.",
  useOauth: "Connect with Google (OAuth)",
  useOauthHint: "Alternative option. Google may show an unverified app warning.",
  back: "Back",
  wrong_password: "Gmail did not accept that app password for this address. Create it while signed in to Google with this same address.",
  web_login_required: "Google wants you to confirm access. Open your Google Account, check the security alert and try again.",
  invalid_characters: "App passwords only have letters. Copy it again from Google.",
  app_password_required: "Use a 16-letter app password, not your Google password.",
  imap_disabled: "IMAP is turned off for this account. For work or school accounts, ask your admin to turn it on.",
  invalid_address: "Enter your full Gmail address.",
  network: "Gmail did not respond. Try again.",
  email_mismatch: "Use the same Gmail you signed in to Donexto with.",
  imap_failed: "Could not connect Gmail. Try again.",
  rate_limited: "Too many attempts. Wait a moment.",
  gmail_imap_credentials_missing: "Connect Gmail again.",
};

const fr: Record<GmailImapCopyKey, string> = {
  title: "Connecter Gmail avec un mot de passe d'application",
  intro: "Lecture seule. 2 minutes.",
  step1Title: "1. Activez la validation en deux étapes",
  step1Body: "Cliquez sur le bouton, connectez-vous à votre compte Google et activez-la. Si elle est déjà active, passez à l'étape 2.",
  step1Cta: "Ouvrir la validation en deux étapes",
  step2Title: "2. Créez le mot de passe d'application",
  step2Body: "Cliquez sur le bouton, saisissez Donexto comme nom puis cliquez sur Créer. Copiez les 16 lettres.",
  step2Cta: "Ouvrir les mots de passe d'application",
  step3Title: "3. Collez-le ici",
  emailLabel: "Adresse Gmail",
  passwordLabel: "Mot de passe d'application (16 lettres)",
  passwordPlaceholder: "xxxx xxxx xxxx xxxx",
  submit: "Connecter Gmail",
  submitting: "Vérification avec Gmail…",
  showPassword: "Afficher",
  hidePassword: "Masquer",
  privacy: "Enregistré chiffré. Vous pouvez le révoquer dans votre compte Google à tout moment.",
  useOauth: "Se connecter avec Google (OAuth)",
  useOauthHint: "Option alternative. Google peut afficher un avertissement d'application non validée.",
  back: "Retour",
  wrong_password: "Gmail a refusé ce mot de passe d'application pour cette adresse. Créez-le en étant connecté à Google avec cette même adresse.",
  web_login_required: "Google demande de confirmer l'accès. Ouvrez votre compte Google, vérifiez l'alerte de sécurité et réessayez.",
  invalid_characters: "Le mot de passe d'application ne contient que des lettres. Copiez-le à nouveau depuis Google.",
  app_password_required: "Utilisez un mot de passe d'application de 16 lettres, pas votre mot de passe Google.",
  imap_disabled: "IMAP est désactivé pour ce compte. Pour un compte professionnel ou scolaire, demandez à l'administrateur de l'activer.",
  invalid_address: "Saisissez l'adresse Gmail complète.",
  network: "Gmail ne répond pas. Réessayez.",
  email_mismatch: "Utilisez le même Gmail que pour Donexto.",
  imap_failed: "Impossible de connecter Gmail. Réessayez.",
  rate_limited: "Trop de tentatives. Patientez un instant.",
  gmail_imap_credentials_missing: "Reconnectez Gmail.",
};

const it: Record<GmailImapCopyKey, string> = {
  title: "Collega Gmail con una password per le app",
  intro: "Sola lettura. Bastano 2 minuti.",
  step1Title: "1. Attiva la verifica in due passaggi",
  step1Body: "Fai clic sul pulsante, accedi al tuo account Google e attivala. Se è già attiva, vai al passaggio 2.",
  step1Cta: "Apri la verifica in due passaggi",
  step2Title: "2. Crea la password per le app",
  step2Body: "Fai clic sul pulsante, scrivi Donexto come nome e fai clic su Crea. Copia le 16 lettere.",
  step2Cta: "Apri le password per le app",
  step3Title: "3. Incollala qui",
  emailLabel: "Indirizzo Gmail",
  passwordLabel: "Password per le app (16 lettere)",
  passwordPlaceholder: "xxxx xxxx xxxx xxxx",
  submit: "Collega Gmail",
  submitting: "Verifica con Gmail…",
  showPassword: "Mostra",
  hidePassword: "Nascondi",
  privacy: "Salvata cifrata. Puoi revocarla dal tuo account Google quando vuoi.",
  useOauth: "Collega con Google (OAuth)",
  useOauthHint: "Opzione alternativa. Google può mostrare un avviso di app non verificata.",
  back: "Indietro",
  wrong_password: "Gmail non ha accettato questa password per le app per questo indirizzo. Creala con l'accesso a Google di questo stesso indirizzo.",
  web_login_required: "Google chiede di confermare l'accesso. Apri il tuo account Google, controlla l'avviso di sicurezza e riprova.",
  invalid_characters: "La password per le app contiene solo lettere. Copiala di nuovo da Google.",
  app_password_required: "Usa una password per le app di 16 lettere, non la password di Google.",
  imap_disabled: "IMAP è disattivato per questo account. Se è di lavoro o scuola, chiedi all'amministratore di attivarlo.",
  invalid_address: "Inserisci l'indirizzo Gmail completo.",
  network: "Gmail non risponde. Riprova.",
  email_mismatch: "Usa lo stesso Gmail con cui sei entrato in Donexto.",
  imap_failed: "Impossibile collegare Gmail. Riprova.",
  rate_limited: "Troppi tentativi. Attendi un momento.",
  gmail_imap_credentials_missing: "Collega di nuovo Gmail.",
};

const pt: Record<GmailImapCopyKey, string> = {
  title: "Conectar o Gmail com senha de app",
  intro: "Somente leitura. Leva 2 minutos.",
  step1Title: "1. Ative a verificação em duas etapas",
  step1Body: "Clique no botão, entre na sua Conta do Google e ative. Se já estiver ativa, vá para a etapa 2.",
  step1Cta: "Abrir verificação em duas etapas",
  step2Title: "2. Crie a senha de app",
  step2Body: "Clique no botão, digite Donexto como nome e clique em Criar. Copie as 16 letras.",
  step2Cta: "Abrir senhas de app",
  step3Title: "3. Cole aqui",
  emailLabel: "E-mail do Gmail",
  passwordLabel: "Senha de app (16 letras)",
  passwordPlaceholder: "xxxx xxxx xxxx xxxx",
  submit: "Conectar Gmail",
  submitting: "Verificando com o Gmail…",
  showPassword: "Mostrar",
  hidePassword: "Ocultar",
  privacy: "Salva criptografada. Você pode revogá-la na sua Conta do Google quando quiser.",
  useOauth: "Conectar com o Google (OAuth)",
  useOauthHint: "Opção alternativa. O Google pode mostrar um aviso de app não verificado.",
  back: "Voltar",
  wrong_password: "O Gmail não aceitou essa senha de app para este e-mail. Crie-a com a sessão do Google deste mesmo e-mail.",
  web_login_required: "O Google pede para confirmar o acesso. Abra sua Conta do Google, veja o alerta de segurança e tente de novo.",
  invalid_characters: "A senha de app só tem letras. Copie de novo no Google.",
  app_password_required: "Use uma senha de app de 16 letras, não a sua senha do Google.",
  imap_disabled: "O IMAP está desativado nesta conta. Se for de trabalho ou escola, peça ao administrador para ativar.",
  invalid_address: "Digite o e-mail completo do Gmail.",
  network: "O Gmail não respondeu. Tente de novo.",
  email_mismatch: "Use o mesmo Gmail com que entrou no Donexto.",
  imap_failed: "Não foi possível conectar o Gmail. Tente de novo.",
  rate_limited: "Muitas tentativas. Aguarde um momento.",
  gmail_imap_credentials_missing: "Conecte o Gmail de novo.",
};

const COPY: Record<AppLanguage, Record<GmailImapCopyKey, string>> = { es, en, fr, it, pt };

export const GOOGLE_TWO_STEP_URL = "https://myaccount.google.com/signinoptions/twosv";
export const GOOGLE_APP_PASSWORDS_URL = "https://myaccount.google.com/apppasswords";

export function gmailImapText(language: AppLanguage, key: GmailImapCopyKey): string {
  return COPY[language]?.[key] || COPY.es[key];
}

const FAILURE_KEYS = new Set<GmailImapCopyKey>([
  "wrong_password",
  "app_password_required",
  "imap_disabled",
  "web_login_required",
  "invalid_characters",
  "invalid_address",
  "network",
  "email_mismatch",
  "imap_failed",
  "rate_limited",
  "gmail_imap_credentials_missing",
]);

/** Mensaje traducido por código; nunca el detalle crudo del backend. */
export function gmailImapFailureText(language: AppLanguage, code: string | undefined): string {
  if (code && FAILURE_KEYS.has(code as GmailImapCopyKey)) {
    return gmailImapText(language, code as GmailImapCopyKey);
  }
  return gmailImapText(language, "imap_failed");
}
