/**
 * Ruteo de alta por dominio del buzón que el usuario quiere monitorear.
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

export const MICROSOFT_LOGIN_DOMAINS = [
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
] as const;

const HOTMAIL_DOMAINS = [...MICROSOFT_LOGIN_DOMAINS];

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

const TYPO_TLDS = new Set(["cox", "con", "cm", "comm", "cpm"]);

function editDistance(left: string, right: string): number {
  const previous = Array.from({ length: right.length + 1 }, (_, i) => i);
  for (let i = 0; i < left.length; i += 1) {
    const current = [i + 1];
    for (let j = 0; j < right.length; j += 1) {
      current.push(
        Math.min(
          current[j] + 1,
          previous[j + 1] + 1,
          previous[j] + (left[i] === right[j] ? 0 : 1),
        ),
      );
    }
    previous.splice(0, previous.length, ...current);
  }
  return previous[right.length];
}

const KNOWN_DOMAINS = [
  ...GMAIL_DOMAINS,
  ...YAHOO_DOMAINS,
  ...HOTMAIL_DOMAINS,
  ...APPLE_DOMAINS,
];

export function suggestKnownMailbox(email: string): string | null {
  const domain = emailDomain(email);
  const local = email.trim().toLowerCase().split("@")[0] || "";
  if (!domain || !local) {
    return null;
  }
  if (KNOWN_DOMAINS.some((root) => domain === root || domain.endsWith(`.${root}`))) {
    return null;
  }
  const name = domain.includes(".") ? domain.slice(0, domain.lastIndexOf(".")) : domain;
  const tld = domain.includes(".") ? domain.slice(domain.lastIndexOf(".") + 1) : "";
  if (TYPO_TLDS.has(tld) && KNOWN_DOMAINS.includes(`${name}.com`)) {
    return `${local}@${name}.com`;
  }
  let best: string | null = null;
  let bestDistance = 99;
  for (const candidate of KNOWN_DOMAINS) {
    const candName = candidate.split(".")[0] || candidate;
    const distance = Math.min(
      editDistance(domain, candidate),
      editDistance(name, candName),
    );
    if (distance < bestDistance) {
      bestDistance = distance;
      best = candidate;
    }
  }
  if (best && bestDistance <= 2 && name.length >= 5) {
    return `${local}@${best}`;
  }
  return null;
}

export function isKnownActiveMailbox(email: string): boolean {
  const provider = resolveMailboxProviderFromEmail(email);
  return provider === "yahoo" || provider === "hotmail";
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
