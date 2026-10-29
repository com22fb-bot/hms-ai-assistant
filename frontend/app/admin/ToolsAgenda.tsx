"use client";

import { Loader2 } from "lucide-react";
import { useEffect, useState } from "react";

import { hmsJson } from "@/lib/hmsApi";

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

const COLOR: Record<Sev, string> = { low: "#14804a", medium: "#b54708", critical: "#b42318" };
const LABEL: Record<Sev, string> = { low: "Verde", medium: "Amarillo", critical: "Rojo" };
const PERIOD: Record<string, string> = { mensual: "/mes", anual: "/año", unico: " único" };
const fmt = (n: number) => n.toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function Dot({ sev }: { sev: Sev }) {
  return <span aria-label={LABEL[sev]} title={LABEL[sev]} style={{ display: "inline-block", width: 10, height: 10, borderRadius: 999, background: COLOR[sev], flex: "none" }} />;
}

function Bar({ pct, sev }: { pct: number; sev: Sev }) {
  return (
    <span style={{ display: "inline-block", width: 90, height: 6, borderRadius: 3, background: "#e4e9f2", verticalAlign: "middle" }}>
      <span style={{ display: "block", width: `${Math.max(3, Math.min(100, pct))}%`, height: 6, borderRadius: 3, background: COLOR[sev] }} />
    </span>
  );
}

const card: React.CSSProperties = { background: "#fff", border: "1px solid #e4e9f2", borderRadius: 16, padding: 20, flex: "1 1 200px" };
const muted: React.CSSProperties = { color: "#667085", fontSize: 12 };
const pill: React.CSSProperties = { display: "inline-block", padding: "3px 10px", borderRadius: 999, background: "#2457d622", color: "#2457d6", fontSize: 11, fontWeight: 600 };

export function ToolsAgenda() {
  const [data, setData] = useState<Agenda | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    hmsJson<Agenda>("/api/hms/admin/tools-agenda", { cache: "no-store" }).then(setData).catch((e: unknown) => setError(e instanceof Error ? e.message : "Error"));
  }, []);
  if (error) return <section className="admin-card"><p style={muted}>Agenda de herramientas no disponible: {error}</p></section>;
  if (!data) return <section className="admin-card"><Loader2 className="spin" size={16} /> Cargando agenda…</section>;
  const pending = data.rows.filter((r) => r.cost.estimated || /por confirmar/i.test(r.limits)).length;
  const topUse = data.rows.flatMap((r) => r.usage.map((u) => ({ ...u, tool: r.name }))).filter((u) => u.pct != null).sort((a, b) => (b.pct ?? 0) - (a.pct ?? 0))[0];
  return (
    <section aria-label="Agenda de herramientas" style={{ display: "grid", gap: 16, marginBottom: 24 }}>
      <header>
        <h2 style={{ margin: 0, fontSize: 22 }}>Agenda de herramientas</h2>
        <p style={{ ...muted, fontSize: 13, margin: "4px 0 0" }}>
          Plan, límites, uso real y vencimientos · {data.fx.source} {data.fx.date}: {fmt(data.fx.usd_mxn)} MXN/US$
        </p>
      </header>
      <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
        <div style={card}><div style={muted}>Gasto fijo mensual</div><div style={{ fontSize: 24, fontWeight: 700 }}>US${fmt(data.monthly_fixed.usd)}</div><div style={muted}>TC {fmt(data.monthly_fixed.fx)} · MXN {fmt(data.monthly_fixed.mxn)}</div></div>
        <div style={card}><div style={muted}>Próximo vencimiento</div>
          <div style={{ fontSize: 24, fontWeight: 700, color: data.next_due ? COLOR[data.next_due.severity] : undefined }}>{data.next_due ? `${data.next_due.tool} · ${data.next_due.on}` : "—"}</div>
          <div style={muted}>{data.next_due ? `${data.next_due.days} días · ${LABEL[data.next_due.severity]}` : ""}</div></div>
        <div style={card}><div style={muted}>Uso más alto</div>
          <div style={{ fontSize: 24, fontWeight: 700, color: topUse?.severity ? COLOR[topUse.severity] : undefined }}>{topUse ? `${topUse.tool} ${topUse.label} ${topUse.pct}%` : "n/d"}</div>
          <div style={muted}>Estado general: {LABEL[data.status]}</div></div>
        <div style={card}><div style={muted}>Por confirmar</div><div style={{ fontSize: 24, fontWeight: 700, color: pending ? COLOR.medium : undefined }}>{pending}</div><div style={muted}>Montos estimados o datos pendientes</div></div>
      </div>
      <div style={{ background: "#fff", border: "1px solid #e4e9f2", borderRadius: 16, overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead><tr style={{ background: "#f8faff", textAlign: "left" }}>
            {["Herramienta", "Plan", "Límites", "Uso real", "Costo (US$ · TC · MXN)", "Renovación / vencimiento"].map((h) => <th key={h} style={{ padding: "12px 16px", ...muted, fontWeight: 600 }}>{h}</th>)}
          </tr></thead>
          <tbody>
            {data.rows.map((r) => (
              <tr key={r.id} style={{ borderTop: "1px solid #e4e9f2", verticalAlign: "top" }}>
                <td style={{ padding: "12px 16px", fontWeight: 600 }}><span style={{ display: "inline-flex", gap: 8, alignItems: "center" }}><Dot sev={r.severity} />{r.name}</span></td>
                <td style={{ padding: "12px 16px" }}><span style={pill}>{r.plan}</span></td>
                <td style={{ padding: "12px 16px", ...muted, maxWidth: 280 }}>{r.limits}</td>
                <td style={{ padding: "12px 16px" }}>
                  {r.usage.length === 0 ? <span style={muted}>n/d</span> : r.usage.map((u) => (
                    <div key={u.label} style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 4 }}>
                      <span style={{ ...muted, width: 60 }}>{u.label}</span>
                      {u.pct != null && u.severity ? <><Bar pct={u.pct} sev={u.severity} /><b style={{ color: COLOR[u.severity], fontSize: 12 }}>{u.pct}%</b></> : null}
                      <span style={muted}>{u.used ?? "—"}/{u.limit ?? "—"} {u.unit}</span>
                    </div>
                  ))}
                </td>
                <td style={{ padding: "12px 16px" }} title={r.cost.note ?? undefined}>
                  {r.cost.estimated ? "~" : ""}US${fmt(r.cost.usd)}{PERIOD[r.cost.period] ?? ""}
                  <div style={muted}>TC {fmt(r.cost.fx)} ({r.cost.fx_date}) · MXN {fmt(r.cost.mxn)}{r.cost.estimated ? " · por confirmar" : ""}</div>
                </td>
                <td style={{ padding: "12px 16px" }}>
                  {r.dates.length === 0 ? <span style={muted}>—</span> : r.dates.map((d) => (
                    <div key={d.label} style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 4 }}>
                      <Dot sev={d.severity} /><span>{d.label}: {d.estimated ? "~" : ""}{d.on}</span><span style={muted}>{d.days < 0 ? `vencido hace ${-d.days} d` : `${d.days} d`}</span>
                    </div>
                  ))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p style={muted}>Verde: más de 7 días y uso &lt;70% · Amarillo: ≤7 días o uso ≥70% · Rojo: vencido o uso ≥90%. Se verifica a diario en el checklist del respaldo.</p>
    </section>
  );
}
