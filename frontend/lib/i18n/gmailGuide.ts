import type { AppLanguage } from "@/lib/i18n/languages";

/** Guía animada para crear la contraseña de aplicación de Google (5 idiomas). */
export type GmailGuideKey =
  | "title" | "sameAccount" | "play" | "pause" | "prev" | "next" | "stepOf" | "show" | "hide"
  | "s1" | "s2" | "s3" | "s4" | "s5" | "s6"
  | "mGoogleAccount" | "mHome" | "mSecurity" | "mTwoStep" | "mTurnOn" | "mOff"
  | "mAppPasswords" | "mAppName" | "mCreate" | "mGenerated" | "mCopy" | "mDone"
  | "mEmail" | "mPassword" | "mConnect";

type Copy = Record<GmailGuideKey, string>;

const es: Copy = {
  title: "Cómo crear la contraseña de aplicación",
  sameAccount: "La contraseña solo funciona con la misma cuenta de Google en la que la creas. Usa ese mismo correo en Donexto.",
  play: "Reproducir", pause: "Pausar", prev: "Anterior", next: "Siguiente", stepOf: "Paso {n} de {total}",
  show: "Ver la guía", hide: "Ocultar la guía",
  s1: "Abre myaccount.google.com y revisa que el correo de arriba sea el mismo que escribes en Donexto.",
  s2: "Da Click en Seguridad → Verificación en dos pasos y actívala.",
  s3: "Ve a myaccount.google.com/apppasswords.",
  s4: "Escribe el nombre Donexto y da Click en Crear.",
  s5: "Copia las 16 letras que muestra Google.",
  s6: "Pégalas en Donexto con el mismo correo y da Click en Conectar Gmail.",
  mGoogleAccount: "Cuenta de Google", mHome: "Inicio", mSecurity: "Seguridad", mTwoStep: "Verificación en dos pasos",
  mTurnOn: "Activar", mOff: "Desactivada", mAppPasswords: "Contraseñas de aplicaciones", mAppName: "Nombre de la app",
  mCreate: "Crear", mGenerated: "Contraseña de aplicación generada", mCopy: "Copiar", mDone: "Listo",
  mEmail: "Correo de Gmail", mPassword: "Contraseña de aplicación", mConnect: "Conectar Gmail",
};

const en: Copy = {
  title: "How to create the app password",
  sameAccount: "The password only works for the same Google Account you create it in. Use that same address in Donexto.",
  play: "Play", pause: "Pause", prev: "Previous", next: "Next", stepOf: "Step {n} of {total}",
  show: "Show the guide", hide: "Hide the guide",
  s1: "Open myaccount.google.com and check the address at the top matches the one you enter in Donexto.",
  s2: "Click Security → 2-Step Verification and turn it on.",
  s3: "Go to myaccount.google.com/apppasswords.",
  s4: "Type the name Donexto and click Create.",
  s5: "Copy the 16 letters Google shows.",
  s6: "Paste them in Donexto with the same address and click Connect Gmail.",
  mGoogleAccount: "Google Account", mHome: "Home", mSecurity: "Security", mTwoStep: "2-Step Verification",
  mTurnOn: "Turn on", mOff: "Off", mAppPasswords: "App passwords", mAppName: "App name",
  mCreate: "Create", mGenerated: "Generated app password", mCopy: "Copy", mDone: "Done",
  mEmail: "Gmail address", mPassword: "App password", mConnect: "Connect Gmail",
};

const fr: Copy = {
  title: "Créer le mot de passe d'application",
  sameAccount: "Le mot de passe ne fonctionne que pour le compte Google où vous le créez. Utilisez cette même adresse dans Donexto.",
  play: "Lire", pause: "Pause", prev: "Précédent", next: "Suivant", stepOf: "Étape {n} sur {total}",
  show: "Voir le guide", hide: "Masquer le guide",
  s1: "Ouvrez myaccount.google.com et vérifiez que l'adresse en haut est celle que vous saisissez dans Donexto.",
  s2: "Cliquez sur Sécurité → Validation en deux étapes et activez-la.",
  s3: "Allez sur myaccount.google.com/apppasswords.",
  s4: "Saisissez le nom Donexto et cliquez sur Créer.",
  s5: "Copiez les 16 lettres affichées par Google.",
  s6: "Collez-les dans Donexto avec la même adresse et cliquez sur Connecter Gmail.",
  mGoogleAccount: "Compte Google", mHome: "Accueil", mSecurity: "Sécurité", mTwoStep: "Validation en deux étapes",
  mTurnOn: "Activer", mOff: "Désactivée", mAppPasswords: "Mots de passe des applications", mAppName: "Nom de l'application",
  mCreate: "Créer", mGenerated: "Mot de passe d'application généré", mCopy: "Copier", mDone: "OK",
  mEmail: "Adresse Gmail", mPassword: "Mot de passe d'application", mConnect: "Connecter Gmail",
};

