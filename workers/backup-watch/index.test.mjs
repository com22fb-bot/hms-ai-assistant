import { test } from "node:test";
import assert from "node:assert/strict";
import { run, evaluate } from "./index.js";

const NOW = Date.parse("2026-10-23T15:00:00Z");
const bucket = (objs, fail) => ({ list: async ({ cursor }) => {
  if (fail) throw new TypeError("r2");
  if (!cursor && objs.length > 1) return { objects: objs.slice(0, 1), truncated: true, cursor: "c" };
  return { objects: cursor ? objs.slice(1) : objs, truncated: false };
} });
const o = (key, iso) => ({ key, uploaded: new Date(iso) });
const sender = ({ slackOk = true, resendOk = true } = {}) => {
  const calls = [];
  return { calls, fetchImpl: async (u) => {
    calls.push(u);
    if (u.includes("slack")) { if (slackOk === "net") throw new TypeError("net"); return { status: 200, json: async () => ({ ok: slackOk }) }; }
    return { status: resendOk ? 200 : 503 };
  } };
};
const base = { MAX_AGE_HOURS: "30", SLACK_BOT_TOKEN: "fixture", RESEND_API_KEY: "fixture", ALERT_TO: "x@example.com", ALERT_FROM: "m@example.com" };

test("fresco (paginado): no avisa", async () => {
  const s = sender();
  const r = await run({ ...base, BACKUPS: bucket([o("db/a", "2026-10-22T14:27:00Z"), o("db/b", "2026-10-23T12:05:00Z")]) }, { now: NOW, ...s });
  assert.equal(r.ok, true); assert.equal(r.key, "db/b"); assert.equal(s.calls.length, 0);
});
test("viejo: avisa por Slack y Resend", async () => {
  const s = sender();
  const r = await run({ ...base, BACKUPS: bucket([o("db/a", "2026-10-21T14:00:00Z")]) }, { now: NOW, ...s });
  assert.equal(r.ok, false); assert.equal(r.sent, 2); assert.equal(s.calls.length, 2);
});
test("sin respaldos: avisa", async () => {
  const s = sender(); const r = await run({ ...base, BACKUPS: bucket([]) }, { now: NOW, ...s });
  assert.match(r.reason, /no hay respaldos/); assert.equal(r.sent, 2);
});
test("R2 ilegible: avisa", async () => {
  const r = await evaluate({ ...base, BACKUPS: bucket([], true) }, NOW); assert.equal(r.ok, false); assert.match(r.reason, /R2/);
});
test("Slack caído: Resend entrega igual", async () => {
  const s = sender({ slackOk: "net" }); const r = await run({ ...base, BACKUPS: bucket([]) }, { now: NOW, ...s }); assert.equal(r.sent, 1);
});
test("Resend caído: Slack entrega igual", async () => {
  const s = sender({ resendOk: false }); const r = await run({ ...base, BACKUPS: bucket([]) }, { now: NOW, ...s }); assert.equal(r.sent, 1);
});
test("ambos caídos: falla visible (log de Workers)", async () => {
  const s = sender({ slackOk: false, resendOk: false });
  await assert.rejects(run({ ...base, BACKUPS: bucket([]) }, { now: NOW, ...s }), /ningún canal/);
});
