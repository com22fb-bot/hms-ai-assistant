/**
 * Detects an external identity for routing and contamination cleanup. An
 * OAuth identity is not Donexto email verification.
 */

export type OAuthIdentityUser = {
  email?: string | null;
  identities?: Array<{ provider?: string | null } | null> | null;
  user_metadata?: { signup_via?: unknown; donexto_verified?: unknown } | null;
  app_metadata?: {
    provider?: unknown;
    providers?: unknown;
    donexto_verified?: unknown;
    donexto_verification_source?: unknown;
  } | null;
};

const OAUTH_SIGNUP_VIA = new Set([
  "yahoo_oauth",
  "microsoft_oauth",
  "google_oauth",
  "apple_oauth",
]);

function isNonEmailProvider(value: unknown): boolean {
  if (typeof value !== "string") {
    return false;
  }
  const provider = value.trim().toLowerCase();
  return provider.length > 0 && provider !== "email";
}

export function userHasOAuthIdentity(
  user: OAuthIdentityUser | null | undefined,
): boolean {
  if (!user) {
    return false;
  }

  const identities = user.identities ?? [];
  if (identities.some((row) => isNonEmailProvider(row?.provider))) {
    return true;
  }

  const via = String(user.user_metadata?.signup_via ?? "")
    .trim()
    .toLowerCase();
  if (OAUTH_SIGNUP_VIA.has(via)) {
    return true;
  }

  if (isNonEmailProvider(user.app_metadata?.provider)) {
    return true;
  }

  const providers = user.app_metadata?.providers;
  if (Array.isArray(providers) && providers.some(isNonEmailProvider)) {
    return true;
  }

  return false;
}

export type DonextoBootstrapAction = "redeem" | "skip" | "send";

/**
 * Live checks trust only app_metadata written by the backend.
 * user_metadata is client-writable and must not skip the Verificar email.
 */
export function isDonextoVerified(
  user: OAuthIdentityUser | null | undefined,
): boolean {
  if (user?.app_metadata?.donexto_verified === true) {
    if (
      userHasOAuthIdentity(user)
      && user.app_metadata?.donexto_verification_source !== "email"
    ) {
      return false;
    }
    return true;
  }
  return false;
}

/**
 * Every account, including OAuth accounts, needs the Donexto email link
 * unless the backend has recorded a trusted verification source.
 */
export function sessionNeedsDonextoEmailConfirm(
  session: { user?: OAuthIdentityUser | null } | null,
): boolean {
  const user = session?.user;
  if (!user) {
    return false;
  }
  return !isDonextoVerified(user);
}

/**
 * Session bootstrap. A stored verify proof still redeems (cold click).
 * A trusted app_metadata flag, including one re-read from the server,
 * never auto-sends. Brand-new OAuth without that flag still sends once.
 */
export function donextoBootstrapAction(input: {
  user: OAuthIdentityUser | null | undefined;
  hasVerifyProof: boolean;
  refreshedUser?: OAuthIdentityUser | null;
}): DonextoBootstrapAction {
  const email = input.user?.email?.trim() ?? "";
  if (!input.user || !email) {
    return "skip";
  }
  if (!isDonextoVerified(input.user) && input.hasVerifyProof) {
    return "redeem";
  }
  if (isDonextoVerified(input.user) || isDonextoVerified(input.refreshedUser)) {
    return "skip";
  }
  return "send";
}
