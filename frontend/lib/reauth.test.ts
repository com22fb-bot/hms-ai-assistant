import assert from "node:assert/strict";
import test from "node:test";

import { reauthPrompt } from "./reauth.ts";

test("sin needs_reauth no hay aviso", () => {
  assert.equal(reauthPrompt(null), null);
  assert.equal(reauthPrompt({ connected: true, needs_reauth: true }), null);
  assert.equal(reauthPrompt({ connected: false }), null);
});

test("needs_reauth muestra proveedor y correo", () => {
  const p = reauthPrompt({ connected: false, needs_reauth: true, provider: "microsoft", email: "a@example.test" });
  assert.equal(p?.title, "Vuelve a conectar Outlook");
  assert.match(p?.detail || "", /a@example\.test/);
  assert.equal(reauthPrompt({ needs_reauth: true })?.title, "Vuelve a conectar Gmail");
});
