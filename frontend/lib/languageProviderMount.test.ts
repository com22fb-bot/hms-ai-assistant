import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { describe, it } from "node:test";
import { fileURLToPath } from "node:url";

const frontendRoot = join(dirname(fileURLToPath(import.meta.url)), "..");

function source(relativePath: string): string {
  return readFileSync(join(frontendRoot, relativePath), "utf8");
}

describe("LanguageProvider mount", () => {
  it("wraps every route from the root layout", () => {
    const layout = source("app/layout.tsx");
    assert.match(
      layout,
      /import \{ LanguageProvider \} from "@\/lib\/i18n\/LanguageProvider"/,
    );
    assert.match(
      layout,
      /<LanguageProvider>\s*\{children\}\s*<\/LanguageProvider>/,
    );
  });

  it("keeps the home provider so a signed-in user id still syncs language", () => {
    const home = source("app/page.tsx");
    assert.match(home, /<LanguageProvider userId=\{session\?\.id \?\? null\}>/);
    assert.match(home, /<\/LanguageProvider>/);
  });

  it("documents that /admin renders LoginScreen, which requires useLanguage", () => {
    const admin = source("app/admin/page.tsx");
    const login = source("components/auth/LoginScreen.tsx");
    assert.match(admin, /<LoginScreen/);
    assert.match(login, /useLanguage\(/);
    assert.match(
      source("lib/i18n/LanguageProvider.tsx"),
      /useLanguage must be used within LanguageProvider/,
    );
  });
});

describe("admin is Spanish-only", () => {
  it("locks /admin to Spanish without writing the stored language", () => {
    const admin = source("app/admin/page.tsx");
    const provider = source("lib/i18n/LanguageProvider.tsx");
    assert.match(admin, /<LanguageProvider lockedLanguage="es">/);
    assert.match(provider, /const language = lockedLanguage \?\? storedLanguage/);
    assert.match(provider, /if \(lockedLanguage\) \{\s*return;\s*\}/);
    assert.doesNotMatch(provider, /lockedLanguage[\s\S]{0,80}rememberLoginLanguage/);
  });

  it("hides the language switcher when the language is locked", () => {
    const strip = source("components/UserSettingsPanel.tsx");
    const lockedReturn = strip.indexOf("if (languageLocked)");
    const compactSelect = strip.indexOf("dx-lang-strip--compact");
    assert.ok(lockedReturn >= 0);
    assert.ok(compactSelect > lockedReturn);
    assert.match(strip, /if \(languageLocked\) \{\s*return null;\s*\}/);
  });

  it("does not let /admin overwrite the home login language", () => {
    const login = source("components/auth/LoginScreen.tsx");
    assert.match(login, /if \(!languageLocked\) \{\s*rememberLoginLanguage\(language\);\s*\}/);
  });

  it("keeps the multi-language strip on the home login", () => {
    const home = source("app/page.tsx");
    const login = source("components/auth/LoginScreen.tsx");
    assert.doesNotMatch(home, /lockedLanguage/);
    assert.match(home, /<LanguageStrip/);
    assert.match(login, /<LanguageStrip compact className="dx-login__language" \/>/);
    assert.match(home, /<LanguageProvider userId=\{session\?\.id \?\? null\}>/);
  });
});
