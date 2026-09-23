"use client";

import type { Session, User } from "@supabase/supabase-js";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  authEventMayCarrySession,
  readLogoutQueryFlag,
  shouldDeferAuthStateChange,
  stripLogoutQueryParam,
} from "@/lib/appAuthSession";
import { supabase } from "@/lib/supabase";
import { hmsJson } from "@/lib/hmsApi";
import {
  languageForDonextoVerifyEmail,
  localeForLanguage,
  rememberLoginLanguage,
  type AppLanguage,
} from "@/lib/i18n/languages";
import { resolveMailboxProviderFromEmail } from "@/lib/mailboxSignup";
import { userHasOAuthIdentity } from "@/lib/oauthIdentity";
import { authReturnUrl, verifyEmailRedirectUrl } from "@/lib/adminCanonical";
import { buildApiUrl } from "@/lib/apiBase";
import {
  confirmDonextoPath,
  donextoVerifyFailure,
  acknowledgeVerifyLinkError,
  forgetDonextoVerifyProof,
  interpretConfirmDonextoResponse,
  loadDonextoVerifyProof,
  readDonextoVerifyProof,
  rememberDonextoVerifyProof,
  rememberVerifyLinkError,
  stripDonextoVerifySearch,
  type DonextoVerifyProof,
  type VerifyLinkErrorCode,
} from "@/lib/donextoVerifyLink";
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

const OAUTH_EXPECTED_EMAIL_KEY = "donexto_oauth_expected_email";

function clearOAuthExpectedEmail() {
  try {
    sessionStorage.removeItem(OAUTH_EXPECTED_EMAIL_KEY);
  } catch {
    // ignore
  }
}

function rememberOAuthExpectedEmail(email: string | undefined): string {
  const hint = email?.trim().toLowerCase() ?? "";
  if (!hint.includes("@")) {
    throw new Error(
      "Escribe el correo en Donexto antes de continuar. Tiene que ser el mismo con el que firmas en el proveedor.",
    );
  }
  try {
    sessionStorage.setItem(OAUTH_EXPECTED_EMAIL_KEY, hint);
  } catch {
    // sessionStorage puede fallar en modo restringido
  }
  return hint;
}

function consumeOAuthEmailMismatch(sessionEmail: string | undefined): string | null {
  let expected = "";
  try {
    expected = sessionStorage.getItem(OAUTH_EXPECTED_EMAIL_KEY) || "";
  } catch {
    return null;
  }
  if (!expected) {
    return null;
  }
  const actual = (sessionEmail || "").trim().toLowerCase();
  if (!actual) {
    return null;
  }
  try {
    sessionStorage.removeItem(OAUTH_EXPECTED_EMAIL_KEY);
  } catch {
    // ignore
  }
  if (actual === expected) {
    return null;
  }
  return (
    `Firmaste con ${actual}, pero en Donexto pediste ${expected}. ` +
    "Cierra sesión en el proveedor (o usa una ventana privada) y vuelve a pulsar Continuar. No se abrió sesión."
  );
}

type RedeemResult =
  | { ok: true; session: Session }
  | { ok: false; code: VerifyLinkErrorCode | "absent" };

function browserStore(): Storage | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

function rememberVerifyCode(code: VerifyLinkErrorCode) {
  const store = browserStore();
  if (store) {
    rememberVerifyLinkError(store, code);
  }
}

function captureDonextoVerifyProof(): DonextoVerifyProof | null {
  if (typeof window === "undefined") {
    return null;
  }
  const fromUrl = readDonextoVerifyProof(window.location.search);
  const store = browserStore();
  if (fromUrl && store) {
    rememberDonextoVerifyProof(store, fromUrl);
    return fromUrl;
  }
  return store ? loadDonextoVerifyProof(store) : fromUrl;
}

function clearDonextoVerifyProof() {
  const store = browserStore();
  if (store) {
    forgetDonextoVerifyProof(store);
  }
  if (typeof window === "undefined") {
    return;
  }
  const next = stripDonextoVerifySearch(window.location.href);
  const current = `${window.location.pathname}${window.location.search}${window.location.hash}`;
  if (next !== current) {
    window.history.replaceState({}, "", next);
  }
}

