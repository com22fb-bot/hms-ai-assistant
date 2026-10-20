/** Aviso mínimo para buzones en needs_reauth (token vencido o revocado). */
export type ReauthStatus = {
  connected?: boolean;
  needs_reauth?: boolean;
  email?: string | null;
  provider?: string | null;
} | null | undefined;

const PROVIDER_NAMES: Record<string, string> = {
  google: "Gmail",
  microsoft: "Outlook",
  yahoo: "Yahoo",
  imap: "Yahoo",
  icloud: "iCloud",
  gmail_imap: "Gmail",
};

export function reauthPrompt(status: ReauthStatus): { title: string; detail: string } | null {
  if (!status || status.connected || !status.needs_reauth) return null;
  const name = PROVIDER_NAMES[String(status.provider || "google")] || "tu correo";
  return {
    title: `Vuelve a conectar ${name}`,
    detail: status.email
      ? `${status.email} perdió la autorización. Reconéctalo para seguir recibiendo correos.`
      : "Tu buzón perdió la autorización. Reconéctalo para seguir recibiendo correos.",
  };
}
