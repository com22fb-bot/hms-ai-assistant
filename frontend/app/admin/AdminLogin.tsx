"use client";

import { KeyRound, Mail, Shield } from "lucide-react";
import { FormEvent, useState } from "react";

import { authReturnUrl } from "@/lib/adminCanonical";
import { postPublicHms } from "@/lib/publicHms";

/**
 * Owner login for /admin. Not the consumer "Conecta Gmail" screen:
 * no Google consent screen, no mailbox scope. Two ways in:
 *  1. one-time link mailed to an ADMIN_EMAILS inbox (default),
 *  2. email + password (for admin accounts that have one).
 */
export function AdminLogin({
  onSignIn,
}: {
  onSignIn: (email: string, password: string) => Promise<void>;
}) {
  const [mode, setMode] = useState<"link" | "password">("link");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function requestLink(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const result = await postPublicHms("/admin/login-link", {
        email: email.trim().toLowerCase(),
        return_to: authReturnUrl(window.location),
      });
      if (result.status === 429) {
        setError("Demasiados intentos. Espera unos minutos y revisa tu correo.");
      } else if (!result.ok) {
        setError("No pudimos pedir el enlace. Inténtalo otra vez en un momento.");
      } else {
        setSent(true);
      }
    } catch {
      setError("Sin conexión con Donexto. Revisa la red e inténtalo otra vez.");
    } finally {
      setBusy(false);
    }
  }

  async function signInWithPassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await onSignIn(email.trim().toLowerCase(), password);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "No fue posible entrar.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="dx-admin dx-admin-gate" data-testid="admin-login">
      <section className="dx-admin-gate__card" aria-labelledby="admin-login-title">
        <p className="dx-admin__eyebrow"><Shield size={14} aria-hidden /> Donexto · Operaciones</p>
        <h1 id="admin-login-title">Admin Donexto</h1>
        <p className="dx-admin-gate__lead">
          Panel del propietario. Solo entran los correos autorizados. Esto no conecta tu Gmail ni lee tu correo.
        </p>

        {sent ? (
          <div className="dx-admin__alert is-ok" role="status" data-testid="admin-login-sent">
            Si <b>{email.trim().toLowerCase()}</b> está autorizado, te llegó un correo de Donexto con el botón
            <b> Entrar al panel</b>. Ábrelo en este mismo navegador. Revisa también Spam.
          </div>
        ) : mode === "link" ? (
          <form className="dx-admin-gate__form" onSubmit={(event) => void requestLink(event)}>
            <label>
              Correo de administrador
              <input
                required
                type="email"
                autoComplete="email"
                inputMode="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="tu@correo.com"
              />
            </label>
            <button type="submit" className="dx-admin__btn" disabled={busy}>
              <Mail size={16} aria-hidden />
              {busy ? "Enviando…" : "Enviarme enlace de acceso"}
            </button>
          </form>
        ) : (
          <form className="dx-admin-gate__form" onSubmit={(event) => void signInWithPassword(event)}>
            <label>
              Correo de administrador
              <input
                required
                type="email"
                autoComplete="username"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </label>
            <label>
              Contraseña
              <input
                required
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </label>
            <button type="submit" className="dx-admin__btn" disabled={busy}>
              <KeyRound size={16} aria-hidden />
              {busy ? "Entrando…" : "Entrar"}
            </button>
          </form>
        )}

        {error ? <p className="dx-admin__alert is-error" role="alert">{error}</p> : null}

        <div className="dx-admin-gate__switch">
          {sent ? (
            <button type="button" className="dx-admin__btn dx-admin__btn--ghost" onClick={() => setSent(false)}>
              Usar otro correo
            </button>
          ) : (
            <button
              type="button"
              className="dx-admin__btn dx-admin__btn--ghost"
              onClick={() => {
                setError(null);
                setMode(mode === "link" ? "password" : "link");
              }}
            >
              {mode === "link" ? "Entrar con contraseña" : "Mejor un enlace a mi correo"}
            </button>
          )}
        </div>
      </section>
    </div>
  );
}
