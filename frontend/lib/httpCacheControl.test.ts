import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { describe, it } from "node:test";
import { fileURLToPath } from "node:url";

import {
  DOCUMENT_CACHE_CONTROL,
  HASHED_STATIC_ASSET_CACHE_CONTROL,
} from "./httpCacheControl.ts";

const frontendRoot = join(dirname(fileURLToPath(import.meta.url)), "..");

describe("document vs hashed-static cache policy", () => {
  it("keeps documents off the CDN year-long TTL", () => {
    assert.equal(
      DOCUMENT_CACHE_CONTROL,
      "private, no-cache, no-store, must-revalidate",
    );
    assert.doesNotMatch(DOCUMENT_CACHE_CONTROL, /s-maxage=31536000/);
    assert.equal(
      HASHED_STATIC_ASSET_CACHE_CONTROL,
      "public,max-age=31536000,immutable",
    );
  });

  it("forces App Router documents to render per request", () => {
    const layout = readFileSync(join(frontendRoot, "app/layout.tsx"), "utf8");
    assert.match(layout, /export const dynamic = "force-dynamic"/);
    assert.match(layout, /export const revalidate = 0/);
  });

  it("sets document Cache-Control in next.config for Worker responses", () => {
    const config = readFileSync(join(frontendRoot, "next.config.ts"), "utf8");
    assert.match(config, /DOCUMENT_CACHE_CONTROL/);
    assert.match(config, /HASHED_STATIC_ASSET_CACHE_CONTROL/);
    assert.match(config, /source: "\/"/);
    assert.match(config, /source: "\/:path\(\(\?!_next\/static\|_next\/image\).\*\)"/);
    assert.match(config, /source: "\/_next\/static\/:path\*"/);
  });

  it("keeps Cloudflare Static Assets long-cache only for hashed chunks", () => {
    const headers = readFileSync(join(frontendRoot, "public/_headers"), "utf8");
    assert.match(
      headers,
      /\/_next\/static\/\*\s*\n\s*Cache-Control:\s*public,max-age=31536000,immutable/,
    );
    assert.doesNotMatch(
      headers,
      /(?:^|\n)\/(?:\s|\n).*s-maxage=31536000/,
    );
  });
});
