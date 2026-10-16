import type { AppLanguage } from "@/lib/i18n/languages";

/** Motivos que el backend manda en ?donexto=oauth_error&provider=google&reason=… */
export const OAUTH_RETURN_REASONS = [
  "state_invalid",
  "gmail_permission_missing",
  "access_denied",
  "google_rejected",
  "token_failed",
  "gmail_mismatch",
  "connection_failed",
] as const;
export type OAuthReturnReason = (typeof OAUTH_RETURN_REASONS)[number];

type Copy = { title: string; retry: string; close: string } & Record<OAuthReturnReason, string>;

const COPY: Record<AppLanguage, Copy> = {
  es: {
    title: "No pudimos conectar tu Gmail",
    retry: "Intentar de nuevo",
    close: "Cerrar",
    state_invalid: "Esa ventana de Google ya se había usado o caducó (pasa si vuelves a una pestaña vieja o cambias de navegador). Inicia la conexión otra vez desde Donexto.",
    gmail_permission_missing: "Google no nos dio permiso para leer tu correo. Al volver a intentarlo, marca la casilla «Ver tus mensajes de correo electrónico» antes de continuar.",
    access_denied: "Cancelaste la autorización en Google. Puedes intentarlo de nuevo cuando quieras.",
    google_rejected: "Google rechazó la autorización. Inténtalo de nuevo en unos minutos.",
    token_failed: "Google no terminó la autorización. Inicia la conexión otra vez desde Donexto.",
    gmail_mismatch: "Autorizaste un Gmail distinto al de tu cuenta Donexto. Elige el mismo Gmail al intentarlo de nuevo.",
    connection_failed: "Algo falló al conectar tu Gmail. Inténtalo de nuevo; si continúa, escríbenos.",
  },
  en: {
    title: "We couldn't connect your Gmail",
    retry: "Try again",
    close: "Close",
    state_invalid: "That Google window was already used or expired (this happens if you go back to an old tab or switch browsers). Start the connection again from Donexto.",
    gmail_permission_missing: "Google didn't give us permission to read your mail. When you try again, check the box “View your email messages” before continuing.",
    access_denied: "You cancelled the authorization in Google. You can try again anytime.",
    google_rejected: "Google rejected the authorization. Please try again in a few minutes.",
    token_failed: "Google didn't finish the authorization. Start the connection again from Donexto.",
    gmail_mismatch: "You authorized a different Gmail than your Donexto account. Pick the same Gmail when you try again.",
    connection_failed: "Something went wrong connecting your Gmail. Try again; if it keeps happening, contact us.",
  },
  fr: {
    title: "Impossible de connecter votre Gmail",
    retry: "Réessayer",
    close: "Fermer",
    state_invalid: "Cette fenêtre Google a déjà été utilisée ou a expiré (cela arrive si vous revenez à un ancien onglet ou changez de navigateur). Relancez la connexion depuis Donexto.",
    gmail_permission_missing: "Google ne nous a pas autorisés à lire votre courrier. En réessayant, cochez la case « Afficher vos e-mails » avant de continuer.",
    access_denied: "Vous avez annulé l'autorisation dans Google. Vous pouvez réessayer quand vous voulez.",
    google_rejected: "Google a refusé l'autorisation. Réessayez dans quelques minutes.",
    token_failed: "Google n'a pas terminé l'autorisation. Relancez la connexion depuis Donexto.",
    gmail_mismatch: "Vous avez autorisé un autre Gmail que celui de votre compte Donexto. Choisissez le même Gmail en réessayant.",
    connection_failed: "Un problème est survenu lors de la connexion de votre Gmail. Réessayez ; si cela continue, contactez-nous.",
  },
  it: {
    title: "Non siamo riusciti a collegare il tuo Gmail",
    retry: "Riprova",
    close: "Chiudi",
    state_invalid: "Quella finestra di Google era già stata usata o è scaduta (succede se torni a una scheda vecchia o cambi browser). Avvia di nuovo il collegamento da Donexto.",
    gmail_permission_missing: "Google non ci ha dato il permesso di leggere la tua posta. Riprovando, seleziona la casella «Visualizza i tuoi messaggi email» prima di continuare.",
    access_denied: "Hai annullato l'autorizzazione in Google. Puoi riprovare quando vuoi.",
    google_rejected: "Google ha rifiutato l'autorizzazione. Riprova tra qualche minuto.",
    token_failed: "Google non ha completato l'autorizzazione. Avvia di nuovo il collegamento da Donexto.",
    gmail_mismatch: "Hai autorizzato un Gmail diverso da quello del tuo account Donexto. Scegli lo stesso Gmail quando riprovi.",
    connection_failed: "Qualcosa è andato storto nel collegare il tuo Gmail. Riprova; se continua, scrivici.",
  },
  pt: {
    title: "Não conseguimos conectar seu Gmail",
    retry: "Tentar de novo",
    close: "Fechar",
    state_invalid: "Essa janela do Google já tinha sido usada ou expirou (acontece se você volta a uma aba antiga ou troca de navegador). Inicie a conexão de novo pelo Donexto.",
    gmail_permission_missing: "O Google não nos deu permissão para ler seu e-mail. Ao tentar de novo, marque a caixa “Ver suas mensagens de e-mail” antes de continuar.",
    access_denied: "Você cancelou a autorização no Google. Pode tentar de novo quando quiser.",
    google_rejected: "O Google recusou a autorização. Tente de novo em alguns minutos.",
    token_failed: "O Google não concluiu a autorização. Inicie a conexão de novo pelo Donexto.",
    gmail_mismatch: "Você autorizou um Gmail diferente do da sua conta Donexto. Escolha o mesmo Gmail ao tentar de novo.",
    connection_failed: "Algo deu errado ao conectar seu Gmail. Tente de novo; se continuar, fale conosco.",
  },
};

export function oauthReturnReason(raw: string | null): OAuthReturnReason {
  return (OAUTH_RETURN_REASONS as readonly string[]).includes(raw || "")
    ? (raw as OAuthReturnReason)
    : "connection_failed";
}

export function oauthReturnText(language: AppLanguage, key: keyof Copy): string {
  return (COPY[language] ?? COPY.es)[key];
}
