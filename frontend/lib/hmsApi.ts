import { supabase } from "@/lib/supabase";

export class HmsApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "HmsApiError";
    this.status = status;
  }
}

function detailMessage(payload: unknown): string | null {
  if (!payload || typeof payload !== "object") {
    return null;
  }

  const detail = (payload as { detail?: unknown }).detail;

  if (typeof detail === "string") {
    return detail;
  }

  if (detail && typeof detail === "object") {
    const message = (detail as { message?: unknown }).message;
    return typeof message === "string" ? message : null;
  }

  const message = (payload as { message?: unknown }).message;
  return typeof message === "string" ? message : null;
}

export async function hmsFetch(
  input: RequestInfo | URL,
  init: RequestInit = {},
): Promise<Response> {
  const { data, error } = await supabase.auth.getSession();

  if (error || !data.session?.access_token) {
    throw new HmsApiError(
      "La sesión Donexto expiró. Vuelve a iniciar sesión.",
      401,
    );
  }

  const headers = new Headers(init.headers);
  headers.set(
    "Authorization",
    `Bearer ${data.session.access_token}`,
  );

  return fetch(input, {
    ...init,
    headers,
  });
}

export async function hmsJson<T>(
  input: RequestInfo | URL,
  init: RequestInit = {},
): Promise<T> {
  const response = await hmsFetch(input, init);
  const raw = await response.text();
  let payload: unknown = null;

  if (raw.trim()) {
    try {
      payload = JSON.parse(raw) as unknown;
    } catch {
      payload = { message: raw.trim() };
    }
  }

  if (!response.ok) {
    throw new HmsApiError(
      detailMessage(payload) ??
        `La operación de Donexto respondió HTTP ${response.status}.`,
      response.status,
    );
  }

  return payload as T;
}
