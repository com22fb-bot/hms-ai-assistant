"use client";

import { Loader2, Pencil, Plus, Trash2 } from "lucide-react";
import { FormEvent, useCallback, useEffect, useState } from "react";

import { hmsJson } from "@/lib/hmsApi";

type Expense = {
  id: string;
  servicio: string;
  plan: string;
  monto: number;
  moneda: "USD" | "MXN";
  periodicidad: "mensual" | "anual" | "unico";
  proximo_cobro: string | null;
  notas: string;
  activo: boolean;
};

type ExpensesResponse = {
  expenses: Expense[];
  monthly_usd: number;
  monthly_mxn: number;
  usd_mxn: number;
  upcoming_30d: Array<{ id: string; servicio: string; monto: number; moneda: string; proximo_cobro: string }>;
};

type Draft = Omit<Expense, "id">;

const EMPTY: Draft = {
  servicio: "",
  plan: "",
  monto: 0,
  moneda: "USD",
  periodicidad: "mensual",
  proximo_cobro: null,
  notas: "",
  activo: true,
};

const PERIOD_LABEL = { mensual: "Mensual", anual: "Anual", unico: "Pago único" } as const;

function money(value: number, currency: string): string {
  return new Intl.NumberFormat("es-MX", { style: "currency", currency }).format(value || 0);
}

function day(value: string | null): string {
  if (!value) return "—";
  return new Date(`${value}T12:00:00`).toLocaleDateString("es-MX", { day: "numeric", month: "short", year: "numeric" });
}

