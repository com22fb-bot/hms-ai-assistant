"use client";

import { LoaderCircle, Mail, X } from "lucide-react";
import { useState } from "react";

import { AccountVsMailboxHint } from "@/components/auth/AccountVsMailboxHint";
import { GmailConnectNotice } from "@/components/auth/GmailConnectNotice";
import { IcloudConnectForm } from "@/components/auth/IcloudConnectForm";
import { YahooConnectForm } from "@/components/auth/YahooConnectForm";
import { icloudText } from "@/lib/i18n/icloudConnect";
import { useLanguage } from "@/lib/i18n/LanguageProvider";
import {
  ACCOUNT_VS_MAILBOX,
  authorizeMailboxTitle,
} from "@/lib/accountVsMailbox";
import type { MailboxConnectMode } from "@/lib/mailboxSignup";

import "./mailbox-connect.css";

type ProviderChoice = "choose" | "yahoo" | "microsoft" | "gmail";

function stepForMode(mode: MailboxConnectMode): ProviderChoice {
  if (mode === "yahoo") return "yahoo";
  if (mode === "microsoft") return "microsoft";
  if (mode === "gmail") return "gmail";
  return "choose";
}

type MailboxConnectModalProps = {
  open: boolean;
  connectingYahoo: boolean;
  connectingMicrosoft?: boolean;
  connectingIcloud?: boolean;
  connectingYahooImap?: boolean;
  required?: boolean;
  accountEmail: string;
  mode?: MailboxConnectMode;
  onClose: () => void;
  onConnectGoogle: () => void | Promise<void>;
  onConnectMicrosoft?: () => Promise<void>;
  onConnectIcloud?: (email: string, appPassword: string) => Promise<void>;
  onConnectYahooImap?: (email: string, appPassword: string) => Promise<void>;
  onSignOut?: () => void;
};

