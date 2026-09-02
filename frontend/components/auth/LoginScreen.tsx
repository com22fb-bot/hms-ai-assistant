"use client";

import {
  AlertTriangle,
  CheckCircle2,
  LoaderCircle,
  Mail,
} from "lucide-react";
import { FormEvent, useEffect, useRef, useState } from "react";

import { LanguageStrip } from "@/components/UserSettingsPanel";
import { ACCOUNT_VS_MAILBOX } from "@/lib/accountVsMailbox";
import type { AuthOAuthProvider, YahooAuthIntent } from "@/hooks/useAppAuth";
import { useLanguage } from "@/lib/i18n/LanguageProvider";
import { loginText, loginTextReplace } from "@/lib/i18n/loginMessages";
import {
  comingSoonProviderLabel,
  gateNextAfterResolve,
  isComingSoonGate,
  oauthFromResolveNext,
  type AuthGateNext,
} from "@/lib/loginGate";
import {
  isBrowserNetworkError,
  postPublicHms,
} from "@/lib/publicHms";
import {
  isValidSignupEmail,
  resolveMailboxProviderFromEmail,
  suggestKnownMailbox,
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

type GateStep = "email" | "confirm" | "waitlist";

type ResolvePayload = {
  next?: string;
  exists?: boolean;
  provider?: string;
  message?: string;
  suggested_email?: string | null;
  detail?: { message?: string } | string;
};

const LIVE_CHIPS = [
  { id: "outlook", labelKey: "chipOutlook" as const, tone: "live" },
  { id: "hotmail", labelKey: "chipHotmail" as const, tone: "live" },
  { id: "live", labelKey: "chipLive" as const, tone: "live" },
  { id: "msn", labelKey: "chipMsn" as const, tone: "live" },
  { id: "m365", labelKey: "chipM365" as const, tone: "live" },
];

const SOON_CHIPS = [
  { id: "gmail", labelKey: "chipGmail" as const, tone: "gmail" },
  { id: "workspace", labelKey: "chipWorkspace" as const, tone: "gmail" },
  { id: "yahoo", labelKey: "chipYahoo" as const, tone: "yahoo" },
  { id: "icloud", labelKey: "chipIcloud" as const, tone: "apple" },
];

/**
 * Acceso Donexto: un correo (el buzón) y un Continuar.
 * Hoy leemos Outlook/Hotmail/M365. Gmail/Yahoo/iCloud: lista de aviso.
 * Donexto no pide contraseña de correo ni de cuenta.
 */
export function LoginScreen({
  onSignInWithGoogle,
  onSignInWithYahoo,
  onSignInWithMicrosoft,
  onSignInWithProvider,
}: LoginScreenProps) {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [oauthBusy, setOauthBusy] = useState<AuthOAuthProvider | null>(null);
  const [step, setStep] = useState<GateStep>("email");
  const [suggestedEmail, setSuggestedEmail] = useState<string | null>(null);
  const [waitlistProvider, setWaitlistProvider] = useState("Gmail");
  const [waitlistKind, setWaitlistKind] = useState<"coming_soon" | "company">(
    "coming_soon",
  );
  const emailRef = useRef<HTMLInputElement>(null);
  const { language } = useLanguage();
  const L = (key: Parameters<typeof loginText>[1]) => loginText(language, key);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const flag = params.get("donexto");
    if (!flag) {
      return;
    }
    const hinted = (params.get("email") || "").trim().toLowerCase();
    const reason = params.get("reason");
    const url = new URL(window.location.href);
    url.searchParams.delete("donexto");
    url.searchParams.delete("reason");
    url.searchParams.delete("email");
    const cleaned = `${url.pathname}${url.search}${url.hash}`;
    window.history.replaceState({}, "", cleaned || "/");
    const frame = window.requestAnimationFrame(() => {
      if (flag === "microsoft_error") {
        setError(reason || loginText(language, "microsoftOpenFailed"));
      }
      if (flag === "signup" && isValidSignupEmail(hinted)) {
        setEmail(hinted);
        setStep("confirm");
      }
    });
    return () => window.cancelAnimationFrame(frame);
  }, [language]);

  useEffect(() => {
    if (step === "email") {
      return;
    }
    document.getElementById("dx-auth-title")?.scrollIntoView({
      block: "start",
      behavior: "smooth",
    });
  }, [step]);

  useEffect(() => {
    const viewport = window.visualViewport;
    if (!viewport) {
      return;
    }
    const syncKeyboardGap = () => {
      const covered = Math.max(
        0,
        window.innerHeight - viewport.height - viewport.offsetTop,
      );
      document.documentElement.style.setProperty(
        "--dx-keyboard-gap",
        `${covered}px`,
      );
    };
    syncKeyboardGap();
    viewport.addEventListener("resize", syncKeyboardGap);
    viewport.addEventListener("scroll", syncKeyboardGap);
    return () => {
      viewport.removeEventListener("resize", syncKeyboardGap);
      viewport.removeEventListener("scroll", syncKeyboardGap);
      document.documentElement.style.removeProperty("--dx-keyboard-gap");
    };
  }, []);

  function friendlyError(requestError: unknown, fallback: string): string {
    if (isBrowserNetworkError(requestError)) {
      return L("networkFailed");
    }
    return requestError instanceof Error ? requestError.message : fallback;
  }

  function resetAlerts() {
    setError(null);
    setMessage(null);
    setSuggestedEmail(null);
  }

  function focusEmail() {
    window.requestAnimationFrame(() => {
      emailRef.current?.focus();
      emailRef.current?.select();
    });
  }

  function showStayOnEmail(text: string, asError: boolean) {
    setStep("email");
    setBusy(false);
    setOauthBusy(null);
    if (asError) {
      setMessage(null);
      setError(text);
    } else {
      setError(null);
      setMessage(text);
    }
    focusEmail();
  }

  function openWaitlist(kind: "coming_soon" | "company", providerLabel: string) {
    setWaitlistKind(kind);
    setWaitlistProvider(providerLabel);
    setBusy(false);
    setOauthBusy(null);
    setError(null);
    setMessage(null);
    setStep("waitlist");
  }

  function handleComingSoonGate(gate: AuthGateNext, payload: ResolvePayload) {
    if (gate === "unsupported_imap_domain" || gate === "waitlist") {
      openWaitlist("company", "Microsoft 365");
      return true;
    }
    if (isComingSoonGate(gate) || gate === "icloud_unavailable") {
      openWaitlist(
        "coming_soon",
        comingSoonProviderLabel(payload.next, payload.provider),
      );
      return true;
    }
    return false;
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
    setStep("email");
    setError(
      `${L("wantedToSay")} ${suggested}? ${ACCOUNT_VS_MAILBOX.domainFixFallback}`,
    );
    setMessage(null);
    focusEmail();
    return true;
  }

  async function startOAuth(
    provider: AuthOAuthProvider,
    address: string,
    yahooIntent: YahooAuthIntent = "login",
  ) {
    if (provider === "apple") {
      openWaitlist("coming_soon", "iCloud");
      return;
    }
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
          : provider === "yahoo"
            ? L("yahooOpenFailed")
            : L("googleOpenFailed");
      setError(friendlyError(requestError, fallback));
      setBusy(false);
      setOauthBusy(null);
    }
  }

  function stopWithDomain(payload: ResolvePayload, asError: boolean) {
    const text =
      payload.message
      || (asError
        ? ACCOUNT_VS_MAILBOX.domainFixFallback
        : ACCOUNT_VS_MAILBOX.domainPendingFallback);
    setSuggestedEmail(payload.suggested_email || null);
    showStayOnEmail(text, asError);
  }

  async function continueWithProvider(
    address: string,
    yahooIntent: YahooAuthIntent,
  ) {
    const provider = resolveMailboxProviderFromEmail(address);
    if (provider === "hotmail") {
      await startOAuth("azure", address, yahooIntent);
      return;
    }
    if (provider === "yahoo") {
      openWaitlist("coming_soon", "Yahoo");
      return;
    }
    if (provider === "gmail") {
      openWaitlist("coming_soon", "Gmail");
      return;
    }
    if (provider === "apple") {
      openWaitlist("coming_soon", "iCloud");
      return;
    }
    openWaitlist("company", "Microsoft 365");
  }

  async function resolvePayload(address: string): Promise<ResolvePayload> {
    const resolved = await postPublicHms("/auth/login/resolve", {
      email: address,
    });
    const payload = (resolved.payload || {}) as ResolvePayload;
    if (!resolved.ok) {
      const detail = payload.detail;
      throw new Error(
        typeof detail === "string"
          ? detail
          : detail?.message || L("reviewFailed"),
      );
    }
    return payload;
  }

  async function resolveAndContinue(address: string) {
    setBusy(true);
    resetAlerts();
    try {
      const payload = await resolvePayload(address);
      const exists = Boolean(payload.exists) && payload.next !== "signup";
      const gate = gateNextAfterResolve(
        exists ? "login" : "signup",
        exists,
        payload.next,
        payload.provider,
      );
      if (handleComingSoonGate(gate, payload)) {
        return;
      }
      if (gate === "fix_domain") {
        stopWithDomain(payload, true);
        return;
      }
      if (gate === "confirm_first_time") {
        setBusy(false);
        setOauthBusy(null);
        setError(null);
        setMessage(null);
        setStep("confirm");
        return;
      }
      const oauth = oauthFromResolveNext(payload.next);
      if (oauth) {
        await startOAuth(oauth, address, "login");
        return;
      }
      showStayOnEmail(L("noActiveService"), true);
    } catch (requestError) {
      setError(friendlyError(requestError, L("continueFailed")));
      setBusy(false);
      setOauthBusy(null);
      setStep("email");
    }
  }

  async function continueWithEmail(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) {
      return;
    }
    const clean = email.trim().toLowerCase();
    if (!isValidSignupEmail(clean)) {
      setError(L("invalidEmail"));
      focusEmail();
      return;
    }
    if (email !== clean) {
      setEmail(clean);
    }
    if (blockUnknownMailbox(clean)) {
      return;
    }
    await resolveAndContinue(clean);
  }

  async function confirmFirstTime() {
    if (busy) {
      return;
    }
    const clean = email.trim().toLowerCase();
    if (!isValidSignupEmail(clean)) {
      setError(L("invalidEmail"));
      setStep("email");
      focusEmail();
      return;
    }
    if (blockUnknownMailbox(clean)) {
      return;
    }
    setBusy(true);
    resetAlerts();
    try {
      const payload = await resolvePayload(clean);
      const exists = Boolean(payload.exists) && payload.next !== "signup";
      const gate = gateNextAfterResolve(
        "signup",
        exists,
        payload.next,
        payload.provider,
      );
      if (handleComingSoonGate(gate, payload)) {
        return;
      }
      if (gate === "fix_domain") {
        stopWithDomain(payload, true);
        return;
      }
      if (exists) {
        setStep("email");
        await resolveAndContinue(clean);
        return;
      }
      await continueWithProvider(clean, "signup");
    } catch (requestError) {
      setError(friendlyError(requestError, L("confirmFailed")));
      setBusy(false);
      setOauthBusy(null);
    }
  }

  async function joinWaitlist() {
    if (busy) {
      return;
    }
    const clean = email.trim().toLowerCase();
    const provider = resolveMailboxProviderFromEmail(clean);
    setBusy(true);
    resetAlerts();
    try {
      const resolved = await postPublicHms("/auth/login/waitlist", {
        email: clean,
        provider: waitlistKind === "company" ? "other" : provider,
      });
      const payload = (resolved.payload || {}) as { message?: string };
      setBusy(false);
      setStep("email");
      setMessage(payload.message || L("waitlistThanks"));
      focusEmail();
    } catch (requestError) {
      setError(friendlyError(requestError, L("continueFailed")));
      setBusy(false);
    }
  }

  function goChangeEmail() {
    resetAlerts();
    setStep("email");
    setError(L("changeEmailExplain"));
    focusEmail();
  }

  function goLater() {
    resetAlerts();
    setStep("email");
    focusEmail();
  }

  const confirming = step === "confirm";
  const waiting = step === "waitlist";
  const displayEmail = email.trim().toLowerCase();
  const waitlistBody =
    waitlistKind === "company"
      ? L("companyImapWaitlist")
      : loginTextReplace(language, "waitlistBody", {
          provider: waitlistProvider,
        });

  return (
    <main
      className={
        confirming || waiting ? "dx-auth dx-auth--confirm" : "dx-auth"
      }
    >
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
              {waiting
                ? L("waitlistTitle")
                : confirming
                  ? L("confirmTitle")
                  : L("title")}
            </h2>
            {waiting ? (
              <p className="dx-auth__slogan">{waitlistBody}</p>
            ) : confirming ? (
              <p className="dx-auth__slogan">{L("confirmHelper")}</p>
            ) : (
              <>
                <p className="dx-auth__slogan">{L("body")}</p>
                <p className="dx-auth__note">{L("noPasswordNote")}</p>
              </>
            )}
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
                setStep("email");
                resetAlerts();
                focusEmail();
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
              if (waiting) {
                void joinWaitlist();
                return;
              }
              if (confirming) {
                void confirmFirstTime();
                return;
              }
              void continueWithEmail(event);
            }}
            noValidate
          >
            {confirming || waiting ? (
              <p className="dx-auth__confirm-email">{displayEmail}</p>
            ) : (
              <label className="dx-auth__field">
                <span>{L("emailLabel")}</span>
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
            )}

            {waiting ? (
              <div className="dx-auth__actions">
                <button type="submit" className="dx-auth__submit" disabled={busy}>
                  {busy ? (
                    <>
                      <LoaderCircle className="dx-auth__spin" size={18} />
                      {L("continuing")}
                    </>
                  ) : (
                    L("waitlistNotify")
                  )}
                </button>
                <button
                  type="button"
                  className="dx-auth__later"
                  disabled={busy}
                  onClick={goLater}
                >
                  {L("waitlistLater")}
                </button>
              </div>
            ) : confirming ? (
              <div className="dx-auth__actions">
                <button type="submit" className="dx-auth__submit" disabled={busy}>
                  {busy ? (
                    <>
                      <LoaderCircle className="dx-auth__spin" size={18} />
                      {oauthBusy ? L("openingMailbox") : L("confirming")}
                    </>
                  ) : (
                    L("yesContinue")
                  )}
                </button>
                <button
                  type="button"
                  className="dx-auth__secondary"
                  disabled={busy}
                  onClick={goChangeEmail}
                >
                  {L("changeEmail")}
                </button>
                <button
                  type="button"
                  className="dx-auth__later"
                  disabled={busy}
                  onClick={goLater}
                >
                  {L("later")}
                </button>
              </div>
            ) : (
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
            )}
          </form>

          {step === "email" ? (
            <div className="dx-auth__availability" aria-label={L("servicesKicker")}>
              <p className="dx-auth__services-kicker">
                {L("availableNow")}
              </p>
              <ul className="dx-auth__chips">
                {LIVE_CHIPS.map((chip) => (
                  <li
                    key={chip.id}
                    className={`dx-auth__chip dx-auth__chip--${chip.tone}`}
                  >
                    {L(chip.labelKey)}
                  </li>
                ))}
              </ul>
              <p className="dx-auth__services-kicker dx-auth__services-kicker--soon">
                {L("comingSoonBadge")}
              </p>
              <ul className="dx-auth__chips">
                {SOON_CHIPS.map((chip) => (
                  <li
                    key={chip.id}
                    className={`dx-auth__chip dx-auth__chip--soon dx-auth__chip--${chip.tone}`}
                  >
                    {L(chip.labelKey)}
                    <span>{L("comingSoonBadge")}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          <LanguageStrip compact className="dx-lang-strip--gate" />

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
