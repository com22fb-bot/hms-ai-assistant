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
    return "El correo o la contraseña no son correctos.";
  }

  if (normalized.includes("email not confirmed")) {
    return "Debes confirmar tu correo antes de iniciar sesión.";
  }

  if (normalized.includes("user already registered")) {
    return "Ya existe una cuenta con ese correo.";
  }

  if (normalized.includes("password")) {
    return "La contraseña no cumple los requisitos de seguridad.";
  }

  return message;
}

export function useAppAuth() {
  const [rawSession, setRawSession] =
    useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

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
    } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setRawSession(nextSession);
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

  const signUp = useCallback(
    async (
      email: string,
      password: string,
      fullName: string,
    ) => {
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: {
            full_name: fullName,
            locale: "es-MX",
            timezone: "America/Chihuahua",
          },
          emailRedirectTo: window.location.origin,
        },
      });

      if (error) {
        throw new Error(translateAuthError(error.message));
      }

      return {
        requiresConfirmation: !data.session,
      };
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
    signIn,
    signUp,
    signOut,
    resetPassword,
  };
}
