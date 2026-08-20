"use client";

import {
  AlertTriangle,
  CheckCircle2,
  Eye,
  EyeOff,
  KeyRound,
  LoaderCircle,
  Mail,
} from "lucide-react";
import { FormEvent, useEffect, useRef, useState } from "react";

import { LanguageStrip } from "@/components/UserSettingsPanel";
import { ACCOUNT_VS_MAILBOX } from "@/lib/accountVsMailbox";
import { DONEXTO_QUALITY } from "@/lib/donextoQuality";
import type { AuthOAuthProvider } from "@/hooks/useAppAuth";
import {
  isValidSignupEmail,
  resolveMailboxProviderFromEmail,
  type MailboxSignupProvider,
} from "@/lib/mailboxSignup";

import "./hms-gate.css";
import "./dx-auth-neon.css";

export type GateThemeId =
  | "midnight"
  | "aurora"
  | "accessible"
  | "graphite";

const TERMS_URL = "https://www.donexto.com/terminos.html";
const PRIVACY_URL = "https://www.donexto.com/privacidad.html";

function mailboxToOAuth(
  provider: MailboxSignupProvider,
): AuthOAuthProvider | null {
  if (provider === "gmail") {
    return "google";
  }
  if (provider === "hotmail") {
    return "azure";
  }
  if (provider === "apple") {
    return "apple";
  }
  return null;
}

type LoginScreenProps = {
  theme: GateThemeId;
  setTheme: (theme: GateThemeId) => void;
  onSignIn: (email: string, password: string) => Promise<void>;
  onSignUp: (
    email: string,
    password: string,
    fullName: string,
  ) => Promise<unknown>;
  onSignInWithGoogle: () => Promise<void>;
  onSignInWithYahoo: (email: string, password: string) => Promise<void>;
  onSignInWithProvider: (provider: AuthOAuthProvider) => Promise<void>;
  onResendSignupEmail?: (email: string) => Promise<void>;
  onMagicLink: (email: string) => Promise<void>;
  onResetPassword: (email: string) => Promise<void>;
};

function ProviderMark({
  provider,
}: {
  provider: MailboxSignupProvider;
}) {
  const letter =
    provider === "gmail"
      ? "G"
      : provider === "yahoo"
        ? "Y"
        : provider === "hotmail"
          ? "M"
          : provider === "apple"
            ? ""
            : "@";

  return (
    <span
      className={`dx-auth__mark dx-auth__mark--${provider}`}
      aria-hidden
    >
      {provider === "apple" ? (
        <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
          <path d="M16.7 12.6c0-2.3 1.9-3.4 2-3.5-1.1-1.6-2.8-1.8-3.4-1.8-1.4-.2-2.8.9-3.5.9s-1.8-.8-3-.8c-1.5 0-3 .9-3.8 2.3-1.6 2.8-.4 7 1.2 9.3.8 1.1 1.7 2.4 2.9 2.3 1.2 0 1.6-.7 3-.7s1.8.7 3 .7 2-.1 2.9-2.3c.7-1.1 1-2.1 1-2.2-.1 0-1.9-.7-1.9-3.2zM14.8 6.4c.6-.8 1.1-1.8.9-2.9-1 .1-2.1.7-2.8 1.5-.6.7-1.2 1.8-1 2.8 1.1.1 2.2-.6 2.9-1.4z" />
        </svg>
      ) : (
        letter
      )}
    </span>
  );
}

/**
 * Acceso Donexto.
 * Yahoo: correo + la misma clave de Yahoo. No hay alta de usuario Donexto.
 * Gmail: Google OAuth; la contraseña de Gmail no se pide aquí.
 */
