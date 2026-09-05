import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  authEventMayCarrySession,
  readLogoutQueryFlag,
  shouldDeferAuthStateChange,
  stripLogoutQueryParam,
} from "./appAuthSession.ts";

describe("shouldDeferAuthStateChange", () => {
  it("blocks INITIAL_SESSION until bootstrap completes", () => {
    assert.equal(shouldDeferAuthStateChange("INITIAL_SESSION", false), true);
    assert.equal(shouldDeferAuthStateChange("SIGNED_IN", false), true);
    assert.equal(shouldDeferAuthStateChange("TOKEN_REFRESHED", false), true);
  });

  it("allows PASSWORD_RECOVERY during bootstrap", () => {
    assert.equal(shouldDeferAuthStateChange("PASSWORD_RECOVERY", false), false);
  });

  it("accepts all events after bootstrap", () => {
    assert.equal(shouldDeferAuthStateChange("INITIAL_SESSION", true), false);
    assert.equal(shouldDeferAuthStateChange("SIGNED_IN", true), false);
  });
});

describe("authEventMayCarrySession", () => {
  it("lists session-bearing Supabase auth events", () => {
    assert.equal(authEventMayCarrySession("INITIAL_SESSION"), true);
    assert.equal(authEventMayCarrySession("SIGNED_IN"), true);
    assert.equal(authEventMayCarrySession("TOKEN_REFRESHED"), true);
    assert.equal(authEventMayCarrySession("USER_UPDATED"), true);
    assert.equal(authEventMayCarrySession("SIGNED_OUT"), false);
    assert.equal(authEventMayCarrySession("PASSWORD_RECOVERY"), false);
  });
});

describe("logout query helpers", () => {
  it("detects ?logout=1 and strips it from the URL", () => {
    assert.equal(readLogoutQueryFlag("?logout=1&foo=bar"), true);
    assert.equal(readLogoutQueryFlag("?foo=bar"), false);
    assert.equal(stripLogoutQueryParam("/", "?logout=1"), "/");
    assert.equal(stripLogoutQueryParam("/app", "?logout=1&x=1"), "/app?x=1");
  });
});
