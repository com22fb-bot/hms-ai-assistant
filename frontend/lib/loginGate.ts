export type AuthGateIntent = "login" | "signup";
export type AuthGateNext =
  | "provider_login"
  | "provider_signup"
  | "stay_subscribe";

/** Continuar solo entra si ya hay cuenta. Suscribirse es el alta. */
export function gateNextAfterResolve(
  intent: AuthGateIntent,
  exists: boolean,
): AuthGateNext {
  if (exists) {
    return "provider_login";
  }
  if (intent === "signup") {
    return "provider_signup";
  }
  return "stay_subscribe";
}
