import path from "node:path";
import { fileURLToPath } from "node:url";
import type { NextConfig } from "next";

import { DOCUMENT_CACHE_CONTROL } from "./lib/httpCacheControl";

// Root must be this folder (frontend/), not the monorepo root.
// A package-lock.json in the parent makes Next 16 mis-detect the root
// and fail with: Couldn't find any `pages` or `app` directory.
const frontendRoot = path.dirname(fileURLToPath(import.meta.url));

const documentCacheHeaders = [
  { key: "Cache-Control", value: DOCUMENT_CACHE_CONTROL },
];

const nextConfig: NextConfig = {
  outputFileTracingRoot: frontendRoot,
  turbopack: {
    root: frontendRoot,
  },
  // Belt-and-suspenders for Worker-served documents / RSC. Next overwrites
  // Cache-Control on SSG pages, so `app/layout.tsx` is also `force-dynamic`.
  // Exclude `/_next/static` so hashed chunks keep long immutable cache when
  // Next itself serves them (`next start`). On Cloudflare, those files come
  // from Static Assets + `public/_headers`, not this `headers()` map.
  async headers() {
    return [
      { source: "/", headers: documentCacheHeaders },
      {
        source: "/:path((?!_next/static|_next/image).*)",
        headers: documentCacheHeaders,
      },
    ];
  },
};

export default nextConfig;

// OpenNext/Cloudflare binding simulation only when explicitly enabled.
// Default off so `./hms start` works in this monorepo.
if (process.env.OPENNEXT_CLOUDFLARE_DEV === "1") {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { initOpenNextCloudflareForDev } = require("@opennextjs/cloudflare");
  initOpenNextCloudflareForDev();
}
