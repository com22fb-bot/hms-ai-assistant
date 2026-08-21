export type AuthGateIntent = "login" | "signup";
export type AuthGateNext =
  | "provider_login"
  | "confirm_signup"
  | "stay_subscribe";

/** Continuar solo entra si ya hay cuenta. Suscribirse confirma el correo en Donexto. */
export function gateNextAfterResolve(
  intent: AuthGateIntent,
  exists: boolean,
): AuthGateNext {
  if (exists) {
    return "provider_login";
  }
  if (intent === "signup") {
    return "confirm_signup";
  }
  return "stay_subscribe";
}
