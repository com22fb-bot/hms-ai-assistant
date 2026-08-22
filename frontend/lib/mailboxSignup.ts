/**
 * Ruteo de alta por dominio del buzón que el usuario quiere vigilar.
 * Gmail → Google OAuth. Hotmail/Outlook → Azure. Apple → Apple.
 * Yahoo → un paso: te llevamos al sitio de Yahoo (OAuth). No hay clave en Donexto.
 */

export type MailboxConnectMode = "gmail" | "yahoo" | "microsoft" | "choose";

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
]; // México: @yahoo.com.mx usa el mismo OAuth que @yahoo.com

const HOTMAIL_DOMAINS = [
  "hotmail.com",
  "hotmail.es",
  "hotmail.com.mx",
  "outlook.com",
  "outlook.es",
  "outlook.com.mx",
  "live.com",
  "live.com.mx",
  "msn.com",
  "onmicrosoft.com",
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
  const at = clean.lastIndexOf("@");
  if (at <= 0 || at === clean.length - 1) {
    return false;
  }
  const local = clean.slice(0, at);
  const domain = emailDomain(clean);
  if (!local || local.includes(" ")) {
    return false;
  }
  if (!domain.includes(".") || domain.startsWith(".") || domain.endsWith(".")) {
    return false;
  }
  const labels = domain.split(".");
  return labels.length >= 2 && labels.every((label) => label.length > 0);
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
  if (provider === "hotmail") {
    return "microsoft";
  }
  return "choose";
}
