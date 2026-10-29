import { test } from "node:test";
import assert from "node:assert/strict";
import worker, { dispatch, workflowsFor } from "./index.js";

const env = { GH_DISPATCH_TOKEN: "fixture-not-real" };
// codes: respuestas para POST /dispatches; runsCount: lo que devuelve GET /runs
const fake = (codes, runsCount = 0) => {
  const posts = [], gets = [];
  return { posts, gets, fetchImpl: async (u, o = {}) => {
    if (o.method === "POST") { posts.push(JSON.parse(o.body)); const c = codes.shift(); if (c === "net") throw new TypeError("x"); return { status: c }; }
    gets.push(u); return { status: 200, json: async () => ({ total_count: typeof runsCount === "function" ? runsCount() : runsCount }) };
  } };
};
const sleep = async () => {};

test("diario lunes a sábado, diario+semanal domingo (09:00 UTC)", () => {
  assert.deepEqual(workflowsFor(Date.parse("2026-10-22T09:00:00Z")), ["backup-daily.yml", "log-journal.yml"]);
  assert.deepEqual(workflowsFor(Date.parse("2026-10-25T09:00:00Z")), ["backup-daily.yml", "log-journal.yml", "backup-weekly.yml"]);
});
test("204 = una sola llamada y envía origen=cf-cron", async () => {
  const f = fake([204]); assert.equal(await dispatch(env, "backup-daily.yml", { ...f, sleep }), true);
  assert.equal(f.posts.length, 1); assert.deepEqual(f.posts[0], { ref: "main", inputs: { origen: "cf-cron" } }); assert.equal(f.gets.length, 0);
});
test("reintenta 5xx y red si GitHub no creó la corrida", async () => { const f = fake([502, "net", 204], 0); await dispatch(env, "w", { ...f, sleep }); assert.equal(f.posts.length, 3); assert.equal(f.gets.length, 2); });
test("respuesta perdida: GitHub ya creó la corrida -> no reintenta (sin duplicado)", async () => {
  const f = fake(["net", 204], 1); assert.equal(await dispatch(env, "w", { ...f, sleep }), true); assert.equal(f.posts.length, 1);
});
test("403 no reintenta y falla visible", async () => { const f = fake([403]); await assert.rejects(dispatch(env, "w", { ...f, sleep }), /HTTP 403/); assert.equal(f.posts.length, 1); });
test("429/5xx agota intentos y falla", async () => { const f = fake([429, 500, 503]); await assert.rejects(dispatch(env, "w", { ...f, sleep }), /HTTP 503/); assert.equal(f.posts.length, 3); });
test("sin secreto falla", async () => { await assert.rejects(worker.scheduled({ scheduledTime: Date.now() }, {}), /GH_DISPATCH_TOKEN/); });
