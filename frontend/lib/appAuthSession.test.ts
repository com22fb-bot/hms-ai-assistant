import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  authEventMayCarrySession,
  readLogoutQueryFlag,
  shouldDeferAuthStateChange,
  stripLogoutQueryParam,
} from "./appAuthSession.ts";

describe("authEventMayCarrySession", () => {
  it("includes session-bearing Supabase events", () => {
    assert.equal(authEventMayCarrySession("INITIAL_SESSION"), true);
    assert.equal(authEventMayCarrySession("SIGNED_IN"), true);
    assert.equal(authEventMayCarrySession("TOKEN_REFRESHED"), true);
    assert.equal(authEventMayCarrySession("SIGNED_OUT"), false);
  });
});

describe("shouldDeferAuthStateChange", () => {
  it("defers until bootstrap completes except password recovery", () => {
    assert.equal(shouldDeferAuthStateChange("INITIAL_SESSION", false), true);
    assert.equal(shouldDeferAuthStateChange("PASSWORD_RECOVERY", false), false);
    assert.equal(shouldDeferAuthStateChange("INITIAL_SESSION", true), false);
  });
});

describe("logout query helpers", () => {
  it("reads and strips logout=1", () => {
    assert.equal(readLogoutQueryFlag("?logout=1&foo=bar"), true);
    assert.equal(stripLogoutQueryParam("/", "?logout=1"), "/");
    assert.equal(stripLogoutQueryParam("/", "?logout=1&x=1"), "/?x=1");
  });
});
