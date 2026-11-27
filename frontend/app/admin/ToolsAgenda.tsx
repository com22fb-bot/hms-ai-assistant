"use client";

import { Loader2 } from "lucide-react";
import { useEffect, useState } from "react";

import { hmsJson } from "@/lib/hmsApi";
import { SEVERITY_COLOR, daysPhrase, fmtDate, fmtDateShort, severityForDays, type PaySeverity } from "@/lib/paymentsAgenda";

type Sev = "low" | "medium" | "critical";
type Usage = { label: string; used: number | null; limit: number | null; unit: string; pct: number | null; severity: Sev | null };
type Due = { label: string; on: string; kind: string; estimated: boolean; severity: Sev; days: number; tool?: string };
type Row = {
  id: string; name: string; plan: string; limits: string; usage: Usage[]; dates: Due[]; severity: Sev;
  cost: { usd: number; fx: number; fx_date: string; fx_source: string; mxn: number; period: string; estimated: boolean; note?: string | null };
};
type Agenda = {
  today: string; fx: { usd_mxn: number; date: string; source: string };
  monthly_fixed: { usd: number; fx: number; mxn: number }; next_due: Due | null; status: Sev;
  alerts: Array<{ tool: string; severity: Sev }>; rows: Row[];
};

const USAGE_SEV: Record<Sev, PaySeverity> = { low: "verde", medium: "naranja", critical: "rojo" };
const RANK: Record<PaySeverity, number> = { luego: 0, verde: 1, naranja: 2, rojo: 3 };
const PERIOD: Record<string, string> = { mensual: "/mes", anual: "/año", unico: " único" };
const fmt = (n: number) => n.toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function toolSeverity(r: Row): PaySeverity {
  const sevs: PaySeverity[] = [
    ...r.dates.map((d) => severityForDays(d.days)),
    ...r.usage.filter((u) => u.severity).map((u) => USAGE_SEV[u.severity as Sev]),
  ];
  if (sevs.length === 0) return "luego";
  return sevs.reduce((a, b) => (RANK[b] > RANK[a] ? b : a));
}

export function ToolsAgenda() {
  const [data, setData] = useState<Agenda | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    hmsJson<Agenda>("/api/hms/admin/tools-agenda", { cache: "no-store" }).then(setData).catch((e: unknown) => setError(e instanceof Error ? e.message : "Error"));
  }, []);
  if (error) return <section className="dx-pay dx-pay-ui"><p className="dx-pay__muted">Agenda de herramientas no disponible: {error}</p></section>;
  if (!data) return <section className="dx-pay dx-pay-ui"><p className="dx-pay__muted"><Loader2 className="dx-admin__spin" size={16} /> Cargando agenda…</p></section>;
  const pending = data.rows.filter((r) => r.cost.estimated || /por confirmar/i.test(r.limits)).length;
  const topUse = data.rows.flatMap((r) => r.usage.map((u) => ({ ...u, tool: r.name }))).filter((u) => u.pct != null).sort((a, b) => (b.pct ?? 0) - (a.pct ?? 0))[0];
  const next = data.next_due;
  const nextSev = next ? severityForDays(next.days) : "luego";
  const rows = [...data.rows].sort((a, b) => RANK[toolSeverity(b)] - RANK[toolSeverity(a)]);
  return (
    <section aria-label="Agenda de herramientas" className="dx-pay dx-pay-ui">
      <header className="dx-pay__head">
        <div>
          <p className="dx-pay__eyebrow">Donexto</p>
          <h2>Agenda de herramientas</h2>
          <p>Plan, límites, uso real y vencimientos · TC {data.fx.usd_mxn} ({data.fx.source}, {fmtDate(data.fx.date)})</p>
        </div>
      </header>
      <div className="dx-pay-kpis">
        <div><span>Gasto fijo mensual</span><strong>US${fmt(data.monthly_fixed.usd)}</strong><small>MXN {fmt(data.monthly_fixed.mxn)} · TC {data.monthly_fixed.fx}</small></div>
        <div style={{ ["--sev" as string]: SEVERITY_COLOR[nextSev] }}><span>Próximo vencimiento</span>
          <strong style={{ color: next ? SEVERITY_COLOR[nextSev] : undefined }}>{next ? `${next.tool} · ${fmtDateShort(next.on)}` : "—"}</strong>
          <small>{next ? daysPhrase(next.days) : ""}</small></div>
        <div><span>Uso más alto</span>
          <strong style={{ color: topUse?.severity ? SEVERITY_COLOR[USAGE_SEV[topUse.severity]] : undefined }}>{topUse ? `${topUse.pct}%` : "n/d"}</strong>
          <small>{topUse ? `${topUse.tool} · ${topUse.label}` : "Sin métricas"}</small></div>
        <div><span>Por confirmar</span><strong style={{ color: pending ? SEVERITY_COLOR.naranja : undefined }}>{pending}</strong><small>Montos estimados o datos pendientes</small></div>
      </div>
      <div className="dx-pay-cards">
        {rows.map((r) => {
          const sev = toolSeverity(r);
          return (
            <article key={r.id} className="dx-pay__item" style={{ ["--sev" as string]: SEVERITY_COLOR[sev] }} data-severity={sev}>
              <header>
                <h4><i aria-hidden />{r.name}</h4>
                <span className="dx-pay__pill">{r.plan}</span>
              </header>
              <p className="dx-pay__amount" title={r.cost.note ?? undefined}>
                <strong>{r.cost.estimated ? "~" : ""}US${fmt(r.cost.usd)}<small className="dx-pay__muted">{PERIOD[r.cost.period] ?? ""}</small></strong>
                <span>MXN {fmt(r.cost.mxn)}{r.cost.estimated ? " · por confirmar" : ""}</span>
              </p>
              {r.usage.length > 0 && (
                <div className="dx-pay__usage">
                  {r.usage.map((u) => {
                    const us = u.severity ? USAGE_SEV[u.severity] : "luego";
                    return (
                      <div key={u.label} style={{ ["--sev" as string]: SEVERITY_COLOR[us] }}>
                        <span>{u.label}</span>
                        <span className="dx-pay__bar"><i style={{ width: `${Math.max(3, Math.min(100, u.pct ?? 0))}%` }} /></span>
                        <span>{u.pct != null ? `${u.pct}%` : "—"} · {u.used ?? "—"}/{u.limit ?? "—"} {u.unit}</span>
                      </div>
                    );
                  })}
                </div>
              )}
              {r.dates.length > 0 && (
                <ul className="dx-pay__dates">
                  {r.dates.map((d) => (
                    <li key={d.label}>
                      <i style={{ background: SEVERITY_COLOR[severityForDays(d.days)] }} aria-hidden />
                      <span>{d.label}: {d.estimated ? "~" : ""}{fmtDate(d.on)}</span>
                      <em>{daysPhrase(d.days)}</em>
                    </li>
                  ))}
                </ul>
              )}
              <p className="dx-pay__limits">{r.limits}</p>
            </article>
          );
        })}
      </div>
      <p className="dx-pay__foot">🔴 vencido o ≤3 días / uso ≥90 % · 🟠 4–14 días / uso ≥70 % · 🟢 15–60 días · ⚪ sin fecha. Se verifica a diario en el checklist del respaldo.</p>
    </section>
  );
}
