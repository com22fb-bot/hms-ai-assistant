import assert from "node:assert/strict";
import test from "node:test";

import {
  askLocal,
  dayOffset,
  dueBucket,
  needsActionToday,
  orderStage,
  parseAsk,
  parseAskAmount,
  recentAlerts,
  summarizeAreas,
  summarizeOrders,
  summarizeSubscriptions,
  summaryParts,
  upcomingDue,
} from "./commandCenter.ts";
import type { LifeItem } from "./lifeAreas.ts";

const NOW = new Date(2026, 9, 5, 10, 0, 0); // Mon 5 Oct 2026, 10:00 local
const H = 36e5;
const at = (hours: number) => new Date(NOW.getTime() + hours * H).toISOString();

function item(id: string, extra: Partial<LifeItem>): LifeItem {
  return {
    id,
    source: "case",
    caseId: id,
    messageId: null,
    title: id,
    line: id,
    area: "other",
    sender: "",
    when: at(-1),
    dueAt: null,
    status: "new",
    priority: "normal",
    amount: null,
    amountRaw: null,
    refund: false,
    priceIncrease: false,
    reconciled: false,
    requestedAction: null,
    sourceCount: 1,
    ...extra,
  };
}

test("due buckets use calendar days in local time", () => {
  assert.equal(dueBucket(item("a", { dueAt: at(-2) }), NOW), "overdue");
  assert.equal(dueBucket(item("b", { dueAt: at(5) }), NOW), "today");
  assert.equal(dueBucket(item("c", { dueAt: at(20) }), NOW), "tomorrow");
  assert.equal(dueBucket(item("d", { dueAt: at(24 * 5) }), NOW), "week");
  assert.equal(dueBucket(item("e", { dueAt: at(24 * 9) }), NOW), "later");
  assert.equal(dueBucket(item("f", {}), NOW), "none");
  assert.equal(dayOffset(at(20), NOW), 1);
  assert.equal(dayOffset("not a date", NOW), null);
});

test("upcoming timeline groups the next 7 days and skips closed or snoozed items", () => {
  const items = [
    item("late", { dueAt: at(-30) }),
    item("today", { dueAt: at(4) }),
    item("tomorrow", { dueAt: at(26) }),
    item("week", { dueAt: at(24 * 6) }),
    item("far", { dueAt: at(24 * 12) }),
    item("closed", { dueAt: at(5), status: "resolved" }),
    item("snoozed", { dueAt: at(6) }),
    item("ancient", { dueAt: at(-24 * 20) }),
  ];
  const days = upcomingDue(items, NOW, 7, (row) => row.id === "snoozed");
  assert.deepEqual(days.map((day) => day.offset), [-1, 0, 1, 6]);
  assert.deepEqual(days.flatMap((day) => day.items.map((row) => row.id)), ["late", "today", "tomorrow", "week"]);
});

test("requires-action-today keeps overdue, due today, high priority and security", () => {
  const items = [
    item("security", { area: "security", when: at(-3) }),
    item("bill", { area: "bills", dueAt: at(6) }),
    item("vip", { priority: "high", dueAt: at(24 * 3) }),
    item("late", { dueAt: at(-5) }),
    item("later", { dueAt: at(24 * 4) }),
    item("done", { priority: "critical", status: "resolved" }),
  ];
  const ids = needsActionToday(items, NOW).map((row) => row.id);
  assert.deepEqual(new Set(ids), new Set(["security", "bill", "vip", "late"]));
  assert.ok(!ids.includes("later"));
  assert.ok(ids.indexOf("late") < ids.indexOf("vip"), "overdue before a high-priority item due in 3 days");
});

