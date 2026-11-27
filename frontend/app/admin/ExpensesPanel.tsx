"use client";

import { Loader2, Pencil, Plus, Trash2 } from "lucide-react";
import { FormEvent, useCallback, useEffect, useState } from "react";

import { hmsJson } from "@/lib/hmsApi";
import {
  EXPENSES_CHANGED_EVENT, SEVERITY_COLOR, daysPhrase, daysUntil, fmtDate, mxn as mxnText, severityForDays, todayCdmx, usd as usdText,
} from "@/lib/paymentsAgenda";

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

/** Avisa a la agenda de pagos de arriba para que se actualice al instante. */
function notifyAgenda() {
  window.dispatchEvent(new Event(EXPENSES_CHANGED_EVENT));
}

/** US$ y MXN siempre juntos, con el TC de Mis gastos. */
function pair(value: number, currency: string, fx: number): string {
  const amount = Number(value) || 0;
  if (currency === "MXN") return `${usdText(fx ? amount / fx : 0)} · ${mxnText(amount)}`;
  return `${usdText(amount)} · ${mxnText(amount * fx)}`;
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
      notifyAgenda();
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
      notifyAgenda();
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
      notifyAgenda();
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

  const today = todayCdmx();
  const sorted = [...data.expenses].sort((x, y) => {
    if (x.activo !== y.activo) return x.activo ? -1 : 1;
    return (x.proximo_cobro || "9999").localeCompare(y.proximo_cobro || "9999") || x.servicio.localeCompare(y.servicio);
  });

  return (
    <section className="dx-pay dx-pay-ui dx-perf">
      <header className="dx-pay__head">
        <div>
          <p className="dx-pay__eyebrow">Donexto</p>
          <h2>Mis gastos</h2>
          <p>Lo que pagas para que Donexto funcione. Al guardar, la agenda de arriba se actualiza sola.</p>
        </div>
        <button type="button" className="dx-admin__btn" onClick={() => startEdit()} disabled={saving}>
          <Plus size={16} /> Agregar gasto
        </button>
      </header>
      {error && <p className="dx-pay__error" role="alert">{error}</p>}

      <div className="dx-pay-kpis">
        <div><span>Total al mes</span><strong>{usdText(data.monthly_usd)}</strong><small>TC {data.usd_mxn}</small></div>
        <div><span>En pesos</span><strong>{mxnText(data.monthly_mxn)}</strong><small>al mes</small></div>
        <div>
          <span>Tipo de cambio (MXN por US$)</span>
          <form onSubmit={saveFx} className="dx-perf__fx">
            <input value={fx} onChange={(e) => setFx(e.target.value)} inputMode="decimal" aria-label="Pesos por dólar" />
            <button type="submit" className="dx-admin__btn dx-admin__btn--ghost" disabled={saving}>Guardar</button>
          </form>
        </div>
        <div>
          <span>Próximos 30 días</span>
          <strong>{data.upcoming_30d.length === 0 ? "Sin cobros" : `${data.upcoming_30d.length} cobro(s)`}</strong>
          <small>{data.upcoming_30d.map((u) => u.servicio).join(" · ")}</small>
        </div>
      </div>

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

      <div className="dx-pay-cards" data-testid="expenses-cards">
        {sorted.map((e) => {
          const days = e.proximo_cobro ? daysUntil(e.proximo_cobro, today) : null;
          const sev = !e.activo || days === null ? "luego" : severityForDays(days);
          return (
            <article key={e.id} className={e.activo ? "dx-pay__item" : "dx-pay__item is-inactive"} style={{ ["--sev" as string]: SEVERITY_COLOR[sev] }} data-severity={sev}>
              <header>
                <h4><i aria-hidden />{e.servicio}</h4>
                <span className="dx-pay__tools">
                  <button type="button" aria-label={`Editar ${e.servicio}`} onClick={() => startEdit(e)}><Pencil size={14} /></button>
                  <button type="button" aria-label={`Borrar ${e.servicio}`} onClick={() => void remove(e)}><Trash2 size={14} /></button>
                </span>
              </header>
              <p className="dx-pay__meta">
                {[e.plan || null, PERIOD_LABEL[e.periodicidad], e.activo ? null : "inactivo"].filter(Boolean).join(" · ")}
              </p>
              <p className="dx-pay__amount">
                <strong>{e.moneda === "MXN" ? usdText(data.usd_mxn ? Number(e.monto) / data.usd_mxn : 0) : usdText(Number(e.monto))}</strong>
                <span>{e.moneda === "MXN" ? mxnText(Number(e.monto)) : mxnText(Number(e.monto) * data.usd_mxn)}</span>
              </p>
              <p className="dx-pay__action" title={pair(Number(e.monto), e.moneda, data.usd_mxn)}>
                {e.proximo_cobro ? (
                  <>Próximo cobro: <b>{fmtDate(e.proximo_cobro)}</b>{e.activo && days !== null ? <span style={{ color: SEVERITY_COLOR[sev] }}> · {daysPhrase(days)}</span> : null}</>
                ) : "Sin próximo cobro"}
              </p>
              {e.notas && <p className="dx-pay__limits" title={e.notas}>{e.notas}</p>}
            </article>
          );
        })}
      </div>
    </section>
  );
}
