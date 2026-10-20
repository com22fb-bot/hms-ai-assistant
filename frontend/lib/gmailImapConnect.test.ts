import assert from "node:assert/strict";
import test from "node:test";

import { APP_LANGUAGES } from "./i18n/languages.ts";
import {
  GOOGLE_APP_PASSWORDS_URL,
  gmailImapFailureText,
  gmailImapText,
} from "./i18n/gmailImapConnect.ts";

test("app passwords link is the Google page", () => {
  assert.equal(GOOGLE_APP_PASSWORDS_URL, "https://myaccount.google.com/apppasswords");
});

test("every language has the guided steps", () => {
  for (const language of APP_LANGUAGES) {
    for (const key of ["title", "step1Title", "step2Title", "step3Title", "submit", "useOauth"] as const) {
      assert.ok(gmailImapText(language, key).length > 0, `${language}.${key}`);
    }
  }
  assert.notEqual(gmailImapText("en", "title"), gmailImapText("es", "title"));
});

test("Spanish uses Click, never clic", () => {
  const keys = ["step1Body", "step2Body"] as const;
  for (const key of keys) {
    const text = gmailImapText("es", key);
    assert.match(text, /Click/);
    assert.doesNotMatch(text, /\bclic\b/i);
  }
});

test("unknown codes never show raw backend text", () => {
  assert.equal(gmailImapFailureText("es", "something_raw"), gmailImapText("es", "imap_failed"));
  assert.equal(gmailImapFailureText("en", "wrong_password"), gmailImapText("en", "wrong_password"));
});

test("new error codes are translated in every language", () => {
  for (const language of APP_LANGUAGES) {
    for (const code of ["web_login_required", "invalid_characters", "wrong_password"]) {
      assert.equal(gmailImapFailureText(language, code), gmailImapText(language, code as "wrong_password"));
      assert.notEqual(gmailImapFailureText(language, code), gmailImapText(language, "imap_failed"));
    }
  }
});
