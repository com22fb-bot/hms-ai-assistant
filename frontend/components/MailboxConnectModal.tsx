"use client";

import { ExternalLink, LoaderCircle, Mail, X } from "lucide-react";
import { FormEvent, useState } from "react";

import { AccountVsMailboxHint } from "@/components/auth/AccountVsMailboxHint";
import {
  ACCOUNT_VS_MAILBOX,
  authorizeMailboxTitle,
} from "@/lib/accountVsMailbox";
import type { MailboxConnectMode } from "@/lib/mailboxSignup";
import {
  formatYahooAppPassword,
  YAHOO_ACCOUNT_SECURITY_URL,
  YAHOO_APP_PASSWORD_HELP_URL,
  YAHOO_APP_PASSWORD_NAME,
  YAHOO_CODE_TOO_LONG,
  YAHOO_CODE_TOO_SHORT,
  YAHOO_CONNECT_CTA,
  YAHOO_CONNECT_LEAD,
  YAHOO_CONNECT_TITLE,
  YAHOO_OPEN_SECURITY_CTA,
  YAHOO_PASTE_LABEL,
  YAHOO_STEPS,
  YAHOO_TWO_STEP_TIP,
  yahooAppPasswordCharCount,
} from "@/lib/yahooAppPasswordGuide";

import "./mailbox-connect.css";

type ProviderChoice = "choose" | "yahoo";

type MailboxConnectModalProps = {
  open: boolean;
  connectingYahoo: boolean;
  required?: boolean;
  accountEmail: string;
  mode?: MailboxConnectMode;
  onClose: () => void;
  onConnectGoogle: () => void | Promise<void>;
  onConnectYahoo: (email: string, appPassword: string) => Promise<void>;
};

