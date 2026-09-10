// default open-next.config.ts file created by @opennextjs/cloudflare
import { defineCloudflareConfig } from "@opennextjs/cloudflare";
// import r2IncrementalCache from "@opennextjs/cloudflare/overrides/incremental-cache/r2-incremental-cache";

export default defineCloudflareConfig({
	// Dummy incremental cache (default): do not serve year-old prerendered HTML
	// from R2 / Static Assets. App documents must stay request-time so deploys
	// pick up new hashed `/_next/static/*` chunks without a hard refresh.
	// See https://opennext.js.org/cloudflare/caching
	// incrementalCache: r2IncrementalCache
});