test("recent alerts explain why each one is there", () => {
  const alerts = recentAlerts(
    [
      item("login", { area: "security", when: at(-2) }),
      item("netflix", { area: "subscriptions", priceIncrease: true, when: at(-5) }),
      item("old", { area: "security", when: at(-24 * 10) }),
      item("promo", { area: "promos", priority: "high", when: at(-1) }),
      item("boss", { sender: "Jefa", when: at(-4) }),
    ],
    NOW,
    (row) => row.sender === "Jefa",
  );
  assert.deepEqual(alerts.map((alert) => [alert.item.id, alert.reason]), [
    ["login", "security"],
    ["boss", "rule"],
    ["netflix", "priceIncrease"],
  ]);
});

test("order status thread is rule-based", () => {
  assert.equal(orderStage(item("o1", { title: "Tu pedido de Amazon fue enviado" })), "shipped");
  assert.equal(orderStage(item("o2", { title: "Your package was delivered" })), "delivered");
  assert.equal(orderStage(item("o3", { title: "Pedido cancelado" })), "cancelled");
  assert.equal(orderStage(item("o4", { title: "Confirmación de tu pedido" })), "confirmed");
  assert.equal(orderStage(item("o5", { title: "Reembolso de tu pedido", refund: true })), "refunded");
  const orders = summarizeOrders([
    item("o1", { area: "orders", title: "Tu pedido fue enviado", when: at(-1) }),
    item("o2", { area: "orders", title: "Pedido entregado", status: "resolved", when: at(-30) }),
  ], NOW);
  assert.equal(orders.inTransit, 1);
  assert.equal(orders.delivered, 1);
  assert.equal(orders.latest?.stage, "shipped");
});

test("area and subscription summaries count only real open items", () => {
  const items = [
    item("s1", { area: "subscriptions", sender: "Netflix", priceIncrease: true, dueAt: at(24 * 3) }),
    item("s2", { area: "subscriptions", sender: "Spotify", dueAt: at(24 * 20) }),
    item("b1", { area: "bills", dueAt: at(30) }),
    item("b2", { area: "bills", status: "resolved" }),
  ];
  const areas = summarizeAreas(items, NOW);
  assert.equal(areas.bills.open, 1);
  assert.equal(areas.bills.dueSoon, 1);
  assert.equal(areas.bills.next?.id, "b1");
  assert.equal(areas.health, undefined);
  const subs = summarizeSubscriptions(items, NOW);
  assert.deepEqual(subs, { renewingSoon: 1, priceIncreases: 1, active: 2 });
});

test("Pregunta a Donexto parses intent locally without any model", () => {
  const intent = parseAsk("¿Qué pedidos llegan esta semana?");
  assert.deepEqual(intent.areas, ["orders"]);
  assert.equal(intent.time, "week");
  assert.deepEqual(intent.terms, ["llegan"]);
  assert.equal(parseAsk("cargo de $58.47").amount, 58.47);
  assert.equal(parseAsk("facturas vencidas").time, "overdue");
  assert.equal(parseAsk("what is pending?").status, "open");
});

test("local search filters by area, time, amount and free text", () => {
  const items = [
    item("amazon", { area: "orders", title: "Tu pedido de Amazon fue enviado", sender: "Amazon", dueAt: at(24 * 2), amount: 58.47 }),
    item("ml", { area: "orders", title: "Paquete de Mercado Libre", sender: "Mercado Libre", status: "resolved" }),
    item("chase", { area: "money", title: "Cargo de $58.47 en Chase", sender: "Chase", amount: 58.47 }),
    item("coned", { area: "bills", title: "Factura de Con Edison", sender: "Con Edison", dueAt: at(-3) }),
  ];
  assert.deepEqual(askLocal(items, "pedidos esta semana", NOW).hits.map((row) => row.id), ["amazon"]);
  assert.deepEqual(askLocal(items, "pedidos", NOW).hits.map((row) => row.id), ["amazon", "ml"]);
  assert.deepEqual(new Set(askLocal(items, "$58.47", NOW).hits.map((row) => row.id)), new Set(["amazon", "chase"]));
  assert.deepEqual(askLocal(items, "facturas vencidas", NOW).hits.map((row) => row.id), ["coned"]);
  assert.deepEqual(askLocal(items, "Mercado Libre", NOW).hits.map((row) => row.id), ["ml"]);
  assert.deepEqual(askLocal(items, "nada que ver aqui zzz", NOW).hits, []);
});

