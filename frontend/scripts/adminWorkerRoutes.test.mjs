import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  ADMIN_WORKER_ROUTE_PATTERNS,
  ADMIN_WORKER_SCRIPT,
  assertAdminRoutesLeaveMarketingRoot,
} from "./adminWorkerRoutes.mjs";

describe("admin worker routes", () => {
  it("covers www and the apex without taking the marketing root", () => {
    assert.equal(ADMIN_WORKER_SCRIPT, "donexto-app");
    assertAdminRoutesLeaveMarketingRoot(ADMIN_WORKER_ROUTE_PATTERNS);
    assert.ok(ADMIN_WORKER_ROUTE_PATTERNS.includes("www.donexto.com/admin*"));
    assert.ok(ADMIN_WORKER_ROUTE_PATTERNS.includes("donexto.com/admin*"));
    assert.ok(ADMIN_WORKER_ROUTE_PATTERNS.includes("www.donexto.com/_next/*"));
    assert.ok(ADMIN_WORKER_ROUTE_PATTERNS.includes("donexto.com/api/hms*"));
    assert.equal(
      ADMIN_WORKER_ROUTE_PATTERNS.some((pattern) => pattern.endsWith("/*") && !pattern.includes("/_next/") && !pattern.includes("/brand/")),
      false,
    );
    assert.equal(
      ADMIN_WORKER_ROUTE_PATTERNS.includes("www.donexto.com/*"),
      false,
    );
    assert.equal(ADMIN_WORKER_ROUTE_PATTERNS.includes("donexto.com/*"), false);
    assert.equal(ADMIN_WORKER_ROUTE_PATTERNS.includes("app.donexto.com/*"), false);
  });

  it("rejects a catch-all that would replace the landing", () => {
    assert.throws(
      () => assertAdminRoutesLeaveMarketingRoot(["www.donexto.com/*"]),
      /landing/,
    );
    assert.throws(
      () => assertAdminRoutesLeaveMarketingRoot(["donexto.com"]),
      /landing/,
    );
  });
});