function withFreshUser(session: Session | null, user: User | null | undefined): Session | null {
  if (!session) {
    return null;
  }
  if (!user) {
    return session;
  }
  return { ...session, user };
}

let redeemInflight: Promise<RedeemResult> | null = null;

async function establishSessionFromTokens(
  accessToken: string,
  refreshToken: string,
): Promise<Session | null> {
  const { data, error } = await supabase.auth.setSession({
    access_token: accessToken,
    refresh_token: refreshToken,
  });
  if (error) {
    throw error;
  }
  let user = (await supabase.auth.getUser()).data.user;
  if (user && !isDonextoVerified(user)) {
    user = (await supabase.auth.getUser()).data.user ?? user;
  }
  return withFreshUser(data.session, user);
}

async function redeemProof(proof: DonextoVerifyProof): Promise<RedeemResult> {
  acknowledgeVerifyLinkError();
  let resolved: { ok: boolean; status: number; payload: unknown };
  try {
    resolved = await postPublicHms(confirmDonextoPath(proof), {});
  } catch (error) {
    console.error("No fue posible confirmar Donexto en el servidor:", error);
    rememberVerifyCode("retry");
    return { ok: false, code: "retry" };
  }

  const outcome = interpretConfirmDonextoResponse(resolved.status, resolved.payload);
  if (outcome.kind === "invalid") {
    clearDonextoVerifyProof();
    rememberVerifyCode("invalid");
    return { ok: false, code: "invalid" };
  }
  if (outcome.kind === "retry") {
    rememberVerifyCode("retry");
    return { ok: false, code: "retry" };
  }
  if (outcome.kind === "verified_without_session") {
    clearDonextoVerifyProof();
    const { data } = await supabase.auth.getSession();
    const { data: userData } = await supabase.auth.getUser();
    const session = withFreshUser(data.session, userData.user);
    if (session?.user) {
      return { ok: true, session };
    }
    rememberVerifyCode("sign_in_again");
    return { ok: false, code: "sign_in_again" };
  }

  try {
    const session = await establishSessionFromTokens(
      outcome.accessToken,
      outcome.refreshToken,
    );
    clearDonextoVerifyProof();
    if (!session?.user) {
      rememberVerifyCode("sign_in_again");
      return { ok: false, code: "sign_in_again" };
    }
    return { ok: true, session };
  } catch (error) {
    console.error("La cuenta quedó confirmada, pero no se abrió la sesión:", error);
    clearDonextoVerifyProof();
    rememberVerifyCode("sign_in_again");
    return { ok: false, code: "sign_in_again" };
  }
}

