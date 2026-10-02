import assert from "node:assert/strict";
import test from "node:test";

import { isAuthError, jobOutcome, refreshMailbox, type ImportStatusPayload } from "./mailRefresh.ts";

function fakeDeps(statuses: ImportStatusPayload[], startCalls: { n: number }) {
  let index = 0;
  let clock = 0;
  return {
    start: async () => {
      startCalls.n += 1;
      return { job: { id: "job-1", status: "queued" } };
    },
    status: async () => statuses[Math.min(index++, statuses.length - 1)],
    sleep: async (ms: number) => {
      clock += ms;
    },
    now: () => clock,
    pollMs: 1000,
    timeoutMs: 5000,
  };
}

const READY: ImportStatusPayload = { initial_import_complete: true, needs_initial_import: false, phase: "ready", active: null, latest: { id: "old", status: "completed" } };

test("mail refresh: starts an incremental import and reports how many emails arrived", async () => {
  const calls = { n: 0 };
  const progress: number[] = [];
  const result = await refreshMailbox({
    ...fakeDeps([
      READY,
      { initial_import_complete: true, phase: "downloading", active: { id: "job-1", status: "running", messages_inserted: 3 }, progress: { downloaded: 3 } },
      { initial_import_complete: true, phase: "ready", active: null, latest: { id: "job-1", status: "completed", messages_inserted: 7, created_cases: 2 } },
    ], calls),
    onProgress: (count) => progress.push(count),
  });
  assert.deepEqual(result, { ok: true, inserted: 7, createdCases: 2 });
  assert.equal(calls.n, 1);
  assert.deepEqual(progress.slice(0, 1), [3]);
});

test("mail refresh: a revoked Google permission asks to reconnect", async () => {
  const calls = { n: 0 };
  const result = await refreshMailbox(fakeDeps([
    READY,
    { initial_import_complete: true, phase: "failed", active: null, latest: { id: "job-1", status: "failed", last_error: "('invalid_grant: Token has been expired or revoked.', {})" } },
  ], calls));
  assert.equal(result.ok, false);
  assert.equal(result.ok === false && result.reason, "auth");
});

test("mail refresh: before the first import it opens the guided import instead", async () => {
  const calls = { n: 0 };
  const result = await refreshMailbox(fakeDeps([{ initial_import_complete: false, needs_initial_import: true }], calls));
  assert.deepEqual(result, { ok: false, reason: "initial", message: "" });
  assert.equal(calls.n, 0);
});

test("mail refresh: long downloads end in a background notice, not an error", async () => {
  const calls = { n: 0 };
  const result = await refreshMailbox(fakeDeps([
    READY,
    { initial_import_complete: true, phase: "downloading", active: { id: "job-1", status: "running" } },
  ], calls));
  assert.deepEqual(result, { ok: false, reason: "timeout", message: "" });
});

test("mail refresh: outcome helpers", () => {
  assert.equal(jobOutcome({ active: { id: "x", status: "interrupted" } }), null);
  assert.equal(jobOutcome({ active: null, latest: { status: "running" } }), null);
  assert.deepEqual(jobOutcome({ active: null, latest: { status: "completed", messages_inserted: 0 } }), { ok: true, inserted: 0, createdCases: 0 });
  assert.equal(isAuthError("invalid_grant: Bad Request"), true);
  assert.equal(isAuthError("HttpError 503"), false);
});
