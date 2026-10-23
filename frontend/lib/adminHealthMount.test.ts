// Criterio 7: el semáforo se monta al entrar a /admin, fuera de cualquier pestaña, y su CSS es responsive.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const page = readFileSync(new URL("../app/admin/page.tsx", import.meta.url), "utf8");
const css = readFileSync(new URL("../app/admin/admin.css", import.meta.url), "utf8");

test("HealthBar se renderiza antes de la navegación de pestañas y no depende de `tab`", () => {
  const bar = page.indexOf("{!forbidden && <HealthBar />}");
  const nav = page.indexOf('<nav className="dx-admin__nav"');
  assert.ok(bar > 0 && bar < nav);
  assert.ok(!/tab === "[a-z]+" && <HealthBar/.test(page));
});
test("CSS sin anchos fijos: envuelve en móvil y tablet", () => {
  assert.match(css, /\.dx-health__bar \{[^}]*flex-wrap: wrap/);
  assert.match(css, /@media \(max-width: 640px\)/);
  assert.match(css, /\.dx-health__note \{[^}]*min-width: 0/);
});