export function ExpensesPanel() {
  const [data, setData] = useState<ExpensesResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState<string | "new" | null>(null);
  const [draft, setDraft] = useState<Draft>(EMPTY);
  const [fx, setFx] = useState("");

  const load = useCallback(async () => {
    try {
      const result = await hmsJson<ExpensesResponse>("/api/hms/admin/expenses", { cache: "no-store" });
      setData(result);
      setFx(String(result.usd_mxn));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "No fue posible cargar los gastos.");
    }
  }, []);

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => void load());
    return () => window.cancelAnimationFrame(frame);
  }, [load]);

  function startEdit(expense?: Expense) {
    setError(null);
    if (expense) {
      const { id, ...rest } = expense;
      setEditing(id);
      setDraft({ ...rest, monto: Number(rest.monto) });
    } else {
      setEditing("new");
      setDraft(EMPTY);
    }
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const body = JSON.stringify({ ...draft, proximo_cobro: draft.proximo_cobro || null });
      if (editing === "new") {
        await hmsJson("/api/hms/admin/expenses", { method: "POST", headers: { "Content-Type": "application/json" }, body });
      } else if (editing) {
        await hmsJson(`/api/hms/admin/expenses/${editing}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body });
      }
      setEditing(null);
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "No se pudo guardar.");
    } finally {
      setSaving(false);
    }
  }

  async function remove(expense: Expense) {
    if (!window.confirm(`¿Borrar el gasto "${expense.servicio}"? Si solo dejó de cobrarse, mejor márcalo como inactivo.`)) return;
    setSaving(true);
    try {
      await hmsJson(`/api/hms/admin/expenses/${expense.id}`, { method: "DELETE" });
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "No se pudo borrar.");
    } finally {
      setSaving(false);
    }
  }

  async function saveFx(event: FormEvent) {
    event.preventDefault();
    const value = Number(fx);
    if (!value || value <= 0) return;
    setSaving(true);
    try {
      await hmsJson("/api/hms/admin/expenses-settings", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ usd_mxn: value }) });
      await load();
    } finally {
      setSaving(false);
    }
  }

  if (!data) {
    return (
      <section className="dx-admin__section">
        {error ? <p className="dx-admin__alert">{error}</p> : <p className="dx-admin__loading"><Loader2 className="dx-admin__spin" size={18} /> Cargando gastos…</p>}
      </section>
    );
  }

  return (
    <section className="dx-admin__section dx-perf">
      <header className="dx-perf__head">
        <div>
          <h2>Mis gastos</h2>
          <p>Lo que pagas para que Donexto funcione.</p>
        </div>
        <button type="button" className="dx-admin__btn" onClick={() => startEdit()} disabled={saving}>
          <Plus size={16} /> Agregar gasto
        </button>
      </header>
      {error && <p className="dx-admin__alert">{error}</p>}

      <div className="dx-perf__kpis dx-perf__kpis--big">
        <div><span>Total al mes</span><strong>{money(data.monthly_usd, "USD")}</strong></div>
        <div><span>En pesos</span><strong>{money(data.monthly_mxn, "MXN")}</strong></div>
        <div>
          <span>Tipo de cambio</span>
          <form onSubmit={saveFx} className="dx-perf__fx">
            <input value={fx} onChange={(e) => setFx(e.target.value)} inputMode="decimal" aria-label="Pesos por dólar" />
            <button type="submit" className="dx-admin__btn dx-admin__btn--ghost" disabled={saving}>Guardar</button>
          </form>
        </div>
        <div>
          <span>Próximos 30 días</span>
          <strong>{data.upcoming_30d.length === 0 ? "Sin cobros" : `${data.upcoming_30d.length} cobro(s)`}</strong>
        </div>
      </div>
      {data.upcoming_30d.length > 0 && (
        <ul className="dx-perf__upcoming">
          {data.upcoming_30d.map((item) => (
            <li key={item.id}><strong>{day(item.proximo_cobro)}</strong> {item.servicio} · {money(Number(item.monto), item.moneda)}</li>
          ))}
        </ul>
      )}

      {editing && (
        <form className="dx-admin__form dx-perf__editor" onSubmit={save}>
          <label>Servicio<input required value={draft.servicio} onChange={(e) => setDraft({ ...draft, servicio: e.target.value })} /></label>
          <label>Plan<input value={draft.plan} onChange={(e) => setDraft({ ...draft, plan: e.target.value })} /></label>
          <label>Monto<input type="number" min={0} step="0.01" value={draft.monto} onChange={(e) => setDraft({ ...draft, monto: Number(e.target.value) })} /></label>
          <label>Moneda
            <select value={draft.moneda} onChange={(e) => setDraft({ ...draft, moneda: e.target.value as Draft["moneda"] })}>
              <option value="USD">USD</option><option value="MXN">MXN</option>
            </select>
          </label>
          <label>Periodicidad
            <select value={draft.periodicidad} onChange={(e) => setDraft({ ...draft, periodicidad: e.target.value as Draft["periodicidad"] })}>
              <option value="mensual">Mensual</option><option value="anual">Anual</option><option value="unico">Pago único</option>
            </select>
          </label>
          <label>Próximo cobro<input type="date" value={draft.proximo_cobro || ""} onChange={(e) => setDraft({ ...draft, proximo_cobro: e.target.value || null })} /></label>
          <label className="dx-admin__full">Notas<input value={draft.notas} onChange={(e) => setDraft({ ...draft, notas: e.target.value })} /></label>
          <label className="dx-perf__check"><input type="checkbox" checked={draft.activo} onChange={(e) => setDraft({ ...draft, activo: e.target.checked })} /> Activo</label>
          <div className="dx-perf__editor-actions">
            <button type="button" className="dx-admin__btn dx-admin__btn--ghost" onClick={() => setEditing(null)}>Cancelar</button>
            <button type="submit" className="dx-admin__btn" disabled={saving}>{saving ? "Guardando…" : "Guardar"}</button>
          </div>
        </form>
      )}

      <div className="dx-admin__table-wrap">
        <table className="dx-admin__table dx-perf__table">
          <thead>
            <tr><th>Servicio</th><th>Plan</th><th>Monto</th><th>Periodo</th><th>Próximo cobro</th><th>Notas</th><th /></tr>
          </thead>
          <tbody>
            {data.expenses.map((e) => (
              <tr key={e.id} className={e.activo ? "" : "is-inactive"}>
                <td><strong>{e.servicio}</strong>{!e.activo && <span className="dx-admin__pill">inactivo</span>}</td>
                <td>{e.plan || "—"}</td>
                <td>{money(Number(e.monto), e.moneda)}</td>
                <td>{PERIOD_LABEL[e.periodicidad]}</td>
                <td>{day(e.proximo_cobro)}</td>
                <td className="dx-perf__notes" title={e.notas}>{e.notas || "—"}</td>
                <td className="dx-perf__actions">
                  <button type="button" aria-label={`Editar ${e.servicio}`} onClick={() => startEdit(e)}><Pencil size={15} /></button>
                  <button type="button" aria-label={`Borrar ${e.servicio}`} onClick={() => void remove(e)}><Trash2 size={15} /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
