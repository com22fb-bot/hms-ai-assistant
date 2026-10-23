import { test } from "node:test";
import assert from "node:assert/strict";
import { closePatch, estadoOf, isPedido, matchesEstado, sinTerminar, type EstadoEvent } from "./bitacoraEstado.ts";

const NOW = "2026-10-23T22:00:00.000Z";
// "Recargar": la fila que devolvería la BD tras aplicar el update.
const reload = (e: EstadoEvent): EstadoEvent => JSON.parse(JSON.stringify({ ...e, ...closePatch(e, NOW) }));
const pedido = (estado: "pendiente" | "en_curso" | "hecho", status: "abierto" | "resuelto" = "abierto"): EstadoEvent => ({
  status, ended_at: null, meta: { kind: "pedido", estado, historial: [{ estado, at: "2026-10-23T20:00:00.000Z" }] },
});

test("en curso → Cerrar → Realizado tras recargar", () => {
  const r = reload(pedido("en_curso"));
  assert.equal(r.status, "resuelto");
  assert.equal(r.ended_at, NOW);
  assert.equal(estadoOf(r), "hecho");
  assert.deepEqual(r.meta?.historial?.map((h) => h.estado), ["en_curso", "hecho"]);
});

test("pendiente → Cerrar → Realizado tras recargar", () => {
  const r = reload(pedido("pendiente"));
  assert.equal(estadoOf(r), "hecho");
  assert.equal(r.meta?.kind, "pedido");
});

test("contador de sin terminar disminuye", () => {
  const rows = [pedido("pendiente"), pedido("en_curso"), pedido("hecho", "resuelto")];
  const count = (xs: EstadoEvent[]) => xs.filter(isPedido).filter(sinTerminar).length;
  assert.equal(count(rows), 2);
  rows[1] = reload(rows[1]);
  assert.equal(count(rows), 1);
  rows[0] = reload(rows[0]);
  assert.equal(count(rows), 0);
});

test("historial sin duplicados al cerrar algo ya hecho o cerrar dos veces", () => {
  const once = reload(pedido("en_curso"));
  const twice = reload(once);
  assert.deepEqual(twice.meta?.historial, once.meta?.historial);
  assert.equal(twice.ended_at, NOW);
  const yaHecho = reload(pedido("hecho"));
  assert.equal(yaHecho.meta?.historial?.length, 1);
});

test("pedido sin historial previo crea uno", () => {
  const r = reload({ status: "abierto", meta: { kind: "pedido", estado: "en_curso" } });
  assert.deepEqual(r.meta?.historial, [{ estado: "hecho", at: NOW }]);
});

test("eventos antiguos sin meta.estado conservan comportamiento", () => {
  const legacy: EstadoEvent = { status: "abierto", meta: null };
  assert.equal(estadoOf(legacy), "pendiente");
  const p = closePatch(legacy, NOW);
  assert.deepEqual(p, { status: "resuelto", ended_at: NOW });
  assert.equal(estadoOf(reload(legacy)), "hecho");
  const backup: EstadoEvent = { status: "abierto", meta: { kind: "diario", result: "ok" } };
  assert.equal("meta" in closePatch(backup, NOW), false);
  assert.equal(estadoOf({ status: "resuelto" }), "hecho");
});

test("filtro Estado coincide con el estado mostrado", () => {
  const rows: EstadoEvent[] = [
    pedido("pendiente"), pedido("en_curso"), pedido("hecho", "resuelto"),
    { status: "abierto" }, { status: "resuelto", meta: null },
    // inconsistente heredado: status resuelto pero meta en_curso → se muestra y filtra igual
    { status: "resuelto", meta: { kind: "pedido", estado: "en_curso" } },
  ];
  for (const f of ["pendiente", "en_curso", "hecho"] as const) {
    for (const r of rows) assert.equal(matchesEstado(r, f), estadoOf(r) === f);
  }
  assert.equal(rows.filter((r) => matchesEstado(r, "")).length, rows.length);
});
