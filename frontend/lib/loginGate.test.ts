import assert from "node:assert/strict";
import { describe, it } from "node:test";

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
      "yahoo_connect",
    );
    assert.equal(
      gateNextAfterResolve("login", true, "google_oauth", "gmail"),
      "gmail_notice",
    );
  });

  it("asks first-time Outlook/Hotmail/M365 to confirm before Microsoft OAuth", () => {
    assert.equal(
      gateNextAfterResolve("signup", false, "signup", "hotmail"),
      "confirm_first_time",
    );
    assert.equal(
      gateNextAfterResolve("login", false, "signup", "hotmail"),
      "confirm_first_time",
    );
  });

  it("sends first-time Gmail to the unverified notice and Yahoo to the app password", () => {
    assert.equal(
      gateNextAfterResolve("login", false, "coming_soon_gmail", "gmail"),
      "gmail_notice",
    );
    assert.equal(
      gateNextAfterResolve("login", false, "google_oauth", "gmail"),
      "gmail_notice",
    );
    assert.equal(
      gateNextAfterResolve("signup", false, "coming_soon_yahoo", "yahoo"),
      "yahoo_connect",
    );
    assert.equal(isComingSoonGate("gmail_notice"), false);
    assert.equal(isComingSoonGate("yahoo_connect"), false);
    assert.equal(isComingSoonGate("coming_soon_gmail"), true);
  });

  it("keeps existing Gmail and Yahoo on their connect notices", () => {
    assert.equal(
      gateNextAfterResolve("login", true, "coming_soon_gmail", "gmail"),
      "gmail_notice",
    );
    assert.equal(
      gateNextAfterResolve("login", true, "coming_soon_yahoo", "yahoo"),
      "yahoo_connect",
    );
  });

  it("sends iCloud to the app-password connect form", () => {
    assert.equal(
      gateNextAfterResolve("login", false, "icloud_imap", "apple"),
      "icloud_connect",
    );
    assert.equal(
      gateNextAfterResolve("login", false, "coming_soon_icloud", "apple"),
      "icloud_connect",
    );
    assert.equal(isComingSoonGate("icloud_connect"), false);
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

  it("treats Gmail, Yahoo, and iCloud as readable mailboxes", () => {
    assert.equal(isKnownActiveMailbox("ana@icloud.com"), true);
    assert.equal(isKnownActiveMailbox("ana@me.com"), true);
    assert.equal(isKnownActiveMailbox("hmcelinfo@gmail.com"), true);
    assert.equal(isKnownActiveMailbox("hsalcidor@yahoo.com"), true);
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
