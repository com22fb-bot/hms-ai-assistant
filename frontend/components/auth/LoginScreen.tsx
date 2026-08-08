"use client";

import {
  AlertTriangle,
  CheckCircle2,
  Eye,
  EyeOff,
  KeyRound,
  LoaderCircle,
  Mail,
  ShieldCheck,
} from "lucide-react";
import { FormEvent, useState } from "react";

import "./hms-gate.css";

export type GateThemeId =
  | "midnight"
  | "aurora"
  | "accessible"
  | "graphite";

type LoginScreenProps = {
  theme: GateThemeId;
  setTheme: (theme: GateThemeId) => void;
  onSignIn: (email: string, password: string) => Promise<void>;
  onMagicLink: (email: string) => Promise<void>;
  onResetPassword: (email: string) => Promise<void>;
};

/**
 * Pantalla de acceso HMS: mobile-first, una sola tarea (entrar).
 * La cuenta HMS es independiente del buzón de correo.
 */
export function LoginScreen({
  theme,
  setTheme,
  onSignIn,
  onMagicLink,
  onResetPassword,
}: LoginScreenProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState<"credentials" | "help">("credentials");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);

    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail.includes("@")) {
      setError("Escribe el correo de tu cuenta HMS.");
      return;
    }
    if (password.length < 8) {
      setError("La contraseña HMS usa al menos 8 caracteres.");
      return;
    }

    setBusy(true);
    try {
      await onSignIn(cleanEmail, password);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "No fue posible iniciar sesión.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function magicLink() {
    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail.includes("@")) {
      setError("Escribe primero tu correo HMS.");
      return;
    }
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await onMagicLink(cleanEmail);
      setMessage("Revisa tu correo: enviamos un enlace para entrar sin contraseña.");
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "No fue posible enviar el enlace.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function recover() {
    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail.includes("@")) {
      setError("Escribe primero tu correo HMS.");
      return;
    }
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await onResetPassword(cleanEmail);
      setMessage("Enviamos un enlace para restablecer la contraseña de HMS.");
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "No fue posible solicitar el restablecimiento.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="hms-gate" data-theme={theme}>
      <div className="hms-gate__atmosphere" aria-hidden />
      <div className="hms-gate__grid" aria-hidden />

      <div className="hms-gate__frame">
        <header className="hms-gate__brand">
          <div className="hms-gate__mark" aria-hidden>
            <span>H</span>
          </div>
          <div className="hms-gate__brand-text">
            <p className="hms-gate__product">HMS</p>
            <p className="hms-gate__tagline">AI Assistant</p>
          </div>
        </header>

        <section className="hms-gate__hero">
          <h1>Entra a tu centro de pendientes</h1>
          <p>
            Una sola cuenta HMS. Después conectarás el correo en otro paso
            seguro.
          </p>
        </section>

        <section className="hms-gate__panel" aria-labelledby="hms-gate-title">
          <div className="hms-gate__panel-head">
            <h2 id="hms-gate-title">Iniciar sesión</h2>
            <p>Correo y contraseña de HMS — no los de Gmail ni Outlook.</p>
          </div>

          {step === "credentials" ? (
            <form className="hms-gate__form" onSubmit={submit} noValidate>
              <label className="hms-gate__field">
                <span>Correo HMS</span>
                <div className="hms-gate__control">
                  <Mail size={18} aria-hidden />
                  <input
                    type="email"
                    name="email"
                    value={email}
                    inputMode="email"
                    autoComplete="email"
                    autoCapitalize="none"
                    autoCorrect="off"
                    spellCheck={false}
                    placeholder="tu@empresa.com"
                    disabled={busy}
                    onChange={(event) => setEmail(event.target.value)}
                  />
                </div>
              </label>

              <label className="hms-gate__field">
                <span>Contraseña HMS</span>
                <div className="hms-gate__control">
                  <KeyRound size={18} aria-hidden />
                  <input
                    type={showPassword ? "text" : "password"}
                    name="password"
                    value={password}
                    autoComplete="current-password"
                    autoCapitalize="none"
                    spellCheck={false}
                    placeholder="••••••••"
                    disabled={busy}
                    onChange={(event) => setPassword(event.target.value)}
                  />
                  <button
                    type="button"
                    className="hms-gate__icon-btn"
                    aria-label={
                      showPassword ? "Ocultar contraseña" : "Mostrar contraseña"
                    }
                    onClick={() => setShowPassword((v) => !v)}
                  >
                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
              </label>

              {error ? (
                <div className="hms-gate__alert is-error" role="alert">
                  <AlertTriangle size={18} />
                  <span>{error}</span>
                </div>
              ) : null}

              {message ? (
                <div className="hms-gate__alert is-ok" role="status">
                  <CheckCircle2 size={18} />
                  <span>{message}</span>
                </div>
              ) : null}

              <button
                type="submit"
                className="hms-gate__submit"
                disabled={busy}
              >
                {busy ? (
                  <>
                    <LoaderCircle className="hms-gate__spin" size={18} />
                    Entrando…
                  </>
                ) : (
                  "Entrar"
                )}
              </button>

              <div className="hms-gate__links">
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => {
                    setStep("help");
                    setError(null);
                  }}
                >
                  Otras formas de entrar
                </button>
              </div>
            </form>
          ) : (
            <div className="hms-gate__help">
              <button
                type="button"
                className="hms-gate__back"
                onClick={() => {
                  setStep("credentials");
                  setError(null);
                }}
              >
                ← Volver al inicio de sesión
              </button>

              <p className="hms-gate__help-lead">
                Usa el mismo correo de arriba. No se usa la contraseña del
                correo personal.
              </p>

              {error ? (
                <div className="hms-gate__alert is-error" role="alert">
                  <AlertTriangle size={18} />
                  <span>{error}</span>
                </div>
              ) : null}
              {message ? (
                <div className="hms-gate__alert is-ok" role="status">
                  <CheckCircle2 size={18} />
                  <span>{message}</span>
                </div>
              ) : null}

              <button
                type="button"
                className="hms-gate__secondary"
                disabled={busy}
                onClick={() => void magicLink()}
              >
                <Mail size={18} />
                Enviarme enlace de acceso
              </button>

              <button
                type="button"
                className="hms-gate__secondary is-ghost"
                disabled={busy}
                onClick={() => void recover()}
              >
                Restablecer contraseña HMS
              </button>
            </div>
          )}

          <footer className="hms-gate__foot">
            <ShieldCheck size={16} aria-hidden />
            <span>
              HMS no pide la contraseña de Gmail, Outlook ni Yahoo en este
              formulario.
            </span>
          </footer>
        </section>

        <aside className="hms-gate__aside" aria-hidden="true">
          <p className="hms-gate__aside-kicker">Centro inteligente</p>
          <p className="hms-gate__aside-title">
            Detecta lo que requiere atención. Tú decides qué hacer.
          </p>
          <ul>
            <li>Pendientes y plazos a la vista</li>
            <li>Clasificación antes de la bandeja</li>
            <li>Avisos solo cuando importan</li>
          </ul>
        </aside>
      </div>

      <div className="hms-gate__theme">
        <label>
          <span className="sr-only">Tema visual</span>
          <select
            value={theme}
            onChange={(event) =>
              setTheme(event.target.value as GateThemeId)
            }
            aria-label="Tema de la aplicación"
          >
            <option value="accessible">Tema accesible</option>
            <option value="midnight">Medianoche</option>
            <option value="aurora">Aurora</option>
            <option value="graphite">Grafito</option>
          </select>
        </label>
      </div>
    </main>
  );
}
