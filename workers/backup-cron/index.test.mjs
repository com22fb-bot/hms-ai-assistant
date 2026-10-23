import { test } from "node:test";
import assert from "node:assert/strict";
import worker, { dispatch, workflowsFor } from "./index.js";

const env = { GH_DISPATCH_TOKEN: "fixture-not-real" };
const fake = (codes) => { const calls = []; return { calls, fetchImpl: async (u, o) => { calls.push(u); const c = codes.shift(); if (c === "net") throw new TypeError("x"); return { status: c }; } }; };
const sleep = async () => {};

test("diario lunes a sábado, diario+semanal domingo (09:00 UTC)", () => {
  assert.deepEqual(workflowsFor(Date.parse("2026-10-22T09:00:00Z")), ["backup-daily.yml"]);
  assert.deepEqual(workflowsFor(Date.parse("2026-10-25T09:00:00Z")), ["backup-daily.yml", "backup-weekly.yml"]);
});
test("204 = una sola llamada", async () => { const f = fake([204]); assert.equal(await dispatch(env, "backup-daily.yml", { ...f, sleep }), true); assert.equal(f.calls.length, 1); });
test("reintenta 5xx y red, luego éxito", async () => { const f = fake([502, "net", 204]); await dispatch(env, "w", { ...f, sleep }); assert.equal(f.calls.length, 3); });
test("403 no reintenta y falla visible", async () => { const f = fake([403]); await assert.rejects(dispatch(env, "w", { ...f, sleep }), /HTTP 403/); assert.equal(f.calls.length, 1); });
test("429 reintenta; agota intentos y falla", async () => { const f = fake([429, 500, 503]); await assert.rejects(dispatch(env, "w", { ...f, sleep }), /HTTP 503/); assert.equal(f.calls.length, 3); });
test("sin secreto falla", async () => { await assert.rejects(worker.scheduled({ scheduledTime: Date.now() }, {}), /GH_DISPATCH_TOKEN/); });
