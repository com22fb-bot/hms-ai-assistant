export const RAILWAY_API_BASE =
  "https://hms-ai-assistant-production.up.railway.app";

export function configuredPublicApiBase(): string {
  const explicit =
    process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "")?.trim() ?? "";

  if (explicit) {
    return explicit;
  }

  if (typeof window !== "undefined") {
    const host = window.location.hostname.toLowerCase();
    const isLocalhost =
      host === "localhost" ||
      host.startsWith("127.0.0.1") ||
      host.includes("github.dev") ||
      host.includes("githubpreview.dev") ||
      host.includes("vercel.app");

    if (isLocalhost || host.endsWith(".donexto.com") || host === "app.donexto.com") {
      return RAILWAY_API_BASE;
    }
  }

  return "/api/hms";
}

export function buildApiUrl(path: string): string {
  const route = path.startsWith("/") ? path : `/${path}`;
  const base = configuredPublicApiBase();
  return `${base}${route}`;
}
