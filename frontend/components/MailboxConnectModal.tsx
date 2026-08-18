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
          {mode === "gmail" || showChooser ? (
            <AccountVsMailboxHint variant="connect" email={accountEmail} />
          ) : null}

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
              autoComplete="on"
              onSubmit={(event) => void handleYahooSubmit(event)}
            >
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
                Correo de Yahoo
                <input
                  id="dx-yahoo-mailbox-email"
                  name="username"
                  type="email"
                  inputMode="email"
                  required
                  readOnly={yahooLocked}
                  autoComplete="username"
                  autoCapitalize="none"
                  autoCorrect="off"
                  spellCheck={false}
                  placeholder="tucorreo@yahoo.com"
                  value={yahooLocked ? accountEmail : yahooEmail}
                  onChange={(event) => {
                    if (!yahooLocked) {
                      setYahooEmail(event.target.value);
                    }
                  }}
                />
              </label>
              <label htmlFor="dx-yahoo-password">
                Contraseña de Yahoo
                <input
                  id="dx-yahoo-password"
                  name="password"
                  type="password"
                  required
                  minLength={6}
                  autoComplete="current-password"
                  placeholder="La misma con la que entras a Yahoo"
                  value={yahooPassword}
                  onChange={(event) => setYahooPassword(event.target.value)}
                />
              </label>
              <p className="dx-connect-hint">
                Solo tu correo y tu clave de Yahoo. Sin códigos extra ni
                verificación en dos pasos en Donexto.
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
                    Conectando Yahoo…
                  </>
                ) : (
                  "Conectar Yahoo"
                )}
              </button>
            </form>
          )}
        </div>
      </section>
    </div>
  );
}
