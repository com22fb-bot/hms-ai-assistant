import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { APP_LANGUAGES } from "./i18n/languages.ts";
import {
  icloudFailureText,
  icloudSteps,
  icloudText,
} from "./i18n/icloudConnect.ts";

describe("icloud connect copy", () => {
  it("has the guided steps and privacy note in every UI language", () => {
    for (const language of APP_LANGUAGES) {
      const steps = icloudSteps(language);
      assert.equal(steps.length, 4);
      assert.ok(steps.every((step) => step.trim().length > 20));
      assert.match(icloudText(language, "privacy"), /Apple|apple/i);
      assert.match(icloudText(language, "step2"), /account\.apple\.com/);
      assert.notEqual(icloudText(language, "title"), "");
    }
  });

  it("maps IMAP failure codes without leaking a password", () => {
    const text = icloudFailureText("es", "wrong_password", "secreto-abcd");
    assert.match(text, /contraseña de app/i);
    assert.equal(text.includes("secreto-abcd"), false);
    assert.equal(
      icloudFailureText("en", "unknown_code", "Try again."),
      "Try again.",
    );
  });
});
