import {
  AlertTriangle,
  ArrowRight,
  Clock3,
  Mail,
  MessagesSquare,
} from "lucide-react";

import type { IntelligentCase } from "@/types/cases";

type Props = {
  cases: IntelligentCase[];
  loading: boolean;
};

const statusLabels: Record<IntelligentCase["status"], string> = {
  new: "Nuevo",
  analyzing: "En análisis",
  in_progress: "En proceso",
  delegated: "Delegado",
  waiting_internal: "Esperando equipo",
  waiting_external: "Esperando tercero",
  resolved: "Resuelto",
  closed: "Cerrado",
  archived: "Archivado",
};

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("es-MX", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export default function CaseList({ cases, loading }: Props) {
  if (loading) {
    return (
      <div className="case-empty">
        Analizando Casos Inteligentes…
      </div>
    );
  }

  if (cases.length === 0) {
    return (
      <div className="case-empty">
        <MessagesSquare size={28} />
        <strong>No hay casos que requieran atención.</strong>
        <span>
          Sincroniza Gmail y ejecuta el motor de casos.
        </span>
      </div>
    );
  }

  return (
    <div className="case-list">
      {cases.map((item) => (
        <article
          className={`case-row case-priority-${item.priority}`}
          key={item.id}
        >
          <div className="case-risk">
            <strong>{item.risk_score}</strong>
            <span>RIESGO</span>
          </div>

          <div className="case-copy">
            <div className="case-row-heading">
              <span className={`case-priority-pill ${item.priority}`}>
                {item.priority === "critical" ? (
                  <AlertTriangle size={13} />
                ) : null}
                {item.priority}
              </span>

              <span className="case-type">{item.case_type}</span>

              <span className="case-status">
                {statusLabels[item.status]}
              </span>
            </div>

            <h3>{item.title}</h3>

            <p>
              {item.requested_action ??
                item.summary ??
                "Caso detectado a partir de comunicaciones relacionadas."}
            </p>

            <div className="case-meta">
              <span>
                <Mail size={14} />
                {item.requester_email ?? "Solicitante por identificar"}
              </span>

              <span>
                <MessagesSquare size={14} />
                {item.source_count} evidencias
              </span>

              <span>
                <Clock3 size={14} />
                {formatDate(item.last_activity_at)}
              </span>
            </div>
          </div>

          <a
            className="case-open-button"
            href={`${process.env.NEXT_PUBLIC_API_BASE_URL?.replace(
              /\/$/,
              "",
            ) ?? ""}/cases/${item.id}`}
            target="_blank"
            rel="noreferrer"
            aria-label={`Abrir caso ${item.title}`}
          >
            <ArrowRight size={18} />
          </a>
        </article>
      ))}
    </div>
  );
}
