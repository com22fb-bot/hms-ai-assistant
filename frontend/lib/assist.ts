/**
 * Asistencia personalizada (/asistencia): pure helpers, no React.
 *
 * The backend signs every token. The page only keeps the session token in
 * sessionStorage (cleared when the tab closes) and trims the chat history
 * it sends back.
 */

export const ASSIST_SESSION_KEY = "donexto.assist.session";
export const ASSIST_MAX_TURNS = 12;
export const ASSIST_MAX_CHARS = 1000;
export const ASSIST_SIGNUP_URL = "https://app.donexto.com/";

export type AssistRole = "user" | "assistant";
export type AssistTurn = { role: AssistRole; content: string };
export type AssistSession = { token: string; email: string; expiresAt: number };
export type AssistCta = { label: string; detail: string; url: string };

type StorageLike = Pick<Storage, "getItem" | "setItem" | "removeItem">;

/** `?t=` from the auto-reply email, or null. */
export function linkTokenFromSearch(search: string): string | null {
  const params = new URLSearchParams(search.startsWith("?") ? search.slice(1) : search);
  const token = (params.get("t") || "").trim();
  return token.length >= 10 && token.length <= 2000 && token.includes(".") ? token : null;
}

/** `?lang=` from the auto-reply link (2 letters), default Spanish. */
export function langFromSearch(search: string): string {
  const params = new URLSearchParams(search.startsWith("?") ? search.slice(1) : search);
  const code = (params.get("lang") || "").toLowerCase().replace(/[^a-z]/g, "").slice(0, 2);
  return code.length === 2 ? code : "es";
}

/** Same URL without `t`, so a reload or a shared screenshot does not leak it. */
export function stripLinkToken(href: string): string {
  const url = new URL(href);
  url.searchParams.delete("t");
  return `${url.pathname}${url.search}${url.hash}`;
}

export function sessionFromVerified(payload: unknown, now = Date.now()): AssistSession | null {
  if (!payload || typeof payload !== "object") return null;
  const record = payload as Record<string, unknown>;
  const token = typeof record.session === "string" ? record.session : "";
  const email = typeof record.email === "string" ? record.email : "";
  const seconds = typeof record.expires_in === "number" ? record.expires_in : 0;
  if (record.status !== "verified" || !token || seconds <= 0) return null;
  // One minute of margin so a request does not race the expiry.
  return { token, email, expiresAt: now + Math.max(0, seconds - 60) * 1000 };
}

export function saveSession(storage: StorageLike, session: AssistSession): void {
  storage.setItem(ASSIST_SESSION_KEY, JSON.stringify(session));
}

export function loadSession(storage: StorageLike, now = Date.now()): AssistSession | null {
  const raw = storage.getItem(ASSIST_SESSION_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as Partial<AssistSession>;
    if (
      typeof parsed.token === "string" &&
      typeof parsed.email === "string" &&
      typeof parsed.expiresAt === "number" &&
      parsed.expiresAt > now
    ) {
      return { token: parsed.token, email: parsed.email, expiresAt: parsed.expiresAt };
    }
  } catch {
    // fall through
  }
  storage.removeItem(ASSIST_SESSION_KEY);
  return null;
}

export function clearSession(storage: StorageLike): void {
  storage.removeItem(ASSIST_SESSION_KEY);
}

/** Last turns only, each trimmed, empties dropped. Matches the backend limits. */
export function historyForRequest(turns: AssistTurn[]): AssistTurn[] {
  return turns
    .map((turn) => ({ role: turn.role, content: turn.content.replace(/\s+/g, " ").trim().slice(0, ASSIST_MAX_CHARS) }))
    .filter((turn) => turn.content.length > 0)
    .slice(-ASSIST_MAX_TURNS);
}

export function onlyDigits(value: string): string {
  return value.replace(/\D/g, "").slice(0, 6);
}

export function welcomeMessage(maskedEmail: string): string {
  const who = maskedEmail ? ` (${maskedEmail})` : "";
  return (
    `¡Listo! Verificamos tu correo${who}. Soy el asistente de Donexto. ` +
    "Pregúntame cómo funciona, qué correos puedes conectar, cómo cuidamos tu privacidad o cuánto cuesta. " +
    "Si prefieres a una persona, dímelo y el equipo te escribe."
  );
}

export function ctaFromPayload(payload: unknown): AssistCta | null {
  if (!payload || typeof payload !== "object") return null;
  const cta = (payload as Record<string, unknown>).cta;
  if (!cta || typeof cta !== "object") return null;
  const record = cta as Record<string, unknown>;
  const url = typeof record.url === "string" ? record.url : "";
  // Only our own app; never follow a URL the server did not mean.
  if (!/^https:\/\/(?:app|www)\.donexto\.com\//.test(url)) return null;
  return {
    label: String(record.label || "Crear mi cuenta y suscribirme"),
    detail: String(record.detail || ""),
    url,
  };
}

export function errorMessage(payload: unknown, fallback: string): string {
  if (payload && typeof payload === "object") {
    const detail = (payload as Record<string, unknown>).detail;
    if (detail && typeof detail === "object") {
      const message = (detail as Record<string, unknown>).message;
      if (typeof message === "string" && message) return message;
    }
  }
  return fallback;
}

export type TextSegment = { text: string; href?: string };

const LINK_RE =
  /(https?:\/\/(?:www\.|app\.)?donexto\.com(?:\/[^\s),;]*)?|(?:www\.|app\.)donexto\.com(?:\/[^\s),;]*)?|support@donexto\.com)/gi;

/**
 * Split chat text into plain parts and clickable links. Only donexto.com
 * addresses and support@donexto.com become links; anything else stays text.
 */
export function linkSegments(text: string): TextSegment[] {
  const segments: TextSegment[] = [];
  let last = 0;
  for (const match of text.matchAll(LINK_RE)) {
    let raw = match[0];
    // Sentence punctuation right after a link is not part of it.
    while (/[.?!:]$/.test(raw)) raw = raw.slice(0, -1);
    const start = match.index ?? 0;
    if (start > last) segments.push({ text: text.slice(last, start) });
    const href = raw.includes("@")
      ? `mailto:${raw}`
      : /^https?:\/\//i.test(raw)
        ? raw
        : `https://${raw}`;
    segments.push({ text: raw, href });
    last = start + raw.length;
  }
  if (last < text.length) segments.push({ text: text.slice(last) });
  return segments;
}
