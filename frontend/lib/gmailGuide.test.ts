import assert from "node:assert/strict";
import test from "node:test";

import { APP_LANGUAGES } from "./i18n/languages.ts";
import { GMAIL_GUIDE_STEPS, gmailGuideText, nextGuideStep } from "./i18n/gmailGuide.ts";

test("six steps, translated in every language", () => {
  assert.equal(GMAIL_GUIDE_STEPS.length, 6);
  for (const language of APP_LANGUAGES) {
    for (const key of [...GMAIL_GUIDE_STEPS, "title", "sameAccount", "mCreate", "mConnect"] as const) {
      assert.ok(gmailGuideText(language, key).length > 0, `${language}.${key}`);
    }
  }
  assert.notEqual(gmailGuideText("en", "s4"), gmailGuideText("es", "s4"));
});

test("Spanish says Click, never clic", () => {
  for (const key of GMAIL_GUIDE_STEPS) {
    assert.doesNotMatch(gmailGuideText("es", key), /\bclic\b/i);
  }
  assert.match(gmailGuideText("es", "s4"), /Click en Crear/);
  assert.match(gmailGuideText("es", "s6"), /Click en Conectar Gmail/);
});

test("steps wrap around both ways", () => {
  assert.equal(nextGuideStep(5, 1), 0);
  assert.equal(nextGuideStep(0, -1), 5);
  assert.equal(gmailGuideText("es", "stepOf", { n: 2, total: 6 }), "Paso 2 de 6");
});
