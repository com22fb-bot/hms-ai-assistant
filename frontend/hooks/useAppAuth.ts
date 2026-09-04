"use client";

import type { Session, User } from "@supabase/supabase-js";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { supabase } from "@/lib/supabase";
import { hmsJson } from "@/lib/hmsApi";
import { resolveMailboxProviderFromEmail } from "@/lib/mailboxSignup";
import { userHasOAuthIdentity } from "@/lib/oauthIdentity";
import { isBrowserNetworkError, postPublicHms } from "@/lib/publicHms";

export { userHasOAuthIdentity } from "@/lib/oauthIdentity";

export type SignUpResult =
  | { kind: "signed_in" }
  | { kind: "confirm_email" }
  | { kind: "already_registered" };

/** Proveedores OAuth de identidad en Supabase Auth (alta / login). */
export type AuthOAuthProvider = "google" | "azure" | "apple" | "yahoo";
export type YahooAuthIntent = "login" | "signup";

const OAUTH_PROVIDER_LABEL: Record<AuthOAuthProvider, string> = {
  google: "Google",
  azure: "Microsoft",
  apple: "Apple",
  yahoo: "Yahoo",
};

type AppSession = {
  id: string;
  email: string;
  name: string;
};

const DONEXTO_VERIFY_QUERY = "donexto_verify";
const HMS_API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "/api/hms";

function isDonextoVerified(user: User | null | undefined): boolean {
  if (user?.app_metadata?.donexto_verified === true) {
    return true;
  }
  // Legacy flag in user_metadata is ignored for authorization; backend is source of truth.
  return false;
}

async function confirmDonextoWithBackend(): Promise<boolean> {
  try {
    const result = await hmsJson<{ donexto_verified?: boolean }>(
      `${HMS_API_BASE}/identity/confirm-donexto`,
      { method: "POST" },
    );
    return result.donexto_verified === true;
  } catch (error) {
    console.error("No fue posible confirmar Donexto en el servidor:", error);
    return false;
  }
}

function yahooImapOwnsIdentity(user: User | null | undefined): boolean {
  if (!user?.email) {
    return false;
  }
  const via = String(user.user_metadata?.signup_via ?? "").toLowerCase();
  if (via === "yahoo_imap" || via === "yahoo_oauth") {
    return true;
  }
  return resolveMailboxProviderFromEmail(user.email) === "yahoo";
}

/**
 * Password / magic-link accounts still need the Donexto verify email.
 * Signing in at Yahoo, Google, or Microsoft is the verification.
 */
function sessionNeedsDonextoEmailConfirm(session: Session | null): boolean {
  const user = session?.user;
  if (!user) {
    return false;
  }
  if (userHasOAuthIdentity(user)) {
    return false;
  }
  return !isDonextoVerified(user);
}

function isDonextoVerifyReturn(): boolean {
  if (typeof window === "undefined") {
    return false;
  }

  const search = new URLSearchParams(window.location.search);
  return search.get(DONEXTO_VERIFY_QUERY) === "1";
}

function donextoVerifyRedirectTo(): string {
  return `${window.location.origin}/?${DONEXTO_VERIFY_QUERY}=1`;
}

function clearDonextoVerifyQuery() {
  if (typeof window === "undefined") {
    return;
  }

  const url = new URL(window.location.href);
  if (!url.searchParams.has(DONEXTO_VERIFY_QUERY)) {
    return;
  }

  url.searchParams.delete(DONEXTO_VERIFY_QUERY);
  const next = `${url.pathname}${url.search}${url.hash}`;
  window.history.replaceState({}, "", next);
}

function mapSession(session: Session | null): AppSession | null {
  const user = session?.user;

  if (!user?.email) {
    return null;
  }

  const metadataName = String(
    user.user_metadata?.full_name ?? "",
  ).trim();

  const fallbackName = user.email
    .split("@")[0]
    .split(/[._-]/)
    .filter(Boolean)
    .map((part) =>
      part.charAt(0).toUpperCase() + part.slice(1),
    )
    .join(" ");

  return {
    id: user.id,
    email: user.email,
    name: metadataName || fallbackName || "Usuario",
  };
}

