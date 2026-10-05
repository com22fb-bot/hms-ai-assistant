"use client";

import { ArrowRight, Mail, MessageCircle, Send, ShieldCheck, Sparkles } from "lucide-react";
import { FormEvent, useEffect, useRef, useState } from "react";

import {
  ASSIST_SIGNUP_URL,
  type AssistCta,
  type AssistSession,
  type AssistTurn,
  clearSession,
  ctaFromPayload,
  errorMessage,
  historyForRequest,
  langFromSearch,
  linkSegments,
  linkTokenFromSearch,
  loadSession,
  onlyDigits,
  saveSession,
  sessionFromVerified,
  stripLinkToken,
  welcomeMessage,
} from "@/lib/assist";
import { postPublicHms } from "@/lib/publicHms";

type Step = "loading" | "email" | "code" | "chat";

const DEFAULT_CTA: AssistCta = {
  label: "Crear mi cuenta y suscribirme",
  detail: "Plan Normal · US$19.99 al mes",
  url: ASSIST_SIGNUP_URL,
};

const OFFLINE = "Sin conexión con Donexto. Revisa la red e inténtalo otra vez.";

/**
 * /asistencia: verify the email (signed link from the auto-reply, or a
 * 6-digit code), then chat. Replies come from rules or the contact AI on the
 * backend; the mailbox analyzer (AI_PROVIDER) is never involved.
 */
