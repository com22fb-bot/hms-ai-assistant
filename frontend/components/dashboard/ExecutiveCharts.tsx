"use client";

import {
  AlertTriangle,
  BarChart3,
  CalendarClock,
  CheckCircle2,
  CircleDot,
  FolderKanban,
  Reply,
} from "lucide-react";

import type {
  MailAnalysis,
  MailAnalysisCategory,
  MailPriority,
} from "@/types/analysis";

type ExecutiveChartsProps = {
  analyses: MailAnalysis[];
};

type ChartItem = {
  key: string;
  label: string;
  value: number;
  className: string;
};

const priorityLabels: Record<MailPriority, string> = {
  high: "Alta",
  medium: "Media",
  low: "Baja",
};

const priorityClassNames: Record<MailPriority, string> = {
  high: "executive-bar-danger",
  medium: "executive-bar-warning",
  low: "executive-bar-success",
};

const categoryLabels: Record<MailAnalysisCategory, string> = {
  finance: "Finanzas",
  approval: "Aprobaciones",
  document: "Documentos",
  meeting: "Reuniones",
  support: "Soporte",
  commercial: "Comercial",
  general: "General",
};

const categoryClassNames: Record<MailAnalysisCategory, string> = {
  finance: "executive-bar-blue",
  approval: "executive-bar-purple",
  document: "executive-bar-cyan",
  meeting: "executive-bar-orange",
  support: "executive-bar-green",
  commercial: "executive-bar-pink",
  general: "executive-bar-neutral",
};

function calculatePercentage(
  value: number,
  total: number,
): number {
  if (total <= 0 || value <= 0) {
    return 0;
  }

  return Math.min(100, Math.round((value / total) * 100));
}

