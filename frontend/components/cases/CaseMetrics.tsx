import {
  AlertTriangle,
  BellRing,
  CircleCheck,
  Clock3,
  Inbox,
  Users,
} from "lucide-react";

import type { CaseDashboardMetrics } from "@/types/cases";

type Props = {
  metrics: CaseDashboardMetrics;
};

export default function CaseMetrics({ metrics }: Props) {
  const items = [
    {
      label: "Casos abiertos",
      value: metrics.total_open,
      icon: Inbox,
    },
    {
      label: "Críticos",
      value: metrics.critical,
      icon: AlertTriangle,
    },
    {
      label: "Esperando equipo",
      value: metrics.waiting_internal,
      icon: Users,
    },
    {
      label: "Esperando tercero",
      value: metrics.waiting_external,
      icon: Clock3,
    },
    {
      label: "Vencidos",
      value: metrics.overdue,
      icon: BellRing,
    },
    {
      label: "Resueltos hoy",
      value: metrics.resolved_today,
      icon: CircleCheck,
    },
  ];

  return (
    <section className="case-metrics" aria-label="Métricas de casos">
      {items.map((item) => {
        const Icon = item.icon;

        return (
          <article className="case-metric-card" key={item.label}>
            <span className="case-metric-icon" aria-hidden="true">
              <Icon size={19} />
            </span>

            <div>
              <strong>{item.value}</strong>
              <span>{item.label}</span>
            </div>
          </article>
        );
      })}
    </section>
  );
}
