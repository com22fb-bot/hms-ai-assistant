"use client";

import { LoaderCircle, Mail } from "lucide-react";
import { useState } from "react";

import { ACCOUNT_VS_MAILBOX } from "@/lib/accountVsMailbox";

import "./hms-gate.css";
import "./dx-auth-neon.css";

type ConfirmEmailGateProps = {
  email: string;
  onResend: (email: string) => Promise<void>;
  onRefresh: () => Promise<void>;
  onSignOut: () => Promise<void> | void;
};

/**
 * Bloquea el dashboard hasta `app_metadata.donexto_verified === true`
 * (clic en el mail Donexto con `?donexto_verify=1`, confirmado vía backend).
 * Identidad OAuth (Yahoo / Google / Microsoft) no usa esta pantalla.
 */
export function ConfirmEmailGate({
  email,
  onResend,
  onRefresh,
  onSignOut,
}: ConfirmEmailGateProps) {
  const [busy, setBusy] = useState<"resend" | "refresh" | "out" | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function resend() {
    if (busy) {
      return;
    }
    setBusy("resend");
    setError(null);
    setMessage(null);
    try {
      await onResend(email);
      setMessage("Listo. Revisa la bandeja (y spam) de ese mismo correo.");
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "No fue posible reenviar el correo.",
      );
    } finally {
      setBusy(null);
    }
  }

  async function refresh() {
    if (busy) {
      return;
    }
    setBusy("refresh");
    setError(null);
    setMessage(null);
    try {
      await onRefresh();
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Aún no vemos la confirmación. Abre el enlace del correo.",
      );
    } finally {
      setBusy(null);
    }
  }

  async function signOut() {
    if (busy) {
      return;
    }
    setBusy("out");
    try {
      await onSignOut();
    } finally {
      setBusy(null);
    }
  }

  return (
    <main className="dx-auth">
      <aside className="dx-auth__hero">
        <div className="dx-auth__hero-inner">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            className="dx-auth__logo"
            src="/brand/donexto-logo-official.png"
            width={1024}
            height={1024}
            alt="Donexto — Do Next To…"
            decoding="async"
          />
          <p className="dx-auth__sr">Donexto</p>
        </div>
      </aside>

      <section className="dx-auth__panel">
        <div className="dx-auth__card" aria-labelledby="dx-confirm-title">
          <header className="dx-auth__heading">
            <h2 id="dx-confirm-title" className="dx-auth__title">
              {ACCOUNT_VS_MAILBOX.confirmGateTitle}
            </h2>
            <p className="dx-auth__slogan">
              Abre el enlace que enviamos a <strong>{email}</strong>.
              Eso te identifica; no es la contraseña del buzón.
            </p>
          </header>

          <div className="dx-auth__signin">
            {error ? (
              <div className="dx-auth__alert is-error" role="alert">
                <span>{error}</span>
              </div>
            ) : null}
            {message ? (
              <div className="dx-auth__alert is-ok" role="status">
                <span>{message}</span>
              </div>
            ) : null}

            <button
              type="button"
              className="dx-auth__submit"
              disabled={busy !== null}
              onClick={() => void refresh()}
            >
              {busy === "refresh" ? (
                <>
                  <LoaderCircle className="dx-auth__spin" size={18} />
                  Comprobando…
                </>
              ) : (
                ACCOUNT_VS_MAILBOX.confirmGateRefresh
              )}
            </button>

            <button
              type="button"
              className="dx-auth__secondary"
              disabled={busy !== null}
              onClick={() => void resend()}
            >
              {busy === "resend" ? (
                <>
                  <LoaderCircle className="dx-auth__spin" size={18} />
                  Enviando…
                </>
              ) : (
                <>
                  <Mail size={18} />
                  {ACCOUNT_VS_MAILBOX.confirmGateResend}
                </>
              )}
            </button>
          </div>

          <div className="dx-auth__bottom-mode">
            <button
              type="button"
              disabled={busy !== null}
              onClick={() => void signOut()}
            >
              {ACCOUNT_VS_MAILBOX.confirmGateSignOut}
            </button>
          </div>

          <p className="dx-auth__secure" role="note">
            Al continuar, Donexto solo confirma que ese correo es tuyo.
          </p>
        </div>
      </section>
    </main>
  );
}
