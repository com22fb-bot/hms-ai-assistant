import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { translate } from "./i18n/messages.ts";
import {
  confirmDonextoPath,
  consumeVerifyLinkError,
  acknowledgeVerifyLinkError,
  forgetDonextoVerifyProof,
  interpretConfirmDonextoResponse,
  loadDonextoVerifyProof,
  readDonextoVerifyProof,
  rememberDonextoVerifyProof,
  rememberVerifyLinkError,
  stripDonextoVerifySearch,
  verifyUiErrorCode,
  donextoVerifyFailure,
} from "./donextoVerifyLink.ts";

function memoryStore() {
  const data = new Map<string, string>();
  return {
    getItem(key: string) {
      return data.has(key) ? data.get(key)! : null;
    },
    setItem(key: string, value: string) {
      data.set(key, value);
    },
    removeItem(key: string) {
      data.delete(key);
    },
  };
}

const EMAIL_LINK =
  "https://app.donexto.com/?donexto_verify=1&token_hash=hash-from-outlook&type=magiclink";

describe("cold Donexto verify link", () => {
  it("reads the Outlook Verificar URL without a session", () => {
    const proof = readDonextoVerifyProof(new URL(EMAIL_LINK).search);
    assert.deepEqual(proof, {
      tokenHash: "hash-from-outlook",
      tokenType: "magiclink",
    });
    assert.equal(
      confirmDonextoPath(proof!),
      "/identity/confirm-donexto?donexto_verify=1&token_hash=hash-from-outlook&type=magiclink",
    );
  });

  it("ignores a hand-crafted flag that has no token", () => {
    assert.equal(readDonextoVerifyProof("?donexto_verify=1"), null);
    assert.equal(readDonextoVerifyProof("?token_hash=orphan"), null);
  });

  it("keeps the proof for the Ya abrí button after the URL is gone", () => {
    const store = memoryStore();
    const proof = readDonextoVerifyProof(new URL(EMAIL_LINK).search)!;
    rememberDonextoVerifyProof(store, proof);
    assert.deepEqual(loadDonextoVerifyProof(store), proof);
    forgetDonextoVerifyProof(store);
    assert.equal(loadDonextoVerifyProof(store), null);
  });

  it("turns a successful confirm into session tokens", () => {
    assert.deepEqual(
      interpretConfirmDonextoResponse(200, {
        status: "ok",
        donexto_verified: true,
        access_token: "access",
        refresh_token: "refresh",
      }),
      { kind: "session", accessToken: "access", refreshToken: "refresh" },
    );
  });

  it("treats reused and expired links as a clear failure", () => {
    assert.deepEqual(
      interpretConfirmDonextoResponse(403, {
        detail: { status: "invalid_verification_token" },
      }),
      { kind: "invalid" },
    );
    assert.equal(verifyUiErrorCode(donextoVerifyFailure("invalid")), "invalid");
    assert.equal(verifyUiErrorCode(new Error("network")), "unverified");
  });

  it("strips the token from the address bar and keeps unrelated params", () => {
    assert.equal(
      stripDonextoVerifySearch(
        "https://app.donexto.com/?lang=es&donexto_verify=1&token_hash=abc&type=magiclink",
      ),
      "/?lang=es",
    );
  });

  it("tells every login language that the gate button is not the confirmation", () => {
    const buttonNotConfirmation = /confirmé|confermato|confirmei|i confirmed|ya confirm/i;
    for (const language of ["es", "en", "fr", "it", "pt"] as const) {
      assert.equal(
        buttonNotConfirmation.test(translate(language, "confirmGateRefresh")),
        false,
        language,
      );
      assert.match(translate(language, "confirmGateHelper"), /Verificar|Verify|Vérifier|Verifica/i);
      assert.match(
        translate(language, "confirmGateRefreshError"),
        /no confirma|does not confirm|ne confirme pas|non conferma|não confirma/i,
      );
    }
  });

  it("keeps a failed link visible for the screen that opens", () => {
    const store = memoryStore();
    rememberVerifyLinkError(store, "invalid");
    assert.equal(consumeVerifyLinkError(store), "invalid");
    assert.equal(consumeVerifyLinkError(store), "invalid");
    acknowledgeVerifyLinkError();
    assert.equal(consumeVerifyLinkError(store), null);
  });
});