function ChartRow({
  item,
  total,
}: {
  item: ChartItem;
  total: number;
}) {
  const percentage = calculatePercentage(item.value, total);

  return (
    <div className="executive-chart-row">
      <div className="executive-chart-row-header">
        <span>{item.label}</span>

        <strong>
          {item.value}
          <small>{percentage}%</small>
        </strong>
      </div>

      <div
        className="executive-chart-track"
        role="progressbar"
        aria-label={`${item.label}: ${item.value}`}
        aria-valuemin={0}
        aria-valuemax={Math.max(total, 1)}
        aria-valuenow={item.value}
      >
        <span
          className={`executive-chart-bar ${item.className}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

function ChartCard({
  eyebrow,
  title,
  description,
  icon,
  items,
  total,
}: {
  eyebrow: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  items: ChartItem[];
  total: number;
}) {
  const visibleItems = items.filter((item) => item.value > 0);

  return (
    <article className="executive-chart-card">
      <header className="executive-chart-card-header">
        <div className="executive-chart-heading">
          <div className="executive-chart-icon">
            {icon}
          </div>

          <div>
            <p className="eyebrow">{eyebrow}</p>
            <h3>{title}</h3>
          </div>
        </div>

        <span className="executive-chart-total">
          {total}
        </span>
      </header>

      <p className="executive-chart-description">
        {description}
      </p>

      {visibleItems.length > 0 ? (
        <div className="executive-chart-content">
          {visibleItems.map((item) => (
            <ChartRow
              key={item.key}
              item={item}
              total={total}
            />
          ))}
        </div>
      ) : (
        <div className="executive-chart-empty">
          <CircleDot size={20} aria-hidden="true" />

          <span>
            Aún no hay datos suficientes para mostrar esta gráfica.
          </span>
        </div>
      )}
    </article>
  );
}

export default function ExecutiveCharts({
  analyses,
}: ExecutiveChartsProps) {
  const total = analyses.length;

  const priorityItems: ChartItem[] = (
    ["high", "medium", "low"] as MailPriority[]
  ).map((priority) => ({
    key: priority,
    label: priorityLabels[priority],
    value: analyses.filter(
      (analysis) => analysis.priority === priority,
    ).length,
    className: priorityClassNames[priority],
  }));

  const requiresAction = analyses.filter(
    (analysis) => analysis.requiresAction,
  ).length;

  const requiresReply = analyses.filter(
    (analysis) => analysis.requiresReply,
  ).length;

  const completedOrInformative = analyses.filter(
    (analysis) =>
      !analysis.requiresAction &&
      !analysis.requiresReply,
  ).length;

  const attentionItems: ChartItem[] = [
    {
      key: "requires-action",
      label: "Requieren acción",
      value: requiresAction,
      className: "executive-bar-warning",
    },
    {
      key: "requires-reply",
      label: "Requieren respuesta",
      value: requiresReply,
      className: "executive-bar-blue",
    },
    {
      key: "informative",
      label: "Solo informativos",
      value: completedOrInformative,
      className: "executive-bar-success",
    },
  ];

  const categories = Object.keys(
    categoryLabels,
  ) as MailAnalysisCategory[];

  const categoryItems: ChartItem[] = categories
    .map((category) => ({
      key: category,
      label: categoryLabels[category],
      value: analyses.filter(
        (analysis) => analysis.category === category,
      ).length,
      className: categoryClassNames[category],
    }))
    .sort((first, second) => second.value - first.value);

  const withDeadline = analyses.filter(
    (analysis) => analysis.hasDeadline,
  ).length;

  const withoutDeadline = total - withDeadline;

  const deadlineItems: ChartItem[] = [
    {
      key: "with-deadline",
      label: "Con fecha límite",
      value: withDeadline,
      className: "executive-bar-danger",
    },
    {
      key: "without-deadline",
      label: "Sin fecha límite",
      value: withoutDeadline,
      className: "executive-bar-neutral",
    },
  ];

  return (
    <section
      className="executive-section"
      aria-labelledby="executive-analysis-title"
    >
      <div className="executive-section-header">
        <div>
          <p className="eyebrow">ANÁLISIS EJECUTIVO</p>

          <h2 id="executive-analysis-title">
            Tendencias del correo
          </h2>

          <p>
            Visualiza prioridades, pendientes, categorías y fechas
            límite detectadas automáticamente.
          </p>
        </div>

        <div className="executive-section-badge">
          <BarChart3 size={16} aria-hidden="true" />
          <span>{total} analizados</span>
        </div>
      </div>

      <div className="executive-charts-grid">
        <ChartCard
          eyebrow="PRIORIDAD"
          title="Distribución por prioridad"
          description="Clasificación automática según urgencia e impacto."
          icon={<AlertTriangle size={19} aria-hidden="true" />}
          items={priorityItems}
          total={total}
        />

        <ChartCard
          eyebrow="ATENCIÓN"
          title="Estado de seguimiento"
          description="Correos que requieren una acción o respuesta."
          icon={<Reply size={19} aria-hidden="true" />}
          items={attentionItems}
          total={total}
        />

        <ChartCard
          eyebrow="CLASIFICACIÓN"
          title="Categorías detectadas"
          description="Principales temas identificados por el analizador."
          icon={<FolderKanban size={19} aria-hidden="true" />}
          items={categoryItems}
          total={total}
        />

        <ChartCard
          eyebrow="VENCIMIENTOS"
          title="Control de fechas límite"
          description="Mensajes con compromisos o fechas detectadas."
          icon={<CalendarClock size={19} aria-hidden="true" />}
          items={deadlineItems}
          total={total}
        />
      </div>

      {total > 0 ? (
        <div className="executive-summary-strip">
          <div>
            <CheckCircle2 size={18} aria-hidden="true" />
            <span>Correos sin acción pendiente</span>
            <strong>{completedOrInformative}</strong>
          </div>

          <div>
            <AlertTriangle size={18} aria-hidden="true" />
            <span>Prioridad alta</span>
            <strong>{priorityItems[0].value}</strong>
          </div>

          <div>
            <CalendarClock size={18} aria-hidden="true" />
            <span>Con fecha límite</span>
            <strong>{withDeadline}</strong>
          </div>
        </div>
      ) : null}
    </section>
  );
}
