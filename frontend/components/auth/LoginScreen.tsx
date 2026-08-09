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
 * Acceso Donexto — layout de producto serio: marca + formulario centrado.
 * Mobile: formulario primero. Desktop: split marca | acceso.
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
    <main className="dx-auth" data-theme={theme}>
      <aside className="dx-auth__brand" aria-label="Donexto">
        <div className="dx-auth__brand-inner">
          <div className="dx-auth__logo">
            <span className="dx-auth__mark" aria-hidden>
              D
            </span>
            <div>
              <p className="dx-auth__name">Donexto</p>
              <p className="dx-auth__slogan">Do Next To…</p>
            </div>
          </div>

          <h1 className="dx-auth__headline">
            Lo que requiere atención en tu correo
          </h1>
          <p className="dx-auth__sub">
            Prioridades y respuestas, sin el caos de la bandeja. El buzón Gmail
            o Yahoo se conecta después del acceso.
          </p>

          <figure className="dx-auth__visual">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/donexto-hero.png"
              alt=""
              width={720}
              height={720}
              decoding="async"
            />
          </figure>
        </div>
      </aside>

      <section className="dx-auth__access">
        <div className="dx-auth__card">
          <header className="dx-auth__card-head">
            <p className="dx-auth__card-brand">Donexto</p>
            <h2 id="dx-auth-title">
              {mode === "signup" ? "Crear cuenta" : "Iniciar sesión"}
            </h2>
            <p className="dx-auth__card-note">
              Usa tu cuenta Donexto (no es la contraseña de Gmail ni Yahoo).
            </p>
          </header>

          <div className="dx-auth__mode">
            <button
              type="button"
              className={mode === "signin" ? "is-on" : undefined}
              disabled={busy}
              onClick={() => {
                setMode("signin");
                setError(null);
                setMessage(null);
                setStep("credentials");
              }}
            >
              Entrar
            </button>
            <button
              type="button"
              className={mode === "signup" ? "is-on" : undefined}
              disabled={busy}
              onClick={() => {
                setMode("signup");
                setError(null);
                setMessage(null);
                setStep("credentials");
              }}
            >
              Crear cuenta
            </button>
          </div>

          {step === "credentials" ? (
            <form
              className="dx-auth__form"
              onSubmit={submit}
              noValidate
              aria-labelledby="dx-auth-title"
            >
              <label className="dx-auth__field">
                <span>Correo</span>
                <div className="dx-auth__control">
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

              <label className="dx-auth__field">
                <span>Contraseña</span>
                <div className="dx-auth__control">
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
                    placeholder="Mínimo 8 caracteres"
                    disabled={busy}
                    onChange={(event) => setPassword(event.target.value)}
                  />
                  <button
                    type="button"
                    className="dx-auth__eye"
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
                <div className="dx-auth__alert is-error" role="alert">
                  <AlertTriangle size={18} />
                  <span>{error}</span>
                </div>
              ) : null}

              {message ? (
                <div className="dx-auth__alert is-ok" role="status">
                  <CheckCircle2 size={18} />
                  <span>{message}</span>
                </div>
              ) : null}

              <button
                type="submit"
                className="dx-auth__submit"
                disabled={busy}
              >
                {busy ? (
                  <>
                    <LoaderCircle className="dx-auth__spin" size={18} />
                    {mode === "signup" ? "Creando…" : "Entrando…"}
                  </>
                ) : mode === "signup" ? (
                  "Crear cuenta"
                ) : (
                  "Continuar"
                )}
              </button>

              <button
                type="button"
                className="dx-auth__link"
                disabled={busy}
                onClick={() => {
                  setStep("help");
                  setError(null);
                }}
              >
                Olvidé mi contraseña u otras opciones
              </button>
            </form>
          ) : (
            <div className="dx-auth__help">
              <button
                type="button"
                className="dx-auth__link"
                onClick={() => {
                  setStep("credentials");
                  setError(null);
                }}
              >
                ← Volver al acceso
              </button>

              <p className="dx-auth__help-text">
                Usa el mismo correo. No pedimos la contraseña de Gmail ni Yahoo.
              </p>

              {error ? (
                <div className="dx-auth__alert is-error" role="alert">
                  <AlertTriangle size={18} />
                  <span>{error}</span>
                </div>
              ) : null}
              {message ? (
                <div className="dx-auth__alert is-ok" role="status">
                  <CheckCircle2 size={18} />
                  <span>{message}</span>
                </div>
              ) : null}

              <button
                type="button"
                className="dx-auth__secondary"
                disabled={busy}
                onClick={() => void magicLink()}
              >
                <Mail size={18} />
                Enviarme enlace de acceso
              </button>

              <button
                type="button"
                className="dx-auth__secondary is-ghost"
                disabled={busy}
                onClick={() => void recover()}
              >
                Restablecer contraseña
              </button>
            </div>
          )}

          <footer className="dx-auth__foot">
            <ShieldCheck size={16} aria-hidden />
            <span>Acceso seguro · acceso independiente del buzón</span>
          </footer>
        </div>

        <label className="dx-auth__theme">
          <span className="sr-only">Tema del panel después de entrar</span>
          <select
            value={theme}
            onChange={(event) =>
              setTheme(event.target.value as GateThemeId)
            }
            aria-label="Tema del panel"
          >
            <option value="accessible">Tema: Confianza</option>
            <option value="graphite">Tema: Grafito</option>
            <option value="aurora">Tema: Cielo</option>
            <option value="midnight">Tema: Noche</option>
          </select>
        </label>
      </section>
    </main>
  );
}
