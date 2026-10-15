import assert from "node:assert/strict";
import { test } from "node:test";

import { importCategoryLabel } from "./importWizard.ts";
import { mailCategoryLabel, mailPriorityLabel } from "./mailInbox.ts";

const LANGS = ["es", "en", "fr", "it", "pt"] as const;
const KEYS = ["notice", "review", "action_required", "automated", "promotional", "informational", "critical_action", "case_followup"];

test("import progress cards never show raw backend keys", () => {
  assert.equal(importCategoryLabel("es", "notice"), "Avisos");
  assert.equal(importCategoryLabel("es", "review"), "Por revisar");
  for (const lang of LANGS) {
    for (const key of KEYS) {
      const label = importCategoryLabel(lang, key);
      assert.notEqual(label, key, `${lang}:${key}`);
      assert.ok(label.length > 0);
    }
    assert.equal(importCategoryLabel(lang, "zzz_unknown"), importCategoryLabel(lang, "other"));
    assert.notEqual(importCategoryLabel(lang, "zzz_unknown"), "zzz_unknown");
  }
});

test("mail inbox labels translate categories and priorities with a translated fallback", () => {
  for (const lang of LANGS) {
    assert.notEqual(mailCategoryLabel(lang, "notice"), "notice");
    assert.notEqual(mailCategoryLabel(lang, "weird_key"), "weird_key");
    assert.notEqual(mailPriorityLabel(lang, "high"), "high");
    assert.notEqual(mailPriorityLabel(lang, "weird"), "weird");
  }
  assert.equal(mailCategoryLabel("en", "review"), "To review");
});
