import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { describe, it } from "node:test";
import { fileURLToPath } from "node:url";

import {
  accountExistsFromResolveNext,
  comingSoonProviderLabel,
  gateNextAfterResolve,
  isComingSoonGate,
  oauthFromResolveNext,
} from "./loginGate.ts";
import { userHasOAuthIdentity } from "./oauthIdentity.ts";
import { isKnownActiveMailbox, resolveMailboxProviderFromEmail } from "./mailboxSignup.ts";

describe("accountExistsFromResolveNext", () => {
  it("detects existing accounts from oauth next values", () => {
    assert.equal(accountExistsFromResolveNext("yahoo_oauth"), true);
    assert.equal(accountExistsFromResolveNext("signup"), false);
    assert.equal(accountExistsFromResolveNext("coming_soon_gmail"), false);
  });
});

describe("gateNextAfterResolve", () => {
  it("names Hotmail as live Microsoft and sends existing testers to identity login", () => {
    assert.equal(
      gateNextAfterResolve("login", true, "azure_oauth", "hotmail"),
      "provider_login",
    );
    assert.equal(
      gateNextAfterResolve("login", true, "yahoo_oauth", "yahoo"),
      "provider_login",
    );
    assert.equal(
      gateNextAfterResolve("login", true, "google_oauth", "gmail"),
      "provider_login",
    );
  });

  it("asks first-time Outlook/Hotmail/M365 to confirm before Microsoft OAuth", () => {
    assert.equal(
      gateNextAfterResolve("signup", false, "signup", "hotmail"),
      "confirm_first_time",
    );
    assert.equal(
      gateNextAfterResolve("login", false, "azure_oauth", "hotmail"),
      "confirm_first_time",
    );
  });

  it("does not send first-time Gmail or Yahoo to OAuth — waitlist instead", () => {
    assert.equal(
      gateNextAfterResolve("login", false, "coming_soon_gmail", "gmail"),
      "coming_soon_gmail",
    );
    assert.equal(
      gateNextAfterResolve("login", false, "pending_review", "gmail"),
      "coming_soon_gmail",
    );
    assert.equal(
      gateNextAfterResolve("signup", false, "coming_soon_yahoo", "yahoo"),
      "coming_soon_yahoo",
    );
    assert.equal(isComingSoonGate("coming_soon_gmail"), true);
  });

  it("keeps existing Gmail/Yahoo testers on identity login even if coming soon", () => {
    assert.equal(
      gateNextAfterResolve("login", true, "coming_soon_gmail", "gmail"),
      "provider_login",
    );
    assert.equal(
      gateNextAfterResolve("login", true, "coming_soon_yahoo", "yahoo"),
      "provider_login",
    );
  });

  it("blocks iCloud OAuth and offers waitlist", () => {
    assert.equal(
      gateNextAfterResolve("login", false, "coming_soon_icloud", "apple"),
      "coming_soon_icloud",
    );
    assert.equal(comingSoonProviderLabel("coming_soon_icloud", "apple"), "iCloud");
  });

  it("does not pretend a random @empresa.com mailbox can be IMAP-read", () => {
    assert.equal(
      gateNextAfterResolve("login", false, "unsupported_imap_domain", "other"),
      "unsupported_imap_domain",
    );
    assert.equal(
      gateNextAfterResolve("login", false, "unsupported", "other"),
      "unsupported_imap_domain",
    );
    assert.equal(
      gateNextAfterResolve("login", false, "waitlist", "other"),
      "waitlist",
    );
  });

  it("keeps unknown and typo domains on the email field", () => {
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
    assert.equal(oauthFromResolveNext("coming_soon_gmail"), null);
    assert.equal(oauthFromResolveNext("signup"), null);
  });
});

describe("honest mailbox availability", () => {
  it("treats Hotmail/Outlook/Live/MSN/M365 as readable now", () => {
    assert.equal(resolveMailboxProviderFromEmail("donexto@hotmail.com"), "hotmail");
    assert.equal(resolveMailboxProviderFromEmail("ana@outlook.com"), "hotmail");
    assert.equal(resolveMailboxProviderFromEmail("ana@live.com"), "hotmail");
    assert.equal(resolveMailboxProviderFromEmail("ana@msn.com"), "hotmail");
    assert.equal(
      resolveMailboxProviderFromEmail("ana@contoso.onmicrosoft.com"),
      "hotmail",
    );
    assert.equal(isKnownActiveMailbox("donexto@hotmail.com"), true);
  });

  it("does not treat Gmail, Yahoo, iCloud or random empresa as live read", () => {
    assert.equal(isKnownActiveMailbox("hmcelinfo@gmail.com"), false);
    assert.equal(isKnownActiveMailbox("hsalcidor@yahoo.com"), false);
    assert.equal(isKnownActiveMailbox("ana@icloud.com"), false);
    assert.equal(isKnownActiveMailbox("ana@empresa.mx"), false);
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

describe("login CSS breakpoints", () => {
  it("declares 360 / 768 / 1024 / 1440 media queries", () => {
    const cssPath = join(
      dirname(fileURLToPath(import.meta.url)),
      "..",
      "components",
      "auth",
      "hms-gate.css",
    );
    const css = readFileSync(cssPath, "utf8");
    for (const width of ["360px", "768px", "1024px", "1440px"]) {
      assert.match(css, new RegExp(`@media \\(min-width: ${width}\\)`));
    }
  });
});
