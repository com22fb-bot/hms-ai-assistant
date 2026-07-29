"use client";

import {
  Mail,
  MailOpen,
  User,
  Megaphone,
} from "lucide-react";

interface MetricsGridProps {
  total: number;
  unread: number;
  personal: number;
  promotions: number;
}

interface MetricCardProps {
  title: string;
  value: number;
  icon: React.ReactNode;
  description: string;
}

function MetricCard({
  title,
  value,
  icon,
  description,
}: MetricCardProps) {
  return (
    <article className="metric-card">
      <div className="metric-icon">
        {icon}
      </div>

      <div className="metric-content">
        <span className="metric-title">{title}</span>

        <strong className="metric-value">
          {value.toLocaleString()}
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
  unread,
  personal,
  promotions,
}: MetricsGridProps) {
  return (
    <section
      className="metrics-grid"
      aria-label="Resumen del buzón"
    >
      <MetricCard
        title="Total"
        value={total}
        icon={<Mail size={22} />}
        description="Correos cargados"
      />

      <MetricCard
        title="No leídos"
        value={unread}
        icon={<MailOpen size={22} />}
        description="Pendientes por revisar"
      />

      <MetricCard
        title="Personales"
        value={personal}
        icon={<User size={22} />}
        description="Mensajes importantes"
      />

      <MetricCard
        title="Promociones"
        value={promotions}
        icon={<Megaphone size={22} />}
        description="Publicidad detectada"
      />
    </section>
  );
}