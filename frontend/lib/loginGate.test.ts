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
  const cssPath = join(
    dirname(fileURLToPath(import.meta.url)),
    "..",
    "components",
    "auth",
    "hms-gate.css",
  );

  it("declares 768 / 1024 / 1440 media queries", () => {
    const css = readFileSync(cssPath, "utf8");
    for (const width of ["768px", "1024px", "1440px"]) {
      assert.match(css, new RegExp(`@media \\(min-width: ${width}\\)`));
    }
  });

  it("right-aligns the compact gate language strip", () => {
    const css = readFileSync(cssPath, "utf8");
    assert.match(css, /\.dx-lang-strip-host--gate\s*\{[^}]*justify-content:\s*flex-end/);
    assert.match(css, /\.dx-lang-strip--gate\.dx-lang-strip--compact\s*\{[^}]*justify-content:\s*flex-end/);
  });

  it("splits the studio login left/right on laptop without a stacked half-hero", () => {
    const css = readFileSync(cssPath, "utf8");
    assert.match(
      css,
      /@media \(min-width: 768px\)[\s\S]*?\.dx-auth:has\(> \.dx-auth__hero--studio\)\s*\{[\s\S]*?flex-direction:\s*row/,
    );
    assert.match(
      css,
      /@media \(min-width: 1024px\)[\s\S]*?\.dx-auth:has\(> \.dx-auth__hero--studio\)\s*\{[\s\S]*?flex-direction:\s*row/,
    );
    assert.match(
      css,
      /@media \(min-width: 768px\)[\s\S]*?\.dx-auth:has\(> \.dx-auth__hero--studio\) \.dx-auth__hero--studio\s*\{[\s\S]*?flex:\s*0 0 48%/,
    );
    assert.match(
      css,
      /@media \(min-width: 768px\)[\s\S]*?\.dx-auth:has\(> \.dx-auth__hero--studio\) \.dx-auth__panel\s*\{[\s\S]*?flex:\s*1 1 52%/,
    );
    assert.match(
      css,
      /@media \(min-width: 768px\)[\s\S]*?\.dx-auth\s*\{[\s\S]*?overflow:\s*hidden/,
    );
    assert.doesNotMatch(
      css,
      /@media \(min-width: 768px\)[\s\S]*?\.dx-auth:has\(> \.dx-auth__hero--studio\) \.dx-auth__hero--studio\s*\{[\s\S]*?flex:\s*0 0 46dvh/,
    );
    assert.match(
      css,
      /filter:\s*brightness\(1\.04\)\s*contrast\(1\.04\)\s*saturate\(1\.05\)/,
    );
  });

  it("keeps the studio plaque in frame on the left column", () => {
    const css = readFileSync(cssPath, "utf8");
    assert.match(
      css,
      /@media \(min-width: 768px\)[\s\S]*?\.dx-auth__hero--studio \.dx-auth__hero-media img\s*\{[\s\S]*?object-fit:\s*cover/,
    );
    assert.match(
      css,
      /@media \(min-width: 1024px\)[\s\S]*?\.dx-auth__hero--studio \.dx-auth__hero-media img\s*\{[\s\S]*?object-fit:\s*cover/,
    );
    assert.match(
      css,
      /@media \(min-width: 768px\)[\s\S]*?\.dx-auth__hero-media img\s*\{[\s\S]*?object-position:\s*50% 50%/,
    );
    assert.doesNotMatch(
      css,
      /@media \(min-width: 768px\)[\s\S]*?\.dx-auth__hero--studio \.dx-auth__hero-media img\s*\{[\s\S]*?object-fit:\s*contain/,
    );
    assert.doesNotMatch(
      css,
      /@media \(min-width: 768px\) and \(max-height: 800px\)[\s\S]*?object-position:\s*50% 62%/,
    );
  });

  it("shows compact white hero copy at the top of the left studio column", () => {
    const css = readFileSync(cssPath, "utf8");
    const start768 = css.indexOf("@media (min-width: 768px) {");
    assert.ok(start768 >= 0);
    const block768 = css.slice(start768, css.indexOf("@media (min-width: 1024px)", start768));
    assert.match(block768, /flex-direction:\s*row/);
    assert.match(block768, /object-fit:\s*cover/);
    assert.match(
      block768,
      /\.dx-auth__hero--studio \.dx-auth__hero-inner\s*\{[\s\S]*?justify-content:\s*flex-start/,
    );
    assert.match(
      block768,
      /\.dx-auth__hero--studio \.dx-auth__hero-headline,\s*\.dx-auth__hero--studio \.dx-auth__hero-subline\s*\{[\s\S]*?display:\s*block/,
    );
    assert.doesNotMatch(
      block768,
      /\.dx-auth__hero--studio \.dx-auth__hero-headline,\s*\.dx-auth__hero--studio \.dx-auth__hero-subline\s*\{[\s\S]*?display:\s*none/,
    );
    assert.match(
      css,
      /\.dx-auth__hero--studio \.dx-auth__hero-headline,\s*\.dx-auth__hero--studio \.dx-auth__hero-subline\s*\{[\s\S]*?text-shadow:/,
    );
  });

  it("locks the 14-inch login to the viewport without panel scroll", () => {
    const css = readFileSync(cssPath, "utf8");
    const start = css.indexOf("@media (min-width: 768px) and (max-height: 800px)");
    assert.ok(start >= 0);
    const block = css.slice(start, start + 3200);
    assert.match(block, /overflow:\s*hidden/);
    assert.match(block, /flex-direction:\s*row/);
    assert.match(block, /flex:\s*0 0 46%/);
    assert.match(block, /\.dx-auth:has\(> \.dx-auth__hero--studio\) \.dx-auth__panel\s*\{[\s\S]*?overflow:\s*hidden/);
    assert.doesNotMatch(block, /42dvh|46dvh|48dvh/);
  });

  it("keeps the cinematic login hero copy in ES and EN", () => {
    const messagesPath = join(
      dirname(fileURLToPath(import.meta.url)),
      "i18n",
      "loginMessages.ts",
    );
    const source = readFileSync(messagesPath, "utf8");
    assert.match(source, /Tu correo\. Tu siguiente paso\./);
    assert.match(source, /Your email\. Your next step\./);
    assert.match(source, /Correos importantes, tareas y pendientes en un solo lugar\./);
    assert.match(source, /Important mail, tasks, and to-dos in one place\./);
  });

  it("compacts the desktop card so Continuar stays on-screen in the right column", () => {
    const css = readFileSync(cssPath, "utf8");
    assert.match(
      css,
      /@media \(min-width: 1024px\)[\s\S]*?\.dx-auth__availability\s*\{[^}]*margin:\s*0\.35rem 0 0\.45rem/,
    );
    assert.match(
      css,
      /@media \(min-width: 1024px\)[\s\S]*?\.dx-auth__card\s*\{[^}]*padding:\s*0\.95rem 1\.35rem 0\.85rem/,
    );
  });

  it("fills the studio right column with the login card instead of a floating island", () => {
    const css = readFileSync(cssPath, "utf8");
    const start768 = css.indexOf("@media (min-width: 768px) {");
    assert.ok(start768 >= 0);
    const block768 = css.slice(start768, css.indexOf("@media (min-width: 1024px)", start768));
    assert.match(
      block768,
      /\.dx-auth:has\(> \.dx-auth__hero--studio\) \.dx-auth__panel\s*\{[\s\S]*?align-items:\s*stretch/,
    );
    assert.match(
      block768,
      /\.dx-auth:has\(> \.dx-auth__hero--studio\) \.dx-auth__panel\s*\{[\s\S]*?padding:\s*0\.4rem 0\.45rem/,
    );
    assert.match(
      block768,
      /\.dx-auth:has\(> \.dx-auth__hero--studio\) \.dx-auth__card\s*\{[\s\S]*?width:\s*100%/,
    );
    assert.match(
      block768,
      /\.dx-auth:has\(> \.dx-auth__hero--studio\) \.dx-auth__card\s*\{[\s\S]*?flex:\s*1 1 auto/,
    );
    assert.match(
      block768,
      /\.dx-auth:has\(> \.dx-auth__hero--studio\) \.dx-auth__legal-agree\s*\{[\s\S]*?margin-top:\s*auto/,
    );
    assert.doesNotMatch(
      block768,
      /\.dx-auth:has\(> \.dx-auth__hero--studio\) \.dx-auth__card\s*\{[\s\S]*?width:\s*min\(100%, 28rem\)/,
    );

    const start1024 = css.indexOf("@media (min-width: 1024px) {");
    assert.ok(start1024 >= 0);
    const block1024 = css.slice(start1024, css.indexOf("@media (min-width: 1440px)", start1024));
    assert.match(
      block1024,
      /\.dx-auth:has\(> \.dx-auth__hero--studio\) \.dx-auth__panel\s*\{[\s\S]*?align-items:\s*stretch/,
    );
    assert.match(
      block1024,
      /\.dx-auth:has\(> \.dx-auth__hero--studio\) \.dx-auth__card\s*\{[\s\S]*?width:\s*100%/,
    );
    assert.doesNotMatch(
      block1024,
      /\.dx-auth:has\(> \.dx-auth__hero--studio\) \.dx-auth__panel\s*\{[\s\S]*?justify-content:\s*center/,
    );
  });

  it("keeps the compact gate language strip small and right-aligned", () => {
    const css = readFileSync(cssPath, "utf8");
    assert.match(
      css,
      /\.dx-lang-strip--gate\.dx-lang-strip--compact\s*\{[^}]*font-size:\s*0\.65rem/,
    );
    assert.match(
      css,
      /\.dx-lang-strip--gate \.dx-lang-strip__select\s*\{[^}]*font-size:\s*0\.65rem/,
    );
    assert.match(
      css,
      /\.dx-lang-strip--gate \.dx-lang-strip__select\s*\{[^}]*min-height:\s*1\.25rem/,
    );
  });
});

describe("login hero sizes", () => {
  it("loads the full-width banner from the viewport width", () => {
    const loginPath = join(
      dirname(fileURLToPath(import.meta.url)),
      "..",
      "components",
      "auth",
      "LoginScreen.tsx",
    );
    const source = readFileSync(loginPath, "utf8");
    const sizes = source.match(/sizes="[^"]+"/g) ?? [];
    assert.ok(sizes.length >= 2);
    for (const attr of sizes) {
      assert.match(attr, /sizes="\(min-width: 768px\) 50vw, 100vw"/);
    }
    assert.match(source, /dx-auth__hero--studio/);
    assert.match(source, /heroHeadline/);
    assert.match(source, /heroSubline/);
  });
});
