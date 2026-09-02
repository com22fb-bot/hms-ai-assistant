export type AuthGateIntent = "login" | "signup";
export type AuthGateNext =
  | "provider_login"
  | "confirm_first_time"
  | "fix_domain"
  | "pending_review"
  | "unsupported"
  | "icloud_unavailable";

export type AuthGateOAuth = "google" | "azure" | "apple" | "yahoo";

/**
 * Email-first gate: one Continuar.
 * Existence + routing come from POST /auth/login/resolve
 * (`{ exists, next, provider, message }`). The extra fields are needed to
 * tell pending_review / typo / unsupported apart from a first-time Yahoo
 * or Outlook mailbox. On network failure the client stays on Screen 1.
 */
export function gateNextAfterResolve(
  _intent: AuthGateIntent,
  exists: boolean,
  next?: string,
  provider?: string,
): AuthGateNext {
  if (provider === "apple" || next === "apple_oauth") {
    return "icloud_unavailable";
  }
  if (next === "fix_domain" || next === "typo" || next === "invalid_domain") {
    return "fix_domain";
  }
  if (!exists && next === "pending_review") {
    return "pending_review";
  }
  if (!exists && next === "unsupported") {
    return "unsupported";
  }
  if (exists) {
    return "provider_login";
  }
  if (next === "signup" || next === undefined || next === "") {
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
