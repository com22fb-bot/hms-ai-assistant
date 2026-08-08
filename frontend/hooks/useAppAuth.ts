"use client";

import type { Session } from "@supabase/supabase-js";
import { useCallback, useEffect, useMemo, useState } from "react";

import { supabase } from "@/lib/supabase";

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

function translateAuthError(message: string): string {
  const normalized = message.toLowerCase();

  if (normalized.includes("invalid login credentials")) {
    return (
      "La contraseña de tu cuenta HMS no coincide. " +
      "No tiene que ser la misma contraseña de Yahoo, Gmail u otro buzón."
    );
  }

  if (normalized.includes("email not confirmed")) {
    return "Debes confirmar tu correo antes de iniciar sesión.";
  }

  if (normalized.includes("user already registered")) {
    return "Ya existe una cuenta HMS con ese correo.";
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
      "La contraseña HMS debe tener al menos 8 caracteres " +
      "y cumplir los requisitos de seguridad."
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

  const signInWithMagicLink = useCallback(
    async (email: string) => {
      const { error } = await supabase.auth.signInWithOtp({
        email,
        options: {
          shouldCreateUser: false,
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
    signInWithMagicLink,
    signOut,
    resetPassword,
    updatePassword,
    cancelPasswordRecovery,
  };
}
