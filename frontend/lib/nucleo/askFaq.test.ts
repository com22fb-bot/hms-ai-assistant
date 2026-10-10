import assert from "node:assert/strict";
import test from "node:test";

import { askLocal } from "./commandCenter.ts";
import { matchHelp } from "./helpKb.ts";
import type { LifeItem } from "./lifeAreas.ts";

function item(id: string, title: string, area: LifeItem["area"], line = title): LifeItem {
  return { id, source: "thread", caseId: null, messageId: id, title, line, area, sender: "Netflix", when: "2026-10-09T10:00:00Z",
    dueAt: null, status: "new", priority: "normal", amount: null, amountRaw: null, refund: false, priceIncrease: false,
    reconciled: false, requestedAction: null, sourceCount: 1 };
}

test("product price question answers from the built-in FAQ", () => {
  const out = matchHelp("cuanto es el costo de la suscripción?");
  assert.equal(out[0]?.entry.id, "pricing");
  assert.match(out[0].entry.copy.es.body, /19\.99/);
  assert.match(out[0].entry.copy.es.body, /175\.99/);
});

test("trial and import window questions", () => {
  assert.equal(matchHelp("cuantos dias dura la prueba gratis")[0]?.entry.id, "trial");
  assert.equal(matchHelp("cuanto historial de correo importa")[0]?.entry.id, "importWindow");
});

test("accent-insensitive, synonym search; no empty area filter", () => {
  const items = [item("a", "Tu membresía Netflix: nuevo precio", "promos"), item("b", "Pedido enviado", "orders")];
  const res = askLocal(items, "cuanto es el costo de la suscripción?");
  assert.ok(res.hits.some((hit) => hit.id === "a"));
});

test("partial match: facturas finds factura", () => {
  const res = askLocal([item("a", "Tu factura de CFE", "bills")], "facturas cfe");
  assert.equal(res.hits.length, 1);
});

test("no substring noise: costo does not match important", () => {
  const res = askLocal([item("a", "Important update about your account", "work")], "costo");
  assert.equal(res.hits.length, 0);
});
