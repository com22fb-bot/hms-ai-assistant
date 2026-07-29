import {
  AlertTriangle,
  CalendarClock,
  CheckCircle2,
  Gauge,
  Reply,
  Tag,
} from "lucide-react";

import type {
  MailAnalysis,
  MailAnalysisCategory,
  MailPriority,
} from "@/types/analysis";
import type {
  GmailMessage,
  MailCategory,
} from "@/types/mail";

function containsLabel(
  message: GmailMessage,
  label: string,
): boolean {
  return message.labels.includes(label);
}

function getCategory(message: GmailMessage): MailCategory {
  if (containsLabel(message, "CATEGORY_PERSONAL")) {
    return {
      label: "Personal",
      className: "category category-personal",
    };
  }

  if (containsLabel(message, "CATEGORY_PROMOTIONS")) {
    return {
      label: "Promoción",
      className: "category category-promotions",
    };
  }

  if (containsLabel(message, "CATEGORY_SOCIAL")) {
    return {
      label: "Social",
      className: "category category-social",
    };
  }

  if (containsLabel(message, "CATEGORY_UPDATES")) {
    return {
      label: "Actualización",
      className: "category category-updates",
    };
  }

  return {
    label: "General",
    className: "category category-general",
  };
}

function formatMessageDate(value: string | null): string {
  if (!value) {
    return "Fecha no disponible";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("es-MX", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function getInitials(name: string): string {
  const initials = name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join("");

  return initials || "✉";
}

function getPriorityLabel(priority: MailPriority): string {
  const labels: Record<MailPriority, string> = {
    high: "Alta",
    medium: "Media",
    low: "Baja",
  };

  return labels[priority];
}

function getPriorityClass(priority: MailPriority): string {
  return `analysis-chip analysis-priority analysis-priority-${priority}`;
}

function getAnalysisCategoryLabel(
  category: MailAnalysisCategory,
): string {
  const labels: Record<MailAnalysisCategory, string> = {
    finance: "Finanzas",
    approval: "Aprobación",
    document: "Documento",
    meeting: "Reunión",
    support: "Soporte",
    commercial: "Comercial",
    general: "General",
  };

  return labels[category];
}

function formatConfidence(confidence: number): string {
  const percentage =
    confidence <= 1
      ? Math.round(confidence * 100)
      : Math.round(confidence);

  const normalizedPercentage = Math.min(
    100,
    Math.max(0, percentage),
  );

  return `${normalizedPercentage}%`;
}

interface MailItemProps {
  message: GmailMessage;
  analysis?: MailAnalysis;
}

export default function MailItem({
  message,
  analysis,
}: MailItemProps) {
  const category = getCategory(message);

  return (
    <article
      className={
        message.is_unread
          ? "mail-item mail-item-unread"
          : "mail-item"
      }
      data-analysis-ready={analysis ? "true" : "false"}
    >
      <div className="sender-avatar">
        {getInitials(message.sender)}
      </div>

      <div className="mail-body">
        <div className="mail-primary-row">
          <div className="mail-sender-row">
            {message.is_unread ? (
              <span
                className="unread-dot"
                title="Correo no leído"
              />
            ) : null}

            <strong>{message.sender}</strong>

            <span className={category.className}>
              {category.label}
            </span>
          </div>

          <time dateTime={message.received_at ?? undefined}>
            {formatMessageDate(message.received_at)}
          </time>
        </div>

        <h3>{message.subject || "Sin asunto"}</h3>

        <p>
          {message.snippet || "Sin vista previa disponible."}
        </p>

        {analysis ? (
          <div
            className="mail-analysis-row"
            aria-label="Análisis inteligente del correo"
          >
            <span
              className={getPriorityClass(
                analysis.priority,
              )}
              title={`Prioridad ${getPriorityLabel(
                analysis.priority,
              ).toLowerCase()}`}
            >
              <AlertTriangle size={12} aria-hidden="true" />
              Prioridad {getPriorityLabel(analysis.priority)}
            </span>

            <span
              className="analysis-chip analysis-category"
              title="Categoría detectada"
            >
              <Tag size={12} aria-hidden="true" />
              {getAnalysisCategoryLabel(analysis.category)}
            </span>

            {analysis.requiresReply ? (
              <span
                className="analysis-chip analysis-reply"
                title="Este correo requiere respuesta"
              >
                <Reply size={12} aria-hidden="true" />
                Responder
              </span>
            ) : null}

            {analysis.requiresAction ? (
              <span
                className="analysis-chip analysis-action"
                title="Este correo requiere una acción"
              >
                <CheckCircle2
                  size={12}
                  aria-hidden="true"
                />
                Acción
              </span>
            ) : null}

            {analysis.hasDeadline ? (
              <span
                className="analysis-chip analysis-deadline"
                title="Se detectó una fecha límite"
              >
                <CalendarClock
                  size={12}
                  aria-hidden="true"
                />
                {analysis.deadline || "Con fecha límite"}
              </span>
            ) : null}

            <span
              className="analysis-chip analysis-confidence"
              title="Nivel de confianza del análisis"
            >
              <Gauge size={12} aria-hidden="true" />
              {formatConfidence(analysis.confidence)}
            </span>
          </div>
        ) : null}

        <div className="mail-footer">
          <span>
            {message.sender_email || "Correo no disponible"}
          </span>

          <span
            className={
              message.is_unread
                ? "unread-label"
                : undefined
            }
          >
            {message.is_unread ? "No leído" : "Leído"}
          </span>
        </div>
      </div>
    </article>
  );
}
