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
  User,
} from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

import { ACCOUNT_VS_MAILBOX } from "@/lib/accountVsMailbox";
import { DONEXTO_QUALITY } from "@/lib/donextoQuality";
import type { SignUpResult } from "@/hooks/useAppAuth";

import "./hms-gate.css";
import "./dx-auth-neon.css";

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
  ) => Promise<SignUpResult>;
  onResendSignupEmail?: (email: string) => Promise<void>;
  onMagicLink: (email: string) => Promise<void>;
  onResetPassword: (email: string) => Promise<void>;
};

/**
 * Gate Donexto — split en escritorio, columna en celular.
 * Logo 3D “Do Next To…” (D, no P). Cuenta ≠ buzón.
 */
export function LoginScreen({
  theme: _theme,
  setTheme: _setTheme,
  onSignIn,
  onSignUp,
  onResendSignupEmail,
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
  const [signupDone, setSignupDone] = useState(false);

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
    if (busy || signupDone) {
      return;
    }
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
        const result = await onSignUp(cleanEmail, password, cleanName);
        if (result.kind === "already_registered") {
          setError(
            "Ya existe una cuenta Donexto con ese correo. Entra o recupera tu contraseña.",
          );
          return;
        }
        if (result.kind === "confirm_email") {
          setSignupDone(true);
          setMessage(
            `Cuenta creada. Revisa ${cleanEmail} (bandeja y spam) y confirma el enlace. Luego vuelve aquí y entra.`,
          );
          return;
        }
        setSignupDone(true);
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

  async function resendConfirm() {
    if (!onResendSignupEmail || busy) {
      return;
    }
    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail.includes("@")) {
      setError("Escribe el correo de tu cuenta Donexto.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await onResendSignupEmail(cleanEmail);
      setMessage(
        `Reenviamos el correo de confirmación a ${cleanEmail}. Revisa bandeja y spam.`,
      );
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "No fue posible reenviar el correo de confirmación.",
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

  const gateClass = [
    "dx-auth",
    mode === "signup" || signupDone ? "dx-auth--signup" : "",
    step === "help" ? "dx-auth--help" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <main className={gateClass}>
      <aside className="dx-auth__hero">
        <div className="dx-auth__hero-inner">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            className="dx-auth__logo"
            src="/brand/donexto-3d-do-next-to-tile.png"
            width={512}
            height={512}
            alt="Donexto — Do Next To…"
            decoding="async"
          />
          <p className="dx-auth__brand">Donexto</p>
          <h1 className="dx-auth__promise">{DONEXTO_QUALITY.whatItDoes}</h1>
        </div>
      </aside>

      <section className="dx-auth__panel">
        <div className="dx-auth__card" aria-labelledby="dx-auth-title">
          <h2 id="dx-auth-title" className="dx-auth__title">
            {signupDone
              ? "Confirma tu correo"
              : mode === "signup"
                ? ACCOUNT_VS_MAILBOX.loginTitleSignUp
                : ACCOUNT_VS_MAILBOX.loginTitleSignIn}
          </h2>
          {!signupDone ? (
            <p className="dx-auth__boundary">{DONEXTO_QUALITY.boundary}</p>
          ) : null}

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
                setSignupDone(false);
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
                setSignupDone(false);
              }}
            >
              Crear cuenta
            </button>
          </div>

          {signupDone ? (
            <div className="dx-auth__done">
              <div className="dx-auth__alert is-ok" role="status">
                <CheckCircle2 size={18} />
                <span>{message}</span>
              </div>
              {error ? (
                <div className="dx-auth__alert is-error" role="alert">
                  <AlertTriangle size={18} />
                  <span>{error}</span>
                </div>
              ) : null}
              {onResendSignupEmail ? (
                <button
                  type="button"
                  className="dx-auth__secondary"
                  disabled={busy}
                  onClick={() => void resendConfirm()}
                >
                  {busy ? (
                    <>
                      <LoaderCircle className="dx-auth__spin" size={18} />
                      Reenviando…
                    </>
                  ) : (
                    <>
                      <Mail size={18} />
                      Reenviar correo de confirmación
                    </>
                  )}
                </button>
              ) : null}
              <button
                type="button"
                className="dx-auth__submit"
                disabled={busy}
                onClick={() => {
                  setSignupDone(false);
                  setMode("signin");
                  setStep("credentials");
                  setMessage(null);
                  setError(null);
                }}
              >
                Ya confirmé — Entrar
              </button>
            </div>
          ) : step === "credentials" ? (
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

              <button
                type="submit"
                className="dx-auth__submit"
                disabled={busy || signupDone}
              >
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
        </div>

        <p className="dx-auth__secure">
          <ShieldCheck size={14} aria-hidden />
          {ACCOUNT_VS_MAILBOX.loginFoot}
        </p>

        <footer className="dx-auth__footer">
          <p className="dx-auth__legal">
            <span>© HMSR · MR</span>
            <span>Héctor M. Salcido Roacho</span>
          </p>
        </footer>
      </section>
    </main>
  );
}
