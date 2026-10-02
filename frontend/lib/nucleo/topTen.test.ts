import assert from "node:assert/strict";
import test from "node:test";

import type { LifeItem } from "./lifeAreas.ts";
import { rankTopTen, scoreItem, shouldShowTopTen } from "./topTen.ts";

const NOW = new Date("2026-10-02T16:00:00-06:00");

function item(id: string, patch: Partial<LifeItem>): LifeItem {
  return {
    id,
    source: "case",
    caseId: id,
    messageId: null,
    title: id,
    line: id,
    area: "other",
    sender: "Remitente",
    when: "2026-10-01T10:00:00-06:00",
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
    ...patch,
  };
}

test("top10: overdue bills and due-today items outrank old notices; promos/social never appear", () => {
  const rows = rankTopTen([
    item("promo", { area: "promos", kind: "promo", when: "2026-10-02T15:00:00-06:00" }),
    item("social", { area: "social", kind: "social_suggest" }),
    item("welcome", { kind: "welcome" }),
    item("old-code", { area: "security", kind: "verification_code", when: "2026-10-01T09:00:00-06:00" }),
    item("bill-overdue", { area: "bills", kind: "bill_due", dueAt: "2026-10-01T12:00:00-06:00", amount: 840, amountRaw: "$840" }),
    item("today", { area: "government", dueAt: "2026-10-02T20:00:00-06:00" }),
    item("signin", { area: "security", kind: "security_alert", when: "2026-10-02T09:00:00-06:00" }),
    item("delivered", { area: "orders", kind: "order_delivered" }),
    item("done", { area: "bills", kind: "bill_due", status: "resolved", dueAt: "2026-10-01T12:00:00-06:00" }),
  ], NOW);
  const ids = rows.map((row) => row.item.id);
  assert.deepEqual(ids.slice(0, 3), ["bill-overdue", "today", "signin"]);
  for (const hidden of ["promo", "social", "welcome", "old-code", "done"]) assert.ok(!ids.includes(hidden), hidden);
  assert.equal(rows[0].reason, "overdue");
  assert.equal(rows[1].reason, "today");
  assert.equal(rows[2].reason, "security");
});

test("top10: at most ten rows, snoozed items skipped, fresh codes allowed", () => {
  const many = Array.from({ length: 25 }, (_, index) => item(`c${index}`, { area: "work", dueAt: `2026-10-${String(3 + (index % 20)).padStart(2, "0")}T12:00:00-06:00` }));
  assert.equal(rankTopTen(many, NOW).length, 10);
  const snoozed = rankTopTen(many, NOW, (row) => row.id === "c0");
  assert.ok(!snoozed.some((row) => row.item.id === "c0"));
  const fresh = rankTopTen([item("code", { kind: "verification_code", area: "security", when: "2026-10-02T15:40:00-06:00" })], NOW);
  assert.equal(fresh.length, 1);
});

test("top10: earlier due date wins a tie", () => {
  const rows = rankTopTen([
    item("later", { area: "bills", dueAt: "2026-10-06T12:00:00-06:00" }),
    item("sooner", { area: "bills", dueAt: "2026-10-05T12:00:00-06:00" }),
  ], NOW);
  assert.deepEqual(rows.map((row) => row.item.id), ["sooner", "later"]);
  assert.ok(scoreItem(item("hi", { priority: "high" }), NOW).score > scoreItem(item("lo", { priority: "low" }), NOW).score);
});

test("top10: shown once, only after mail is classified and nothing else is open", () => {
  const base = { seenAt: null, ready: true, loading: false, blocked: false, count: 4 };
  assert.equal(shouldShowTopTen(base), true);
  assert.equal(shouldShowTopTen({ ...base, seenAt: "2026-10-02T22:00:00Z" }), false);
  assert.equal(shouldShowTopTen({ ...base, ready: false }), false);
  assert.equal(shouldShowTopTen({ ...base, loading: true }), false);
  assert.equal(shouldShowTopTen({ ...base, blocked: true }), false);
  assert.equal(shouldShowTopTen({ ...base, count: 0 }), false);
});
