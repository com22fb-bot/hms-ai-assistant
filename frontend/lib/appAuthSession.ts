import type { AuthChangeEvent } from "@supabase/supabase-js";

/** Supabase events that may carry a session object needing server validation. */
export function authEventMayCarrySession(event: AuthChangeEvent): boolean {
  return (
    event === "INITIAL_SESSION"
    || event === "SIGNED_IN"
    || event === "TOKEN_REFRESHED"
    || event === "USER_UPDATED"
  );
}

/**
 * During bootstrap we call getUser() before trusting localStorage.
 * Ignore session-bearing auth events until that finishes — otherwise
 * INITIAL_SESSION from a stale JWT shows the dashboard before validation.
 */
export function shouldDeferAuthStateChange(
  event: AuthChangeEvent,
  bootstrapComplete: boolean,
): boolean {
  if (bootstrapComplete) {
    return false;
  }
  return event !== "PASSWORD_RECOVERY";
}

export function readLogoutQueryFlag(search: string): boolean {
  return new URLSearchParams(search).get("logout") === "1";
}

export function stripLogoutQueryParam(pathname: string, search: string): string {
  const params = new URLSearchParams(search);
  if (!params.has("logout")) {
    return `${pathname}${search}`;
  }
  params.delete("logout");
  const nextSearch = params.toString();
  return nextSearch ? `${pathname}?${nextSearch}` : pathname;
}
