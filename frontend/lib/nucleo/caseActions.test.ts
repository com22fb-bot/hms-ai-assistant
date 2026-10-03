import assert from "node:assert/strict";
import test from "node:test";

import { caseActionErrorKey, caseActionRequest, isClosedStatus, runCaseAction, snoozeUntil } from "./caseActions.ts";

class FakeApiError extends Error {
  status: number;
  constructor(status: number) {
    super(`HTTP ${status}`);
    this.status = status;
  }
}

test("case actions use the per-user endpoint, never PATCH /cases/{id}", () => {
  for (const action of ["done", "reopen", "snooze", "unsnooze"] as const) {
    const { url, init } = caseActionRequest("abc-1", action, new Date("2026-10-03T15:00:00Z"));
    assert.equal(url, "/api/hms/cases/abc-1/user-action");
    assert.equal(init.method, "POST");
    const body = JSON.parse(String(init.body));
    assert.equal(body.action, action);
    assert.equal("until" in body, action === "snooze");
    assert.equal("status" in body || "due_at" in body, false);
  }
  assert.equal(JSON.parse(String(caseActionRequest("x", "snooze", new Date("2026-10-03T15:00:00Z")).init.body)).until, "2026-10-03T15:00:00.000Z");
  assert.equal(caseActionRequest("a/b", "done").url, "/api/hms/cases/a%2Fb/user-action");
});

test("errors map to clear plain-language keys", () => {
  assert.equal(caseActionErrorKey(new FakeApiError(423)), "caseErrLocked");
  assert.equal(caseActionErrorKey(new FakeApiError(401)), "caseErrSession");
  assert.equal(caseActionErrorKey(new FakeApiError(403)), "caseErrSession");
  assert.equal(caseActionErrorKey(new FakeApiError(404)), "caseErrMissing");
  assert.equal(caseActionErrorKey(new FakeApiError(422)), "caseErrInvalid");
  assert.equal(caseActionErrorKey(new FakeApiError(400)), "caseErrInvalid");
  assert.equal(caseActionErrorKey(new FakeApiError(500)), "caseErrGeneric");
  assert.equal(caseActionErrorKey(new TypeError("Failed to fetch")), "caseErrNetwork");
  assert.equal(caseActionErrorKey(new FakeApiError(0)), "caseErrNetwork");
  assert.equal(caseActionErrorKey("weird"), "caseErrGeneric");
});

test("runCaseAction reports ok / failure without throwing", async () => {
  const calls: string[] = [];
  const ok = await runCaseAction(async (url) => { calls.push(url); return { status: "resolved" }; }, "c1", "done");
  assert.deepEqual(ok, { ok: true, status: "resolved" });
  assert.deepEqual(calls, ["/api/hms/cases/c1/user-action"]);
  const bad = await runCaseAction(async () => { throw new FakeApiError(423); }, "c1", "done");
  assert.deepEqual(bad, { ok: false, key: "caseErrLocked", status: 423 });
});

test("snooze presets", () => {
  const now = new Date(2026, 9, 2, 16, 30, 0);
  assert.equal(snoozeUntil(1, now).getTime(), now.getTime() + 36e5);
  const tomorrow = snoozeUntil(15, now);
  assert.deepEqual([tomorrow.getDate(), tomorrow.getHours(), tomorrow.getMinutes()], [3, 9, 0]);
  assert.equal(snoozeUntil(72, now).getTime(), now.getTime() + 72 * 36e5);
  assert.equal(isClosedStatus("resolved"), true);
  assert.equal(isClosedStatus("in_progress"), false);
});
