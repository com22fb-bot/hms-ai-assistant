"use client";

import { LoaderCircle, Mail } from "lucide-react";
import { useState } from "react";

import { useOptionalLanguage } from "@/lib/i18n/LanguageProvider";
import type { AppLanguage } from "@/lib/i18n/languages";
import { translate, type MessageKey } from "@/lib/i18n/messages";

import "./hms-gate.css";
import "./dx-auth-neon.css";

type ConfirmEmailGateProps = {
  email: string;
  onResend: (email: string, language: AppLanguage) => Promise<void>;
  onRefresh: () => Promise<void>;
  onSignOut: () => Promise<void> | void;
};

/**
 * Bloquea el dashboard hasta que el backend confirme el enlace Donexto con
 * `?donexto_verify=1`; entrar mediante OAuth nunca sustituye ese paso.
 */
export function ConfirmEmailGate({
  email,
  onResend,
  onRefresh,
  onSignOut,
}: ConfirmEmailGateProps) {
  const languageContext = useOptionalLanguage();
  const language = languageContext?.language || "es";
  const t = (key: MessageKey) =>
    languageContext?.t(key) || translate("es", key);
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
      await onResend(email, language);
      setMessage(t("confirmGateResent"));
    } catch {
      setError(t("confirmGateResendError"));
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
    } catch {
      setError(t("confirmGateRefreshError"));
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
              {t("confirmGateTitle")}
            </h2>
            <p className="dx-auth__slogan">
              {t("confirmGateHelper").replace("{email}", email)}
            </p>
          </header>

          <div className="dx-auth__signin">
            <p className="dx-auth__alert" role="note">
              {t("confirmGateSpam")}
            </p>
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
                  {t("confirmGateChecking")}
                </>
              ) : (
                t("confirmGateRefresh")
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
                  {t("confirmGateSending")}
                </>
              ) : (
                <>
                  <Mail size={18} />
                  {t("confirmGateResend")}
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
              {t("confirmGateSignOut")}
            </button>
          </div>

          <p className="dx-auth__secure" role="note">
            {t("confirmGateSecure")}
          </p>
        </div>
      </section>
    </main>
  );
}
