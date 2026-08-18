"use client";

import { LoaderCircle, Mail, X } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

import { AccountVsMailboxHint } from "@/components/auth/AccountVsMailboxHint";
import {
  ACCOUNT_VS_MAILBOX,
  authorizeMailboxTitle,
} from "@/lib/accountVsMailbox";
import type { MailboxConnectMode } from "@/lib/mailboxSignup";

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

  const yahooLocked = mode === "yahoo";
  const showChooser = mode === "choose" && step === "choose";
  const showYahooForm = mode === "yahoo" || step === "yahoo";
  const canDismiss = !required;

  useEffect(() => {
    if (!open) {
      return;
    }
    setStep(mode === "yahoo" ? "yahoo" : "choose");
    setYahooEmail(mode === "yahoo" ? accountEmail : "");
    setYahooPassword("");
    setLocalError(null);
    setConnectingGoogle(false);
  }, [open, mode, accountEmail]);

  useEffect(() => {
    if (step !== "yahoo" || yahooLocked) {
      return;
    }
    setYahooEmail("");
    setYahooPassword("");
    setLocalError(null);
  }, [step, yahooLocked]);

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

    try {
      const mailboxEmail = yahooLocked
        ? accountEmail
        : yahooEmail;
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

  const title =
    mode === "gmail"
      ? authorizeMailboxTitle(accountEmail)
      : showYahooForm && !showChooser
        ? ACCOUNT_VS_MAILBOX.connectYahooTitle
        : ACCOUNT_VS_MAILBOX.connectChooserTitle;

  const body =
    mode === "gmail"
      ? ACCOUNT_VS_MAILBOX.connectGmailBody
      : showYahooForm && !showChooser
        ? ACCOUNT_VS_MAILBOX.connectYahooBody
        : ACCOUNT_VS_MAILBOX.connectChooserBody;

  return (
    <div className="dx-connect-overlay" role="dialog" aria-modal="true">
      <section className="dx-connect-card">
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
          <AccountVsMailboxHint variant="connect" email={accountEmail} />

          {mode === "gmail" ? (
            <>
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
                  setStep("yahoo");
                }}
              >
                Yahoo Mail
              </button>
              <p className="dx-connect-hint">
                {ACCOUNT_VS_MAILBOX.connectYahooChooserHint}
              </p>
            </>
          ) : (
            <form
              className="dx-connect-form"
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
                  }}
                >
                  ← Volver
                </button>
              ) : null}

              <label htmlFor="dx-yahoo-mailbox-email">
                Correo del buzón Yahoo
                <input
                  id="dx-yahoo-mailbox-email"
                  name="dx_yahoo_mailbox_email"
                  type="text"
                  inputMode="email"
                  required
                  readOnly={yahooLocked}
                  autoComplete="off"
                  autoCapitalize="none"
                  autoCorrect="off"
                  spellCheck={false}
                  data-1p-ignore="true"
                  data-lpignore="true"
                  data-form-type="other"
                  placeholder="tucorreo@yahoo.com"
                  value={yahooLocked ? accountEmail : yahooEmail}
                  onChange={(event) => {
                    if (!yahooLocked) {
                      setYahooEmail(event.target.value);
                    }
                  }}
                />
              </label>
              <label htmlFor="dx-yahoo-app-password">
                {ACCOUNT_VS_MAILBOX.connectYahooAppPasswordLabel}
                <input
                  id="dx-yahoo-app-password"
                  name="dx_yahoo_app_password"
                  type="password"
                  required
                  minLength={8}
                  autoComplete="new-password"
                  data-1p-ignore="true"
                  data-lpignore="true"
                  data-form-type="other"
                  placeholder="xxxx xxxx xxxx xxxx"
                  value={yahooPassword}
                  onChange={(event) => setYahooPassword(event.target.value)}
                />
              </label>
              <p className="dx-connect-hint">
                1){" "}
                <a
                  href="https://login.yahoo.com/account/security"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Seguridad Yahoo
                </a>
                . 2) Verificación en 2 pasos. 3) Conexiones externas → Crear
                contraseña de aplicación → nombre <strong>Donexto</strong>. 4)
                Pega aquí el código de ~16 caracteres (no la contraseña de
                Yahoo ni la de Donexto).
              </p>
              {localError ? (
                <div className="dx-connect-error" role="alert">
                  {localError}
                </div>
              ) : null}
              <button
                type="submit"
                className="dx-connect-btn dx-connect-btn--primary"
                disabled={connectingYahoo}
              >
                {connectingYahoo ? (
                  <>
                    <LoaderCircle size={16} className="app-spin" />
                    Verificando Yahoo…
                  </>
                ) : (
                  "Verificar y conectar este Yahoo"
                )}
              </button>
            </form>
          )}
        </div>
      </section>
    </div>
  );
}
