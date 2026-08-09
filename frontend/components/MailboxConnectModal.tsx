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
    setYahooEmail("");
    setYahooPassword("");
    setLocalError(null);
    setConnectingGoogle(false);
  }, [open]);

  // Al entrar al paso Yahoo: siempre en blanco (sin autofill de Donexto).
  useEffect(() => {
    if (step !== "yahoo") {
      return;
    }
    setYahooEmail("");
    setYahooPassword("");
    setLocalError(null);
  }, [step]);

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
              autoComplete="off"
              data-1p-ignore="true"
              data-lpignore="true"
              data-form-type="other"
              onSubmit={(event) => void handleYahooSubmit(event)}
            >
              {/* Señuelos: evitan que el password manager rellene el buzón Yahoo
                  con el login de Donexto. */}
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
                  setYahooEmail("");
                  setYahooPassword("");
                  setLocalError(null);
                }}
              >
                ← Volver a Gmail o Yahoo
              </button>

              <label htmlFor="dx-yahoo-mailbox-email">
                Correo Yahoo
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
              <label htmlFor="dx-yahoo-app-password">
                Contraseña de aplicación
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
                No se rellenan credenciales de Donexto. Necesitas una{" "}
                <strong>contraseña de aplicación</strong> de Yahoo (código de
                ~16 caracteres), no la de mail.yahoo.com ni la de entrar a
                Donexto.
              </p>
              <p className="dx-connect-hint">
                Cómo crear:{" "}
                <a
                  href="https://login.yahoo.com/account/security"
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ color: "#20d8d2" }}
                >
                  Seguridad de la cuenta Yahoo
                </a>
                {" → "}
                Conexiones externas → Crear contraseña de aplicación → nombre
                “Donexto” → Generar → copiar aquí.
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
          )}        </div>
      </section>
    </div>
  );
}
