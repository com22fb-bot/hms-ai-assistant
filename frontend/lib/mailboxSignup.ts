/**
 * Ruteo de alta por dominio del buzón que el usuario quiere vigilar.
 * Gmail → Google OAuth. Hotmail/Outlook → Azure. Apple → Apple.
 * Yahoo → un paso: te llevamos al sitio de Yahoo (OAuth). No hay clave en Donexto.
 */

export type MailboxConnectMode = "gmail" | "yahoo" | "choose";

export type MailboxSignupProvider =
  | "gmail"
  | "yahoo"
  | "hotmail"
  | "apple"
  | "other";

const GMAIL_DOMAINS = ["gmail.com", "googlemail.com"];

const YAHOO_DOMAINS = [
  "yahoo.com",
  "yahoo.com.mx",
  "yahoo.es",
  "ymail.com",
  "rocketmail.com",
];

const HOTMAIL_DOMAINS = [
  "hotmail.com",
  "hotmail.es",
  "outlook.com",
  "outlook.es",
  "live.com",
  "msn.com",
];

const APPLE_DOMAINS = ["icloud.com", "me.com", "mac.com"];

function emailDomain(email: string): string {
  const at = email.trim().toLowerCase().lastIndexOf("@");
  if (at < 0 || at === email.trim().length - 1) {
    return "";
  }
  return email.trim().toLowerCase().slice(at + 1);
}

function matchesDomain(domain: string, roots: string[]): boolean {
  return roots.some(
    (root) => domain === root || domain.endsWith(`.${root}`),
  );
}

export function resolveMailboxProviderFromEmail(
  email: string,
): MailboxSignupProvider {
  const domain = emailDomain(email);
  if (!domain) {
    return "other";
  }
  if (matchesDomain(domain, GMAIL_DOMAINS)) {
    return "gmail";
  }
  if (matchesDomain(domain, YAHOO_DOMAINS)) {
    return "yahoo";
  }
  if (matchesDomain(domain, HOTMAIL_DOMAINS)) {
    return "hotmail";
  }
  if (matchesDomain(domain, APPLE_DOMAINS)) {
    return "apple";
  }
  return "other";
}

export function isValidSignupEmail(email: string): boolean {
  const clean = email.trim().toLowerCase();
  return clean.includes("@") && emailDomain(clean).includes(".");
}

export function mailboxConnectModeFromEmail(
  email: string,
): MailboxConnectMode {
  const provider = resolveMailboxProviderFromEmail(email);
  if (provider === "gmail") {
    return "gmail";
  }
  if (provider === "yahoo") {
    return "yahoo";
  }
  return "choose";
}