const it: Copy = {
  title: "Come creare la password per le app",
  sameAccount: "La password funziona solo con lo stesso account Google in cui la crei. Usa lo stesso indirizzo in Donexto.",
  play: "Riproduci", pause: "Pausa", prev: "Indietro", next: "Avanti", stepOf: "Passaggio {n} di {total}",
  show: "Mostra la guida", hide: "Nascondi la guida",
  s1: "Apri myaccount.google.com e controlla che l'indirizzo in alto sia quello che scrivi in Donexto.",
  s2: "Fai clic su Sicurezza → Verifica in due passaggi e attivala.",
  s3: "Vai su myaccount.google.com/apppasswords.",
  s4: "Scrivi il nome Donexto e fai clic su Crea.",
  s5: "Copia le 16 lettere mostrate da Google.",
  s6: "Incollale in Donexto con lo stesso indirizzo e fai clic su Collega Gmail.",
  mGoogleAccount: "Account Google", mHome: "Home", mSecurity: "Sicurezza", mTwoStep: "Verifica in due passaggi",
  mTurnOn: "Attiva", mOff: "Disattivata", mAppPasswords: "Password per le app", mAppName: "Nome app",
  mCreate: "Crea", mGenerated: "Password per l'app generata", mCopy: "Copia", mDone: "Fine",
  mEmail: "Indirizzo Gmail", mPassword: "Password per le app", mConnect: "Collega Gmail",
};

const pt: Copy = {
  title: "Como criar a senha de app",
  sameAccount: "A senha só funciona na mesma Conta do Google em que você a cria. Use esse mesmo e-mail no Donexto.",
  play: "Reproduzir", pause: "Pausar", prev: "Anterior", next: "Próximo", stepOf: "Etapa {n} de {total}",
  show: "Ver o guia", hide: "Ocultar o guia",
  s1: "Abra myaccount.google.com e confira se o e-mail no topo é o mesmo que você digita no Donexto.",
  s2: "Clique em Segurança → Verificação em duas etapas e ative.",
  s3: "Acesse myaccount.google.com/apppasswords.",
  s4: "Digite o nome Donexto e clique em Criar.",
  s5: "Copie as 16 letras que o Google mostra.",
  s6: "Cole no Donexto com o mesmo e-mail e clique em Conectar Gmail.",
  mGoogleAccount: "Conta do Google", mHome: "Início", mSecurity: "Segurança", mTwoStep: "Verificação em duas etapas",
  mTurnOn: "Ativar", mOff: "Desativada", mAppPasswords: "Senhas de app", mAppName: "Nome do app",
  mCreate: "Criar", mGenerated: "Senha de app gerada", mCopy: "Copiar", mDone: "Concluído",
  mEmail: "E-mail do Gmail", mPassword: "Senha de app", mConnect: "Conectar Gmail",
};

const COPY: Record<AppLanguage, Copy> = { es, en, fr, it, pt };

export const GMAIL_GUIDE_STEPS = ["s1", "s2", "s3", "s4", "s5", "s6"] as const;
export const GMAIL_GUIDE_INTERVAL_MS = 5500;

export function gmailGuideText(
  language: AppLanguage,
  key: GmailGuideKey,
  vars: Record<string, string | number> = {},
): string {
  let text = COPY[language]?.[key] || COPY.es[key];
  for (const [name, value] of Object.entries(vars)) text = text.replace(`{${name}}`, String(value));
  return text;
}

/** Siguiente paso del carrusel (circular). */
export function nextGuideStep(current: number, delta: number, total = GMAIL_GUIDE_STEPS.length): number {
  return ((current + delta) % total + total) % total;
}