export function LoginScreen({
  theme: _theme,
  setTheme: _setTheme,
  onSignIn,
  onSignUp: _onSignUp,
  onSignInWithGoogle,
  onSignInWithYahoo,
  onSignInWithProvider,
  onMagicLink,
  onResetPassword,
}: LoginScreenProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [usePassword, setUsePassword] = useState(false);
  const [yahooMode, setYahooMode] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [oauthBusy, setOauthBusy] = useState<AuthOAuthProvider | null>(null);
  const emailRef = useRef<HTMLInputElement>(null);
  const passwordRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const html = document.documentElement;
    const body = document.body;
    const prevHtml = html.style.overflow;
    const prevBody = body.style.overflow;
    html.style.overflow = "hidden";
    body.style.overflow = "hidden";
    html.style.height = "100%";
    body.style.height = "100%";
    return () => {
      html.style.overflow = prevHtml;
      body.style.overflow = prevBody;
      html.style.height = "";
      body.style.height = "";
    };
  }, []);

  function resetAlerts() {
    setError(null);
    setMessage(null);
  }

  function goSignIn() {
    setMode("signin");
    resetAlerts();
    setBusy(false);
    setOauthBusy(null);
    setUsePassword(false);
    setYahooMode(false);
  }

  function goSignUp() {
    setMode("signup");
    resetAlerts();
    setBusy(false);
    setOauthBusy(null);
    setUsePassword(false);
    setYahooMode(false);
    setPassword("");
  }

  async function startOAuthSignup(provider: AuthOAuthProvider) {
    if (busy) {
      return;
    }
    resetAlerts();
    setBusy(true);
    setOauthBusy(provider);
    try {
      if (provider === "google") {
        await onSignInWithGoogle();
      } else {
        await onSignInWithProvider(provider);
      }
    } catch (requestError) {
      const fallback =
        provider === "azure"
          ? "No fue posible abrir el inicio de sesión de Microsoft."
          : provider === "apple"
            ? "No fue posible abrir el inicio de sesión de Apple."
            : "No fue posible abrir el inicio de sesión de Google.";
      setError(
        requestError instanceof Error ? requestError.message : fallback,
      );
      setBusy(false);
      setOauthBusy(null);
    }
  }

  const typedProvider = resolveMailboxProviderFromEmail(email.trim());
  const yahooFlow = yahooMode || typedProvider === "yahoo";

  async function sendMagicLink(address: string) {
    setBusy(true);
    resetAlerts();
    try {
      await onMagicLink(address);
      setMessage(`Revisa ${address}: abre el enlace para entrar.`);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "No fue posible enviar el enlace.",
      );
    } finally {
      setBusy(false);
    }
  }

  function showYahooForm() {
    setYahooMode(true);
    setUsePassword(false);
    resetAlerts();
    window.setTimeout(() => {
      if (email.trim()) {
        passwordRef.current?.focus();
      } else {
        emailRef.current?.focus();
      }
    }, 0);
  }

  async function enterWithYahoo(address: string, yahooPassword: string) {
    if (yahooPassword.length < 6) {
      setError(
        "Escribe la misma clave con la que entras a Yahoo (mínimo 6 caracteres).",
      );
      passwordRef.current?.focus();
      return;
    }
    setBusy(true);
    resetAlerts();
    try {
      await onSignInWithYahoo(address, yahooPassword);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Yahoo no aceptó el correo o la clave.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function continueWithEmail(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) {
      return;
    }
    const clean = email.trim().toLowerCase();
    if (!isValidSignupEmail(clean)) {
      setError(
        yahooFlow
          ? "Escribe tu correo Yahoo."
          : "Escribe el correo con el que te identificas.",
      );
      return;
    }

    const provider = resolveMailboxProviderFromEmail(clean);
    if (yahooFlow || provider === "yahoo") {
      await enterWithYahoo(clean, password);
      return;
    }

    if (mode === "signin" && usePassword) {
      if (password.length < 8) {
        setError("La contraseña de Donexto usa al menos 8 caracteres.");
        return;
      }
      setBusy(true);
      resetAlerts();
      try {
        await onSignIn(clean, password);
      } catch (requestError) {
        setError(
          requestError instanceof Error
            ? requestError.message
            : "No fue posible iniciar sesión en Donexto.",
        );
      } finally {
        setBusy(false);
      }
      return;
    }

    const oauth = mailboxToOAuth(provider);
    if (oauth) {
      await startOAuthSignup(oauth);
      return;
    }
    await sendMagicLink(clean);
  }

  async function continueYahoo() {
    const clean = email.trim().toLowerCase();
    if (
      isValidSignupEmail(clean) &&
      resolveMailboxProviderFromEmail(clean) !== "yahoo"
    ) {
      setError(
        "Usa un correo Yahoo (@yahoo.com, @ymail.com o @rocketmail.com).",
      );
      emailRef.current?.focus();
      return;
    }
    if (yahooFlow && isValidSignupEmail(clean) && password.length >= 6) {
      await enterWithYahoo(clean, password);
      return;
    }
    showYahooForm();
  }

  async function recoverPassword() {
    const clean = email.trim().toLowerCase();
    if (!isValidSignupEmail(clean)) {
      setError("Escribe primero el correo de tu cuenta Donexto.");
      return;
    }
    setBusy(true);
    resetAlerts();
    try {
      await onResetPassword(clean);
      setMessage("Enviamos un enlace para restablecer la contraseña de Donexto.");
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "No fue posible solicitar el restablecimiento.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="dx-auth">
      <aside className="dx-auth__hero">
        <div className="dx-auth__hero-inner">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            className="dx-auth__logo"
            src="/brand/donexto-3d-2026.png"
            width={512}
            height={512}
            alt="Donexto — Do Next To…"
            decoding="async"
          />
          <h1 className="dx-auth__brand">Donexto</h1>
          <p className="dx-auth__promise">
            {`${DONEXTO_QUALITY.whatItDoes}\n${DONEXTO_QUALITY.promise}`}
          </p>
        </div>
      </aside>

      <section className="dx-auth__panel">
        <div className="dx-auth__card" aria-labelledby="dx-auth-title">
          <header className="dx-auth__heading">
            <h2 id="dx-auth-title" className="dx-auth__title">
              {yahooFlow
                ? ACCOUNT_VS_MAILBOX.loginTitleYahoo
                : mode === "signup"
                  ? ACCOUNT_VS_MAILBOX.loginTitleSignUp
                  : ACCOUNT_VS_MAILBOX.loginTitleSignIn}
            </h2>
            <p className="dx-auth__slogan">
              {yahooFlow
                ? ACCOUNT_VS_MAILBOX.loginHelperYahoo
                : ACCOUNT_VS_MAILBOX.loginHelper}
            </p>
          </header>

          {error ? (
            <div className="dx-auth__alert is-error" role="alert">
              <AlertTriangle size={18} />
              <span>{error}</span>
            </div>
          ) : null}
          {message ? (
            <div className="dx-auth__alert is-ok" role="status">
              <CheckCircle2 size={18} />
              <span>{message}</span>
            </div>
          ) : null}

          <div className="dx-auth__providers">
            <button
              type="button"
              className="dx-auth__provider dx-auth__provider--gmail"
              disabled={busy}
              onClick={() => void startOAuthSignup("google")}
            >
              {oauthBusy === "google" ? (
                <>
                  <LoaderCircle className="dx-auth__spin" size={18} />
                  Abriendo Google…
                </>
              ) : (
                <>
                  <ProviderMark provider="gmail" />
                  Continuar con Google
                </>
              )}
            </button>
            <button
              type="button"
              className="dx-auth__provider"
              disabled={busy}
              onClick={() => void continueYahoo()}
            >
              <ProviderMark provider="yahoo" />
              Continuar con Yahoo
            </button>
          </div>

          <p className="dx-auth__divider">o</p>

          <form
            className="dx-auth__form"
            onSubmit={(event) => void continueWithEmail(event)}
            noValidate
          >
            <label className="dx-auth__field">
              <span>Correo</span>
              <div className="dx-auth__control">
                <Mail size={18} aria-hidden />
                <input
                  ref={emailRef}
                  type="email"
                  name="email"
                  value={email}
                  inputMode="email"
                  autoComplete="email"
                  autoCapitalize="none"
                  autoCorrect="off"
                  spellCheck={false}
                  placeholder={
                    yahooFlow ? "tucorreo@yahoo.com" : "tu@correo.com"
                  }
                  disabled={busy}
                  onChange={(event) => setEmail(event.target.value)}
                />
              </div>
            </label>

            {yahooFlow || (mode === "signin" && usePassword) ? (
              <label className="dx-auth__field">
                <span>
                  {yahooFlow
                    ? ACCOUNT_VS_MAILBOX.loginYahooPasswordLabel
                    : ACCOUNT_VS_MAILBOX.loginPasswordLabel}
                </span>
                <div className="dx-auth__control">
                  <KeyRound size={18} aria-hidden />
                  <input
                    ref={passwordRef}
                    type={showPassword ? "text" : "password"}
                    name="password"
                    value={password}
                    autoComplete="current-password"
                    autoCapitalize="none"
                    spellCheck={false}
                    placeholder={
                      yahooFlow
                        ? "La misma con la que entras a Yahoo"
                        : "Solo si ya la definiste aquí"
                    }
                    disabled={busy}
                    onChange={(event) => setPassword(event.target.value)}
                  />
                  <button
                    type="button"
                    className="dx-auth__eye"
                    aria-label={
                      showPassword ? "Ocultar contraseña" : "Mostrar contraseña"
                    }
                    onClick={() => setShowPassword((value) => !value)}
                  >
                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
              </label>
            ) : null}

            <button type="submit" className="dx-auth__submit" disabled={busy}>
              {busy && oauthBusy === null ? (
                <>
                  <LoaderCircle className="dx-auth__spin" size={18} />
                  {yahooFlow ? "Entrando…" : "Continuando…"}
                </>
              ) : yahooFlow || (mode === "signin" && usePassword) ? (
                "Entrar"
              ) : (
                "Continuar"
              )}
            </button>
          </form>

          {!yahooFlow && mode === "signin" ? (
            <div className="dx-auth__alt">
              <button
                type="button"
                className="dx-auth__link"
                disabled={busy}
                onClick={() => {
                  setUsePassword((value) => !value);
                  resetAlerts();
                }}
              >
                {usePassword
                  ? "Entrar con enlace al correo"
                  : "Tengo contraseña de Donexto"}
              </button>
              {usePassword ? (
                <button
                  type="button"
                  className="dx-auth__link"
                  disabled={busy}
                  onClick={() => void recoverPassword()}
                >
                  Olvidé mi contraseña
                </button>
              ) : null}
            </div>
          ) : null}

          {yahooFlow ? (
            <div className="dx-auth__bottom-mode">
              <button
                type="button"
                disabled={busy}
                onClick={() => {
                  setYahooMode(false);
                  setPassword("");
                  if (typedProvider === "yahoo") {
                    setEmail("");
                  }
                  resetAlerts();
                }}
              >
                ¿Usas Gmail u otro correo?
              </button>
            </div>
          ) : (
            <div className="dx-auth__bottom-mode">
              {mode === "signin" ? (
                <button type="button" disabled={busy} onClick={goSignUp}>
                  ¿No tienes cuenta? Crear cuenta
                </button>
              ) : (
                <button type="button" disabled={busy} onClick={goSignIn}>
                  ¿Ya tienes cuenta? Entrar
                </button>
              )}
            </div>
          )}

          <LanguageStrip />

          <p className="dx-auth__legal-agree">
            Al continuar aceptas los{" "}
            <a href={TERMS_URL} target="_blank" rel="noopener noreferrer">
              Términos
            </a>{" "}
            y la{" "}
            <a href={PRIVACY_URL} target="_blank" rel="noopener noreferrer">
              Privacidad
            </a>{" "}
            de Donexto.
          </p>
        </div>

        <footer className="dx-auth__footer">
          <p className="dx-auth__legal">
            <span>© HMSR · MR</span>
            <span>Héctor M. Salcido Roacho</span>
          </p>
        </footer>
      </section>
    </main>
  );
}
