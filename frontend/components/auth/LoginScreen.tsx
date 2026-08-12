"use client";

import {
  AlertTriangle,
  CheckCircle2,
  Eye,
  EyeOff,
  KeyRound,
  LoaderCircle,
  Mail,
  User,
} from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

import { ACCOUNT_VS_MAILBOX } from "@/lib/accountVsMailbox";
import { DONEXTO_QUALITY } from "@/lib/donextoQuality";

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
  onSignUp: (
    email: string,
    password: string,
    fullName: string,
  ) => Promise<void>;
  onMagicLink: (email: string) => Promise<void>;
  onResetPassword: (email: string) => Promise<void>;
};

/**
 * Gate Donexto — una composición vertical:
 * franja de marca (logo chico + nombre) → promesa → form.
 * Sin split vacío, sin avisos duplicados, sin “olvidé” en alta.
 */
export function LoginScreen({
  theme: _theme,
  setTheme: _setTheme,
  onSignIn,
  onSignUp,
  onMagicLink,
  onResetPassword,
}: LoginScreenProps) {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [step, setStep] = useState<"credentials" | "help">("credentials");

  useEffect(() => {
    const html = document.documentElement;
    const body = document.body;
    const prevHtml = html.style.overflow;
    const prevBody = body.style.overflow;
    html.style.overflow = "hidden";
    body.style.overflow = "hidden";
    html.style.height = "100%";
    body.style.height = "100%";
    return () => {
      html.style.overflow = prevHtml;
      body.style.overflow = prevBody;
      html.style.height = "";
      body.style.height = "";
    };
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);

    const cleanName = fullName.trim().replace(/\s+/g, " ");
    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail.includes("@")) {
      setError("Escribe el correo de tu cuenta Donexto.");
      return;
    }
    if (mode === "signup" && cleanName.length < 2) {
      setError("Escribe tu nombre completo para la cuenta Donexto.");
      return;
    }
    if (password.length < 8) {
      setError(
        "La contraseña de tu cuenta Donexto usa al menos 8 caracteres.",
      );
      return;
    }

    setBusy(true);
    try {
      if (mode === "signup") {
        await onSignUp(cleanEmail, password, cleanName);
        setMessage("Cuenta Donexto creada. Ya puedes usar la app.");
      } else {
        await onSignIn(cleanEmail, password);
      }
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : mode === "signup"
            ? "No fue posible crear la cuenta Donexto."
            : "No fue posible iniciar sesión en Donexto.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function magicLink() {
    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail.includes("@")) {
      setError("Escribe primero el correo de tu cuenta Donexto.");
      return;
    }
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await onMagicLink(cleanEmail);
      setMessage(
        "Revisa tu correo: enviamos un enlace para entrar a Donexto sin contraseña.",
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
      setError("Escribe primero el correo de tu cuenta Donexto.");
      return;
    }
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await onResetPassword(cleanEmail);
      setMessage(
        "Enviamos un enlace para restablecer la contraseña de tu cuenta Donexto.",
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

  const qualityLine = DONEXTO_QUALITY.quality
    .map((item) => item.title)
    .join(" · ");

  return (
    <main className="dx-auth">
      <div className="dx-auth__frame">
        <header className="dx-auth__brandbar">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            className="dx-auth__mark"
            src="/brand/donexto-logo-official.png"
            width={48}
            height={48}
            alt=""
            decoding="async"
          />
          <div className="dx-auth__wordmark">
            <p className="dx-auth__brand">Donexto</p>
            <p className="dx-auth__slogan">{DONEXTO_QUALITY.slogan}</p>
          </div>
        </header>

        <div className="dx-auth__mission">
          <h1 className="dx-auth__promise">{DONEXTO_QUALITY.promise}</h1>
          <p className="dx-auth__mission-body">{DONEXTO_QUALITY.mission}</p>
          <p className="dx-auth__pillars">{qualityLine}</p>
        </div>

        <section className="dx-auth__access" aria-labelledby="dx-auth-title">
          <div className="dx-auth__mode" role="tablist" aria-label="Modo de acceso">
            <button
              type="button"
              role="tab"
              aria-selected={mode === "signin"}
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
              role="tab"
              aria-selected={mode === "signup"}
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

          <h2 id="dx-auth-title" className="dx-auth__title">
            {mode === "signup"
              ? ACCOUNT_VS_MAILBOX.loginTitleSignUp
              : ACCOUNT_VS_MAILBOX.loginTitleSignIn}
          </h2>
          <p className="dx-auth__boundary">{DONEXTO_QUALITY.boundary}</p>

          {step === "credentials" ? (
            <form
              className="dx-auth__form"
              onSubmit={submit}
              noValidate
              aria-labelledby="dx-auth-title"
            >
              {mode === "signup" ? (
                <label className="dx-auth__field">
                  <span>{ACCOUNT_VS_MAILBOX.signupFullNameLabel}</span>
                  <div className="dx-auth__control">
                    <User size={18} aria-hidden />
                    <input
                      type="text"
                      name="full_name"
                      value={fullName}
                      autoComplete="name"
                      autoCapitalize="words"
                      spellCheck={false}
                      placeholder="Nombre y apellido"
                      disabled={busy}
                      onChange={(event) => setFullName(event.target.value)}
                    />
                  </div>
                </label>
              ) : null}

              <label className="dx-auth__field">
                <span>{ACCOUNT_VS_MAILBOX.loginEmailLabel}</span>
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
                <span>{ACCOUNT_VS_MAILBOX.loginPasswordLabel}</span>
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

              <button type="submit" className="dx-auth__submit" disabled={busy}>
                {busy ? (
                  <>
                    <LoaderCircle className="dx-auth__spin" size={18} />
                    {mode === "signup" ? "Creando…" : "Entrando…"}
                  </>
                ) : mode === "signup" ? (
                  "Crear cuenta Donexto"
                ) : (
                  "Entrar a Donexto"
                )}
              </button>

              {mode === "signin" ? (
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
              ) : null}
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
                Usa el correo de tu cuenta Donexto. El buzón se conecta después.
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
                Restablecer contraseña Donexto
              </button>
            </div>
          )}
        </section>

        <footer className="dx-auth__footer">
          <p className="dx-auth__legal">
            <span>© HMSR · MR</span>
            <span>Héctor M. Salcido Roacho</span>
          </p>
        </footer>
      </div>
    </main>
  );
}
