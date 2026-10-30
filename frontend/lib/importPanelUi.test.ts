import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const css = readFileSync(new URL("../components/guided-import.css", import.meta.url), "utf8");
const panel = readFileSync(new URL("../components/ImportStatusPanel.tsx", import.meta.url), "utf8");
const wizard = readFileSync(new URL("../components/GuidedImportWizard.tsx", import.meta.url), "utf8");

test("OBS-UI-02: no robot image in loading/ready CSS nor wizard", () => {
  assert.ok(!/hms-logistics-loading::before\s*\{[^}]*hms-import-robot/.test(css));
  assert.ok(!/url\('\/hms-import-robot\.png'\)/.test(css));
  assert.ok(!wizard.includes("hms-import-robot"));
});

test("OBS-UI-01: stopped panel offers Close and Continue (es/en)", () => {
  for (const s of ["Cerrar", "Continuar descarga", "Close", "Continue download"]) assert.ok(panel.includes(s), s);
  assert.ok(panel.includes('data-testid="import-stopped"'));
  assert.ok(panel.includes("/api/hms/gmail/import/start"));
  assert.ok(panel.includes("setVisible(false)"));
});

test("panel does not overlap the Nexto mascot dock (bottom-right)", () => {
  assert.ok(panel.includes("left: 16, bottom: 16"));
});
