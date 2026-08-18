import { supabase } from "@/lib/supabase";

export type DonextoAccountLookup = "exists" | "missing" | "unknown";

const PENDING_FULL_NAME_KEY = "donexto_pending_full_name";
const INTENDED_EMAIL_KEY = "donexto_intended_email";
const AUTH_ERROR_KEY = "donexto_auth_error";

export function rememberPendingFullName(name: string) {
  const clean = name.trim().replace(/\s+/g, " ");
  if (clean.length < 2) {
    return;
  }
  try {
    sessionStorage.setItem(PENDING_FULL_NAME_KEY, clean);
  } catch {
    // sessionStorage puede fallar en modo restringido
  }
}

export function peekPendingFullName(): string {
  try {
    return (sessionStorage.getItem(PENDING_FULL_NAME_KEY) || "").trim();
  } catch {
    return "";
  }
}

export function clearPendingFullName() {
  try {
    sessionStorage.removeItem(PENDING_FULL_NAME_KEY);
  } catch {
    // ignore
  }
}

export function rememberIntendedEmail(email: string) {
  const clean = email.trim().toLowerCase();
  if (!clean.includes("@")) {
    return;
  }
  try {
    sessionStorage.setItem(INTENDED_EMAIL_KEY, clean);
  } catch {
    // ignore
  }
}

export function peekIntendedEmail(): string {
  try {
    return (sessionStorage.getItem(INTENDED_EMAIL_KEY) || "").trim().toLowerCase();
  } catch {
    return "";
  }
}

export function clearIntendedEmail() {
  try {
    sessionStorage.removeItem(INTENDED_EMAIL_KEY);
  } catch {
    // ignore
  }
}

export function rememberAuthError(message: string) {
  try {
    sessionStorage.setItem(AUTH_ERROR_KEY, message);
  } catch {
    // ignore
  }
}

export function takeAuthError(): string {
  try {
    const value = (sessionStorage.getItem(AUTH_ERROR_KEY) || "").trim();
    sessionStorage.removeItem(AUTH_ERROR_KEY);
    return value;
  } catch {
    return "";
  }
}

function isValidLookupEmail(email: string): boolean {
  const at = email.indexOf("@");
  return at > 0 && email.includes(".", at + 1) && email.length <= 320;
}

export async function lookupDonextoAccount(
  email: string,
): Promise<DonextoAccountLookup> {
  const clean = email.trim().toLowerCase();
  if (!isValidLookupEmail(clean)) {
    return "missing";
  }

  const { data, error } = await supabase.rpc("donexto_account_exists", {
    lookup_email: clean,
  });

  if (!error && typeof data === "boolean") {
    return data ? "exists" : "missing";
  }

  try {
    const response = await fetch("/api/hms/auth/donexto-account", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: clean }),
      cache: "no-store",
    });
    if (!response.ok) {
      return "unknown";
    }
    const payload = (await response.json()) as { exists?: unknown };
    if (typeof payload.exists === "boolean") {
      return payload.exists ? "exists" : "missing";
    }
  } catch {
    return "unknown";
  }

  return "unknown";
}
