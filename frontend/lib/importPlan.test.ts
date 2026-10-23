import { test } from "node:test";
import assert from "node:assert/strict";
import { downloadPlan } from "./importPlan.ts";

// Mismo agregado que produce el backend con el fixture de tests/test_import_download_plan.py.
const P = {
  areas: { trabajo: 0, hogar: 3, dinero: 12, compras: 6, salud: 4, viajes: 0, promociones: 6 },
  review: 10,
  area_protected: { dinero: { bancos: 4, facturas: 8 }, revisar: { seguridad: 4 }, salud: { salud: 4 } },
};

test("sin exclusiones: todo seleccionado", () => {
  assert.deepEqual(downloadPlan(P, []), { selected: 41, protected: 0, excluded: 0, to_process: 41, total: 41 });
});
test("área desmarcada con protegidos: se descargan igual y no se cuentan dos veces", () => {
  assert.deepEqual(downloadPlan(P, ["dinero"]), { selected: 29, protected: 12, excluded: 0, to_process: 41, total: 41 });
});
test("protección apagada: esos mensajes pasan a excluidos", () => {
  assert.deepEqual(downloadPlan(P, ["dinero", "proteger:facturas"]), { selected: 29, protected: 4, excluded: 8, to_process: 33, total: 41 });
});
test("Por revisar desmarcado conserva Seguridad", () => {
  assert.deepEqual(downloadPlan(P, ["revisar", "promociones"]), { selected: 25, protected: 4, excluded: 12, to_process: 29, total: 41 });
});