function translateAuthError(
  message: string,
  oauthProvider?: AuthOAuthProvider,
): string {
  const normalized = message.toLowerCase();
  const oauthLabel = oauthProvider
    ? OAUTH_PROVIDER_LABEL[oauthProvider]
    : null;

  if (normalized.includes("invalid login credentials")) {
    return (
      "La contraseña de tu cuenta Donexto no coincide. " +
      "No tiene que ser la misma contraseña de Yahoo, Gmail u otro buzón."
    );
  }

  if (normalized.includes("email not confirmed")) {
    return "Debes confirmar tu correo antes de iniciar sesión.";
  }

  if (normalized.includes("user already registered")) {
    return "Ya existe una cuenta Donexto con ese correo.";
  }

  if (
    normalized.includes("rate limit") ||
    normalized.includes("security purposes")
  ) {
    return (
      "Se hicieron demasiadas solicitudes seguidas. " +
      "Espera un momento antes de volver a intentarlo."
    );
  }

  if (
    normalized.includes("same password") ||
    normalized.includes("different from the old password")
  ) {
    return "La nueva contraseña debe ser diferente de la anterior.";
  }

  if (
    normalized.includes("password") ||
    normalized.includes("weak")
  ) {
    return (
      "La contraseña Donexto debe tener al menos 8 caracteres " +
      "y cumplir los requisitos de seguridad."
    );
  }

  if (
    normalized.includes("provider is not enabled") ||
    normalized.includes("unsupported provider")
  ) {
    return `Falta activar ${oauthLabel ?? "Google"} en Supabase Auth`;
  }

  if (
    normalized.includes("unable to exchange") ||
    normalized.includes("error getting user profile from external provider")
  ) {
    return (
      `No se pudo completar el acceso con ${oauthLabel ?? "Google"}. ` +
      "Inténtalo de nuevo. Si se repite, revisa el callback de Supabase " +
      "en el portal de ese proveedor."
    );
  }

  return message;
}

function detailMessage(payload: {
  detail?: { message?: string } | string;
  message?: string;
}): string | undefined {
  const detail = payload.detail;
  if (typeof detail === "string") return detail;
  if (detail?.message) return detail.message;
  return payload.message;
}