test("stop-word-only questions return nothing instead of every case", () => {
  const items = [item("a", { title: "Pedido Amazon" }), item("b", { title: "Factura CFE" })];
  for (const query of ["qué hay", "¿Qué hay en mi correo?", "show me", "  ?  ", "dime"]) {
    const result = askLocal(items, query, NOW);
    assert.equal(result.hits.length, 0, query);
    assert.equal(result.vague, true, query);
  }
  assert.equal(askLocal(items, "amazon", NOW).vague, false);
});

test("bare decimals and currency words are amounts; plain integers stay text", () => {
  assert.equal(parseAskAmount("58.47"), 58.47);
  assert.equal(parseAskAmount("cuanto fue 58,47"), 58.47);
  assert.equal(parseAskAmount("$ 12"), 12);
  assert.equal(parseAskAmount("200 pesos"), 200);
  assert.equal(parseAskAmount("19.99 usd"), 19.99);
  assert.equal(parseAskAmount("vuelo 1547"), null);
  assert.equal(parseAsk("58.47").amount, 58.47);
  assert.deepEqual(parseAsk("58.47").terms, []);
  assert.deepEqual(parseAsk("vuelo 1547").terms, ["1547"]);
  assert.equal(parseAsk("¿Cuánto pagué en pedidos, 58,47?").amount, 58.47);
  const items = [
    item("amz", { title: "Amazon", amount: 58.47 }),
    item("other", { title: "Otro cargo", amount: 12 }),
    item("ua", { title: "UA 1547 EWR DEN" }),
  ];
  assert.deepEqual(askLocal(items, "58.47", NOW).hits.map((hit) => hit.id), ["amz"]);
  assert.deepEqual(askLocal(items, "1547", NOW).hits.map((hit) => hit.id), ["ua"]);
});

test("amount search uses the same two-cent tolerance as amountsMatch", () => {
  const items = [
    item("exact", { amount: 58.47 }),
    item("cent", { amount: 58.46 }),
    item("near", { amount: 58.2 }),
    item("dollar", { amount: 57.6 }),
  ];
  assert.deepEqual(askLocal(items, "$58.47", NOW).hits.map((hit) => hit.id).sort(), ["cent", "exact"]);
});

test("'this month' uses the due date, falling back to the received date", () => {
  const items = [
    item("due-this-month", { area: "bills", when: new Date(2026, 8, 20).toISOString(), dueAt: new Date(2026, 9, 25, 12).toISOString() }),
    item("due-next-month", { area: "bills", when: new Date(2026, 9, 2).toISOString(), dueAt: new Date(2026, 10, 10, 12).toISOString() }),
    item("no-due-this-month", { area: "bills", when: new Date(2026, 9, 1).toISOString() }),
    item("no-due-last-month", { area: "bills", when: new Date(2026, 8, 1).toISOString() }),
  ];
  const hits = askLocal(items, "facturas este mes", NOW).hits.map((hit) => hit.id).sort();
  assert.deepEqual(hits, ["due-this-month", "no-due-this-month"]);
});

test("summary names at most three items and counts the rest", () => {
  assert.deepEqual(summaryParts(["A.", "B.", "C.", "D."], 4), { named: ["A.", "B.", "C."], more: 1 });
  assert.deepEqual(summaryParts(["A.", "", null, "D."], 4), { named: ["A.", "D."], more: 2 });
  assert.deepEqual(summaryParts(["A."], 1), { named: ["A."], more: 0 });
  assert.deepEqual(summaryParts([], 0), { named: [], more: 0 });
  assert.deepEqual(summaryParts(["Renta vence hoy", "¿Fuiste tú?"], 2).named, ["Renta vence hoy.", "¿Fuiste tú?"]);
});
