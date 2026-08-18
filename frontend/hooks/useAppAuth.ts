"use client";

import type { Provider, Session, User } from "@supabase/supabase-js";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { supabase } from "@/lib/supabase";
import {
  YAHOO_CUSTOM_PROVIDER,
  YAHOO_PROVIDER_SETUP_MESSAGE,
} from "@/lib/yahooAuth";

export type SignUpResult =
  | { kind: "signed_in" }
  | { kind: "confirm_email" }
  | { kind: "already_registered" };

/** Proveedores OAuth de identidad en Supabase Auth (alta / login). */
export type AuthOAuthProvider = "google" | "azure" | "apple" | "yahoo";

const OAUTH_PROVIDER_LABEL: Record<AuthOAuthProvider, string> = {
  google: "Google",
  azure: "Microsoft",
  apple: "Apple",
  yahoo: "Yahoo",
};

const SUPABASE_OAUTH_PROVIDER: Record<AuthOAuthProvider, Provider> = {
  google: "google",
  azure: "azure",
  apple: "apple",
  yahoo: YAHOO_CUSTOM_PROVIDER,
};

type AppSession = {
  id: string;
  email: string;
  name: string;
};

const DONEXTO_VERIFY_QUERY = "donexto_verify";

function userHasOAuthIdentity(user: User | null | undefined): boolean {
  if (!user) {
    return false;
  }

  const identities = user.identities ?? [];
  if (identities.some((identity) => identity.provider !== "email")) {
    return true;
  }

  const provider = String(user.app_metadata?.provider ?? "").toLowerCase();
  return provider !== "" && provider !== "email";
}

function isDonextoVerified(user: User | null | undefined): boolean {
  return user?.user_metadata?.donexto_verified === true;
}

const FIRST_SESSION_MS = 15 * 60 * 1000;

/** Alta reciente: el mail de Donexto es una vez. Reentradas no. */
function isFirstDonextoSession(user: User | null | undefined): boolean {
  if (!user?.created_at) {
    return true;
  }
  const created = Date.parse(user.created_at);
  if (!Number.isFinite(created)) {
    return true;
  }
  const last = Date.parse(user.last_sign_in_at || user.created_at);
  if (!Number.isFinite(last)) {
    return true;
  }
  return last - created < FIRST_SESSION_MS;
}

/**
 * Sin `user_metadata.donexto_verified === true` no hay app en el alta.
 * Quien ya tiene cuenta (sesión posterior al alta) entra por el proveedor,
 * sin otro correo de Donexto.
 */
function sessionNeedsDonextoEmailConfirm(session: Session | null): boolean {
  const user = session?.user;
  if (!user) {
    return false;
  }
  if (isDonextoVerified(user)) {
    return false;
  }
  return isFirstDonextoSession(user);
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
    normalized.includes("unsupported provider") ||
    normalized.includes("could not be found")
  ) {
    if (oauthProvider === "yahoo") {
      return YAHOO_PROVIDER_SETUP_MESSAGE;
    }
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
        setPasswordRecovery(true);
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

      if (isDonextoVerifyReturn()) {
        verifyBootstrapLock.current = true;
        try {
          if (!isDonextoVerified(currentUser)) {
            const { error } = await supabase.auth.updateUser({
              data: { donexto_verified: true },
            });
            if (error) {
              throw error;
            }
            const { data: next } = await supabase.auth.getSession();
            if (!cancelled) {
              setRawSession(next.session ?? null);
            }
          }
          clearDonextoVerifyQuery();
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

      // Cuenta que ya existía: no mandar otro correo para entrar.
      if (!isFirstDonextoSession(currentUser)) {
        verifyBootstrapLock.current = true;
        try {
          const { error } = await supabase.auth.updateUser({
            data: { donexto_verified: true },
          });
          if (!error) {
            const { data: next } = await supabase.auth.getSession();
            if (!cancelled && next.session) {
              setRawSession(next.session);
            }
          }
        } catch (error) {
          console.error("No fue posible sellar la verificación Donexto:", error);
        } finally {
          verifyBootstrapLock.current = false;
        }
        return;
      }

      if (!userHasOAuthIdentity(currentUser)) {
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
    async (provider: AuthOAuthProvider, loginHint?: string) => {
      const queryParams: Record<string, string> = {};
      const hint = loginHint?.trim().toLowerCase();
      if (hint && (provider === "google" || provider === "azure")) {
        queryParams.login_hint = hint;
      }
      if (provider === "google") {
        queryParams.access_type = "offline";
        queryParams.prompt = "select_account";
      }

      const { data, error } = await supabase.auth.signInWithOAuth({
        provider: SUPABASE_OAUTH_PROVIDER[provider],
        options: {
          skipBrowserRedirect: true,
          redirectTo: `${window.location.origin}/`,
          ...(Object.keys(queryParams).length > 0 ? { queryParams } : {}),
          ...(provider === "yahoo" ? { scopes: "openid email profile" } : {}),
        },
      });

      if (error) {
        throw new Error(translateAuthError(error.message, provider));
      }
      if (!data.url) {
        throw new Error(
          provider === "yahoo"
            ? YAHOO_PROVIDER_SETUP_MESSAGE
            : `No fue posible abrir el inicio de sesión de ${OAUTH_PROVIDER_LABEL[provider]}.`,
        );
      }
      window.location.assign(data.url);
    },
    [],
  );

  const signInWithGoogle = useCallback(async () => {
    await signInWithProvider("google");
  }, [signInWithProvider]);

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
    const { data } = await supabase.auth.getSession();
    const user = data.session?.user;

    if (userHasOAuthIdentity(user)) {
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
      return;
    }

    await resendSignupEmail(cleanEmail);
  }, [resendSignupEmail]);

  const signInWithMagicLink = useCallback(
    async (email: string) => {
      const { error } = await supabase.auth.signInWithOtp({
        email,
        options: {
          shouldCreateUser: false,
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

    const { data: next, error: sessionError } =
      await supabase.auth.getSession();
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
