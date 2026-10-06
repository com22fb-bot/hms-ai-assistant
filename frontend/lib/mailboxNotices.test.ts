import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { APP_LANGUAGES } from "./i18n/languages.ts";
import {
  gmailSetupText,
  gmailSteps,
  mailboxNoticeText,
  missingGoogleEnvNames,
  yahooFailureText,
  yahooSteps,
} from "./i18n/mailboxNotices.ts";
import { gateNextAfterResolve, isComingSoonGate } from "./loginGate.ts";

describe("mailbox notices", () => {
  it("shows the Yahoo app-password notice and steps in every language", () => {
    for (const language of APP_LANGUAGES) {
      const steps = yahooSteps(language);
      assert.equal(steps.length, 4);
      assert.match(mailboxNoticeText(language, "yahooIntro"), /Yahoo/i);
      assert.match(mailboxNoticeText(language, "yahooPrivacy"), /Apple|Yahoo|lecture|lectura|leitura|sola|seule|somente/i);
    }
    assert.match(mailboxNoticeText("es", "yahooIntro"), /contraseña de app/);
    assert.match(mailboxNoticeText("es", "yahooIntro"), /autorización oficial/);
    assert.match(mailboxNoticeText("es", "yahooOpenSecurity"), /Abrir Yahoo/);
    assert.match(mailboxNoticeText("en", "yahooOpenSecurity"), /Open Yahoo/);
    assert.match(mailboxNoticeText("es", "yahooOpenHint"), /Conexiones externas/);
    assert.match(mailboxNoticeText("en", "yahooOpenHint"), /External connections/);
    assert.match(mailboxNoticeText("es", "yahooStep2"), /Conexiones externas/);
    for (const language of APP_LANGUAGES) {
      assert.match(mailboxNoticeText(language, "yahooOpenSecurity"), /Yahoo/i);
      assert.ok(mailboxNoticeText(language, "yahooOpenHint").length > 20);
    }
  });

  it("exports the Yahoo Account Security URL", async () => {
    const { YAHOO_SECURITY_URL } = await import("./i18n/mailboxNotices.ts");
    assert.equal(YAHOO_SECURITY_URL, "https://login.yahoo.com/account/security");
  });

  it("shows the Gmail unverified-app steps before any redirect", () => {
    assert.equal(
      gateNextAfterResolve("login", false, "google_oauth", "gmail"),
      "gmail_notice",
    );
    assert.equal(isComingSoonGate("gmail_notice"), false);
    assert.equal(
      gateNextAfterResolve("login", false, "yahoo_imap", "yahoo"),
      "yahoo_connect",
    );
    for (const language of APP_LANGUAGES) {
      const steps = gmailSteps(language);
      assert.equal(steps.length, 4);
      assert.match(steps.join(" "), /myaccount\.google\.com\/permissions/);
      assert.match(mailboxNoticeText(language, "gmailEarly"), /100/);
    }
    assert.match(gmailSteps("es").join(" "), /Avanzado/);
    assert.match(gmailSteps("en").join(" "), /Advanced/);
  });

  it("lists missing Google env names and does not invent a secret", () => {
    const text = gmailSetupText("es", missingGoogleEnvNames({}));
    assert.match(text, /GOOGLE_CLIENT_ID/);
    assert.match(text, /GOOGLE_CLIENT_SECRET/);
    assert.match(text, /GOOGLE_REDIRECT_URI/);
    assert.match(text, /gmail\.readonly/);
    assert.doesNotMatch(text, /GOCSPX-/);
    const failure = yahooFailureText("es", "wrong_password", "abcd-efgh-ijkl-mnop");
    assert.doesNotMatch(failure, /abcd-efgh-ijkl-mnop/);
  });
});
