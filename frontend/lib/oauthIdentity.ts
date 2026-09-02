/**
 * Identity proven at Yahoo / Google / Microsoft (or Apple) counts as
 * Donexto verification. Backend Yahoo/Microsoft mint Auth users with
 * signup_via metadata rather than a Supabase OAuth identity row.
 */

export type OAuthIdentityUser = {
  identities?: Array<{ provider?: string | null } | null> | null;
  user_metadata?: { signup_via?: unknown } | null;
  app_metadata?: { provider?: unknown; providers?: unknown } | null;
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
