/** Peticiones públicas del login (sin sesión). Si el Worker falla, prueba Railway. */

export const RAILWAY_API_BASE =
  "https://hms-ai-assistant-production.up.railway.app";

export function configuredPublicApiBase(): string {
  return (
    process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") || "/api/hms"
  );
}

export function isBrowserNetworkError(error: unknown): boolean {
  if (!(error instanceof TypeError)) {
    return false;
  }
  return /failed to fetch|networkerror|load failed|network request failed/i.test(
    error.message,
  );
}

function publicApiBases(): string[] {
  const primary = configuredPublicApiBase();
  if (primary === RAILWAY_API_BASE) {
    return [primary];
  }
  return [primary, RAILWAY_API_BASE];
}

export async function postPublicHms(
  path: string,
  body: unknown,
): Promise<{ ok: boolean; status: number; payload: unknown }> {
  const route = path.startsWith("/") ? path : `/${path}`;
  let lastNetwork: Error | null = null;

  for (const base of publicApiBases()) {
    try {
      const response = await fetch(`${base}${route}`, {
        method: "POST",
        cache: "no-store",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      let payload: unknown = {};
      try {
        payload = await response.json();
      } catch {
        payload = {};
      }
      return { ok: response.ok, status: response.status, payload };
    } catch (error) {
      if (isBrowserNetworkError(error)) {
        lastNetwork =
          error instanceof Error ? error : new Error("Failed to fetch");
        continue;
      }
      throw error;
    }
  }

  throw lastNetwork ?? new Error("Failed to fetch");
}