export function AssistChat() {
  const [step, setStep] = useState<Step>("loading");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [challenge, setChallenge] = useState("");
  const [session, setSession] = useState<AssistSession | null>(null);
  const [turns, setTurns] = useState<AssistTurn[]>([]);
  const [draft, setDraft] = useState("");
  const [cta, setCta] = useState<AssistCta>(DEFAULT_CTA);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lang, setLang] = useState("es");
  const endRef = useRef<HTMLDivElement | null>(null);

  function enterChat(next: AssistSession) {
    saveSession(window.sessionStorage, next);
    setSession(next);
    setTurns([{ role: "assistant", content: welcomeMessage(next.email) }]);
    setStep("chat");
  }

  // Runs once, even under React Strict Mode's double effect in dev: the link
  // token is removed from the URL before the first await, so a second run
  // must not start over and fall back to the email step.
  const booted = useRef(false);
  useEffect(() => {
    if (booted.current) return;
    booted.current = true;
    async function boot() {
      setLang(langFromSearch(window.location.search));
      const token = linkTokenFromSearch(window.location.search);
      if (token) {
        window.history.replaceState(null, "", stripLinkToken(window.location.href));
        try {
          const result = await postPublicHms("/public/assist/redeem", { token });
          const verified = result.ok ? sessionFromVerified(result.payload) : null;
          if (verified) {
            enterChat(verified);
            return;
          }
          setError(errorMessage(result.payload, "El enlace no es válido. Verifica tu correo con un código."));
        } catch {
          setError(OFFLINE);
        }
        setStep("email");
        return;
      }
      const stored = loadSession(window.sessionStorage);
      if (stored) {
        enterChat(stored);
      } else {
        setStep("email");
      }
    }
    void boot();
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns]);

  async function requestCode(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const result = await postPublicHms("/public/assist/start", {
        email: email.trim().toLowerCase(),
        lang,
      });
      const payload = result.payload as Record<string, unknown>;
      if (result.ok && typeof payload.challenge === "string") {
        setChallenge(payload.challenge);
        setCode("");
        setNotice(`Te enviamos un código de 6 dígitos a ${email.trim().toLowerCase()}. Revisa también Spam.`);
        setStep("code");
      } else {
        setError(errorMessage(result.payload, "No pudimos enviar el código. Inténtalo otra vez."));
      }
    } catch {
      setError(OFFLINE);
    } finally {
      setBusy(false);
    }
  }

  async function confirmCode(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const result = await postPublicHms("/public/assist/verify", { challenge, code });
      const verified = result.ok ? sessionFromVerified(result.payload) : null;
      if (verified) {
        setNotice(null);
        enterChat(verified);
      } else {
        setError(errorMessage(result.payload, "Ese código no coincide."));
      }
    } catch {
      setError(OFFLINE);
    } finally {
      setBusy(false);
    }
  }

  async function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = draft.trim();
    if (!text || !session || busy) return;
    const next: AssistTurn[] = [...turns, { role: "user", content: text }];
    setTurns(next);
    setDraft("");
    setError(null);
    setBusy(true);
    try {
      const result = await postPublicHms("/public/assist/chat", {
        session: session.token,
        lang,
        // The welcome bubble is local; the backend wants the visitor first.
        messages: historyForRequest(next.slice(1)),
      });
      const payload = result.payload as Record<string, unknown>;
      if (result.status === 401) {
        clearSession(window.sessionStorage);
        setSession(null);
        setStep("email");
        setError(errorMessage(result.payload, "Tu verificación venció. Verifica tu correo otra vez."));
        return;
      }
      if (result.ok && typeof payload.reply === "string") {
        setTurns([...next, { role: "assistant", content: payload.reply }]);
        const nextCta = ctaFromPayload(payload);
        if (nextCta) setCta(nextCta);
      } else {
        setError(errorMessage(result.payload, "No pudimos responder. Inténtalo otra vez."));
      }
    } catch {
      setError(OFFLINE);
    } finally {
      setBusy(false);
    }
  }

  function useAnotherEmail() {
    clearSession(window.sessionStorage);
    setSession(null);
    setTurns([]);
    setChallenge("");
    setCode("");
    setNotice(null);
    setError(null);
    setStep("email");
  }

  return (
    <main className="dx-assist" data-testid="assist-page">
      <section className="dx-assist__card" aria-labelledby="assist-title">
        <p className="dx-assist__eyebrow">
          <Sparkles size={14} aria-hidden /> Donexto
        </p>
        <h1 id="assist-title">Asistencia personalizada</h1>

        {step === "loading" ? <p className="dx-assist__lead">Preparando tu asistencia…</p> : null}

        {step === "email" ? (
          <>
            <p className="dx-assist__lead">
              Primero confirmamos que el correo es tuyo. Te mandamos un código de 6 dígitos; no conectamos ni leemos tu
              buzón.
            </p>
            <form className="dx-assist__form" onSubmit={(event) => void requestCode(event)}>
              <label>
                Tu correo
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
              <button type="submit" className="dx-assist__btn" disabled={busy}>
                <Mail size={16} aria-hidden />
                {busy ? "Enviando…" : "Enviarme un código"}
              </button>
            </form>
          </>
        ) : null}

        {step === "code" ? (
          <>
            {notice ? (
              <p className="dx-assist__notice" role="status">
                {notice}
              </p>
            ) : null}
            <form className="dx-assist__form" onSubmit={(event) => void confirmCode(event)}>
              <label>
                Código de 6 dígitos
                <input
                  required
                  autoComplete="one-time-code"
                  inputMode="numeric"
                  pattern="[0-9]{6}"
                  maxLength={6}
                  value={code}
                  onChange={(event) => setCode(onlyDigits(event.target.value))}
                  placeholder="123456"
                  className="dx-assist__code"
                />
              </label>
              <button type="submit" className="dx-assist__btn" disabled={busy || code.length !== 6}>
                <ShieldCheck size={16} aria-hidden />
                {busy ? "Verificando…" : "Verificar y entrar al chat"}
              </button>
            </form>
            <button type="button" className="dx-assist__link" onClick={useAnotherEmail}>
              Usar otro correo o pedir otro código
            </button>
          </>
        ) : null}

        {step === "chat" ? (
          <>
            <div className="dx-assist__chat" aria-live="polite" data-testid="assist-chat">
              {turns.map((turn, index) => (
                <div key={index} className={`dx-assist__bubble is-${turn.role}`}>
                  {turn.role === "assistant" ? <MessageCircle size={14} aria-hidden /> : null}
                  <span>
                    {turn.role === "assistant"
                      ? linkSegments(turn.content).map((segment, part) =>
                          segment.href ? (
                            <a
                              key={part}
                              href={segment.href}
                              target={segment.href.startsWith("mailto:") ? undefined : "_blank"}
                              rel="noopener noreferrer"
                            >
                              {segment.text}
                            </a>
                          ) : (
                            <span key={part}>{segment.text}</span>
                          ),
                        )
                      : turn.content}
                  </span>
                </div>
              ))}
              {busy ? <div className="dx-assist__bubble is-assistant is-typing">Escribiendo…</div> : null}
              <div ref={endRef} />
            </div>
            <form className="dx-assist__composer" onSubmit={(event) => void sendMessage(event)}>
              <input
                aria-label="Escribe tu pregunta"
                value={draft}
                maxLength={1000}
                onChange={(event) => setDraft(event.target.value)}
                placeholder="Escribe tu pregunta…"
              />
              <button type="submit" className="dx-assist__btn" disabled={busy || !draft.trim()} aria-label="Enviar">
                <Send size={16} aria-hidden />
              </button>
            </form>
            <a className="dx-assist__cta" href={cta.url} data-testid="assist-cta">
              <span>
                <b>{cta.label}</b>
                {cta.detail ? <small>{cta.detail}</small> : null}
              </span>
              <ArrowRight size={18} aria-hidden />
            </a>
            <button type="button" className="dx-assist__link" onClick={useAnotherEmail}>
              Salir o usar otro correo
            </button>
          </>
        ) : null}

        {error ? (
          <p className="dx-assist__error" role="alert">
            {error}
          </p>
        ) : null}

        <p className="dx-assist__foot">
          ¿Prefieres correo? Escribe a <a href="mailto:support@donexto.com">support@donexto.com</a>.
        </p>
      </section>
    </main>
  );
}
