"use client";

import { LoaderCircle } from "lucide-react";
import { FormEvent, useState } from "react";

import { useLanguage } from "@/lib/i18n/LanguageProvider";
import { icloudSteps, icloudText } from "@/lib/i18n/icloudConnect";

type IcloudConnectFormProps = {
  email: string;
  emailLocked?: boolean;
  busy?: boolean;
  error?: string | null;
  variant?: "login" | "modal";
  onSubmit: (email: string, appPassword: string) => Promise<void>;
  onBack?: () => void;
};

export function IcloudConnectForm({
  email,
  emailLocked = false,
  busy = false,
  error,
  variant = "modal",
  onSubmit,
  onBack,
}: IcloudConnectFormProps) {
  const { language } = useLanguage();
  const [draftEmail, setDraftEmail] = useState(email);
  const [appPassword, setAppPassword] = useState("");
  const [showSecret, setShowSecret] = useState(false);
  const steps = icloudSteps(language);
  const shownEmail = emailLocked ? email : draftEmail;
  const login = variant === "login";

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) {
      return;
    }
    try {
      await onSubmit(shownEmail.trim().toLowerCase(), appPassword);
      setAppPassword("");
    } catch {
      // The parent surfaces the message. Keep the app password so the user can retry.
    }
  }

  return (
    <form
      className={login ? "dx-login__form dx-icloud" : "dx-connect-form dx-icloud"}
      onSubmit={(event) => {
        void handleSubmit(event);
      }}
    >
      <p className={login ? "dx-login__note" : "dx-connect-hint"}>
        {icloudText(language, "intro")}
      </p>
      <ol className="dx-icloud-steps">
        {steps.map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ol>
      <label className={login ? "dx-login__field" : undefined}>
        <span>{icloudText(language, "emailLabel")}</span>
        {login ? (
          <div className="dx-login__control">
            <input
              type="email"
              name="icloud-email"
              value={shownEmail}
              autoComplete="username"
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck={false}
              readOnly={emailLocked}
              disabled={busy || emailLocked}
              onChange={(event) => setDraftEmail(event.target.value)}
            />
          </div>
        ) : (
          <input
            type="email"
            name="icloud-email"
            value={shownEmail}
            autoComplete="username"
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
            readOnly={emailLocked}
            disabled={busy || emailLocked}
            onChange={(event) => setDraftEmail(event.target.value)}
          />
        )}
      </label>
      <label className={login ? "dx-login__field" : undefined}>
        <span>{icloudText(language, "passwordLabel")}</span>
        {login ? (
          <div className="dx-login__control">
            <input
              type={showSecret ? "text" : "password"}
              name="icloud-app-password"
              value={appPassword}
              autoComplete="off"
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck={false}
              placeholder={icloudText(language, "passwordPlaceholder")}
              disabled={busy}
              onChange={(event) => setAppPassword(event.target.value)}
            />
            <button
              type="button"
              className="dx-icloud-reveal"
              onClick={() => setShowSecret((current) => !current)}
            >
              {icloudText(language, showSecret ? "hidePassword" : "showPassword")}
            </button>
          </div>
        ) : (
          <span className="dx-icloud-secret">
            <input
              type={showSecret ? "text" : "password"}
              name="icloud-app-password"
              value={appPassword}
              autoComplete="off"
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck={false}
              placeholder={icloudText(language, "passwordPlaceholder")}
              disabled={busy}
              onChange={(event) => setAppPassword(event.target.value)}
            />
            <button
              type="button"
              className="dx-icloud-reveal"
              onClick={() => setShowSecret((current) => !current)}
            >
              {icloudText(language, showSecret ? "hidePassword" : "showPassword")}
            </button>
          </span>
        )}
      </label>
      <p className={login ? "dx-login__note" : "dx-connect-hint"}>
        {icloudText(language, "privacy")}
      </p>
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
            {icloudText(language, "submitting")}
          </>
        ) : (
          icloudText(language, "submit")
        )}
      </button>
      {onBack ? (
        <button type="button" className="dx-connect-back" disabled={busy} onClick={onBack}>
          {icloudText(language, "back")}
        </button>
      ) : null}
    </form>
  );
}
