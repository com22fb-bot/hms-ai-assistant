import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  gateNextAfterResolve,
  oauthFromResolveNext,
} from "./loginGate.ts";
import { userHasOAuthIdentity } from "./oauthIdentity.ts";

describe("gateNextAfterResolve", () => {
  it("sends existing Yahoo/Outlook/Gmail straight to the provider", () => {
    assert.equal(
      gateNextAfterResolve("login", true, "yahoo_oauth", "yahoo"),
      "provider_login",
    );
    assert.equal(
      gateNextAfterResolve("login", true, "azure_oauth", "hotmail"),
      "provider_login",
    );
    assert.equal(
      gateNextAfterResolve("login", true, "google_oauth", "gmail"),
      "provider_login",
    );
  });

  it("asks first-time Yahoo/Outlook to confirm before creating anything", () => {
    assert.equal(
      gateNextAfterResolve("login", false, "signup", "yahoo"),
      "confirm_first_time",
    );
    assert.equal(
      gateNextAfterResolve("signup", false, "signup", "hotmail"),
      "confirm_first_time",
    );
  });

  it("does not send new Gmail users to Google", () => {
    assert.equal(
      gateNextAfterResolve("login", false, "pending_review", "gmail"),
      "pending_review",
    );
    assert.equal(
      gateNextAfterResolve("signup", false, "pending_review", "gmail"),
      "pending_review",
    );
  });

  it("blocks iCloud even if Auth already has that email", () => {
    assert.equal(
      gateNextAfterResolve("login", true, "apple_oauth", "apple"),
      "icloud_unavailable",
    );
    assert.equal(
      gateNextAfterResolve("login", false, "pending_review", "apple"),
      "icloud_unavailable",
    );
  });

  it("keeps unknown and typo domains on the email field", () => {
    assert.equal(
      gateNextAfterResolve("login", false, "unsupported", "other"),
      "unsupported",
    );
    assert.equal(
      gateNextAfterResolve("login", false, "fix_domain", "other"),
      "fix_domain",
    );
  });
});

describe("oauthFromResolveNext", () => {
  it("maps backend next values to the live identity providers", () => {
    assert.equal(oauthFromResolveNext("yahoo_oauth"), "yahoo");
    assert.equal(oauthFromResolveNext("google_oauth"), "google");
    assert.equal(oauthFromResolveNext("azure_oauth"), "azure");
    assert.equal(oauthFromResolveNext("apple_oauth"), "apple");
    assert.equal(oauthFromResolveNext("signup"), null);
  });
});

describe("userHasOAuthIdentity", () => {
  it("treats Yahoo/Microsoft signup_via as proven identity", () => {
    assert.equal(
      userHasOAuthIdentity({
        user_metadata: { signup_via: "yahoo_oauth" },
      }),
      true,
    );
    assert.equal(
      userHasOAuthIdentity({
        user_metadata: { signup_via: "microsoft_oauth" },
      }),
      true,
    );
  });

  it("treats a non-email Supabase identity as proven", () => {
    assert.equal(
      userHasOAuthIdentity({
        identities: [{ provider: "google" }],
      }),
      true,
    );
    assert.equal(
      userHasOAuthIdentity({
        identities: [{ provider: "email" }],
        app_metadata: { providers: ["email"] },
      }),
      false,
    );
  });
});