export function useAppAuth() {
  const [rawSession, setRawSession] =
    useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [passwordRecovery, setPasswordRecovery] =
    useState(false);
  const verifyBootstrapLock = useRef(false);

  useEffect(() => {
    let mounted = true;

    void supabase.auth.getSession().then(({ data, error }) => {
      if (!mounted) {
        return;
      }

      if (error) {
        console.error("No fue posible leer la sesión:", error);
      }

      setRawSession(data.session ?? null);
      setLoading(false);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, nextSession) => {
      setRawSession(nextSession);

      if (event === "PASSWORD_RECOVERY") {
        if (yahooImapOwnsIdentity(nextSession?.user)) {
          setPasswordRecovery(false);
        } else {
          setPasswordRecovery(true);
        }
      }

      if (event === "SIGNED_OUT") {
        setPasswordRecovery(false);
        try {
          for (const key of Object.keys(sessionStorage)) {
            if (key.startsWith("donexto_verify_sent:")) {
              sessionStorage.removeItem(key);
            }
          }
        } catch {
          // sessionStorage puede fallar en modo restringido
        }
      }

      setLoading(false);
    });

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, []);

  useEffect(() => {
    const user = rawSession?.user;
    const accountEmail = user?.email?.trim().toLowerCase() ?? "";
    if (!user || !accountEmail) {
      return;
    }
    const currentUser = user;

    let cancelled = false;

    async function bootstrapDonextoVerify() {
      if (verifyBootstrapLock.current) {
        return;
      }

      if (userHasOAuthIdentity(currentUser) || isDonextoVerifyReturn()) {
        verifyBootstrapLock.current = true;
        try {
          if (!isDonextoVerified(currentUser)) {
            const confirmed = await confirmDonextoWithBackend();
            if (confirmed) {
              const { data: next } = await supabase.auth.refreshSession();
              if (!cancelled) {
                setRawSession(next.session ?? null);
              }
            }
          }
          if (isDonextoVerifyReturn()) {
            clearDonextoVerifyQuery();
          }
        } catch (error) {
          console.error("No fue posible confirmar Donexto:", error);
        } finally {
          verifyBootstrapLock.current = false;
        }
        return;
      }

      if (isDonextoVerified(currentUser)) {
        return;
      }

      verifyBootstrapLock.current = true;
      try {
        const sentKey = `donexto_verify_sent:${accountEmail}`;
        try {
          if (sessionStorage.getItem(sentKey) === "1") {
            return;
          }
          sessionStorage.setItem(sentKey, "1");
        } catch {
          // sessionStorage puede fallar en modo restringido
        }

        const { error } = await supabase.auth.signInWithOtp({
          email: accountEmail,
          options: {
            shouldCreateUser: false,
            emailRedirectTo: donextoVerifyRedirectTo(),
          },
        });
        if (error) {
          try {
            sessionStorage.removeItem(sentKey);
          } catch {
            // ignore
          }
          console.error("No fue posible enviar el correo Donexto:", error);
        }
      } finally {
        verifyBootstrapLock.current = false;
      }
    }

    void bootstrapDonextoVerify();

    return () => {
      cancelled = true;
    };
  }, [rawSession]);

  const signIn = useCallback(
    async (email: string, password: string) => {
      const { error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (error) {
        throw new Error(translateAuthError(error.message));
      }
    },
    [],
  );

  const signInWithProvider = useCallback(
    async (provider: AuthOAuthProvider, email?: string) => {
      // supabase-js no tipa `yahoo` como Provider de Auth.
      // Yahoo identity uses POST /auth/yahoo/login (signInWithYahoo), not
      // supabase.auth.signInWithOAuth("yahoo"). Keep this guard so the
      // generic helper cannot send people into a missing Supabase provider.
      if (provider === "yahoo") {
        throw new Error("Falta activar Yahoo en Supabase Auth");
      }

      const hint = email?.trim().toLowerCase();
      const { error } = await supabase.auth.signInWithOAuth({
        provider,
        options: {
          redirectTo: `${window.location.origin}/`,
          queryParams: {
            prompt: "consent",
            access_type: "offline",
            ...(hint ? { login_hint: hint } : {}),
          },
        },
      });

      if (error) {
        throw new Error(translateAuthError(error.message, provider));
      }
    },
    [],
  );

  const signInWithGoogle = useCallback(async (email?: string) => {
    await signInWithProvider("google", email);
  }, [signInWithProvider]);

  const signInWithYahoo = useCallback(async (
    intent: YahooAuthIntent = "login",
    email?: string,
  ) => {
    const hint = email?.trim().toLowerCase();
    let resolved;
    try {
      resolved = await postPublicHms("/auth/yahoo/login", {
        return_to: window.location.origin,
        intent,
        ...(hint ? { login_hint: hint } : {}),
      });
    } catch (error) {
      if (isBrowserNetworkError(error)) {
        throw new Error(
          "No hay conexión con Donexto. Revisa la red e inténtalo de nuevo.",
        );
      }
      throw error;
    }

    const payload = (resolved.payload || {}) as {
      authorization_url?: string;
      detail?: { message?: string } | string;
      message?: string;
    };

    if (!resolved.ok || !payload.authorization_url) {
      throw new Error(
        detailMessage(payload) ??
          "No fue posible abrir el inicio de sesión de Yahoo.",
      );
    }

    window.location.assign(payload.authorization_url);
  }, []);

  const signInWithMicrosoft = useCallback(async (
    intent: YahooAuthIntent = "login",
    email?: string,
  ) => {
    const hint = email?.trim().toLowerCase();
    let resolved;
    try {
      resolved = await postPublicHms("/auth/microsoft/login", {
        return_to: window.location.origin,
        intent,
        ...(hint ? { login_hint: hint } : {}),
      });
    } catch (error) {
      if (isBrowserNetworkError(error)) {
        throw new Error(
          "No hay conexión con Donexto. Revisa la red e inténtalo de nuevo.",
        );
      }
      throw error;
    }

    const payload = (resolved.payload || {}) as {
      authorization_url?: string;
      detail?: { message?: string } | string;
      message?: string;
    };

    if (!resolved.ok || !payload.authorization_url) {
      throw new Error(
        detailMessage(payload) ??
          "No fue posible abrir el inicio de sesión de Microsoft.",
      );
    }

    window.location.assign(payload.authorization_url);
  }, []);

  const signUp = useCallback(
    async (
      email: string,
      password: string,
      fullName: string,
    ): Promise<SignUpResult> => {
      const cleanName = fullName.trim().replace(/\s+/g, " ");
      if (cleanName.length < 2) {
        throw new Error(
          "Escribe tu nombre completo para la cuenta Donexto.",
        );
      }

      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          emailRedirectTo: donextoVerifyRedirectTo(),
          data: {
            full_name: cleanName,
          },
        },
      });

      if (error) {
        throw new Error(translateAuthError(error.message));
      }

      // Supabase a veces “oculta” usuarios existentes con identities vacías.
      const identities = data.user?.identities ?? [];
      if (data.user && identities.length === 0) {
        return { kind: "already_registered" };
      }

      if (data.session) {
        return { kind: "signed_in" };
      }

      // Confirmación de email activa: cuenta creada, sin sesión aún.
      return { kind: "confirm_email" };
    },
    [],
  );

  const resendSignupEmail = useCallback(async (email: string) => {
    const cleanEmail = email.trim().toLowerCase();
    const { error } = await supabase.auth.resend({
      type: "signup",
      email: cleanEmail,
      options: {
        emailRedirectTo: donextoVerifyRedirectTo(),
      },
    });
    if (error) {
      throw new Error(translateAuthError(error.message));
    }
  }, []);

  const sendDonextoVerifyEmail = useCallback(async (email: string) => {
    const cleanEmail = email.trim().toLowerCase();
    const { error } = await supabase.auth.signInWithOtp({
      email: cleanEmail,
      options: {
        shouldCreateUser: false,
        emailRedirectTo: donextoVerifyRedirectTo(),
      },
    });
    if (error) {
      throw new Error(translateAuthError(error.message));
    }
    try {
      sessionStorage.setItem(`donexto_verify_sent:${cleanEmail}`, "1");
    } catch {
      // ignore
    }
  }, []);

  const signInWithMagicLink = useCallback(
    async (email: string) => {
      const { error } = await supabase.auth.signInWithOtp({
        email,
        options: {
          shouldCreateUser: true,
          emailRedirectTo: donextoVerifyRedirectTo(),
        },
      });

      if (error) {
        throw new Error(translateAuthError(error.message));
      }
    },
    [],
  );

  const resetPassword = useCallback(async (email: string) => {
    const { error } = await supabase.auth.resetPasswordForEmail(
      email,
      {
        redirectTo: `${window.location.origin}/`,
      },
    );

    if (error) {
      throw new Error(translateAuthError(error.message));
    }
  }, []);

  const updatePassword = useCallback(
    async (newPassword: string) => {
      const { error } = await supabase.auth.updateUser({
        password: newPassword,
      });

      if (error) {
        throw new Error(translateAuthError(error.message));
      }

      setPasswordRecovery(false);
    },
    [],
  );

  const cancelPasswordRecovery = useCallback(async () => {
    setPasswordRecovery(false);

    const { error } = await supabase.auth.signOut();

    if (error) {
      throw new Error(translateAuthError(error.message));
    }
  }, []);

  const signOut = useCallback(async () => {
    const { error } = await supabase.auth.signOut();

    if (error) {
      throw new Error(translateAuthError(error.message));
    }
  }, []);

  const session = useMemo(
    () => mapSession(rawSession),
    [rawSession],
  );

  const needsEmailConfirm = useMemo(
    () => sessionNeedsDonextoEmailConfirm(rawSession),
    [rawSession],
  );

  const refreshSession = useCallback(async () => {
    const { data, error } = await supabase.auth.getUser();
    if (error) {
      throw new Error(translateAuthError(error.message));
    }

    if (
      data.user
      && sessionNeedsDonextoEmailConfirm({ user: data.user } as Session)
    ) {
      await confirmDonextoWithBackend();
    }

    const { data: next, error: sessionError } =
      await supabase.auth.refreshSession();
    if (sessionError) {
      throw new Error(translateAuthError(sessionError.message));
    }

    setRawSession(next.session ?? null);

    if (sessionNeedsDonextoEmailConfirm(next.session ?? null) && data.user) {
      throw new Error(
        "Aún no vemos el clic de confirmación. Abre el correo que te enviamos.",
      );
    }
  }, []);

  return {
    session,
    loading,
    passwordRecovery,
    needsEmailConfirm,
    refreshSession,
    sendDonextoVerifyEmail,
    signIn,
    signInWithGoogle,
    signInWithYahoo,
    signInWithMicrosoft,
    signInWithProvider,
    signUp,
    resendSignupEmail,
    signInWithMagicLink,
    signOut,
    resetPassword,
    updatePassword,
    cancelPasswordRecovery,
  };
}
