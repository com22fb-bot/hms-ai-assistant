/**
 * Attach donexto-app path routes on www + apex. Does not delete routes.
 *
 *   CLOUDFLARE_API_TOKEN=... node scripts/configure-admin-routes.mjs
 *   node scripts/configure-admin-routes.mjs --dry-run
 *
 * Token needs Zone → Read and Zone → Workers Routes → Edit on donexto.com.
 * `npm run deploy` does not run this. See docs/ops/ADMIN_EN_WWW.md.
 */

import {
  ADMIN_WORKER_ROUTE_PATTERNS,
  ADMIN_WORKER_SCRIPT,
  ADMIN_ZONE_NAME,
  assertAdminRoutesLeaveMarketingRoot,
} from "./adminWorkerRoutes.mjs";

const API = "https://api.cloudflare.com/client/v4";

function dryRun() {
  return process.argv.includes("--dry-run");
}

async function cf(token, path, init = {}) {
  const response = await fetch(`${API}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      ...(init.headers ?? {}),
    },
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || payload.success === false) {
    const detail = JSON.stringify(payload.errors || payload, null, 2);
    throw new Error(`Cloudflare ${path} HTTP ${response.status}: ${detail}`);
  }
  return payload;
}

async function main() {
  assertAdminRoutesLeaveMarketingRoot(ADMIN_WORKER_ROUTE_PATTERNS);
  console.log(`Worker: ${ADMIN_WORKER_SCRIPT}`);
  console.log(`Zona: ${ADMIN_ZONE_NAME}`);
  for (const pattern of ADMIN_WORKER_ROUTE_PATTERNS) {
    console.log(`- ${pattern}`);
  }

  if (dryRun()) {
    console.log("Dry-run: no se llamó a la API.");
    return;
  }

  const token = process.env.CLOUDFLARE_API_TOKEN?.trim() ?? "";
  if (!token) {
    console.error(
      "Falta CLOUDFLARE_API_TOKEN. Crea las rutas en el dashboard o exporta el token y vuelve a correr este script.",
    );
    process.exitCode = 1;
    return;
  }

  const zones = await cf(
    token,
    `/zones?name=${encodeURIComponent(ADMIN_ZONE_NAME)}`,
  );
  const zone = (zones.result ?? []).find((item) => item.name === ADMIN_ZONE_NAME);
  if (!zone?.id) {
    throw new Error(`No encontré la zona ${ADMIN_ZONE_NAME}.`);
  }

  const existing = await cf(token, `/zones/${zone.id}/workers/routes`);
  const have = new Set(
    (existing.result ?? []).map((route) => String(route.pattern || "")),
  );

  for (const pattern of ADMIN_WORKER_ROUTE_PATTERNS) {
    if (have.has(pattern)) {
      console.log(`Ya existe: ${pattern}`);
      continue;
    }
    await cf(token, `/zones/${zone.id}/workers/routes`, {
      method: "POST",
      body: JSON.stringify({ pattern, script: ADMIN_WORKER_SCRIPT }),
    });
    console.log(`Creada: ${pattern} → ${ADMIN_WORKER_SCRIPT}`);
  }
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : error);
  process.exitCode = 1;
});
