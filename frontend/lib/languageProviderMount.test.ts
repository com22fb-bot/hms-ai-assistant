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