function redeemDonextoEmailLink(): Promise<RedeemResult> {
  const proof = captureDonextoVerifyProof();
  if (!proof) {
    return Promise.resolve({ ok: false, code: "absent" });
  }
  if (!redeemInflight) {
    redeemInflight = redeemProof(proof).finally(() => {
      redeemInflight = null;
    });
  }
  return redeemInflight;
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

function isDonextoVerified(user: User | null | undefined): boolean {
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
function sessionNeedsDonextoEmailConfirm(session: Session | null): boolean {
  const user = session?.user;
  if (!user) {
    return false;
  }
  return !isDonextoVerified(user);
}

function currentAuthReturn(): string {
  return authReturnUrl(window.location);
}

function donextoVerifyRedirectTo(): string {
  return verifyEmailRedirectUrl(window.location);
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
  const bootstrapComplete = useRef(false);

  useEffect(() => {
    let mounted = true;

    async function invalidateLocalSession() {
      try {
        await supabase.auth.signOut();
      } catch {
        await supabase.auth.signOut({ scope: "local" });
      }
      if (mounted) {
        setRawSession(null);
      }
    }

    async function validateAndApplySession(nextSession: Session | null) {
      if (!nextSession?.user) {
        if (mounted) {
          setRawSession(null);
        }
        return;
      }

      const { data: userData, error: userError } = await supabase.auth.getUser();
      if (!mounted) {
        return;
      }

      if (userError || !userData.user) {
        if (userError) {
          console.warn("Sesión rechazada tras cambio de auth:", userError.message);
        }
        await invalidateLocalSession();
        return;
      }

      const mismatch = consumeOAuthEmailMismatch(userData.user.email);
      if (mismatch) {
        await invalidateLocalSession();
        if (typeof window !== "undefined") {
          const url = new URL(window.location.href);
          url.hash = "";
          url.searchParams.set("donexto", "oauth_error");
          url.searchParams.set("reason", mismatch);
          window.location.replace(`${url.pathname}?${url.searchParams.toString()}`);
        }
        return;
      }

      setRawSession(withFreshUser(nextSession, userData.user));
    }

    function clearVerifySentKeys() {
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

    function handlePasswordRecovery(nextSession: Session | null) {
      if (yahooImapOwnsIdentity(nextSession?.user)) {
        setPasswordRecovery(false);
      } else {
        setPasswordRecovery(true);
      }
    }

    async function loadSession() {
      try {
        if (typeof window !== "undefined" && readLogoutQueryFlag(window.location.search)) {
          await invalidateLocalSession();
          const nextPath = stripLogoutQueryParam(
            window.location.pathname,
            window.location.search,
          );
          window.history.replaceState({}, "", nextPath);
          return;
        }

        const redeemed = await redeemDonextoEmailLink();
        if (!mounted) {
          return;
        }
        if (redeemed.ok) {
          const mismatch = consumeOAuthEmailMismatch(redeemed.session.user.email);
          if (mismatch) {
            await invalidateLocalSession();
            const url = new URL(window.location.href);
            url.hash = "";
            url.searchParams.set("donexto", "oauth_error");
            url.searchParams.set("reason", mismatch);
            window.location.replace(`${url.pathname}?${url.searchParams.toString()}`);
            return;
          }
          setRawSession(redeemed.session);
          return;
        }

        const { data: userData, error: userError } = await supabase.auth.getUser();

        if (!mounted) {
          return;
        }

        if (userError || !userData.user) {
          // Stale local JWT (p. ej. usuario borrado en Supabase) — limpiar storage.
          if (userError) {
            console.warn("Sesión local inválida:", userError.message);
          }
          await invalidateLocalSession();
          return;
        }

        const { data, error } = await supabase.auth.getSession();
        if (!mounted) {
          return;
        }

        if (error) {
          console.error("No fue posible leer la sesión:", error);
        }

        const mismatch = consumeOAuthEmailMismatch(userData.user.email);
        if (mismatch) {
          await invalidateLocalSession();
          const url = new URL(window.location.href);
          url.hash = "";
          url.searchParams.set("donexto", "oauth_error");
          url.searchParams.set("reason", mismatch);
          window.location.replace(`${url.pathname}?${url.searchParams.toString()}`);
          return;
        }

        setRawSession(withFreshUser(data.session ?? null, userData.user));
      } finally {
        if (mounted) {
          bootstrapComplete.current = true;
          setLoading(false);
        }
      }
    }

    void loadSession();

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, nextSession) => {
      if (shouldDeferAuthStateChange(event, bootstrapComplete.current)) {
        if (event === "PASSWORD_RECOVERY") {
          handlePasswordRecovery(nextSession);
        }
        return;
      }

      if (event === "SIGNED_OUT") {
        setRawSession(null);
        setPasswordRecovery(false);
        clearVerifySentKeys();
        setLoading(false);
        return;
      }

      if (event === "PASSWORD_RECOVERY") {
        handlePasswordRecovery(nextSession);
        setLoading(false);
        return;
      }

      if (authEventMayCarrySession(event)) {
        void validateAndApplySession(nextSession).finally(() => {
          if (mounted) {
            setLoading(false);
          }
        });
        return;
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

      if (!isDonextoVerified(currentUser) && captureDonextoVerifyProof()) {
        verifyBootstrapLock.current = true;
        try {
          const redeemed = await redeemDonextoEmailLink();
          if (!cancelled && redeemed.ok) {
            setRawSession(redeemed.session);
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

        // Same language as the login screen. Do not read user_metadata.language
        // or navigator.language here: metadata often stays "en" after a Spanish login.
        const language = languageForDonextoVerifyEmail();
        rememberLoginLanguage(language);
        try {
          await hmsJson(buildApiUrl("/identity/send-donexto-verify"), {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ language, redirect_to: currentAuthReturn() }),
          });
        } catch (error) {
          // Log loudly so Auth provider failures are retryable.
          // Clear the "sent" flag so the ConfirmEmailGate can show its
          // "Reenviar" button and the user can retry manually.
          console.error("Auto-resend failed", error);
          try {
            sessionStorage.removeItem(sentKey);
          } catch {
            // ignore
          }
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

      rememberLoginLanguage(languageForDonextoVerifyEmail());
      const hint = rememberOAuthExpectedEmail(email);
      const { error } = await supabase.auth.signInWithOAuth({
        provider,
        options: {
          redirectTo: currentAuthReturn(),
          queryParams: {
            prompt: "consent",
            access_type: "offline",
            ...(hint ? { login_hint: hint } : {}),
          },
        },
      });

      if (error) {
        clearOAuthExpectedEmail();
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
    rememberLoginLanguage(languageForDonextoVerifyEmail());
    const hint = rememberOAuthExpectedEmail(email);
    let resolved;
    try {
      resolved = await postPublicHms("/auth/yahoo/login", {
        return_to: currentAuthReturn(),
        intent,
        ...(hint ? { login_hint: hint } : {}),
      });
    } catch (error) {
      clearOAuthExpectedEmail();
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
      clearOAuthExpectedEmail();
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
    rememberLoginLanguage(languageForDonextoVerifyEmail());
    const hint = rememberOAuthExpectedEmail(email);
    let resolved;
    try {
      resolved = await postPublicHms("/auth/microsoft/login", {
        return_to: currentAuthReturn(),
        intent,
        ...(hint ? { login_hint: hint } : {}),
      });
    } catch (error) {
      clearOAuthExpectedEmail();
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
      clearOAuthExpectedEmail();
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
      language?: AppLanguage,
    ): Promise<SignUpResult> => {
      const accountLanguage = language ?? languageForDonextoVerifyEmail();
      rememberLoginLanguage(accountLanguage);
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
            language: accountLanguage,
            locale: localeForLanguage(accountLanguage),
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

      // Fire the localized Donexto verification email through our backend
      // as the single source of truth. Supabase's own template will still
      // be sent (Free plan cannot disable it without emptying the template);
      // if this call fails we do not block signup because Supabase's own
      // email will land as a fallback.
      if (data.user?.email) {
        try {
          await hmsJson(buildApiUrl("/identity/send-donexto-verify"), {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              language: accountLanguage,
              redirect_to: currentAuthReturn(),
            }),
          });
          try {
            sessionStorage.setItem(
              `donexto_verify_sent:${data.user.email.toLowerCase()}`,
              "1",
            );
          } catch {
            // sessionStorage may be unavailable in restricted modes.
          }
        } catch (err) {
          console.warn("Backend verification email failed", err);
        }
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

  const sendDonextoVerifyEmail = useCallback(async (
    email: string,
    language?: AppLanguage,
  ) => {
    const cleanEmail = email.trim().toLowerCase();
    const accountLanguage = language ?? languageForDonextoVerifyEmail();
    rememberLoginLanguage(accountLanguage);
    await hmsJson(buildApiUrl("/identity/send-donexto-verify"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        language: accountLanguage,
        redirect_to: currentAuthReturn(),
      }),
    });
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
        redirectTo: currentAuthReturn(),
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
    if (captureDonextoVerifyProof()) {
      const redeemed = await redeemDonextoEmailLink();
      if (redeemed.ok && !sessionNeedsDonextoEmailConfirm(redeemed.session)) {
        setRawSession(redeemed.session);
        return;
      }
      if (!redeemed.ok && redeemed.code !== "absent") {
        throw donextoVerifyFailure(redeemed.code);
      }
    }

    const { data, error } = await supabase.auth.getUser();
    if (error) {
      throw new Error(translateAuthError(error.message));
    }

    const { data: next, error: sessionError } =
      await supabase.auth.refreshSession();
    if (sessionError) {
      throw new Error(translateAuthError(sessionError.message));
    }

    const session = withFreshUser(next.session ?? null, data.user);
    setRawSession(session);

    if (sessionNeedsDonextoEmailConfirm(session) && data.user) {
      throw donextoVerifyFailure("unverified");
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