export function MailboxConnectModal({
  open,
  connectingYahoo,
  required = false,
  accountEmail,
  mode = "choose",
  onClose,
  onConnectGoogle,
  onConnectYahoo,
}: MailboxConnectModalProps) {
  const [step, setStep] = useState<ProviderChoice>(
    mode === "yahoo" ? "yahoo" : "choose",
  );
  const [yahooEmail, setYahooEmail] = useState(
    mode === "yahoo" ? accountEmail : "",
  );
  const [yahooPassword, setYahooPassword] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);
  const [connectingGoogle, setConnectingGoogle] = useState(false);
  const [yahooTabOpened, setYahooTabOpened] = useState(false);

  const yahooLocked = mode === "yahoo";
  const showChooser = mode === "choose" && step === "choose";
  const showYahooForm = mode === "yahoo" || step === "yahoo";
  const canDismiss = !required;
  const mailboxEmail = yahooLocked ? accountEmail : yahooEmail;
  const codeChars = yahooAppPasswordCharCount(yahooPassword);

  if (!open) {
    return null;
  }

  async function handleGoogleClick() {
    setLocalError(null);
    setConnectingGoogle(true);
    try {
      await onConnectGoogle();
    } catch (error) {
      setLocalError(
        error instanceof Error
          ? error.message
          : "No fue posible iniciar la conexión con Gmail.",
      );
      setConnectingGoogle(false);
    }
  }

  async function handleYahooSubmit(event: FormEvent) {
    event.preventDefault();
    setLocalError(null);

    const chars = yahooAppPasswordCharCount(yahooPassword);
    if (chars > 16) {
      setLocalError(YAHOO_CODE_TOO_LONG);
      return;
    }
    if (chars !== 16) {
      setLocalError(YAHOO_CODE_TOO_SHORT);
      return;
    }

    try {
      await onConnectYahoo(mailboxEmail, yahooPassword);
      setYahooPassword("");
      onClose();
    } catch (error) {
      setLocalError(
        error instanceof Error
          ? error.message
          : "No fue posible conectar Yahoo.",
      );
    }
  }

  const showingYahooGuide = showYahooForm && !showChooser && mode !== "gmail";

  const title =
    mode === "gmail"
      ? authorizeMailboxTitle(accountEmail)
      : showingYahooGuide
        ? YAHOO_CONNECT_TITLE
        : ACCOUNT_VS_MAILBOX.connectChooserTitle;

  const body =
    mode === "gmail"
      ? ACCOUNT_VS_MAILBOX.connectGmailBody
      : showingYahooGuide
        ? YAHOO_CONNECT_LEAD
        : ACCOUNT_VS_MAILBOX.connectChooserBody;

  return (
    <div className="dx-connect-overlay" role="dialog" aria-modal="true">
      <section
        className={
          showingYahooGuide
            ? "dx-connect-card dx-connect-card--guide"
            : "dx-connect-card"
        }
      >
        <header className="dx-connect-header">
          <div>
            <strong>{title}</strong>
            <p>{body}</p>
          </div>
          {canDismiss ? (
            <button
              type="button"
              className="dx-connect-icon-btn"
              onClick={() => {
                if (step === "yahoo" && mode === "choose") {
                  setStep("choose");
                  setLocalError(null);
                  return;
                }
                onClose();
              }}
              aria-label={
                step === "yahoo" && mode === "choose"
                  ? "Volver a elegir proveedor"
                  : "Cerrar"
              }
            >
              <X size={20} />
            </button>
          ) : null}
        </header>

        <div className="dx-connect-body">
          {mode === "gmail" ? (
            <>
              <AccountVsMailboxHint variant="connect" email={accountEmail} />
              {localError ? (
                <div className="dx-connect-error" role="alert">
                  {localError}
                </div>
              ) : null}
              <button
                type="button"
                className="dx-connect-btn dx-connect-btn--primary"
                disabled={connectingGoogle}
                onClick={() => void handleGoogleClick()}
              >
                {connectingGoogle ? (
                  <>
                    <LoaderCircle size={18} className="app-spin" />
                    Abriendo Google…
                  </>
                ) : (
                  <>
                    <Mail size={18} />
                    {ACCOUNT_VS_MAILBOX.connectGmailCta}
                  </>
                )}
              </button>
              <p className="dx-connect-hint">
                {ACCOUNT_VS_MAILBOX.connectGoogleHint}
              </p>
            </>
          ) : showChooser ? (
            <>
              <AccountVsMailboxHint variant="connect" email={accountEmail} />
              {localError ? (
                <div className="dx-connect-error" role="alert">
                  {localError}
                </div>
              ) : null}
              <button
                type="button"
                className="dx-connect-btn dx-connect-btn--primary"
                disabled={connectingGoogle || connectingYahoo}
                onClick={() => void handleGoogleClick()}
              >
                {connectingGoogle ? (
                  <>
                    <LoaderCircle size={18} className="app-spin" />
                    Abriendo Google…
                  </>
                ) : (
                  <>
                    <Mail size={18} />
                    Gmail (Google)
                  </>
                )}
              </button>
              <p className="dx-connect-hint">
                {ACCOUNT_VS_MAILBOX.connectGoogleHint}
              </p>

              <button
                type="button"
                className="dx-connect-btn dx-connect-btn--secondary"
                disabled={connectingGoogle || connectingYahoo}
                onClick={() => {
                  setLocalError(null);
                  setYahooEmail("");
                  setYahooPassword("");
                  setYahooTabOpened(false);
                  setStep("yahoo");
                }}
              >
                Yahoo Mail
              </button>
              <p className="dx-connect-hint">
                Te llevamos a Yahoo. Ahí inicias sesión y Yahoo te da un código
                de 16 dígitos para Donexto.
              </p>
            </>
          ) : (
            <form
              className="dx-connect-form dx-yahoo-guide"
              autoComplete="off"
              data-1p-ignore="true"
              data-lpignore="true"
              data-form-type="other"
              onSubmit={(event) => void handleYahooSubmit(event)}
            >
              <input
                type="text"
                name="dx_fake_user"
                autoComplete="username"
                tabIndex={-1}
                aria-hidden="true"
                className="dx-connect-honeypot"
                value=""
                readOnly
              />
              <input
                type="password"
                name="dx_fake_pass"
                autoComplete="current-password"
                tabIndex={-1}
                aria-hidden="true"
                className="dx-connect-honeypot"
                value=""
                readOnly
              />

              {mode === "choose" ? (
                <button
                  type="button"
                  className="dx-connect-back"
                  onClick={() => {
                    setStep("choose");
                    setYahooEmail("");
                    setYahooPassword("");
                    setLocalError(null);
                    setYahooTabOpened(false);
                  }}
                >
                  ← Volver
                </button>
              ) : null}

              {yahooLocked ? (
                <p className="dx-yahoo-mailbox">
                  Correo a conectar
                  <strong>{accountEmail}</strong>
                </p>
              ) : (
                <label htmlFor="dx-yahoo-mailbox-email">
                  Correo del buzón Yahoo
                  <input
                    id="dx-yahoo-mailbox-email"
                    name="dx_yahoo_mailbox_email"
                    type="text"
                    inputMode="email"
                    required
                    autoComplete="off"
                    autoCapitalize="none"
                    autoCorrect="off"
                    spellCheck={false}
                    data-1p-ignore="true"
                    data-lpignore="true"
                    data-form-type="other"
                    placeholder="tucorreo@yahoo.com"
                    value={yahooEmail}
                    onChange={(event) => setYahooEmail(event.target.value)}
                  />
                </label>
              )}

              <a
                className="dx-connect-btn dx-connect-btn--yahoo"
                href={YAHOO_ACCOUNT_SECURITY_URL}
                target="_blank"
                rel="noopener noreferrer"
                onClick={() => setYahooTabOpened(true)}
              >
                <ExternalLink size={18} aria-hidden />
                {YAHOO_OPEN_SECURITY_CTA}
              </a>
              <p className="dx-yahoo-url">{YAHOO_ACCOUNT_SECURITY_URL}</p>

              <ol className="dx-yahoo-steps">
                {YAHOO_STEPS.map((item, index) => (
                  <li key={item.title}>
                    <span className="dx-yahoo-steps__n" aria-hidden>
                      {index + 1}
                    </span>
                    <div>
                      <strong>{item.title}</strong>
                      <p>{item.detail}</p>
                    </div>
                  </li>
                ))}
              </ol>

              <p className="dx-yahoo-app-name">
                En Yahoo, el nombre de la aplicación debe ser
                <strong>{YAHOO_APP_PASSWORD_NAME}</strong>
              </p>

              <p className="dx-yahoo-tip">{YAHOO_TWO_STEP_TIP}</p>

              <label htmlFor="dx-yahoo-app-password">
                {YAHOO_PASTE_LABEL}
                <input
                  id="dx-yahoo-app-password"
                  name="dx_yahoo_app_password"
                  type="text"
                  inputMode="text"
                  required
                  autoComplete="off"
                  autoCapitalize="none"
                  autoCorrect="off"
                  spellCheck={false}
                  data-1p-ignore="true"
                  data-lpignore="true"
                  data-form-type="other"
                  placeholder="xxxx xxxx xxxx xxxx"
                  className="dx-yahoo-code"
                  value={yahooPassword}
                  onChange={(event) =>
                    setYahooPassword(formatYahooAppPassword(event.target.value))
                  }
                />
                <span className="dx-yahoo-code-count">
                  {codeChars} / 16
                </span>
              </label>

              {localError ? (
                <div className="dx-connect-error" role="alert">
                  {localError}
                </div>
              ) : yahooTabOpened ? (
                <p className="dx-yahoo-ready">
                  Cuando Yahoo te muestre el código, pégalo arriba y pulsa
                  conectar. Esta ventana de Donexto se queda abierta.
                </p>
              ) : null}

              <button
                type="submit"
                className="dx-connect-btn dx-connect-btn--primary"
                disabled={connectingYahoo || codeChars !== 16}
              >
                {connectingYahoo ? (
                  <>
                    <LoaderCircle size={16} className="app-spin" />
                    Verificando Yahoo…
                  </>
                ) : (
                  YAHOO_CONNECT_CTA
                )}
              </button>

              <a
                className="dx-connect-help"
                href={YAHOO_APP_PASSWORD_HELP_URL}
                target="_blank"
                rel="noopener noreferrer"
              >
                Ayuda oficial de Yahoo · contraseñas de aplicación
              </a>
            </form>
          )}
        </div>
      </section>
    </div>
  );
}
