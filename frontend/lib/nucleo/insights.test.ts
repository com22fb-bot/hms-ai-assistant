import assert from "node:assert/strict";
import test from "node:test";

import { localizeItems } from "./explain.ts";
import { insightArea, insightExcerpts, insightLine, type MailInsight } from "./insights.ts";
import { buildLifeItems, type InboxCase, type InboxThread } from "./lifeAreas.ts";

const ISSSTE: MailInsight = {
  kind: "gov_procedure",
  area: "government",
  main_idea: {
    es: "ISSSTE envió un aviso sobre un trámite: Resolución de devolución FOPI.",
    en: "ISSSTE sent a notice about a procedure: Resolución de devolución FOPI.",
    fr: "ISSSTE a envoyé un avis sur une démarche : Resolución de devolución FOPI.",
    it: "ISSSTE ha inviato un avviso su una pratica: Resolución de devolución FOPI.",
    pt: "ISSSTE enviou um aviso sobre um trâmite: Resolución de devolución FOPI.",
  },
  excerpts: ["Tu solicitud de devolución del FOPI fue resuelta."],
  facts: { brand: "ISSSTE" },
  preview: "Tu solicitud de devolución del FOPI fue resuelta.",
};

const CARD: MailInsight = {
  kind: "card_status",
  area: "money",
  main_idea: { es: "Santander avisa sobre el estado de tu tarjeta." },
  excerpts: ["No pudimos entregar tu tarjeta.", "Visita tu sucursal para recogerla."],
  facts: { brand: "Santander" },
};

function caseRow(title: string, summary: string, insight?: MailInsight): InboxCase {
  return {
    id: title.length.toString(36) + title.slice(0, 3),
    title,
    case_type: "general",
    status: "new",
    priority: "normal",
    summary,
    requested_action: null,
    requester_name: null,
    requester_email: null,
    last_activity_at: "2026-10-02T12:00:00Z",
    due_at: null,
    source_count: 1,
    insight,
  };
}

function threadRow(id: string, subject: string, summary: string, insight?: MailInsight): InboxThread {
  return { latest_message_id: id, subject, summary, sender: "Avisos <avisos@example.com>", latest_received_at: "2026-10-02T12:00:00Z", triage_category: "review", insight };
}

test("insights: backend area wins over keyword scoring (ISSSTE is not Health)", () => {
  const blob = "ISSSTE Instituto de Seguridad y Servicios Sociales: clínica, salud, médico";
  const [withInsight] = buildLifeItems([caseRow("ISSSTE aviso", blob, ISSSTE)], []);
  assert.equal(withInsight.area, "government");
  assert.equal(withInsight.line, ISSSTE.main_idea?.es);
  assert.equal(withInsight.preview, ISSSTE.preview);
});

test("insights: a bank card notice is Money, not Orders", () => {
  const items = buildLifeItems([], [threadRow("m1", "Tu tarjeta no pudo ser entregada", "Envío de tu pedido de tarjeta: entrega, paquete, rastreo", CARD)]);
  assert.equal(items[0].area, "money");
});

test("insights: without an insight the keyword fallback still works", () => {
  const items = buildLifeItems([], [threadRow("m2", "Tu pedido va en camino", "Rastrea tu paquete y entrega")]);
  assert.equal(items[0].area, "orders");
  assert.equal(items[0].insight, null);
});

test("insights: unknown or missing backend area falls back", () => {
  assert.equal(insightArea({ kind: "personal", area: null }, "work"), "work");
  assert.equal(insightArea({ kind: "x", area: "not-an-area" }, "home"), "home");
  assert.equal(insightArea(null, "other"), "other");
});

test("insights: main idea follows the UI language and never re-classifies", () => {
  const items = buildLifeItems([caseRow("ISSSTE aviso", "salud médico clínica", ISSSTE)], []);
  for (const lang of ["es", "en", "fr", "it", "pt"] as const) {
    const [item] = localizeItems(items, lang);
    assert.equal(item.line, ISSSTE.main_idea?.[lang]);
    assert.equal(item.area, "government");
    assert.equal(item.kind, "gov_procedure");
  }
  // A language the backend did not send falls back to Spanish.
  const [cardItem] = localizeItems(buildLifeItems([], [threadRow("m3", "Tarjeta", "x", CARD)]), "fr");
  assert.equal(cardItem.line, CARD.main_idea?.es);
});

test("insights: quotes are passed through exactly, max 3, empties dropped", () => {
  const quotes = insightExcerpts({ kind: "x", excerpts: ["Uno: $1.00", "", "  ", "Dos «exacto»", "Tres", "Cuatro"] });
  assert.deepEqual(quotes, ["Uno: $1.00", "Dos «exacto»", "Tres"]);
  assert.deepEqual(insightExcerpts(null), []);
  assert.equal(insightLine({ kind: "x", main_idea: {} }, "es"), null);
});

test("insights: amount from facts feeds money totals", () => {
  const insight: MailInsight = { kind: "payment_declined", area: "money", main_idea: { es: "Banco rechazó el cobro por $159." }, facts: { amount: "$159" } };
  const [item] = buildLifeItems([], [threadRow("m4", "Rechazo por saldo insuficiente", "Rechazo por saldo insuficiente", insight)]);
  assert.equal(item.amount, 159);
  assert.equal(item.area, "money");
});
