"use client";

import { LoaderCircle, Mail, X } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

import "./mailbox-connect.css";

type ProviderChoice = "choose" | "yahoo";

type MailboxConnectModalProps = {
  open: boolean;
  connectingYahoo: boolean;
  required?: boolean;
  onClose: () => void;
  onConnectGoogle: () => void | Promise<void>;
  onConnectYahoo: (email: string, appPassword: string) => Promise<void>;
};

export function MailboxConnectModal({
  open,
  connectingYahoo,
  required = false,
  onClose,
  onConnectGoogle,
  onConnectYahoo,
}: MailboxConnectModalProps) {
  const [step, setStep] = useState<ProviderChoice>("choose");
  const [yahooEmail, setYahooEmail] = useState("");
  const [yahooPassword, setYahooPassword] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);
  const [connectingGoogle, setConnectingGoogle] = useState(false);

  useEffect(() => {
    if (!open) {
      return;
    }
    setStep("choose");
    setLocalError(null);
    setConnectingGoogle(false);
  }, [open]);

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
      await onConnectYahoo(yahooEmail, yahooPassword);
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

  return (
    <div className="dx-connect-overlay" role="dialog" aria-modal="true">
      <section className="dx-connect-card">
        <header className="dx-connect-header">
          <div>
            <strong>
              {step === "choose"
                ? "¿Qué correo quieres cargar?"
                : "Inicia sesión en Yahoo"}
            </strong>
            <p>
              {step === "choose"
                ? "Elige Gmail o Yahoo. Puede ser cualquier cuenta, no tiene que ser la de Donexto."
                : "Usa tu correo Yahoo y una contraseña de aplicación (IMAP)."}
            </p>
          </div>
          {!(required && step === "choose") ? (
            <button
              type="button"
              className="dx-connect-icon-btn"
              onClick={() => {
                if (step === "yahoo") {
                  setStep("choose");
                  setLocalError(null);
                  return;
                }
                onClose();
              }}
              aria-label={
                step === "yahoo" ? "Volver a elegir proveedor" : "Cerrar"
              }
            >
              <X size={20} />
            </button>
          ) : null}
        </header>

        <div className="dx-connect-body">
          {localError && step === "choose" ? (
            <div className="dx-connect-error" role="alert">
              {localError}
            </div>
          ) : null}

          {step === "choose" ? (
            <>
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
                Te llevamos a la página oficial de Google para iniciar sesión y
                autorizar Donexto.
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
                Luego te pedimos el correo y la contraseña de aplicación de
                Yahoo (IMAP).
              </p>
            </>
          ) : (
            <form
              className="dx-connect-form"
              onSubmit={(event) => void handleYahooSubmit(event)}
            >
              <button
                type="button"
                className="dx-connect-back"
                onClick={() => {
                  setStep("choose");
                  setLocalError(null);
                }}
              >
                ← Volver a Gmail o Yahoo
              </button>

              <label>
                Correo Yahoo
                <input
                  type="email"
                  required
                  autoComplete="email"
                  placeholder="tucorreo@yahoo.com"
                  value={yahooEmail}
                  onChange={(event) => setYahooEmail(event.target.value)}
                />
              </label>
              <label>
                Contraseña de aplicación
                <input
                  type="password"
                  required
                  minLength={8}
                  autoComplete="current-password"
                  placeholder="xxxx xxxx xxxx xxxx"
                  value={yahooPassword}
                  onChange={(event) => setYahooPassword(event.target.value)}
                />
              </label>
              <p className="dx-connect-hint">
                Yahoo → Seguridad de la cuenta → Generar contraseña de
                aplicación (IMAP). No uses la contraseña normal de Yahoo.
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
                  "Verificar y conectar Yahoo"
                )}
              </button>
            </form>
          )}
        </div>
      </section>
    </div>
  );
}
