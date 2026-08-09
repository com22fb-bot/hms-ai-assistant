"use client";

import { LoaderCircle, Mail, X } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

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

  // Cada vez que se abre el modal, volver a la elección Gmail / Yahoo.
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
    <div className="hms-mailbox-overlay" role="dialog" aria-modal="true">
      <section
        className="hms-mailbox-shell"
        style={{ maxWidth: 460, maxHeight: "92vh" }}
      >
        <header className="hms-mailbox-header">
          <div>
            <strong>
              {step === "choose"
                ? "¿Qué correo quieres cargar?"
                : "Inicia sesión en Yahoo"}
            </strong>
            <p style={{ margin: "6px 0 0", fontSize: 14, opacity: 0.8 }}>
              {step === "choose"
                ? "Elige Gmail o Yahoo. Puede ser cualquier cuenta, no tiene que ser la de Donexto."
                : "Usa tu correo Yahoo y una contraseña de aplicación (IMAP)."}
            </p>
          </div>
          <button
            type="button"
            onClick={() => {
              if (step === "yahoo") {
                setStep("choose");
                setLocalError(null);
                return;
              }
              if (!required) {
                onClose();
              }
            }}
            aria-label={step === "yahoo" ? "Volver a elegir proveedor" : "Cerrar"}
            style={
              required && step === "choose"
                ? { visibility: "hidden" }
                : undefined
            }
          >
            <X size={20} />
          </button>
        </header>

        <div style={{ padding: "16px 20px 24px", display: "grid", gap: 14 }}>
          {localError && step === "choose" ? (
            <div className="hms-mailbox-error">{localError}</div>
          ) : null}

          {step === "choose" ? (
            <>
              <button
                type="button"
                className="primary-button app-sidebar-primary"
                style={{
                  width: "100%",
                  minHeight: 56,
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 10,
                  cursor: connectingGoogle ? "wait" : "pointer",
                }}
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
              <p style={{ margin: 0, fontSize: 13, opacity: 0.75 }}>
                Te llevamos a la página oficial de Google para iniciar sesión y
                autorizar Donexto.
              </p>

              <button
                type="button"
                className="secondary-button app-sidebar-secondary"
                style={{
                  width: "100%",
                  minHeight: 56,
                  marginTop: 4,
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 10,
                  cursor: "pointer",
                }}
                disabled={connectingGoogle || connectingYahoo}
                onClick={() => {
                  setLocalError(null);
                  setStep("yahoo");
                }}
              >
                Yahoo Mail
              </button>
              <p style={{ margin: 0, fontSize: 13, opacity: 0.75 }}>
                Luego te pedimos el correo y la contraseña de aplicación de
                Yahoo (IMAP).
              </p>
            </>
          ) : (
            <form onSubmit={(event) => void handleYahooSubmit(event)}>
              <button
                type="button"
                onClick={() => {
                  setStep("choose");
                  setLocalError(null);
                }}
                style={{
                  border: 0,
                  background: "transparent",
                  color: "inherit",
                  opacity: 0.85,
                  textAlign: "left",
                  padding: 0,
                  marginBottom: 8,
                  cursor: "pointer",
                  textDecoration: "underline",
                  fontSize: 14,
                }}
              >
                ← Volver a Gmail o Yahoo
              </button>

              <label
                style={{
                  display: "grid",
                  gap: 6,
                  marginBottom: 12,
                  fontSize: 13,
                }}
              >
                Correo Yahoo
                <input
                  type="email"
                  required
                  autoComplete="email"
                  placeholder="tucorreo@yahoo.com"
                  value={yahooEmail}
                  onChange={(event) => setYahooEmail(event.target.value)}
                  style={{
                    padding: "10px 12px",
                    borderRadius: 10,
                    border: "1px solid rgba(15,40,48,0.18)",
                  }}
                />
              </label>
              <label
                style={{
                  display: "grid",
                  gap: 6,
                  marginBottom: 12,
                  fontSize: 13,
                }}
              >
                Contraseña de aplicación
                <input
                  type="password"
                  required
                  minLength={8}
                  autoComplete="current-password"
                  placeholder="xxxx xxxx xxxx xxxx"
                  value={yahooPassword}
                  onChange={(event) => setYahooPassword(event.target.value)}
                  style={{
                    padding: "10px 12px",
                    borderRadius: 10,
                    border: "1px solid rgba(15,40,48,0.18)",
                  }}
                />
              </label>
              <p style={{ margin: "0 0 12px", fontSize: 12, opacity: 0.75 }}>
                Yahoo → Seguridad de la cuenta → Generar contraseña de
                aplicación (IMAP). No uses la contraseña normal de Yahoo.
              </p>
              {localError ? (
                <div
                  className="hms-mailbox-error"
                  style={{ marginBottom: 12 }}
                >
                  {localError}
                </div>
              ) : null}
              <button
                type="submit"
                className="primary-button app-sidebar-primary"
                style={{
                  width: "100%",
                  minHeight: 52,
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 8,
                }}
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