export function MailboxConnectModal({
  open,
  connectingYahoo,
  connectingMicrosoft = false,
  connectingIcloud = false,
  connectingYahooImap = false,
  required = false,
  accountEmail,
  mode = "choose",
  onClose,
  onConnectGoogle,
  onConnectMicrosoft,
  onConnectIcloud,
  onConnectYahooImap,
  onSignOut,
}: MailboxConnectModalProps) {
  const { language } = useLanguage();
  const [step, setStep] = useState<ProviderChoice>(() => stepForMode(mode));
  const [localError, setLocalError] = useState<string | null>(null);
  const [connectingGoogle, setConnectingGoogle] = useState(false);
  const openSession = open ? `${mode}\0${accountEmail}` : "";
  const [openSessionSeen, setOpenSessionSeen] = useState(openSession);
  if (openSession !== openSessionSeen) {
    setOpenSessionSeen(openSession);
    if (open) {
      setStep(stepForMode(mode));
      setLocalError(null);
      setConnectingGoogle(false);
    }
  }

  const showChooser = mode === "choose" && step === "choose";
  const showYahooForm = mode === "yahoo" || step === "yahoo";
  const showGmailNotice = mode === "gmail" || step === "gmail";
  const showMicrosoftForm = mode === "microsoft" || step === "microsoft";
  const showIcloudForm = mode === "icloud";
  const canDismiss = !required;

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

  async function handleMicrosoftClick() {
    setLocalError(null);
    if (!onConnectMicrosoft) {
      setLocalError("Microsoft aún no está disponible en este espacio.");
      return;
    }
    try {
      await onConnectMicrosoft();
    } catch (error) {
      setLocalError(
        error instanceof Error
          ? error.message
          : "No fue posible abrir Microsoft.",
      );
    }
  }

  const title =
    showIcloudForm
      ? icloudText(language, "title")
      : mode === "gmail"
      ? authorizeMailboxTitle(accountEmail)
      : showMicrosoftForm && !showChooser
        ? ACCOUNT_VS_MAILBOX.connectMicrosoftTitle
        : showYahooForm && !showChooser
          ? ACCOUNT_VS_MAILBOX.connectYahooTitle
          : ACCOUNT_VS_MAILBOX.connectChooserTitle;

  const body =
    showIcloudForm
      ? icloudText(language, "intro")
      : mode === "gmail"
      ? ACCOUNT_VS_MAILBOX.connectGmailBody
      : showMicrosoftForm && !showChooser
        ? ACCOUNT_VS_MAILBOX.connectMicrosoftBody
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
          {showIcloudForm ? (
            <IcloudConnectForm
              email={accountEmail}
              emailLocked
              busy={connectingIcloud}
              error={localError}
              variant="modal"
              onSubmit={async (email, appPassword) => {
                setLocalError(null);
                if (!onConnectIcloud) {
                  setLocalError(icloudText(language, "imap_failed"));
                  return;
                }
                try {
                  await onConnectIcloud(email, appPassword);
                } catch (error) {
                  const coded = error as Error & { code?: string };
                  setLocalError(
                    coded.code
                      ? coded.message
                      : error instanceof Error
                        ? error.message
                        : icloudText(language, "imap_failed"),
                  );
                  throw error;
                }
              }}
            />
          ) : null}

          {mode === "gmail" || showChooser ? (
            <AccountVsMailboxHint variant="connect" email={accountEmail} />
          ) : null}

          {showGmailNotice && !showIcloudForm ? (
            <GmailConnectNotice
              email={accountEmail}
              busy={connectingGoogle}
              error={localError}
              variant="modal"
              onContinue={async () => {
                await handleGoogleClick();
              }}
              onBack={mode === "choose" ? () => {
                setStep("choose");
                setLocalError(null);
              } : undefined}
            />
          ) : null}

          {showYahooForm && !showIcloudForm ? (
            <YahooConnectForm
              email={accountEmail}
              emailLocked
              busy={connectingYahooImap || connectingYahoo}
              error={localError}
              variant="modal"
              onSubmit={async (email, appPassword) => {
                setLocalError(null);
                if (!onConnectYahooImap) {
                  setLocalError("Yahoo");
                  return;
                }
                try {
                  await onConnectYahooImap(email, appPassword);
                } catch (error) {
                  setLocalError(
                    error instanceof Error ? error.message : "Yahoo",
                  );
                  throw error;
                }
              }}
              onBack={mode === "choose" ? () => {
                setStep("choose");
                setLocalError(null);
              } : undefined}
            />
          ) : null}

          {showIcloudForm || showGmailNotice || showYahooForm ? null : showChooser ? (
            <>
              {localError ? (
                <div className="dx-connect-error" role="alert">
                  {localError}
                </div>
              ) : null}
              <button
                type="button"
                className="dx-connect-btn dx-connect-btn--primary"
                disabled={connectingGoogle || connectingYahoo || connectingMicrosoft}
                onClick={() => {
                  setLocalError(null);
                  setStep("gmail");
                }}
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
                disabled={connectingGoogle || connectingYahoo || connectingMicrosoft}
                onClick={() => {
                  setLocalError(null);
                  setStep("yahoo");
                }}
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
              {onConnectMicrosoft ? (
                <>
                  <button
                    type="button"
                    className="dx-connect-btn dx-connect-btn--secondary"
                    disabled={
                      connectingGoogle
                      || connectingYahoo
                      || connectingMicrosoft
                    }
                    onClick={() => void handleMicrosoftClick()}
                  >
                    {connectingMicrosoft ? (
                      <>
                        <LoaderCircle size={18} className="app-spin" />
                        Abriendo Microsoft…
                      </>
                    ) : (
                      "Outlook / Hotmail / Microsoft 365"
                    )}
                  </button>
                  <p className="dx-connect-hint">
                    {ACCOUNT_VS_MAILBOX.connectMicrosoftBody}
                  </p>
                </>
              ) : null}
            </>
          ) : showMicrosoftForm ? (
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
                {ACCOUNT_VS_MAILBOX.connectMicrosoftBody}
              </p>
              {localError ? (
                <div className="dx-connect-error" role="alert">
                  {localError}
                </div>
              ) : null}
              <button
                type="button"
                className="dx-connect-btn dx-connect-btn--primary"
                disabled={connectingMicrosoft}
                onClick={() => void handleMicrosoftClick()}
              >
                {connectingMicrosoft ? (
                  <>
                    <LoaderCircle size={16} className="app-spin" />
                    Abriendo Microsoft…
                  </>
                ) : (
                  ACCOUNT_VS_MAILBOX.connectMicrosoftCta
                )}
              </button>
            </div>
          ) : null}
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
