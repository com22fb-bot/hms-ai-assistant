import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  donextoBootstrapAction,
  isDonextoVerified,
  sessionNeedsDonextoEmailConfirm,
} from "./oauthIdentity.ts";

const returningOAuth = {
  email: "hmcelinfo@gmail.com",
  identities: [{ provider: "google" }],
  user_metadata: { signup_via: "google_oauth" },
  app_metadata: {
    provider: "google",
    donexto_verified: true,
    donexto_verification_source: "email",
  },
};

describe("returning OAuth user with trusted app_metadata", () => {
  it("does not need ConfirmEmailGate and does not auto-send", () => {
    assert.equal(isDonextoVerified(returningOAuth), true);
    assert.equal(
      sessionNeedsDonextoEmailConfirm({ user: returningOAuth }),
      false,
    );
    assert.equal(
      donextoBootstrapAction({
        user: returningOAuth,
        hasVerifyProof: false,
      }),
      "skip",
    );
  });

  it("does not auto-send when only the refreshed server user is trusted", () => {
    const staleSession = {
      email: "hmcelinfo@gmail.com",
      identities: [{ provider: "google" }],
      app_metadata: { provider: "google" },
      user_metadata: { donexto_verified: true },
    };
    assert.equal(
      donextoBootstrapAction({
        user: staleSession,
        hasVerifyProof: false,
        refreshedUser: returningOAuth,
      }),
      "skip",
    );
    assert.equal(sessionNeedsDonextoEmailConfirm({ user: returningOAuth }), false);
  });
});

describe("brand-new OAuth still verifies once", () => {
  const freshOAuth = {
    email: "nuevo@gmail.com",
    identities: [{ provider: "google" }],
    app_metadata: { provider: "google", donexto_verified: true },
    user_metadata: {},
  };

  it("does not trust OAuth or a legacy flag without the email source", () => {
    assert.equal(isDonextoVerified(freshOAuth), false);
    assert.equal(sessionNeedsDonextoEmailConfirm({ user: freshOAuth }), true);
    assert.equal(
      donextoBootstrapAction({ user: freshOAuth, hasVerifyProof: false }),
      "send",
    );
  });

  it("does not trust client-writable user_metadata in the live check", () => {
    const migratedOnlyInUserMetadata = {
      ...freshOAuth,
      app_metadata: { provider: "google" },
      user_metadata: { donexto_verified: true },
    };
    assert.equal(isDonextoVerified(migratedOnlyInUserMetadata), false);
    assert.equal(
      donextoBootstrapAction({
        user: migratedOnlyInUserMetadata,
        hasVerifyProof: false,
      }),
      "send",
    );
  });

  it("redeems a cold Verificar click instead of sending another mail", () => {
    assert.equal(
      donextoBootstrapAction({ user: freshOAuth, hasVerifyProof: true }),
      "redeem",
    );
  });
});
