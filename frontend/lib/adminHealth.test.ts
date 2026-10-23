import { test } from "node:test";
import assert from "node:assert/strict";
import { lightState, type HealthPayload } from "./adminHealth.ts";

const base = (state: "VERDE" | "AMARILLO" | "ROJO", at: string): HealthPayload => ({
  overall: { state, reason: "r" }, evaluated_at: at, cache_age_s: 0, stale_after_s: 180,
  recovery_policy: "", checks: [], incidents: [],
});
const NOW = Date.parse("2026-10-23T18:00:00Z");

test("carga inicial = VERIFICANDO", () => assert.equal(lightState(null, false, NOW).state, "VERIFICANDO"));
test("sin respuesta nunca es verde", () => assert.equal(lightState(null, true, NOW).state, "AMARILLO"));
test("verde fresco = VERDE", () => assert.equal(lightState(base("VERDE", "2026-10-23T17:59:00Z"), false, NOW).state, "VERDE"));
test("verde vencido (>180 s) no es verde", () => assert.equal(lightState(base("VERDE", "2026-10-23T17:50:00Z"), false, NOW).state, "AMARILLO"));
test("rojo vencido sigue rojo", () => assert.equal(lightState(base("ROJO", "2026-10-23T17:00:00Z"), false, NOW).state, "ROJO"));
test("refresco fallido con verde previo => amarillo", () => assert.equal(lightState(base("VERDE", "2026-10-23T17:59:30Z"), true, NOW).state, "AMARILLO"));
