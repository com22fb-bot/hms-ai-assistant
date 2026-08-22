export type AuthGateIntent = "login" | "signup";
export type AuthGateNext =
  | "provider_login"
  | "confirm_signup"
  | "stay_subscribe"
  | "fix_domain"
  | "pending_review"
  | "unsupported";

/** Continuar solo entra si ya hay cuenta. Suscribirse confirma el correo en Donexto. */
export function gateNextAfterResolve(
  intent: AuthGateIntent,
  exists: boolean,
  next?: string,
): AuthGateNext {
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
  if (next === "signup" && intent === "signup") {
    return "confirm_signup";
  }
  if (next === "signup" && intent === "login") {
    return "stay_subscribe";
  }
  if (intent === "signup" && (next === undefined || next === "")) {
    return "confirm_signup";
  }
  return "fix_domain";
}
