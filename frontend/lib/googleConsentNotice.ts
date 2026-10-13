// Aviso "Compromiso Donexto" antes de mandar al usuario a la pantalla de Google.
// Texto ajustado a los permisos reales (gmail.readonly): no puede enviar ni borrar.
// No decimos "nunca comparte": el análisis con IA puede usar un proveedor externo.

type Copy = { title: string; body: string; ok: string; cancel: string };

export const GOOGLE_CONSENT_COPY: Record<string, Copy> = {
  es: {
    title: "Compromiso Donexto",
    body: "Ahora Google te pedirá confirmar el acceso. Es un paso normal y seguro de la conexión. Donexto solo lee tu correo para organizarlo: no puede enviar ni borrar tus mensajes, nunca vende tus datos ni los usa para publicidad, y puedes quitar el acceso cuando quieras.",
    ok: "Continuar con Google",
    cancel: "Ahora no",
  },
  en: {
    title: "Donexto commitment",
    body: "Google will now ask you to confirm access. This is a normal, safe step of the connection. Donexto only reads your email to organize it: it cannot send or delete your messages, never sells your data or uses it for ads, and you can remove access anytime.",
    ok: "Continue with Google",
    cancel: "Not now",
  },
  fr: {
    title: "Engagement Donexto",
    body: "Google va vous demander de confirmer l’accès. C’est une étape normale et sûre de la connexion. Donexto lit seulement vos e-mails pour les organiser : il ne peut ni envoyer ni supprimer vos messages, ne vend jamais vos données ni ne les utilise pour la publicité, et vous pouvez retirer l’accès à tout moment.",
    ok: "Continuer avec Google",
    cancel: "Plus tard",
  },
  it: {
    title: "Impegno Donexto",
    body: "Ora Google ti chiederà di confermare l’accesso. È un passaggio normale e sicuro della connessione. Donexto legge la tua posta solo per organizzarla: non può inviare né eliminare i tuoi messaggi, non vende mai i tuoi dati né li usa per pubblicità, e puoi revocare l’accesso quando vuoi.",
    ok: "Continua con Google",
    cancel: "Non ora",
  },
  pt: {
    title: "Compromisso Donexto",
    body: "Agora o Google vai pedir que você confirme o acesso. É uma etapa normal e segura da conexão. A Donexto só lê seu e-mail para organizá-lo: não pode enviar nem apagar suas mensagens, nunca vende seus dados nem os usa para publicidade, e você pode remover o acesso quando quiser.",
    ok: "Continuar com o Google",
    cancel: "Agora não",
  },
};

export function googleConsentCopy(lang?: string): Copy {
  const code = (lang || "es").slice(0, 2).toLowerCase();
  return GOOGLE_CONSENT_COPY[code] ?? GOOGLE_CONSENT_COPY.es;
}

/** Muestra el aviso; resuelve true si el usuario continúa. */
export function confirmGoogleConsent(lang?: string): Promise<boolean> {
  if (typeof document === "undefined") return Promise.resolve(true);
  const c = googleConsentCopy(lang || document.documentElement.lang);
  return new Promise((resolve) => {
    const overlay = document.createElement("div");
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", "true");
    overlay.setAttribute("aria-labelledby", "dx-gc-title");
    overlay.style.cssText =
      "position:fixed;inset:0;z-index:9999;display:flex;align-items:flex-end;justify-content:center;background:rgba(15,23,42,.55);padding:16px;padding-bottom:max(16px,env(safe-area-inset-bottom));";
    const card = document.createElement("div");
    card.style.cssText =
      "width:100%;max-width:420px;background:#fff;color:#0f172a;border-radius:16px;padding:20px;box-shadow:0 10px 30px rgba(0,0,0,.25);font:15px/1.5 system-ui,-apple-system,sans-serif;margin:auto 0;";
    const h = document.createElement("h2");
    h.id = "dx-gc-title";
    h.textContent = `🔒 ${c.title}`;
    h.style.cssText = "margin:0 0 8px;font-size:18px;font-weight:700;";
    const p = document.createElement("p");
    p.textContent = c.body;
    p.style.cssText = "margin:0 0 16px;";
    const row = document.createElement("div");
    row.style.cssText = "display:flex;flex-direction:column;gap:8px;";
    const ok = document.createElement("button");
    ok.type = "button";
    ok.textContent = c.ok;
    ok.style.cssText =
      "min-height:48px;border:0;border-radius:12px;background:#2563eb;color:#fff;font-weight:600;font-size:16px;cursor:pointer;";
    const cancel = document.createElement("button");
    cancel.type = "button";
    cancel.textContent = c.cancel;
    cancel.style.cssText =
      "min-height:44px;border:0;border-radius:12px;background:transparent;color:#475569;font-size:15px;cursor:pointer;";
    const done = (v: boolean) => {
      document.removeEventListener("keydown", onKey);
      overlay.remove();
      resolve(v);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") done(false);
    };
    ok.onclick = () => done(true);
    cancel.onclick = () => done(false);
    overlay.onclick = (e) => {
      if (e.target === overlay) done(false);
    };
    document.addEventListener("keydown", onKey);
    row.append(ok, cancel);
    card.append(h, p, row);
    overlay.append(card);
    document.body.append(overlay);
    ok.focus();
  });
}
