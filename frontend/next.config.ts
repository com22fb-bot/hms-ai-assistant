import path from "node:path";
import { fileURLToPath } from "node:url";
import type { NextConfig } from "next";

// Root must be this folder (frontend/), not the monorepo root.
// A package-lock.json in the parent makes Next 16 mis-detect the root
// and fail with: Couldn't find any `pages` or `app` directory.
const frontendRoot = path.dirname(fileURLToPath(import.meta.url));

const nextConfig: NextConfig = {
  outputFileTracingRoot: frontendRoot,
  turbopack: {
    root: frontendRoot,
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
