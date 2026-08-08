"use client";

import {
  AlertTriangle,
  CheckCircle2,
  Mail,
  Reply,
} from "lucide-react";

interface MetricsGridProps {
  total: number;
  requiresAction: number;
  requiresReply: number;
  highPriority: number;
}

interface MetricCardProps {
  title: string;
  value: number;
  icon: React.ReactNode;
  description: string;
  className?: string;
}

function MetricCard({
  title,
  value,
  icon,
  description,
  className = "",
}: MetricCardProps) {
  return (
    <article
      className={`metric-card ${className}`.trim()}
    >
      <div className="metric-icon">
        {icon}
      </div>

      <div className="metric-content">
        <span className="metric-title">{title}</span>

        <strong className="metric-value">
          {value.toLocaleString("es-MX")}
        </strong>

        <small className="metric-description">
          {description}
        </small>
      </div>
    </article>
  );
}

export default function MetricsGrid({
  total,
  requiresAction,
  requiresReply,
  highPriority,
}: MetricsGridProps) {
  return (
    <section
      className="metrics-grid"
      aria-label="Indicadores inteligentes del buzón"
    >
      <MetricCard
        title="Correos analizados"
        value={total}
        icon={<Mail size={22} aria-hidden="true" />}
        description="Mensajes procesados por la IA"
        className="metric-card-total"
      />

      <MetricCard
        title="Requieren acción"
        value={requiresAction}
        icon={
          <CheckCircle2
            size={22}
            aria-hidden="true"
          />
        }
        description="Solicitudes o tareas detectadas"
        className="metric-card-action"
      />

      <MetricCard
        title="Sin responder"
        value={requiresReply}
        icon={<Reply size={22} aria-hidden="true" />}
        description="Correos que esperan respuesta"
        className="metric-card-reply"
      />

      <MetricCard
        title="Alta prioridad"
        value={highPriority}
        icon={
          <AlertTriangle
            size={22}
            aria-hidden="true"
          />
        }
        description="Mensajes que requieren atención"
        className="metric-card-priority"
      />
    </section>
  );
}
