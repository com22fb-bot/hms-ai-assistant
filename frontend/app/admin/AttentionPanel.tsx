"use client";

import { Loader2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { hmsJson } from "@/lib/hmsApi";

type Metric = {
  value: number | null;
  status: "real" | "pendiente_instrumentacion" | "error_consulta";
  source: string;
  note: string;
};

type AttentionItem = {
  id: string;
  severity: "critical" | "high" | "medium" | "low" | "info";
  category: string;
  title: string;
  detail: string;
  action: string;
  owner: string;
  due_at: string | null;
  source: string;
};

type AttentionResponse = {
  generated_at: string;
  items: AttentionItem[];
  commercial: Record<string, Metric>;
};

const SEVERITY_LABEL: Record<AttentionItem["severity"], string> = {
  critical: "Crítico",
  high: "Alto",
  medium: "Medio",
  low: "Bajo",
  info: "Decisión",
};

const COMMERCIAL_LABELS: Array<[string, string, boolean?]> = [
  ["users", "Usuarios"],
  ["mailboxes_active", "Buzones conectados"],
  ["mailboxes_needs_reauth", "Buzones por reconectar"],
  ["trials_active", "Pruebas activas"],
  ["subscriptions_active", "Suscripciones activas"],
  ["mrr_cents", "MRR", true],
  ["arr_cents", "ARR", true],
  ["payments_confirmed", "Pagos confirmados"],
  ["conversion_funnel", "Embudo de conversión"],
  ["feedback_open", "Quejas e ideas abiertas"],
  ["signed_up_no_product_use_24h", "Sin uso en 24 h"],
];

export function metricText(metric: Metric | undefined, money = false): string {
  if (!metric) return "Sin datos";
  if (metric.status === "pendiente_instrumentacion") return "Pendiente de instrumentación";
  if (metric.status === "error_consulta" || metric.value === null) return "Error de consulta";
  if (money) {
    return new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }).format(
      metric.value / 100,
    );
  }
  return String(metric.value);
}

export default function AttentionPanel() {
  const [data, setData] = useState<AttentionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setError(null);
      setData(await hmsJson<AttentionResponse>("/api/hms/admin/attention", { cache: "no-store" }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cargar");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (error) {
    return (
      <p className="dx-admin__note" role="alert">
        «Requiere mi atención» no verificado: {error}
      </p>
    );
  }
  if (!data) {
    return (
      <p className="dx-admin__hint">
        <Loader2 size={14} className="dx-spin" aria-hidden /> Verificando pendientes…
      </p>
    );
  }

  const updated = new Date(data.generated_at).toLocaleString("es-MX", {
    timeZone: "America/Mexico_City",
  });

  return (
    <>
      <section className="dx-admin__section" aria-labelledby="dx-attention-title">
        <header className="dx-admin__section-head">
          <h2 id="dx-attention-title">Requiere mi atención</h2>
          <p>Ordenado por severidad. Actualizado {updated} (hora CDMX).</p>
        </header>
        <ul className="dx-admin__list" data-testid="attention-list">
          {data.items.map((item) => (
            <li key={item.id} data-severity={item.severity}>
              <strong>[{SEVERITY_LABEL[item.severity] ?? item.severity}] {item.title}</strong>
              <br />
              <span>{item.detail}</span>
              <br />
              <small>
                Acción: {item.action} · Responsable: {item.owner} · Fuente: {item.source}
              </small>
            </li>
          ))}
        </ul>
      </section>
      <section className="dx-admin__section" aria-labelledby="dx-commercial-title">
        <header className="dx-admin__section-head">
          <h2 id="dx-commercial-title">Resumen comercial</h2>
          <p>Solo datos reales. Lo que no tiene fuente dice «Pendiente de instrumentación».</p>
        </header>
        <div className="dx-admin__kpis">
          {COMMERCIAL_LABELS.map(([key, label, money]) => {
            const metric = data.commercial[key];
            return (
              <article key={key} title={metric ? `${metric.source}${metric.note ? " — " + metric.note : ""}` : ""}>
                <span>{label}</span>
                <strong data-status={metric?.status}>{metricText(metric, money)}</strong>
              </article>
            );
          })}
        </div>
      </section>
    </>
  );
}
