/**
 * Path routes for donexto-app on the marketing hostnames.
 *
 * The landing is Cloudflare Pages on donexto.com and www.donexto.com.
 * These patterns are more specific than the Pages site, so / stays the
 * landing. They are applied by configure-admin-routes.mjs, not by
 * `npm run deploy`: wrangler.jsonc has no routes key on purpose, because
 * a routes list in that file would replace the app.donexto.com custom domain.
 */

export const ADMIN_WORKER_SCRIPT = "donexto-app";
export const ADMIN_ZONE_NAME = "donexto.com";

const MARKETING_HOSTS = ["www.donexto.com", "donexto.com"];

const PATH_SUFFIXES = [
  "/admin*",
  "/_next/*",
  "/api/hms*",
  "/brand/*",
  "/favicon.ico",
  "/manifest.webmanifest",
];

export const ADMIN_WORKER_ROUTE_PATTERNS = MARKETING_HOSTS.flatMap((host) =>
  PATH_SUFFIXES.map((suffix) => `${host}${suffix}`),
);

const WHOLE_HOST = /^(?:www\.)?donexto\.com(?:\/\*)?$/;

export function assertAdminRoutesLeaveMarketingRoot(patterns) {
  if (!Array.isArray(patterns) || patterns.length === 0) {
    throw new Error("Faltan rutas de admin.");
  }
  for (const pattern of patterns) {
    if (typeof pattern !== "string" || WHOLE_HOST.test(pattern)) {
      throw new Error(
        `La ruta ${pattern} se comería la landing. Solo paths de admin, assets y API.`,
      );
    }
    if (!pattern.includes("/admin") && !pattern.includes("/_next/") && !pattern.includes("/api/hms") && !pattern.includes("/brand/") && !pattern.endsWith("/favicon.ico") && !pattern.endsWith("/manifest.webmanifest")) {
      throw new Error(`Ruta de admin no reconocida: ${pattern}`);
    }
  }
  for (const host of MARKETING_HOSTS) {
    if (!patterns.includes(`${host}/admin*`)) {
      throw new Error(`Falta ${host}/admin*`);
    }
  }
}
