"use client";

import { LoaderCircle, X } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

import { AccountVsMailboxHint } from "@/components/auth/AccountVsMailboxHint";
import {
  ACCOUNT_VS_MAILBOX,
} from "@/lib/accountVsMailbox";
import type { MailboxConnectMode } from "@/lib/mailboxSignup";

import "./mailbox-connect.css";

type ProviderChoice = "choose" | "yahoo" | "outlook" | "apple";

type MailboxConnectModalProps = {
  open: boolean;
  connectingYahoo: boolean;
  required?: boolean;
  accountEmail: string;
  mode?: MailboxConnectMode;
  onClose: () => void;
  onConnectGoogle: () => void | Promise<void>;
  onConnectYahoo: (
    email: string,
    appPassword: string,
    provider?: "yahoo" | "outlook" | "apple",
  ) => Promise<void>;
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
  const [step, setStep] = useState<ProviderChoice>("choose");
  const [yahooEmail, setYahooEmail] = useState(accountEmail);
  const [yahooPassword, setYahooPassword] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);
  const [connectingGoogle, setConnectingGoogle] = useState(false);

  const imapBrand: "yahoo" | "outlook" | "apple" =
    step === "outlook" || step === "apple" ? step : "yahoo";
  const showChooser = step === "choose";
  const showImapForm = step === "yahoo" || step === "outlook" || step === "apple";
  const canDismiss = !required;

  useEffect(() => {
    if (!open) {
      return;
    }
    setStep("choose");
    setYahooEmail(accountEmail);
    setYahooPassword("");
    setLocalError(null);
    setConnectingGoogle(false);
  }, [open, accountEmail]);

  if (!open) {
    return null;
  }

  const imapCopy = {
    yahoo: {
      title: ACCOUNT_VS_MAILBOX.connectYahooTitle,
      body: ACCOUNT_VS_MAILBOX.connectYahooBody,
      label: ACCOUNT_VS_MAILBOX.connectYahooAppPasswordLabel,
      help: ACCOUNT_VS_MAILBOX.connectYahooChooserHint,
      link: "https://login.yahoo.com/account/security",
      linkLabel: "Seguridad Yahoo",
      cta: "Verificar y conectar este Yahoo",
    },
    outlook: {
      title: "Autoriza la lectura de este Outlook",
      body: "Contraseña de aplicación IMAP de Outlook / Hotmail. No uses la contraseña de Microsoft ni la de Donexto.",
      label: "Contraseña de aplicación Outlook",
      help: "En Microsoft: Seguridad → Contraseñas de aplicación. Pega el código aquí.",
      link: "https://account.microsoft.com/security",
      linkLabel: "Seguridad Microsoft",
      cta: "Verificar y conectar este Outlook",
    },
    apple: {
      title: "Autoriza la lectura de este iCloud",
      body: "Contraseña de aplicación de Apple. No uses la contraseña de iCloud ni la de Donexto.",
      label: "Contraseña de aplicación Apple",
      help: "En appleid.apple.com: Iniciar sesión y seguridad → Contraseñas de aplicaciones.",
      link: "https://appleid.apple.com",
      linkLabel: "Apple ID",
      cta: "Verificar y conectar este iCloud",
    },
  }[imapBrand];

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
      await onConnectYahoo(yahooEmail || accountEmail, yahooPassword, imapBrand);
      setYahooPassword("");
      onClose();
    } catch (error) {
      setLocalError(
        error instanceof Error
          ? error.message
          : `No fue posible conectar ${imapBrand}.`,
      );
    }
  }

  const title = showImapForm
    ? imapCopy.title
    : "Autoriza la lectura de tu correo";
  const body = showImapForm
    ? imapCopy.body
    : "Gmail, Outlook, Yahoo e iCloud. Elige el buzón que vas a vigilar. No pedimos la contraseña de ese correo aquí, salvo la de aplicación IMAP cuando el proveedor la exige.";

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
                if (showImapForm) {
                  setStep("choose");
                  setLocalError(null);
                  return;
                }
                onClose();
              }}
              aria-label={
                showImapForm ? "Volver a elegir proveedor" : "Cerrar"
              }
            >
              <X size={20} />
            </button>
          ) : null}
        </header>

        <div className="dx-connect-body">
          <AccountVsMailboxHint variant="connect" email={accountEmail} />

          {showChooser ? (
            <>
              {localError ? (
                <div className="dx-connect-error" role="alert">
                  {localError}
                </div>
              ) : null}
              <div className="dx-connect-providers">
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
                    "Gmail"
                  )}
                </button>
                <button
                  type="button"
                  className="dx-connect-btn dx-connect-btn--secondary"
                  disabled={connectingGoogle || connectingYahoo}
                  onClick={() => {
                    setLocalError(null);
                    setStep("outlook");
                  }}
                >
                  Outlook
                </button>
                <button
                  type="button"
                  className="dx-connect-btn dx-connect-btn--secondary"
                  disabled={connectingGoogle || connectingYahoo}
                  onClick={() => {
                    setLocalError(null);
                    setStep("yahoo");
                  }}
                >
                  Yahoo
                </button>
                <button
                  type="button"
                  className="dx-connect-btn dx-connect-btn--secondary"
                  disabled={connectingGoogle || connectingYahoo}
                  onClick={() => {
                    setLocalError(null);
                    setStep("apple");
                  }}
                >
                  iCloud
                </button>
              </div>
              <p className="dx-connect-hint">
                Gmail autoriza en Google. Outlook, Yahoo e iCloud usan
                contraseña de aplicación IMAP — nunca la del correo ni la de Donexto.
              </p>
            </>
          ) : showImapForm ? (
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

              <button
                type="button"
                className="dx-connect-back"
                onClick={() => {
                  setStep("choose");
                  setYahooPassword("");
                  setLocalError(null);
                }}
              >
                ← Volver
              </button>

              <label htmlFor="dx-yahoo-mailbox-email">
                Correo del buzón
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
                  placeholder={accountEmail || "tucorreo@dominio.com"}
                  value={yahooEmail}
                  onChange={(event) => setYahooEmail(event.target.value)}
                />
              </label>
              <label htmlFor="dx-yahoo-app-password">
                {imapCopy.label}
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
                  href={imapCopy.link}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {imapCopy.linkLabel}
                </a>
                . {imapCopy.help} Nombre la contraseña <strong>Donexto</strong>.
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
                    Verificando…
                  </>
                ) : (
                  imapCopy.cta
                )}
              </button>
            </form>
          ) : null}
        </div>
      </section>
    </div>
  );
}
