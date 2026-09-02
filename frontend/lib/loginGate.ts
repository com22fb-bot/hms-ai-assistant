export type AuthGateIntent = "login" | "signup";
export type AuthGateNext =
  | "provider_login"
  | "confirm_first_time"
  | "fix_domain"
  | "coming_soon_gmail"
  | "coming_soon_yahoo"
  | "coming_soon_icloud"
  | "waitlist"
  | "unsupported_imap_domain"
  | "pending_review"
  | "unsupported"
  | "icloud_unavailable";

export type AuthGateOAuth = "google" | "azure" | "apple" | "yahoo";

function comingSoonFromNext(next?: string, provider?: string): AuthGateNext | null {
  if (next === "coming_soon_gmail" || next === "coming_soon_yahoo" || next === "coming_soon_icloud") {
    return next;
  }
  if (next === "pending_review") {
    if (provider === "yahoo") return "coming_soon_yahoo";
    if (provider === "apple") return "coming_soon_icloud";
    return "coming_soon_gmail";
  }
  return null;
}

/**
 * Email-first gate: one Continuar.
 * Existence + routing come from POST /auth/login/resolve
 * (`{ exists, next, provider, message }`).
 * Hotmail/Outlook/M365 can enter and we can read mail.
 * Gmail/Yahoo/iCloud first-time go to waitlist; existing testers
 * still get identity login.
 */
export function gateNextAfterResolve(
  _intent: AuthGateIntent,
  exists: boolean,
  next?: string,
  provider?: string,
): AuthGateNext {
  if (provider === "apple" || next === "apple_oauth" || next === "coming_soon_icloud") {
    if (exists && next === "apple_oauth") {
      return "icloud_unavailable";
    }
    return "coming_soon_icloud";
  }
  if (next === "fix_domain" || next === "typo" || next === "invalid_domain") {
    return "fix_domain";
  }
  if (next === "unsupported_imap_domain" || next === "waitlist") {
    return next;
  }
  const comingSoon = comingSoonFromNext(next, provider);
  if (comingSoon) {
    if (exists && (provider === "gmail" || provider === "yahoo")) {
      return "provider_login";
    }
    return comingSoon;
  }
  if (!exists && next === "unsupported") {
    return "unsupported_imap_domain";
  }
  if (exists) {
    return "provider_login";
  }
  if (next === "azure_oauth" || next === "signup" || next === undefined || next === "") {
    return "confirm_first_time";
  }
  return "fix_domain";
}

export function oauthFromResolveNext(next?: string): AuthGateOAuth | null {
  if (next === "yahoo_oauth") {
    return "yahoo";
  }
  if (next === "google_oauth") {
    return "google";
  }
  if (next === "azure_oauth") {
    return "azure";
  }
  if (next === "apple_oauth") {
    return "apple";
  }
  return null;
}

export function comingSoonProviderLabel(
  next?: string,
  provider?: string,
): "Gmail" | "Yahoo" | "iCloud" {
  if (next === "coming_soon_yahoo" || provider === "yahoo") {
    return "Yahoo";
  }
  if (next === "coming_soon_icloud" || provider === "apple") {
    return "iCloud";
  }
  return "Gmail";
}

export function isComingSoonGate(next: AuthGateNext): boolean {
  return (
    next === "coming_soon_gmail"
    || next === "coming_soon_yahoo"
    || next === "coming_soon_icloud"
    || next === "pending_review"
    || next === "icloud_unavailable"
  );
}
