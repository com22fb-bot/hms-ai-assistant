"use client";

import { LoaderCircle, Mail, X } from "lucide-react";
import { useEffect, useState } from "react";

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
  onConnectYahoo: () => Promise<void>;
  onSignOut?: () => void;
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
  onSignOut,
}: MailboxConnectModalProps) {
  const [step, setStep] = useState<ProviderChoice>(
    mode === "yahoo" ? "yahoo" : "choose",
  );
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
    setLocalError(null);
    setConnectingGoogle(false);
  }, [open, mode, accountEmail]);

  useEffect(() => {
    if (step !== "yahoo" || yahooLocked) {
      return;
    }
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

  async function handleYahooClick() {
    setLocalError(null);
    try {
      await onConnectYahoo();
    } catch (error) {
      setLocalError(
        error instanceof Error
          ? error.message
          : "No fue posible abrir Yahoo.",
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
                onClick={() => void handleYahooClick()}
              >
                {connectingYahoo ? (
                  <>
                    <LoaderCircle size={18} className="app-spin" />
                    Abriendo Yahoo…
                  </>
                ) : (
                  "Yahoo Mail"
                )}
              </button>
              <p className="dx-connect-hint">
                {ACCOUNT_VS_MAILBOX.connectYahooChooserHint}
              </p>
            </>
          ) : (
            <div className="dx-connect-form">
              {mode === "choose" ? (
                <button
                  type="button"
                  className="dx-connect-back"
                  onClick={() => {
                    setStep("choose");
                    setLocalError(null);
                  }}
                >
                  ← Volver
                </button>
              ) : null}
              <p className="dx-connect-hint">
                {ACCOUNT_VS_MAILBOX.connectYahooBody}
              </p>
              {localError ? (
                <div className="dx-connect-error" role="alert">
                  {localError}
                </div>
              ) : null}
              <button
                type="button"
                className="dx-connect-btn dx-connect-btn--primary"
                disabled={connectingYahoo}
                onClick={() => void handleYahooClick()}
              >
                {connectingYahoo ? (
                  <>
                    <LoaderCircle size={16} className="app-spin" />
                    Abriendo Yahoo…
                  </>
                ) : (
                  "Ir a Yahoo"
                )}
              </button>
            </div>
          )}
        </div>

        {onSignOut ? (
          <p className="dx-connect-hint dx-connect-signout">
            Esta sesión es <strong>{accountEmail}</strong>.
            <button
              type="button"
              className="dx-connect-back"
              onClick={onSignOut}
            >
              Cerrar sesión y usar otro correo
            </button>
          </p>
        ) : null}
      </section>
    </div>
  );
}
