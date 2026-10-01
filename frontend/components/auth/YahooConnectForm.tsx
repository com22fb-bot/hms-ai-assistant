"use client";

import { LoaderCircle } from "lucide-react";
import { FormEvent, useState } from "react";

import { useLanguage } from "@/lib/i18n/LanguageProvider";
import { mailboxNoticeText, yahooSteps } from "@/lib/i18n/mailboxNotices";

type YahooConnectFormProps = {
  email: string;
  emailLocked?: boolean;
  busy?: boolean;
  error?: string | null;
  variant?: "login" | "modal";
  onSubmit: (email: string, appPassword: string) => Promise<void>;
  onBack?: () => void;
};

export function YahooConnectForm({
  email,
  emailLocked = false,
  busy = false,
  error,
  variant = "modal",
  onSubmit,
  onBack,
}: YahooConnectFormProps) {
  const { language } = useLanguage();
  const [draftEmail, setDraftEmail] = useState(email);
  const [appPassword, setAppPassword] = useState("");
  const [showSecret, setShowSecret] = useState(false);
  const steps = yahooSteps(language);
  const shownEmail = emailLocked ? email : draftEmail;
  const login = variant === "login";
  const text = (key: Parameters<typeof mailboxNoticeText>[1]) =>
    mailboxNoticeText(language, key);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) {
      return;
    }
    try {
      await onSubmit(shownEmail.trim().toLowerCase(), appPassword);
      setAppPassword("");
    } catch {
      // Keep the app password so the user can retry.
    }
  }

  return (
    <form
      className={login ? "dx-login__form dx-icloud" : "dx-connect-form dx-icloud"}
      onSubmit={(event) => {
        void handleSubmit(event);
      }}
    >
      <p className={login ? "dx-login__note" : "dx-connect-hint"}>{text("yahooIntro")}</p>
      <ol className="dx-mail-steps">
        {steps.map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ol>
      <label className={login ? "dx-login__field" : undefined}>
        <span>{text("yahooEmail")}</span>
        <input
          type="email"
          name="yahoo-email"
          value={shownEmail}
          autoComplete="username"
          autoCapitalize="none"
          spellCheck={false}
          readOnly={emailLocked}
          disabled={busy || emailLocked}
          onChange={(event) => setDraftEmail(event.target.value)}
        />
      </label>
      <label className={login ? "dx-login__field" : undefined}>
        <span>{text("yahooPassword")}</span>
        <span className="dx-icloud-secret">
          <input
            type={showSecret ? "text" : "password"}
            name="yahoo-app-password"
            value={appPassword}
            autoComplete="off"
            spellCheck={false}
            placeholder={text("yahooPasswordPlaceholder")}
            disabled={busy}
            onChange={(event) => setAppPassword(event.target.value)}
          />
          <button
            type="button"
            className="dx-icloud-reveal"
            onClick={() => setShowSecret((current) => !current)}
          >
            {text(showSecret ? "yahooHide" : "yahooShow")}
          </button>
        </span>
      </label>
      <p className={login ? "dx-login__note" : "dx-connect-hint"}>{text("yahooPrivacy")}</p>
      {error ? (
        <div className={login ? "dx-login__alert is-error" : "dx-connect-error"} role="alert">
          {error}
        </div>
      ) : null}
      <button
        type="submit"
        className={login ? "dx-login__submit" : "dx-connect-btn dx-connect-btn--primary"}
        disabled={busy || !shownEmail.trim() || appPassword.trim().length < 8}
      >
        {busy ? (
          <>
            <LoaderCircle size={18} className="app-spin" />
            {text("yahooSubmitting")}
          </>
        ) : (
          text("yahooSubmit")
        )}
      </button>
      {onBack ? (
        <button type="button" className="dx-connect-back" disabled={busy} onClick={onBack}>
          {text("yahooBack")}
        </button>
      ) : null}
    </form>
  );
}
