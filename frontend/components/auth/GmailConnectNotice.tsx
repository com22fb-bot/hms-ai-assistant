"use client";

import { LoaderCircle } from "lucide-react";

import { useLanguage } from "@/lib/i18n/LanguageProvider";
import { gmailSteps, mailboxNoticeText } from "@/lib/i18n/mailboxNotices";

type GmailConnectNoticeProps = {
  email: string;
  busy?: boolean;
  error?: string | null;
  variant?: "login" | "modal";
  onContinue: () => Promise<void>;
  onBack?: () => void;
};

export function GmailConnectNotice({
  email,
  busy = false,
  error,
  variant = "modal",
  onContinue,
  onBack,
}: GmailConnectNoticeProps) {
  const { language } = useLanguage();
  const login = variant === "login";
  const steps = gmailSteps(language);
  const text = (key: Parameters<typeof mailboxNoticeText>[1]) =>
    mailboxNoticeText(language, key);

  return (
    <form
      className={login ? "dx-login__form dx-icloud" : "dx-connect-form dx-icloud"}
      onSubmit={(event) => {
        event.preventDefault();
        if (!busy) {
          void onContinue();
        }
      }}
    >
      <p className={login ? "dx-login__note" : "dx-connect-hint"}>{text("gmailIntro")}</p>
      <ol className="dx-mail-steps">
        {steps.map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ol>
      <p className={login ? "dx-login__note" : "dx-connect-hint"}>{text("gmailEarly")}</p>
      <p className={login ? "dx-login__note" : "dx-connect-hint"}>{text("gmailPrivacy")}</p>
      <p className={login ? "dx-login__note" : "dx-connect-hint"}>
        <strong>{email}</strong>
      </p>
      {error ? (
        <div className={login ? "dx-login__alert is-error" : "dx-connect-error"} role="alert">
          {error}
        </div>
      ) : null}
      <button
        type="submit"
        className={login ? "dx-login__submit" : "dx-connect-btn dx-connect-btn--primary"}
        disabled={busy}
      >
        {busy ? (
          <>
            <LoaderCircle size={18} className="app-spin" />
            {text("gmailSubmitting")}
          </>
        ) : (
          text("gmailSubmit")
        )}
      </button>
      {onBack ? (
        <button type="button" className="dx-connect-back" disabled={busy} onClick={onBack}>
          {text("gmailBack")}
        </button>
      ) : null}
    </form>
  );
}
