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
  onSignUp: (email: string, password: string) => Promise<void>;
  onMagicLink: (email: string) => Promise<void>;
  onResetPassword: (email: string) => Promise<void>;
};

/**
 * Acceso Donexto — look homologado con el panel (Confianza slate & teal).
 */
export function LoginScreen({
  theme,
  setTheme,
  onSignIn,
  onSignUp,
  onMagicLink,
  onResetPassword,
}: LoginScreenProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [step, setStep] = useState<"credentials" | "help">("credentials");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);

    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail.includes("@")) {
      setError("Escribe el correo de tu cuenta Donexto.");
      return;
    }
    if (password.length < 8) {
      setError("La contraseña usa al menos 8 caracteres.");
      return;
    }

    setBusy(true);
    try {
      if (mode === "signup") {
        await onSignUp(cleanEmail, password);
        setMessage("Cuenta creada. Ya puedes usar la app.");
      } else {
        await onSignIn(cleanEmail, password);
      }
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : mode === "signup"
            ? "No fue posible crear la cuenta."
            : "No fue posible iniciar sesión.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function magicLink() {
    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail.includes("@")) {
      setError("Escribe primero tu correo Donexto.");
      return;
    }
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await onMagicLink(cleanEmail);
      setMessage(
        "Revisa tu correo: enviamos un enlace para entrar sin contraseña.",
      );
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
      setError("Escribe primero tu correo Donexto.");
      return;
    }
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await onResetPassword(cleanEmail);
      setMessage(
        "Enviamos un enlace para restablecer la contraseña de Donexto.",
      );
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
    <main className="hms-gate dx-login" data-theme={theme}>
      <div className="hms-gate__atmosphere" aria-hidden />

      <div className="dx-login-shell">
        <section className="dx-login-story">
          <header className="hms-gate__brand">
            <div className="hms-gate__mark" aria-hidden>
              <span>D</span>
            </div>
            <div className="hms-gate__brand-text">
              <p className="hms-gate__product">Donexto</p>
              <p className="hms-gate__tagline">Do Next To…</p>
            </div>
          </header>

          <figure className="hms-gate__art dx-login-art">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/hms-import-robot.png"
              alt="Robot Donexto organizando correos hacia una laptop"
              width={960}
              height={640}
            />
          </figure>

          <div className="dx-login-copy">
            <p className="dx-login-eyebrow">Correo con criterio</p>
            <h1>Lo que requiere atención en tu correo.</h1>
            <p className="dx-login-lede">
              Prioridades, dinero y respuestas — antes del caos de la bandeja.
              Entra con tu cuenta Donexto; el buzón se conecta en un paso
              aparte.
            </p>
            <ul className="dx-login-points">
              <li>Buzón Gmail o Yahoo independiente del login</li>
              <li>Panel limpio para decidir qué contestar</li>
              <li>Diseñado para uso diario, no para “demo IA”</li>
            </ul>
          </div>
        </section>

        <section className="hms-gate__panel dx-login-panel" aria-labelledby="hms-gate-title">
          <div className="hms-gate__panel-head">
            <h2 id="hms-gate-title">
              {mode === "signup" ? "Crear cuenta" : "Iniciar sesión"}
            </h2>
            <p>
              Email y contraseña de Donexto — no son los de Gmail ni Yahoo.
            </p>
          </div>

          <div className="hms-gate__links" style={{ marginTop: "0.35rem" }}>
            <button
              type="button"
              disabled={busy}
              onClick={() => {
                setMode(mode === "signin" ? "signup" : "signin");
                setError(null);
                setMessage(null);
              }}
            >
              {mode === "signin"
                ? "¿No tienes cuenta? Crear una"
                : "¿Ya tienes cuenta? Entrar"}
            </button>
          </div>

          {step === "credentials" ? (
            <form className="hms-gate__form" onSubmit={submit} noValidate>
              <label className="hms-gate__field">
                <span>Correo Donexto</span>
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
                <span>Contraseña</span>
                <div className="hms-gate__control">
                  <KeyRound size={18} aria-hidden />
                  <input
                    type={showPassword ? "text" : "password"}
                    name="password"
                    value={password}
                    autoComplete={
                      mode === "signup" ? "new-password" : "current-password"
                    }
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
                      showPassword
                        ? "Ocultar contraseña"
                        : "Mostrar contraseña"
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
                    {mode === "signup" ? "Creando…" : "Entrando…"}
                  </>
                ) : mode === "signup" ? (
                  "Crear cuenta"
                ) : (
                  "Entrar a Donexto"
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
                ← Volver
              </button>

              <p className="hms-gate__help-lead">
                Usa el mismo correo de arriba. No se pide la contraseña del
                proveedor de correo.
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
                Restablecer contraseña Donexto
              </button>
            </div>
          )}

          <footer className="hms-gate__foot">
            <ShieldCheck size={16} aria-hidden />
            <span>
              Donexto no pide la contraseña de Gmail ni Yahoo en este
              formulario.
            </span>
          </footer>
        </section>
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
            <option value="accessible">Confianza · slate & teal</option>
            <option value="graphite">Institucional · grafito</option>
            <option value="aurora">Colaboración · cielo</option>
            <option value="midnight">Noche · indigo</option>
          </select>
        </label>
      </div>
    </main>
  );
}
