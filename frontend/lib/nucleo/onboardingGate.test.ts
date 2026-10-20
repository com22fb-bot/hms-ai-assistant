import assert from "node:assert/strict";
import test from "node:test";

import { canOpenInitialImport } from "./onboardingGate.ts";

test("import waits while the notifications step is undecided or open", () => {
  assert.equal(canOpenInitialImport(true, "pending"), false);
  assert.equal(canOpenInitialImport(true, "open"), false);
});

test("import opens once notifications are finished or skipped", () => {
  assert.equal(canOpenInitialImport(true, "done"), true);
  assert.equal(canOpenInitialImport(false, "done"), false);
});
