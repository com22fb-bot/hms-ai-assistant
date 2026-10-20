"use client";

import { LoaderCircle } from "lucide-react";
import { FormEvent, useState } from "react";

import "@/components/mailbox-connect.css";

import { useLanguage } from "@/lib/i18n/LanguageProvider";
import {
  GOOGLE_APP_PASSWORDS_URL,
  GOOGLE_TWO_STEP_URL,
  gmailImapText,
} from "@/lib/i18n/gmailImapConnect";

type GmailImapConnectFormProps = {
  email: string;
  emailLocked?: boolean;
  busy?: boolean;
  error?: string | null;
  variant?: "login" | "modal";
  onSubmit: (email: string, appPassword: string) => Promise<void>;
  /** Opción secundaria: Google OAuth. */
  onUseOauth?: () => void;
  onBack?: () => void;
};

/** Guía paso a paso: verificación en dos pasos → contraseña de aplicación → pegar. */
export function GmailImapConnectForm({
  email,
  emailLocked = false,
  busy = false,
  error,
  variant = "modal",
  onSubmit,
  onUseOauth,
  onBack,
}: GmailImapConnectFormProps) {
  const { language } = useLanguage();
  const t = (key: Parameters<typeof gmailImapText>[1]) => gmailImapText(language, key);
  const [draftEmail, setDraftEmail] = useState(email);
  const [appPassword, setAppPassword] = useState("");
  const [showSecret, setShowSecret] = useState(false);
  const shownEmail = emailLocked ? email : draftEmail;
  const login = variant === "login";
  const note = login ? "dx-login__note" : "dx-connect-hint";
  const linkClass = login
    ? "dx-login__secondary dx-mail-open"
    : "dx-connect-btn dx-connect-btn--secondary dx-mail-open";
  const compactLength = appPassword.replace(/[\s-]+/g, "").length;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    try {
      await onSubmit(shownEmail.trim().toLowerCase(), appPassword);
      setAppPassword("");
    } catch {
      // The parent shows the message. Keep the value so the user can retry.
    }
  }

  return (
    <form
      className={login ? "dx-login__form dx-icloud dx-gmail-imap" : "dx-connect-form dx-icloud dx-gmail-imap"}
      onSubmit={(event) => {
        void handleSubmit(event);
      }}
    >
      <p className={note}>{t("intro")}</p>

      <section className="dx-gmail-imap__step">
        <strong>{t("step1Title")}</strong>
        <p className={note}>{t("step1Body")}</p>
        <a className={linkClass} href={GOOGLE_TWO_STEP_URL} target="_blank" rel="noopener noreferrer">
          {t("step1Cta")}
        </a>
      </section>

      <section className="dx-gmail-imap__step">
        <strong>{t("step2Title")}</strong>
        <p className={note}>{t("step2Body")}</p>
        <a className={linkClass} href={GOOGLE_APP_PASSWORDS_URL} target="_blank" rel="noopener noreferrer">
          {t("step2Cta")}
        </a>
      </section>

      <section className="dx-gmail-imap__step">
        <strong>{t("step3Title")}</strong>
        <label className={login ? "dx-login__field" : undefined}>
          <span>{t("emailLabel")}</span>
          <span className={login ? "dx-login__control" : undefined}>
            <input
              type="email"
              name="gmail-imap-email"
              value={shownEmail}
              autoComplete="username"
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck={false}
              readOnly={emailLocked}
              disabled={busy || emailLocked}
              onChange={(event) => setDraftEmail(event.target.value)}
            />
          </span>
        </label>
        <label className={login ? "dx-login__field" : undefined}>
          <span>{t("passwordLabel")}</span>
          <span className={login ? "dx-login__control" : "dx-icloud-secret"}>
            <input
              type={showSecret ? "text" : "password"}
              name="gmail-app-password"
              value={appPassword}
              autoComplete="off"
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck={false}
              placeholder={t("passwordPlaceholder")}
              disabled={busy}
              onChange={(event) => setAppPassword(event.target.value)}
            />
            <button
              type="button"
              className="dx-icloud-reveal"
              onClick={() => setShowSecret((current) => !current)}
            >
              {t(showSecret ? "hidePassword" : "showPassword")}
            </button>
          </span>
        </label>
      </section>

      <p className={note}>{t("privacy")}</p>
      {error ? (
        <div className={login ? "dx-login__alert is-error" : "dx-connect-error"} role="alert">
          {error}
        </div>
      ) : null}
      <button
        type="submit"
        className={login ? "dx-login__submit" : "dx-connect-btn dx-connect-btn--primary"}
        disabled={busy || !shownEmail.trim() || compactLength < 16}
      >
        {busy ? (
          <>
            <LoaderCircle size={18} className="app-spin" />
            {t("submitting")}
          </>
        ) : (
          t("submit")
        )}
      </button>

      {onUseOauth ? (
        <>
          <button type="button" className="dx-connect-back" disabled={busy} onClick={onUseOauth}>
            {t("useOauth")}
          </button>
          <p className={note}>{t("useOauthHint")}</p>
        </>
      ) : null}
      {onBack ? (
        <button type="button" className="dx-connect-back" disabled={busy} onClick={onBack}>
          {t("back")}
        </button>
      ) : null}
    </form>
  );
}
