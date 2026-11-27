import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  daysPhrase, daysUntil, donutSegments, fmtDate, fmtDateShort, groupBySeverity, mxn, severityForDays,
  timelinePct, todayCdmx, updatedAgo, usd, type PayItem,
} from "./paymentsAgenda.ts";

const item = (over: Partial<PayItem>): PayItem => ({
  id: "x", servicio: "Cursor", tipo: "pago", on: "2026-12-07", usd: 20, mxn: 393.93, currency: "USD",
  estimated: true, cost_estimated: false, period: "mensual", label: "Pro", action: "", source: "admin_expenses",
  days: 10, severity: "naranja", ...over,
});

test("fechas y montos en español con US$ y MXN", () => {
  assert.equal(fmtDate("2026-12-07"), "7-dic-2026");
  assert.equal(fmtDateShort("2027-01-20"), "20 ene");
  assert.equal(usd(20), "US$20.00");
  assert.equal(mxn(393.93), "MXN 393.93");
});

test("frases de días y semáforo 3/14/60", () => {
  assert.equal(daysPhrase(-1), "vencido hace 1 día");
  assert.equal(daysPhrase(0), "vence hoy");
  assert.equal(daysPhrase(10), "en 10 días");
  assert.deepEqual([-1, 3, 4, 14, 15, 60, 61].map(severityForDays), ["rojo", "rojo", "naranja", "naranja", "verde", "verde", "luego"]);
});

test("hoy en CDMX y días restantes", () => {
  // 03:30 UTC del 28-nov = 21:30 del 27-nov en Ciudad de México.
  assert.equal(todayCdmx(new Date("2026-11-28T03:30:00Z")), "2026-11-27");
  assert.equal(daysUntil("2026-12-07", "2026-11-27"), 10);
  assert.equal(daysUntil("2026-11-26", "2026-11-27"), -1);
});

test("actualizado hace X", () => {
  assert.equal(updatedAgo(null, 0), "Actualizando…");
  assert.equal(updatedAgo(1000, 4000), "Actualizado justo ahora");
  assert.equal(updatedAgo(0, 45_000), "Actualizado hace 45 s");
  assert.equal(updatedAgo(0, 125_000), "Actualizado hace 2 min");
});

test("agrupa por semáforo en orden y ubica en la línea de 60 días", () => {
  const groups = groupBySeverity([item({ severity: "verde" }), item({ severity: "rojo" }), item({ severity: "luego" })]);
  assert.deepEqual(groups.map(([s]) => s), ["rojo", "verde", "luego"]);
  assert.equal(timelinePct(-3, 60), 0);
  assert.equal(timelinePct(30, 60), 50);
  assert.equal(timelinePct(61, 60), null);
});

test("dona: fracciones suman 1 y sin total no dibuja", () => {
  const segs = donutSegments([{ servicio: "Cursor", usd: 20 }, { servicio: "Railway", usd: 5 }]);
  assert.equal(Math.round(segs.reduce((s, x) => s + x.frac, 0) * 1e6) / 1e6, 1);
  assert.deepEqual(donutSegments([]), []);
});

test("el panel se monta arriba de /admin, refresca solo y no muestra n8n", () => {
  const page = readFileSync(new URL("../app/admin/page.tsx", import.meta.url), "utf8");
  const comp = readFileSync(new URL("../app/admin/PaymentsAgenda.tsx", import.meta.url), "utf8");
  assert.ok(page.indexOf("<PaymentsAgenda") > -1 && page.indexOf("<PaymentsAgenda") < page.indexOf("<nav"));
  assert.match(comp, /REFRESH_MS/);
  assert.match(comp, /visibilitychange/);
  assert.match(comp, /EXPENSES_CHANGED_EVENT/);
  assert.doesNotMatch(comp + page, /n8n|GITHUB_TOKEN_DONEXTO/i);
});
