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
import type { AuthOAuthProvider, YahooAuthIntent } from "@/hooks/useAppAuth";
import { useLanguage } from "@/lib/i18n/LanguageProvider";
import { loginText } from "@/lib/i18n/loginMessages";
import { gateNextAfterResolve } from "@/lib/loginGate";
import {
  isValidSignupEmail,
  resolveMailboxProviderFromEmail,
  suggestKnownMailbox,
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
const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "/api/hms";

type LoginScreenProps = {
  theme: GateThemeId;
  setTheme: (theme: GateThemeId) => void;
  onSignIn: (email: string, password: string) => Promise<void>;
  onSignUp: (
    email: string,
    password: string,
    fullName: string,
  ) => Promise<unknown>;
  onSignInWithGoogle: (email?: string) => Promise<void>;
  onSignInWithYahoo: (
    intent?: YahooAuthIntent,
    email?: string,
  ) => Promise<void>;
  onSignInWithMicrosoft: (
    intent?: YahooAuthIntent,
    email?: string,
  ) => Promise<void>;
  onSignInWithProvider: (
    provider: AuthOAuthProvider,
    email?: string,
  ) => Promise<void>;
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
 * Yahoo: te llevamos al sitio de Yahoo (OAuth). Donexto no pide la clave.
 * Gmail: Google OAuth; la contraseña de Gmail no se pide aquí.
 */
export function LoginScreen({
  theme: _theme,
  setTheme: _setTheme,
  onSignIn,
  onSignUp: _onSignUp,
  onSignInWithGoogle,
  onSignInWithYahoo,
  onSignInWithMicrosoft,
  onSignInWithProvider,
  onMagicLink,
  onResetPassword,
}: LoginScreenProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [usePassword, setUsePassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [oauthBusy, setOauthBusy] = useState<AuthOAuthProvider | null>(null);
  const [confirmingSignup, setConfirmingSignup] = useState(false);
  const [suggestedEmail, setSuggestedEmail] = useState<string | null>(null);
  const emailRef = useRef<HTMLInputElement>(null);
  const passwordRef = useRef<HTMLInputElement>(null);
  const { language } = useLanguage();
  const L = (key: Parameters<typeof loginText>[1]) => loginText(language, key);
  const typedProvider = resolveMailboxProviderFromEmail(email);
  const loginHelper =
    typedProvider === "hotmail"
      ? L("helperMicrosoft")
      : typedProvider === "yahoo"
        ? L("helperYahoo")
        : L("helper");
  const confirmNote =
    typedProvider === "hotmail"
      ? L("confirmMicrosoft")
      : typedProvider === "gmail"
        ? L("confirmGmail")
        : typedProvider === "yahoo"
          ? L("confirmYahoo")
          : L("confirmOther");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const flag = params.get("donexto");
    if (flag === "microsoft_error") {
      setError(
        params.get("reason")
        || L("microsoftOpenFailed"),
      );
    }
    if (flag === "signup") {
      const hinted = (params.get("email") || "").trim().toLowerCase();
      if (isValidSignupEmail(hinted)) {
        setEmail(hinted);
        setConfirmingSignup(true);
      }
    }
    if (!flag) {
      return;
    }
    const url = new URL(window.location.href);
    url.searchParams.delete("donexto");
    url.searchParams.delete("reason");
    url.searchParams.delete("email");
    const cleaned = `${url.pathname}${url.search}${url.hash}`;
    window.history.replaceState({}, "", cleaned || "/");
  }, []);

  function resetAlerts() {
    setError(null);
    setMessage(null);
    setSuggestedEmail(null);
  }

  function blockUnknownMailbox(address: string): boolean {
    if (resolveMailboxProviderFromEmail(address) !== "other") {
      return false;
    }
    const suggested = suggestKnownMailbox(address);
    if (!suggested) {
      return false;
    }
    setSuggestedEmail(suggested);
    setConfirmingSignup(false);
    setError(
      `${L("wantedToSay")} ${suggested}? ${ACCOUNT_VS_MAILBOX.domainFixFallback}`,
    );
    setMessage(null);
    return true;
  }

  async function startOAuth(
    provider: AuthOAuthProvider,
    address: string,
    yahooIntent: YahooAuthIntent = "login",
  ) {
    resetAlerts();
    setBusy(true);
    setOauthBusy(provider);
    try {
      if (provider === "google") {
        await onSignInWithGoogle(address);
      } else if (provider === "yahoo") {
        await onSignInWithYahoo(yahooIntent, address);
      } else if (provider === "azure") {
        await onSignInWithMicrosoft(yahooIntent, address);
      } else {
        await onSignInWithProvider(provider, address);
      }
    } catch (requestError) {
      const fallback =
        provider === "azure"
          ? L("microsoftOpenFailed")
          : provider === "apple"
            ? L("appleOpenFailed")
            : provider === "yahoo"
              ? L("yahooOpenFailed")
              : L("googleOpenFailed");
      setError(
        requestError instanceof Error ? requestError.message : fallback,
      );
      setBusy(false);
      setOauthBusy(null);
    }
  }

  type ResolvePayload = {
    next?: string;
    exists?: boolean;
    message?: string;
    suggested_email?: string | null;
    detail?: { message?: string } | string;
  };

  function stopWithDomain(payload: ResolvePayload, asError: boolean) {
    const text =
      payload.message
      || (asError
        ? ACCOUNT_VS_MAILBOX.domainFixFallback
        : ACCOUNT_VS_MAILBOX.domainPendingFallback);
    setSuggestedEmail(payload.suggested_email || null);
    setConfirmingSignup(false);
    setBusy(false);
    setOauthBusy(null);
    if (asError) {
      setMessage(null);
      setError(text);
    } else {
      setError(null);
      setMessage(text);
    }
  }

  async function continueWithProvider(
    address: string,
    yahooIntent: YahooAuthIntent,
  ) {
    const provider = resolveMailboxProviderFromEmail(address);
    if (provider === "yahoo") {
      await startOAuth("yahoo", address, yahooIntent);
      return;
    }
    if (provider === "hotmail") {
      await startOAuth("azure", address, yahooIntent);
      return;
    }
    if (provider === "gmail" || provider === "apple") {
      stopWithDomain(
        { message: ACCOUNT_VS_MAILBOX.domainPendingFallback },
        false,
      );
      return;
    }
    stopWithDomain(
      { message: ACCOUNT_VS_MAILBOX.domainUnsupportedFallback },
      false,
    );
  }

  async function resolveAndContinue(
    address: string,
    intent: "login" | "signup",
  ) {
    setBusy(true);
    resetAlerts();
    try {
      const response = await fetch(`${API_BASE_URL}/auth/login/resolve`, {
        method: "POST",
        cache: "no-store",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: address }),
      });
      const payload = (await response.json()) as ResolvePayload;
      if (!response.ok) {
        const detail = payload.detail;
        throw new Error(
          typeof detail === "string"
            ? detail
            : detail?.message || L("reviewFailed"),
        );
      }
      const exists = Boolean(payload.exists) && payload.next !== "signup";
      const gate = gateNextAfterResolve(intent, exists, payload.next);
      if (gate === "fix_domain") {
        stopWithDomain(payload, true);
        return;
      }
      if (gate === "pending_review" || gate === "unsupported") {
        stopWithDomain(payload, false);
        return;
      }
      if (gate === "stay_subscribe") {
        setBusy(false);
        setOauthBusy(null);
        setConfirmingSignup(false);
        setMessage(null);
        setError(L("noAccount"));
        return;
      }
      if (gate === "confirm_signup") {
        setBusy(false);
        setOauthBusy(null);
        setError(null);
        setMessage(null);
        setConfirmingSignup(true);
        setUsePassword(false);
        return;
      }
      if (exists) {
        if (payload.next === "yahoo_oauth") {
          await startOAuth("yahoo", address, "login");
          return;
        }
        if (payload.next === "google_oauth") {
          await startOAuth("google", address);
          return;
        }
        if (payload.next === "azure_oauth") {
          await startOAuth("azure", address);
          return;
        }
        if (payload.next === "apple_oauth") {
          await startOAuth("apple", address);
          return;
        }
        stopWithDomain(
          {
            message: L("noActiveService"),
          },
          true,
        );
        return;
      }
      setBusy(false);
      setOauthBusy(null);
      setError(L("noAccount"));
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : L("continueFailed"),
      );
      setBusy(false);
      setOauthBusy(null);
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
        L("invalidEmail"),
      );
      return;
    }
    if (blockUnknownMailbox(clean)) {
      return;
    }
    if (usePassword) {
      if (password.length < 8) {
        setError(L("passwordMin"));
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
            : L("donextoSigninFailed"),
        );
      } finally {
        setBusy(false);
      }
      return;
    }
    await resolveAndContinue(clean, "login");
  }

  async function confirmSignupOnDonexto() {
    if (busy) {
      return;
    }
    const clean = email.trim().toLowerCase();
    if (!isValidSignupEmail(clean)) {
      setError(
        L("invalidEmail"),
      );
      return;
    }
    if (blockUnknownMailbox(clean)) {
      return;
    }
    setBusy(true);
    resetAlerts();
    try {
      const response = await fetch(`${API_BASE_URL}/auth/login/resolve`, {
        method: "POST",
        cache: "no-store",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: clean }),
      });
      const payload = (await response.json()) as ResolvePayload;
      if (!response.ok) {
        const detail = payload.detail;
        throw new Error(
          typeof detail === "string"
            ? detail
            : detail?.message || L("reviewFailed"),
        );
      }
      const exists = Boolean(payload.exists) && payload.next !== "signup";
      const gate = gateNextAfterResolve("signup", exists, payload.next);
      if (gate === "fix_domain") {
        stopWithDomain(payload, true);
        return;
      }
      if (gate === "pending_review" || gate === "unsupported") {
        stopWithDomain(payload, false);
        return;
      }
      if (exists) {
        setConfirmingSignup(false);
        await resolveAndContinue(clean, "login");
        return;
      }
      await continueWithProvider(clean, "signup");
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : L("confirmFailed"),
      );
      setBusy(false);
      setOauthBusy(null);
    }
  }

  async function subscribeWithEmail() {
    if (busy) {
      return;
    }
    const clean = email.trim().toLowerCase();
    if (!isValidSignupEmail(clean)) {
      setError(
        L("invalidEmail"),
      );
      return;
    }
    if (blockUnknownMailbox(clean)) {
      return;
    }
    await resolveAndContinue(clean, "signup");
  }

  async function recoverPassword() {
    const clean = email.trim().toLowerCase();
    if (!isValidSignupEmail(clean)) {
      setError(L("recoverNeedEmail"));
      return;
    }
    setBusy(true);
    resetAlerts();
    try {
      await onResetPassword(clean);
      setMessage(L("resetSent"));
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : L("recoverNeedEmail"),
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
            src="/brand/donexto-logo-official.png"
            width={1024}
            height={1024}
            alt="Donexto — Do Next To…"
            decoding="async"
          />
          <h1 className="dx-auth__sr">Donexto</h1>
          <p className="dx-auth__promise">{L("promise")}</p>
        </div>
      </aside>

      <section className="dx-auth__panel">
        <div className="dx-auth__card" aria-labelledby="dx-auth-title">
          <header className="dx-auth__heading">
            <h2 id="dx-auth-title" className="dx-auth__title">
              {confirmingSignup ? L("confirmTitle") : L("title")}
            </h2>
            <p className="dx-auth__slogan">
              {confirmingSignup ? L("confirmHelper") : loginHelper}
            </p>
          </header>

          {error ? (
            <div className="dx-auth__alert is-error" role="alert">
              <AlertTriangle size={18} />
              <span>{error}</span>
            </div>
          ) : null}
          {suggestedEmail ? (
            <button
              type="button"
              className="dx-auth__secondary"
              disabled={busy}
              onClick={() => {
                setEmail(suggestedEmail);
                setConfirmingSignup(false);
                resetAlerts();
              }}
            >
              {L("useSuggested")}: {suggestedEmail}
            </button>
          ) : null}
          {message ? (
            <div className="dx-auth__alert is-ok" role="status">
              <CheckCircle2 size={18} />
              <span>{message}</span>
            </div>
          ) : null}

          <form
            className="dx-auth__form"
            onSubmit={(event) => {
              event.preventDefault();
              if (confirmingSignup) {
                void confirmSignupOnDonexto();
                return;
              }
              void continueWithEmail(event);
            }}
            noValidate
          >
            {confirmingSignup ? (
              <p className="dx-auth__confirm-email">{email.trim().toLowerCase()}</p>
            ) : null}
            <label className="dx-auth__field">
              <span>
                {confirmingSignup ? L("confirmEmailLabel") : L("emailLabel")}
              </span>
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
                  placeholder={L("emailPlaceholder")}
                  disabled={busy}
                  onChange={(event) => setEmail(event.target.value)}
                />
              </div>
            </label>

            {usePassword ? (
              <label className="dx-auth__field">
                <span>{L("passwordLabel")}</span>
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
                    placeholder={L("passwordPlaceholder")}
                    disabled={busy}
                    onChange={(event) => setPassword(event.target.value)}
                  />
                  <button
                    type="button"
                    className="dx-auth__eye"
                    aria-label={
                      showPassword ? L("hidePassword") : L("showPassword")
                    }
                    onClick={() => setShowPassword((value) => !value)}
                  >
                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
              </label>
            ) : null}

            {confirmingSignup ? (
              <>
                <p className="dx-auth__signup-copy">{confirmNote}</p>
                <button type="submit" className="dx-auth__submit" disabled={busy}>
                  {busy ? (
                    <>
                      <LoaderCircle className="dx-auth__spin" size={18} />
                      {L("confirming")}
                    </>
                  ) : (
                    L("confirmCta")
                  )}
                </button>
                <button
                  type="button"
                  className="dx-auth__secondary"
                  disabled={busy}
                  onClick={() => {
                    setConfirmingSignup(false);
                    resetAlerts();
                  }}
                >
                  {L("confirmBack")}
                </button>
              </>
            ) : (
              <>
            <button type="submit" className="dx-auth__submit" disabled={busy}>
              {busy && oauthBusy === null ? (
                <>
                  <LoaderCircle className="dx-auth__spin" size={18} />
                  {L("continuing")}
                </>
              ) : oauthBusy ? (
                <>
                  <LoaderCircle className="dx-auth__spin" size={18} />
                  {L("openingMailbox")}
                </>
              ) : (
                L("continueCta")
              )}
            </button>
            <button
              type="button"
              className="dx-auth__secondary"
              disabled={busy}
              onClick={() => void subscribeWithEmail()}
            >
              {L("subscribeCta")}
            </button>
              </>
            )}
          </form>

          {confirmingSignup ? null : (
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
              {usePassword ? L("enterWithLink") : L("havePassword")}
            </button>
            {usePassword ? (
              <button
                type="button"
                className="dx-auth__link"
                disabled={busy}
                onClick={() => void recoverPassword()}
              >
                {L("forgotPassword")}
              </button>
            ) : null}
          </div>
          )}

          <div
            className="dx-auth__services"
            aria-label={`${L("servicesKicker")} ${L("servicesActive")}`}
          >
            <p className="dx-auth__services-kicker">
              {L("servicesKicker")}{" "}
              <span>{L("servicesActive")}</span>
            </p>
            <ul className="dx-auth__services-list">
              <li className="dx-auth__service">
                <ProviderMark provider="yahoo" />
                <span>{L("serviceYahoo")}</span>
              </li>
              <li className="dx-auth__service dx-auth__service--microsoft">
                <ProviderMark provider="hotmail" />
                <span>
                  <strong>{L("serviceMicrosoftTitle")}</strong>
                  <small>{L("serviceMicrosoftDomains")}</small>
                </span>
              </li>
              <li className="dx-auth__service">
                <ProviderMark provider="gmail" />
                <span>{L("serviceGoogle")}</span>
              </li>
            </ul>
          </div>

          <LanguageStrip />

          <p className="dx-auth__legal-agree">
            {L("legalBefore")}{" "}
            <a href={TERMS_URL} target="_blank" rel="noopener noreferrer">
              {L("terms")}
            </a>{" "}
            {L("legalAnd")}{" "}
            <a href={PRIVACY_URL} target="_blank" rel="noopener noreferrer">
              {L("privacy")}
            </a>{" "}
            {L("legalAfter")}
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
