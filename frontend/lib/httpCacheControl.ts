/**
 * Cache-Control for HTML / RSC document responses (login, admin, navigations).
 *
 * Next.js SSG defaults to `s-maxage=31536000`, which lets Cloudflare pin stale
 * HTML that still points at old hashed `/_next/static/*` chunks after deploy.
 * Documents must revalidate on every request.
 */
export const DOCUMENT_CACHE_CONTROL =
  "private, no-cache, no-store, must-revalidate";

/**
 * Hashed webpack/turbopack files under `/_next/static/`.
 * Filenames change every build; long immutable cache is correct.
 */
export const HASHED_STATIC_ASSET_CACHE_CONTROL =
  "public,max-age=31536000,immutable";
