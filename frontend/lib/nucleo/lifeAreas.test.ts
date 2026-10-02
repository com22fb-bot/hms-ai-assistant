import assert from "node:assert/strict";
import test from "node:test";

import {
  amountsMatch,
  areaChip,
  buildLifeItems,
  classifyText,
  hasTerm,
  monthMoney,
  normalizeAmount,
  oneLineStatement,
  parseAmounts,
} from "./lifeAreas.ts";

// CI runs this file explicitly; pull in the command-center rules too.
import "./commandCenter.test.ts";
import "../mailFrame.test.ts";
import "./helpKb.test.ts";
import "./cleanText.test.ts";
import "./explain.test.ts";
import "./topTen.test.ts";
import "./mailRefresh.test.ts";
import "./nextoDock.test.ts";
import "./caseActions.test.ts";

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

test("matches whole words, so short terms do not leak into other words", () => {
  assert.equal(hasTerm("pay your irs taxes", "irs"), true);
  assert.equal(hasTerm("see you saturday", "sat"), false);
  assert.equal(hasTerm("border control", "order"), false);
  assert.equal(hasTerm("tu suscripcion", "suscripci*"), true);
  assert.equal(hasTerm("aviso de irs.gov", ".gov"), true);
  assert.equal(classifyText("Privacy policy update").area, "other");
  assert.equal(classifyText("Groups update for Saturday").area, "other");
});

test("scores every area and breaks ties by consequence", () => {
  assert.equal(classifyText("El SAT te recuerda tu declaración mensual").area, "government");
  assert.equal(classifyText("Tu póliza de seguro de auto se renueva").area, "insurance");
  assert.equal(classifyText("Colegiatura de octubre de la universidad").area, "education");
  assert.equal(classifyText("Tus boletos para el concierto").area, "events");
  assert.equal(classifyText("Recordatorio de tu cita en Kaiser Permanente", "meeting").area, "health");
  assert.equal(classifyText("Cotización solicitada por el cliente Acme", "quotation").area, "work");
  assert.equal(classifyText("El cargo de $58.47 en Chase coincide con tu pedido").area, "money");
  assert.equal(classifyText("Nouvelle connexion: mot de passe modifié").area, "security");
  assert.equal(classifyText("Contraseña cambiada en tu cuenta").area, "security");
  assert.equal(classifyText("Hola, ¿cómo estás?").area, "other");
  assert.equal(areaChip("other"), "a-other");
});

test("plain 'seguro' is insurance, but not the adjective or other seguro- words", async () => {
  const { classifyText } = await import("./lifeAreas.ts");
  assert.equal(classifyText("Tu seguro vence el 15 de octubre").area, "insurance");
  assert.equal(classifyText("Renueva tu seguro de auto").area, "insurance");
  assert.equal(classifyText("Alerta de seguridad en tu cuenta").area, "security");
  assert.notEqual(classifyText("Pago seguro confirmado con PayPal").area, "insurance");
  assert.notEqual(classifyText("¿Estás seguro de que quieres cancelar tu pedido?").area, "insurance");
  assert.notEqual(classifyText("Asegurar tu lugar en el concierto").area, "insurance");
});
