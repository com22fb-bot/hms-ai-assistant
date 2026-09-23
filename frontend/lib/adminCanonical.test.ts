import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  appHostAdminRedirects,
  authReturnUrl,
  canonicalAdminRedirectTarget,
  verifyEmailRedirectUrl,
} from "./adminCanonical.ts";

const app = {
  origin: "https://app.donexto.com",
  hostname: "app.donexto.com",
};

const www = {
  origin: "https://www.donexto.com",
  hostname: "www.donexto.com",
};

const apex = {
  origin: "https://donexto.com",
  hostname: "donexto.com",
};

describe("canonical admin redirect", () => {
  it("sends only the product host /admin to www", () => {
    assert.equal(
      canonicalAdminRedirectTarget("app.donexto.com", "/admin", ""),
      "https://www.donexto.com/admin",
    );
    assert.equal(
      canonicalAdminRedirectTarget("APP.DONEXTO.COM:443", "/admin/", "?x=1"),
      "https://www.donexto.com/admin/?x=1",
    );
    assert.equal(
      canonicalAdminRedirectTarget("www.donexto.com", "/admin", ""),
      null,
    );
    assert.equal(
      canonicalAdminRedirectTarget("donexto.com", "/admin", ""),
      null,
    );
    assert.equal(
      canonicalAdminRedirectTarget("app.donexto.com", "/", ""),
      null,
    );
    assert.equal(
      canonicalAdminRedirectTarget("app.donexto.com", "/api/hms/health", ""),
      null,
    );
  });

  it("declares permanent host-scoped redirects", () => {
    const rules = appHostAdminRedirects();
    assert.equal(rules.length, 2);
    for (const rule of rules) {
      assert.equal(rule.permanent, true);
      assert.equal(rule.has[0]?.value, "app.donexto.com");
      assert.ok(rule.destination.startsWith("https://www.donexto.com/admin"));
    }
  });
});

describe("auth return urls", () => {
  it("keeps product login on the app origin", () => {
    assert.equal(
      authReturnUrl({ ...app, pathname: "/" }),
      "https://app.donexto.com/",
    );
    assert.equal(
      verifyEmailRedirectUrl({ ...app, pathname: "/" }),
      "https://app.donexto.com/?donexto_verify=1",
    );
  });

  it("returns admin OAuth to the host that showed the panel", () => {
    assert.equal(
      authReturnUrl({ ...app, pathname: "/admin" }),
      "https://www.donexto.com/admin",
    );
    assert.equal(
      authReturnUrl({ ...www, pathname: "/admin" }),
      "https://www.donexto.com/admin",
    );
    assert.equal(
      authReturnUrl({ ...apex, pathname: "/admin/" }),
      "https://donexto.com/admin",
    );
    assert.equal(
      verifyEmailRedirectUrl({ ...www, pathname: "/admin" }),
      "https://www.donexto.com/admin?donexto_verify=1",
    );
  });
});
