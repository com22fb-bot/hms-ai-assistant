import { Activity, BellRing } from "lucide-react";

import type { CaseEvent } from "@/types/cases";

type Props = {
  events: CaseEvent[];
};

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("es-MX", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

export default function RecentCaseEvents({ events }: Props) {
  return (
    <aside className="case-events-panel">
      <div className="case-section-heading">
        <div>
          <span className="case-eyebrow">EVENTOS</span>
          <h2>Actividad relevante</h2>
        </div>

        <Activity size={20} />
      </div>

      <div className="case-events-list">
        {events.length === 0 ? (
          <div className="case-event-empty">
            Aún no hay eventos de negocio.
          </div>
        ) : (
          events.map((event) => (
            <article className="case-event" key={event.id}>
              <span className={`case-event-level level-${event.level}`}>
                <BellRing size={14} />
              </span>

              <div>
                <strong>{event.title}</strong>
                <p>{event.description ?? event.event_type}</p>
                <time>{formatDate(event.created_at)}</time>
              </div>
            </article>
          ))
        )}
      </div>
    </aside>
  );
}
