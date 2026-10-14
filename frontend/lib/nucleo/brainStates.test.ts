import assert from "node:assert/strict";
import test from "node:test";

import { BRAIN_V1_STATUSES, buildLifeItems, isOpenStatus } from "./lifeAreas.ts";

const base = {
  case_type: "general", priority: "normal", summary: null, requested_action: null, requester_name: null,
  requester_email: null, last_activity_at: "2026-10-01T12:00:00.000Z", due_at: null, source_count: 1,
};

test("brain v1 states: scheduled and needs_review are open, no_action is closed", () => {
  assert.equal(isOpenStatus("scheduled"), true);
  assert.equal(isOpenStatus("needs_review"), true);
  assert.equal(isOpenStatus("no_action"), false);
  assert.equal(BRAIN_V1_STATUSES.has("new"), false);
});

test("brain v1: event_at is shown when there is no due date; review items are flagged", () => {
  const items = buildLifeItems(
    [
      { ...base, id: "c1", title: "Cita en clínica", status: "scheduled", event_at: "2026-11-20T16:00:00.000Z" },
      { ...base, id: "c2", title: "Correo ambiguo", status: "needs_review" },
    ],
    [{ latest_message_id: "m1", subject: "Mensaje poco claro", summary: null, sender: "a@b.example",
       latest_received_at: "2026-10-01T12:00:00.000Z", triage_category: "review" }],
  );
  const byId = Object.fromEntries(items.map((item) => [item.id, item]));
  const appt = items.find((item) => item.caseId === "c1")!;
  assert.equal(appt.dueAt, "2026-11-20T16:00:00.000Z");
  assert.equal(appt.eventAt, "2026-11-20T16:00:00.000Z");
  assert.equal(items.find((item) => item.caseId === "c2")!.needsReview, true);
  assert.equal(byId["thread:m1"]?.needsReview, true);
});

test("flag off: legacy cases never carry brain states", () => {
  const items = buildLifeItems([{ ...base, id: "c3", title: "Factura", status: "new" }], []);
  assert.equal(items.some((item) => BRAIN_V1_STATUSES.has(item.status)), false);
  assert.equal(items[0].eventAt, null);
});
