"use client";

import type { Session } from "@supabase/supabase-js";
import { useCallback, useEffect, useMemo, useState } from "react";

import { supabase } from "@/lib/supabase";

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

type AppSession = {
  id: string;
  email: string;
  name: string;
};

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

export function useAppAuth() {
  const [rawSession, setRawSession] =
    useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [passwordRecovery, setPasswordRecovery] =
    useState(false);

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
      }

      setLoading(false);
    });

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, []);

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
    async (provider: AuthOAuthProvider) => {
      // supabase-js no tipa `yahoo` como Provider de Auth.
      if (provider === "yahoo") {
        throw new Error("Falta activar Yahoo en Supabase Auth");
      }

      const { error } = await supabase.auth.signInWithOAuth({
        provider,
        options: {
          redirectTo: `${window.location.origin}/`,
        },
      });

      if (error) {
        throw new Error(translateAuthError(error.message, provider));
      }
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
          emailRedirectTo: `${window.location.origin}/`,
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
        emailRedirectTo: `${window.location.origin}/`,
      },
    });
    if (error) {
      throw new Error(translateAuthError(error.message));
    }
  }, []);

  const signInWithMagicLink = useCallback(
    async (email: string) => {
      const { error } = await supabase.auth.signInWithOtp({
        email,
        options: {
          shouldCreateUser: true,
          emailRedirectTo: `${window.location.origin}/`,
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

  return {
    session,
    loading,
    passwordRecovery,
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
