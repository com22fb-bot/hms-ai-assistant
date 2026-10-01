import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { prefsAfterEdit, prefsAfterLoad } from "./prefsSync.ts";

test("server preferences are applied only when the user has not edited yet", () => {
  assert.equal(prefsAfterLoad({ dirty: false, hasServer: true }), "apply-server");
  assert.equal(prefsAfterLoad({ dirty: false, hasServer: false }), "hold");
  assert.equal(prefsAfterLoad({ dirty: true, hasServer: true }), "upload");
  assert.equal(prefsAfterLoad({ dirty: true, hasServer: false }), "upload");
});

test("edits wait for the first load and then upload", () => {
  assert.equal(prefsAfterEdit({ hydrated: false }), "hold");
  assert.equal(prefsAfterEdit({ hydrated: true }), "upload");
});

test("the dashboard does not upload the initial snapshot", () => {
  const source = readFileSync(
    new URL("../../components/nucleo/NucleoApp.tsx", import.meta.url),
    "utf8",
  );
  assert.match(source, /prefsAfterLoad/);
  assert.match(source, /prefsAfterEdit/);
  assert.doesNotMatch(source, /\[prefs, props\.preview\]/);
  assert.match(source, /onClose=\{\(\) => void finishOnboarding\(false\)\}/);
  assert.match(source, /function show\(next: ViewId\) \{[\s\S]*setCaseId\(null\)/);
  assert.match(source, /aria-label=\{t\("navAlerts"\)\} onClick=\{\(\) => show\("alerts"\)\}/);
  assert.match(source, /onClick=\{\(\) => show\("today"\)\}/);
  assert.match(source, /onClick=\{\(\) => show\("money"\)\}/);
  assert.match(source, /onClick=\{\(\) => show\("orders"\)\}/);
  assert.doesNotMatch(source, /onClick=\{\(\) => setView\(/);
});
