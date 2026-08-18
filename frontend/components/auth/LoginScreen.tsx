"use client";

import {
  AlertTriangle,
  CheckCircle2,
  ChevronLeft,
  Eye,
  EyeOff,
  KeyRound,
  LoaderCircle,
  Mail,
} from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

import {
  ACCOUNT_VS_MAILBOX,
  authSecurityBodyFor,
} from "@/lib/accountVsMailbox";
import { DONEXTO_QUALITY } from "@/lib/donextoQuality";
import type { AuthOAuthProvider, SignUpResult } from "@/hooks/useAppAuth";
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

type SignUpPane = "choose" | "yahoo" | "other" | "other-unrecognized";

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
  ) => Promise<SignUpResult>;
  onSignInWithGoogle: () => Promise<void>;
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
 * Gate Donexto — split en escritorio, columna en celular.
 * Logo 3D “Do Next To…” (D, no P). Login vs Crear cuenta (buzón).
 */
export function LoginScreen({
  theme: _theme,
  setTheme: _setTheme,
  onSignIn,
  onSignUp: _onSignUp,
  onSignInWithGoogle,
  onSignInWithProvider,
  onMagicLink,
  onResetPassword,
}: LoginScreenProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [step, setStep] = useState<"credentials" | "help">("credentials");
  const [signUpPane, setSignUpPane] = useState<SignUpPane>("choose");
  const [otherEmail, setOtherEmail] = useState("");
  const [yahooEmail, setYahooEmail] = useState("");
  const [oauthBusy, setOauthBusy] = useState<AuthOAuthProvider | null>(null);

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

  function goSignIn() {
    setMode("signin");
    setStep("credentials");
    setSignUpPane("choose");
    setError(null);
    setBusy(false);
    setOauthBusy(null);
  }

  function goSignUp() {
    setMode("signup");
    setStep("credentials");
    setSignUpPane("choose");
    setError(null);
    setMessage(null);
    setOtherEmail("");
    setYahooEmail("");
    setBusy(false);
    setOauthBusy(null);
  }

  function openSignUpPane(pane: SignUpPane) {
    setSignUpPane(pane);
    setError(null);
    setMessage(null);
  }

  async function startOAuthSignup(provider: AuthOAuthProvider) {
    if (busy) {
      return;
    }
    setError(null);
    setMessage(null);
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

  function applyMailboxRoute(provider: MailboxSignupProvider) {
    const oauth = mailboxToOAuth(provider);
    if (oauth) {
      void startOAuthSignup(oauth);
      return;
    }
    if (provider === "yahoo") {
      const fromOther = otherEmail.trim().toLowerCase();
      if (fromOther) {
        setYahooEmail(fromOther);
      }
      openSignUpPane("yahoo");
      return;
    }
    openSignUpPane("other-unrecognized");
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) {
      return;
    }
    setError(null);
    setMessage(null);

    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail.includes("@")) {
      setError("Escribe el correo de tu cuenta Donexto.");
      return;
    }
    if (password.length < 8) {
      setError(
        "La contraseña de tu cuenta Donexto usa al menos 8 caracteres.",
      );
      return;
    }

    setBusy(true);
    try {
      await onSignIn(cleanEmail, password);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "No fue posible iniciar sesión en Donexto.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function magicLink() {
    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail.includes("@")) {
      setError("Escribe primero el correo de tu cuenta Donexto.");
      return;
    }
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await onMagicLink(cleanEmail);
      setMessage(
        "Revisa tu correo: enviamos un enlace para entrar a Donexto sin contraseña.",
      );
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

  async function recover() {
    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail.includes("@")) {
      setError("Escribe primero el correo de tu cuenta Donexto.");
      return;
    }
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await onResetPassword(cleanEmail);
      setMessage(
        "Enviamos un enlace para restablecer la contraseña de tu cuenta Donexto.",
      );
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

  function continueOtherEmail() {
    if (busy) {
      return;
    }
    setError(null);
    setMessage(null);
    const clean = otherEmail.trim().toLowerCase();
    if (!isValidSignupEmail(clean)) {
      setError("Escribe un correo válido, por ejemplo nombre@dominio.com.");
      return;
    }
    applyMailboxRoute(resolveMailboxProviderFromEmail(clean));
  }

  async function continueYahooPrep(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) {
      return;
    }
    setError(null);
    setMessage(null);
    const clean = yahooEmail.trim().toLowerCase();
    if (!isValidSignupEmail(clean)) {
      setError("Escribe un correo Yahoo válido, por ejemplo tucorreo@yahoo.com.");
      return;
    }
    if (resolveMailboxProviderFromEmail(clean) !== "yahoo") {
      setError(
        "Usa un correo Yahoo (@yahoo.com, @ymail.com o @rocketmail.com).",
      );
      return;
    }
    setBusy(true);
    try {
      await onMagicLink(clean);
      setMessage(
          "Te enviamos un enlace a ese Yahoo para entrar a Donexto. " +
          "Luego autorizas la lectura de ese mismo correo.",
      );
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "No fue posible enviar el enlace a Yahoo.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function continueUnrecognizedMagicLink() {
    if (busy) {
      return;
    }
    const clean = otherEmail.trim().toLowerCase();
    if (!isValidSignupEmail(clean)) {
      setError("Escribe un correo válido, por ejemplo nombre@dominio.com.");
      return;
    }
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await onMagicLink(clean);
      setMessage(
          "Revisa tu correo: enviamos un enlace para entrar a Donexto. " +
          "Luego autorizamos la lectura de ese mismo buzón.",
      );
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

  const gateClass = [
    "dx-auth",
    mode === "signup" ? "dx-auth--signup" : "",
    step === "help" ? "dx-auth--help" : "",
  ]
    .filter(Boolean)
    .join(" ");

  const showAlerts = Boolean(error || message);

  return (
    <main className={gateClass}>
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
          <p className="dx-auth__brand">Donexto</p>
          <h1 className="dx-auth__promise">
            {`${DONEXTO_QUALITY.whatItDoes}\n${DONEXTO_QUALITY.promise}`}
          </h1>
        </div>
      </aside>

      <section className="dx-auth__panel">
        <div className="dx-auth__card" aria-labelledby="dx-auth-title">
          <header className="dx-auth__heading">
            <h2 id="dx-auth-title" className="dx-auth__title">
              {mode === "signup"
                ? ACCOUNT_VS_MAILBOX.loginTitleSignUp
                : ACCOUNT_VS_MAILBOX.loginTitleSignIn}
            </h2>
            {mode === "signin" && step === "credentials" ? (
              <p className="dx-auth__slogan">{DONEXTO_QUALITY.slogan}</p>
            ) : null}
            {mode === "signup" && signUpPane === "choose" ? (
              <p className="dx-auth__slogan">
                {ACCOUNT_VS_MAILBOX.signupChooserBody}
              </p>
            ) : null}
          </header>

          {mode === "signup" ? (
            <div className="dx-auth__signup">
              {showAlerts ? (
                <>
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
                </>
              ) : null}

              {signUpPane === "choose" ? (
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
                        Gmail
                      </>
                    )}
                  </button>
                  <button
                    type="button"
                    className="dx-auth__provider"
                    disabled={busy}
                    onClick={() => openSignUpPane("yahoo")}
                  >
                    <ProviderMark provider="yahoo" />
                    Yahoo
                  </button>
                  <button
                    type="button"
                    className="dx-auth__provider"
                    disabled={busy}
                    onClick={() => void startOAuthSignup("azure")}
                  >
                    {oauthBusy === "azure" ? (
                      <>
                        <LoaderCircle className="dx-auth__spin" size={18} />
                        Abriendo Microsoft…
                      </>
                    ) : (
                      <>
                        <ProviderMark provider="hotmail" />
                        Hotmail
                      </>
                    )}
                  </button>
                  <button
                    type="button"
                    className="dx-auth__provider"
                    disabled={busy}
                    onClick={() => void startOAuthSignup("apple")}
                  >
                    {oauthBusy === "apple" ? (
                      <>
                        <LoaderCircle className="dx-auth__spin" size={18} />
                        Abriendo Apple…
                      </>
                    ) : (
                      <>
                        <ProviderMark provider="apple" />
                        Apple
                      </>
                    )}
                  </button>
                  <button
                    type="button"
                    className="dx-auth__provider"
                    disabled={busy}
                    onClick={() => openSignUpPane("other")}
                  >
                    <ProviderMark provider="other" />
                    Otro
                  </button>
                </div>
              ) : null}

              {signUpPane === "yahoo" ? (
                <form
                  className="dx-auth__form dx-auth__yahoo"
                  autoComplete="off"
                  data-1p-ignore="true"
                  data-lpignore="true"
                  data-form-type="other"
                  onSubmit={continueYahooPrep}
                >
                  <button
                    type="button"
                    className="dx-auth__back"
                    disabled={busy}
                    onClick={() => openSignUpPane("choose")}
                  >
                    <ChevronLeft size={16} />
                    Volver
                  </button>
                  <p className="dx-auth__signup-copy">
                    {ACCOUNT_VS_MAILBOX.signupYahooBody}
                  </p>
                  <input
                    type="text"
                    name="dx_fake_user"
                    autoComplete="username"
                    tabIndex={-1}
                    aria-hidden="true"
                    className="dx-auth__honeypot"
                    value=""
                    readOnly
                  />
                  <input
                    type="password"
                    name="dx_fake_pass"
                    autoComplete="current-password"
                    tabIndex={-1}
                    aria-hidden="true"
                    className="dx-auth__honeypot"
                    value=""
                    readOnly
                  />
                  <label className="dx-auth__field">
                    <span>Correo Yahoo</span>
                    <div className="dx-auth__control">
                      <Mail size={18} aria-hidden />
                      <input
                        type="text"
                        name="dx_yahoo_mailbox_email"
                        inputMode="email"
                        autoComplete="off"
                        autoCapitalize="none"
                        autoCorrect="off"
                        spellCheck={false}
                        data-1p-ignore="true"
                        placeholder="tucorreo@yahoo.com"
                        value={yahooEmail}
                        disabled={busy}
                        onChange={(event) => setYahooEmail(event.target.value)}
                      />
                    </div>
                  </label>
                  <p className="dx-auth__signup-copy dx-auth__signup-copy--hint">
                    {ACCOUNT_VS_MAILBOX.signupYahooContinue}
                  </p>
                  <button type="submit" className="dx-auth__submit" disabled={busy}>
                    {busy ? (
                      <>
                        <LoaderCircle className="dx-auth__spin" size={18} />
                        Enviando enlace…
                      </>
                    ) : (
                      "Continuar con enlace a Yahoo"
                    )}
                  </button>
                </form>
              ) : null}

              {signUpPane === "other" ? (
                <div className="dx-auth__other">
                  <button
                    type="button"
                    className="dx-auth__back"
                    disabled={busy}
                    onClick={() => openSignUpPane("choose")}
                  >
                    <ChevronLeft size={16} />
                    Volver
                  </button>
                  <p className="dx-auth__signup-copy">
                    {ACCOUNT_VS_MAILBOX.signupOtherPrompt}
                  </p>
                  <label className="dx-auth__field">
                    <span>Correo a vigilar</span>
                    <div className="dx-auth__control">
                      <Mail size={18} aria-hidden />
                      <input
                        type="email"
                        name="dx_other_mailbox_email"
                        value={otherEmail}
                        inputMode="email"
                        autoComplete="email"
                        autoCapitalize="none"
                        autoCorrect="off"
                        spellCheck={false}
                        placeholder="tu@correo.com"
                        disabled={busy}
                        onChange={(event) => setOtherEmail(event.target.value)}
                        onKeyDown={(event) => {
                          if (event.key === "Enter") {
                            event.preventDefault();
                            continueOtherEmail();
                          }
                        }}
                      />
                    </div>
                  </label>
                  <button
                    type="button"
                    className="dx-auth__submit"
                    disabled={busy}
                    onClick={() => continueOtherEmail()}
                  >
                    {busy ? (
                      <>
                        <LoaderCircle className="dx-auth__spin" size={18} />
                        Continuando…
                      </>
                    ) : (
                      ACCOUNT_VS_MAILBOX.signupOtherContinue
                    )}
                  </button>
                </div>
              ) : null}

              {signUpPane === "other-unrecognized" ? (
                <div className="dx-auth__pending">
                  <button
                    type="button"
                    className="dx-auth__back"
                    onClick={() => openSignUpPane("other")}
                  >
                    <ChevronLeft size={16} />
                    Volver
                  </button>
                  <p className="dx-auth__signup-copy">
                    {ACCOUNT_VS_MAILBOX.signupOtherUnrecognized}
                  </p>
                  {otherEmail.trim() ? (
                    <p className="dx-auth__signup-copy dx-auth__signup-copy--hint">
                      Cuenta: {otherEmail.trim().toLowerCase()}
                    </p>
                  ) : null}
                  <button
                    type="button"
                    className="dx-auth__submit"
                    disabled={busy}
                    onClick={() => void continueUnrecognizedMagicLink()}
                  >
                    {busy ? (
                      <>
                        <LoaderCircle className="dx-auth__spin" size={18} />
                        Enviando enlace…
                      </>
                    ) : (
                      ACCOUNT_VS_MAILBOX.signupOtherMagicLink
                    )}
                  </button>
                </div>
              ) : null}
            </div>
          ) : step === "credentials" ? (
            <div className="dx-auth__signin">
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
                      Gmail
                    </>
                  )}
                </button>
              </div>

              <p className="dx-auth__divider">o con correo y contraseña</p>

              <form
                className="dx-auth__form dx-auth__form--backup"
                onSubmit={submit}
                noValidate
                aria-labelledby="dx-auth-title"
              >
                <label className="dx-auth__field">
                  <span>{ACCOUNT_VS_MAILBOX.loginEmailLabel}</span>
                  <div className="dx-auth__control">
                    <Mail size={18} aria-hidden />
                    <input
                      type="email"
                      name="email"
                      value={email}
                      inputMode="email"
                      autoComplete="email"
                      autoCapitalize="none"
                      autoCorrect="off"
                      spellCheck={false}
                      placeholder="tu@nombre.com"
                      disabled={busy}
                      onChange={(event) => setEmail(event.target.value)}
                    />
                  </div>
                </label>

                <label className="dx-auth__field">
                  <span>{ACCOUNT_VS_MAILBOX.loginPasswordLabel}</span>
                  <div className="dx-auth__control">
                    <KeyRound size={18} aria-hidden />
                    <input
                      type={showPassword ? "text" : "password"}
                      name="password"
                      value={password}
                      autoComplete="current-password"
                      autoCapitalize="none"
                      spellCheck={false}
                      placeholder="Mínimo 8 caracteres"
                      disabled={busy}
                      onChange={(event) => setPassword(event.target.value)}
                    />
                    <button
                      type="button"
                      className="dx-auth__eye"
                      aria-label={
                        showPassword
                          ? "Ocultar contraseña"
                          : "Mostrar contraseña"
                      }
                      onClick={() => setShowPassword((v) => !v)}
                    >
                      {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                </label>

                <button
                  type="button"
                  className="dx-auth__link"
                  disabled={busy}
                  onClick={() => {
                    setStep("help");
                    setError(null);
                  }}
                >
                  Olvidé mi contraseña
                </button>

                <button
                  type="submit"
                  className="dx-auth__submit"
                  disabled={busy}
                >
                  {busy && oauthBusy === null ? (
                    <>
                      <LoaderCircle className="dx-auth__spin" size={18} />
                      Entrando…
                    </>
                  ) : (
                    "Entrar a Donexto"
                  )}
                </button>
              </form>
            </div>
          ) : (
            <div className="dx-auth__help">
              <button
                type="button"
                className="dx-auth__link"
                onClick={() => {
                  setStep("credentials");
                  setError(null);
                }}
              >
                ← Volver al acceso
              </button>

              <p className="dx-auth__help-text">
                Usa el correo de tu cuenta Donexto.
              </p>

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

              <button
                type="button"
                className="dx-auth__secondary"
                disabled={busy}
                onClick={() => void magicLink()}
              >
                <Mail size={18} />
                Enviarme enlace de acceso
              </button>

              <button
                type="button"
                className="dx-auth__secondary is-ghost"
                disabled={busy}
                onClick={() => void recover()}
              >
                Restablecer contraseña Donexto
              </button>
            </div>
          )}

          {mode === "signin" ? (
            <>
              <p className="dx-auth__p0">
                <strong>{DONEXTO_QUALITY.boundary}</strong>
              </p>
              <div className="dx-auth__bottom-mode">
                <button type="button" disabled={busy} onClick={goSignUp}>
                  Crear cuenta
                </button>
              </div>
            </>
          ) : null}

          {mode === "signup" ? (
            <div className="dx-auth__bottom-mode">
              <button type="button" disabled={busy} onClick={goSignIn}>
                {ACCOUNT_VS_MAILBOX.signupHaveAccount}
              </button>
            </div>
          ) : null}

          <p className="dx-auth__secure" role="note">
            <strong>{ACCOUNT_VS_MAILBOX.authSecurityTitle}. </strong>
            {authSecurityBodyFor(
              yahooEmail || otherEmail || email,
            )}
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
