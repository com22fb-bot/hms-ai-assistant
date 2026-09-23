import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  chooseVerificationLanguage,
  languageForDonextoVerifyEmail,
} from "./languages.ts";

describe("chooseVerificationLanguage", () => {
  it("keeps a Spanish login when account metadata and the browser are English", () => {
    assert.equal(
      chooseVerificationLanguage({
        ui: "es",
        stored: "es",
        remembered: "es",
        metadata: "en",
        browser: "en-US",
      }),
      "es",
    );
    assert.equal(
      chooseVerificationLanguage({
        ui: "es",
        metadata: "en",
        browser: "en",
      }),
      "es",
    );
    assert.equal(
      chooseVerificationLanguage({
        stored: "es-MX",
        metadata: "en",
        browser: "en-US",
      }),
      "es",
    );
  });

  it("does not default to English when the login screen has no explicit language", () => {
    assert.equal(
      chooseVerificationLanguage({
        metadata: "en",
        browser: "en-US",
      }),
      "es",
    );
    assert.equal(chooseVerificationLanguage({}), "es");
    assert.equal(languageForDonextoVerifyEmail(), "es");
  });

  it("sends English only when the login UI is English", () => {
    assert.equal(
      chooseVerificationLanguage({
        ui: "en",
        stored: "en",
        metadata: "es",
        browser: "es-MX",
      }),
      "en",
    );
    assert.equal(
      chooseVerificationLanguage({
        remembered: "fr",
        metadata: "en",
        browser: "en",
      }),
      "fr",
    );
  });
});
