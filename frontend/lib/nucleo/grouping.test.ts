import assert from "node:assert/strict";
import test from "node:test";

import { groupLifeItems } from "./grouping.ts";
import type { LifeItem } from "./lifeAreas.ts";

function item(id: string, over: Partial<LifeItem>): LifeItem {
  return {
    id, source: "thread", caseId: null, messageId: id, title: "Alerta de seguridad", line: "Google: aviso de seguridad de tu cuenta; revisa si fuiste tú.",
    area: "security", sender: "Google", when: "2026-10-09T10:00:00Z", dueAt: null, status: "new", priority: "normal",
    amount: null, amountRaw: null, refund: false, priceIncrease: false, reconciled: false, requestedAction: null,
    sourceCount: 1, senderEmail: "no-reply@accounts.google.com", kind: "security_alert", ...over,
  };
}

test("same Google security alert across messages and mailboxes = one case ×N", () => {
  const out = groupLifeItems([
    item("a", {}),
    item("b", { when: "2026-10-08T10:00:00Z", title: "Alerta de seguridad para hmcelinfo@gmail.com" }),
    item("c", { when: "2026-10-07T10:00:00Z", title: "Se agregó un nuevo dispositivo" }),
    item("d", { when: "2026-10-09T09:00:00Z" }),
  ]);
  assert.equal(out.length, 1);
  assert.equal(out[0].groupCount, 4);
  assert.match(out[0].line, /×4$/);
});

test("outside the 7-day window is a new case", () => {
  const out = groupLifeItems([item("a", {}), item("b", { when: "2026-09-20T10:00:00Z" })]);
  assert.equal(out.length, 2);
});

test("different brands do not merge", () => {
  const out = groupLifeItems([item("a", {}), item("b", { sender: "Microsoft", senderEmail: "account-security-noreply@accountprotection.microsoft.com" })]);
  assert.equal(out.length, 2);
});

test("verification codes: grouped, low priority, code hidden", () => {
  const out = groupLifeItems([
    item("a", { kind: "verification_code", title: "Your verification code is 482913", priority: "high", senderEmail: "noreply@github.com", sender: "GitHub" }),
    item("b", { kind: "verification_code", title: "Your verification code is 119922", when: "2026-10-09T08:00:00Z", senderEmail: "noreply@github.com", sender: "GitHub" }),
  ]);
  assert.equal(out.length, 1);
  assert.equal(out[0].priority, "low");
  assert.doesNotMatch(out[0].title, /482913/);
});

test("unrelated mails stay separate", () => {
  const out = groupLifeItems([
    item("a", { kind: "order_shipped", area: "orders", title: "Tu pedido 123 va en camino", sender: "Amazon", senderEmail: "envios@amazon.com.mx" }),
    item("b", { kind: "bill_due", area: "bills", title: "Tu recibo CFE", sender: "CFE", senderEmail: "avisos@cfe.mx" }),
  ]);
  assert.equal(out.length, 2);
});
