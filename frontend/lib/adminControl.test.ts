import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dbUsage, mailboxRows, orderPedidos, showValue, checkMark, SIN_DATO, providerSummary } from "./adminControl.ts";

test("sin ceros falsos: null/undefined = 'sin dato'; 0 real se muestra", () => {
  assert.equal(showValue(null), SIN_DATO);
  assert.equal(showValue(undefined), SIN_DATO);
  assert.equal(showValue(0), "0");
});
test("uso de BD sale del check db_quota real", () => {
  const p = { checks: [{ id: "db_quota", status: "ok", evidence: "21 MB de 500 MB (plan Free) = 4.2 %" }] } as never;
  assert.deepEqual(dbUsage(p), { usedMb: 21, limitMb: 500, pct: 4.2 });
  assert.equal(dbUsage(null), null);
  assert.equal(dbUsage({ checks: [{ id: "db_quota", status: "sin_verificar", evidence: "x" }] } as never), null);
});
test("buzones anónimos: nunca correo ni ID", () => {
  const rows = mailboxRows([{ mailboxes: [{ account_id: "uuid-x", email: "a@b.com", provider: "gmail", status: "connected", messages: 3 } as never] }]);
  const s = JSON.stringify(rows);
  assert.ok(!s.includes("a@b.com") && !s.includes("uuid-x"));
  assert.equal(rows[0].provider, "Gmail");
  assert.equal(rows[0].status, "Conectado");
  assert.deepEqual(providerSummary(rows), [["Gmail", 1]]);
});
test("Bitácora en Resumen: Pendiente > En curso > Realizado", () => {
  const ev = [
    { title: "a", occurred_at: "2026-10-23T10:00Z", meta: { kind: "pedido", estado: "hecho" } },
    { title: "b", occurred_at: "2026-10-22T10:00Z", meta: { kind: "pedido", estado: "en_curso" } },
    { title: "c", occurred_at: "2026-10-21T10:00Z", meta: { kind: "pedido", estado: "pendiente" } },
    { title: "x", occurred_at: "2026-10-23T11:00Z", meta: { kind: "evento" } },
  ];
  assert.deepEqual(orderPedidos(ev).map((e) => e.title), ["c", "b", "a"]);
});
test("semáforo: marca por control", () => {
  assert.equal(checkMark("ok").mark, "✓");
  assert.equal(checkMark("falla").mark, "✕");
  assert.equal(checkMark("degradado").mark, "⚠");
});
test("página: marca Donexto, botones 'Click para…', sección Buzones y secciones existentes", () => {
  const page = readFileSync(new URL("../app/admin/page.tsx", import.meta.url), "utf8");
  for (const s of ["Resumen", "Usuarios", "Buzones", "Cobros", "Mis gastos", "Información", "Mensajes", "Quejas e ideas", "Promociones", "Rendimiento", "Bitácora", "Sistema"])
    assert.ok(page.includes(`label: "${s}"`), s);
  assert.ok(page.includes("Donexto"));
  assert.ok(page.includes("Click para actualizar"));
  const panel = readFileSync(new URL("../app/admin/MailboxesPanel.tsx", import.meta.url), "utf8");
  assert.ok(!/\.email\b|account_id/.test(panel), "Buzones no debe pintar correo ni IDs");
});

test("el diseño de rejilla solo aplica al panel (no al acceso ni a la carga)", () => {
  const css = readFileSync(new URL("../app/admin/admin.css", import.meta.url), "utf8");
  const block = css.slice(css.indexOf("/* ===== Centro de control"));
  assert.doesNotMatch(block, /(^|\n)\s*\.dx-admin \{/);
  assert.match(block, /\.dx-admin--shell \{[^}]*grid-template-areas/);
});
