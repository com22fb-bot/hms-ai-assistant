import assert from "node:assert/strict";
import test from "node:test";

import {
  amountsMatch,
  buildLifeItems,
  classifyText,
  monthMoney,
  normalizeAmount,
  oneLineStatement,
  parseAmounts,
} from "./lifeAreas.ts";

test("classifies inbox text into life areas without inventing a bank feed", () => {
  assert.equal(
    classifyText("Tu pedido de Amazon fue enviado").area,
    "orders",
  );
  assert.equal(
    classifyText("Netflix sube a $17.99 al mes").area,
    "subscriptions",
  );
  assert.equal(classifyText("Netflix sube a $17.99 al mes").priceIncrease, true);
  assert.equal(
    classifyText("Nuevo inicio de sesión en Google").area,
    "security",
  );
  assert.equal(classifyText("Reembolso de $40 en PayPal").refund, true);
  assert.equal(classifyText("Factura CFE vence el jueves", "invoice").area, "bills");
});

test("one line stays a single readable sentence", () => {
  assert.equal(
    oneLineStatement("Pedido", "Tu pedido llegó. El cargo coincide."),
    "Tu pedido llegó.",
  );
  assert.equal(oneLineStatement("Solo el título", null), "Solo el título");
  assert.equal(
    oneLineStatement("Luz", "Luz · vence 8 oct · +$6.10 vs. septiembre. Paga antes."),
    "Luz · vence 8 oct · +$6.10 vs septiembre.",
  );
});

test("parses money mentions and reconciles a charge with an order", () => {
  assert.equal(normalizeAmount("1,284.62"), 1284.62);
  assert.equal(normalizeAmount("1.284,62"), 1284.62);
  const amounts = parseAmounts("El cargo de $129.99 en Chase");
  assert.equal(amounts[0]?.value, 129.99);
  assert.equal(amountsMatch(129.99, 129.99001), true);

  const items = buildLifeItems(
    [
      {
        id: "c1",
        title: "Cargo de $58.47 en Chase",
        case_type: "payment",
        status: "new",
        priority: "normal",
        summary: "Cargo de $58.47",
        requested_action: null,
        requester_name: "Chase",
        requester_email: "alerts@chase.com",
        last_activity_at: "2026-10-01T12:00:00.000Z",
        due_at: null,
        source_count: 1,
      },
      {
        id: "c2",
        title: "Tu pedido de Amazon de $58.47 fue enviado",
        case_type: "general",
        status: "new",
        priority: "normal",
        summary: "Pedido enviado",
        requested_action: null,
        requester_name: "Amazon",
        requester_email: "auto@amazon.com",
        last_activity_at: "2026-10-01T13:00:00.000Z",
        due_at: null,
        source_count: 2,
      },
    ],
    [],
  );
  assert.equal(items.every((item) => item.reconciled), true);
  const stats = monthMoney(items, new Date("2026-10-15T12:00:00.000Z"));
  assert.equal(stats.movements, 2);
  assert.ok(stats.outflows > 50);
});
