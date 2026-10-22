"use client";

import { CheckCircle2, Loader2, Plus } from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { supabase } from "@/lib/supabase";

const SOURCES = ["railway", "cloudflare", "supabase", "github", "backup", "monitor", "deploy", "manual"] as const;
const SEVERITIES = ["info", "aviso", "grave", "critico"] as const;

type Source = (typeof SOURCES)[number];
type Severity = (typeof SEVERITIES)[number];
type Status = "abierto" | "resuelto";
type BackupKind = "diario" | "semanal";

type AdminEvent = {
  id: string;
  occurred_at: string;
  ended_at: string | null;
  source: Source;
  severity: Severity;
  title: string;
  detail: string;
  status: Status;
  created_by: string;
  meta?: {
    kind?: BackupKind;
    result?: "ok" | "fallido";
    size_bytes?: number | null;
    duration_s?: number;
    verified?: boolean;
    run_url?: string;
  } | null;
};

const SOURCE_LABEL: Record<Source, string> = {
  railway: "Railway",
  cloudflare: "Cloudflare",
  supabase: "Supabase",
  github: "GitHub",
  backup: "Respaldos",
  monitor: "Monitor",
  deploy: "Despliegue",
  manual: "Manual",
};
const SEVERITY_LABEL: Record<Severity, string> = { info: "Info", aviso: "Aviso", grave: "Grave", critico: "Crítico" };

function when(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("es-MX", { dateStyle: "medium", timeStyle: "short" });
}

function localInputNow(): string {
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
}

// Horarios de los workflows de respaldo (cron UTC): diario 09:00; semanal domingo 09:00.
function nextRun(kind: BackupKind, now = new Date()): Date {
  const d = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), 9, 0, 0));
  if (kind === "diario") {
    if (d <= now) d.setUTCDate(d.getUTCDate() + 1);
    return d;
  }
  d.setUTCDate(d.getUTCDate() + ((7 - d.getUTCDay()) % 7));
  if (d <= now) d.setUTCDate(d.getUTCDate() + 7);
  return d;
}

function BackupCard({ events }: { events: AdminEvent[] }) {
  const rows = (["diario", "semanal"] as const).map((kind) => ({
    kind,
    last: events.find((e) => e.source === "backup" && e.meta?.kind === kind),
    next: nextRun(kind),
  }));
  return (
    <div className="dx-admin__table-wrap">
      <h3>Respaldos</h3>
      <table className="dx-admin__table dx-perf__table">
        <thead>
          <tr>
            <th>Respaldo</th>
            <th>Último</th>
            <th>Resultado</th>
            <th>Tamaño</th>
            <th>Duración</th>
            <th>Verificado</th>
            <th>Próximo</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {rows.map(({ kind, last, next }) => (
            <tr key={kind}>
              <td><strong>{kind === "diario" ? "Diario" : "Semanal"}</strong></td>
              <td>{last ? when(last.occurred_at) : "Sin registro"}</td>
              <td>
                {last?.meta?.result ? (
                  <span className="dx-admin__pill">{last.meta.result === "ok" ? "OK" : "Fallido"}</span>
                ) : (
                  "—"
                )}
              </td>
              <td>{last?.meta?.size_bytes ? `${(last.meta.size_bytes / 1048576).toFixed(1)} MB` : "—"}</td>
              <td>{last?.meta?.duration_s != null ? `${last.meta.duration_s} s` : "—"}</td>
              <td>{last?.meta ? (last.meta.verified ? "Sí" : "No") : "—"}</td>
              <td>{when(next.toISOString())}</td>
              <td>
                {last?.meta?.run_url && (
                  <a href={last.meta.run_url} target="_blank" rel="noreferrer">Ver corrida</a>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function EventsPanel() {
  const [events, setEvents] = useState<AdminEvent[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [adding, setAdding] = useState(false);
  const [fSource, setFSource] = useState<Source | "">("");
  const [fStatus, setFStatus] = useState<Status | "">("");
  const [fText, setFText] = useState("");
  const [draft, setDraft] = useState({
    occurred_at: localInputNow(),
    source: "manual" as Source,
    severity: "info" as Severity,
    title: "",
    detail: "",
  });

  const load = useCallback(async () => {
    const { data, error: err } = await supabase
      .from("admin_events")
      .select("*")
      .order("occurred_at", { ascending: false })
      .limit(500);
    if (err) {
      setError("No fue posible cargar la bitácora.");
      return;
    }
    setError(null);
    setEvents((data ?? []) as AdminEvent[]);
  }, []);

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => void load());
    return () => window.cancelAnimationFrame(frame);
  }, [load]);

  const visible = useMemo(() => {
    const q = fText.trim().toLowerCase();
    return (events ?? []).filter(
      (e) =>
        (!fSource || e.source === fSource) &&
        (!fStatus || e.status === fStatus) &&
        (!q || `${e.title} ${e.detail}`.toLowerCase().includes(q)),
    );
  }, [events, fSource, fStatus, fText]);

  async function add(event: FormEvent) {
    event.preventDefault();
    if (!draft.title.trim()) return;
    setSaving(true);
    const { error: err } = await supabase.from("admin_events").insert({
      occurred_at: new Date(draft.occurred_at).toISOString(),
      source: draft.source,
      severity: draft.severity,
      title: draft.title.trim(),
      detail: draft.detail.trim(),
      status: "abierto",
      created_by: "panel",
    });
    setSaving(false);
    if (err) {
      setError("No fue posible guardar el evento.");
      return;
    }
    setAdding(false);
    setDraft({ occurred_at: localInputNow(), source: "manual", severity: "info", title: "", detail: "" });
    void load();
  }

  async function close(item: AdminEvent) {
    setSaving(true);
    const { error: err } = await supabase
      .from("admin_events")
      .update({ status: "resuelto", ended_at: new Date().toISOString() })
      .eq("id", item.id);
    setSaving(false);
    if (err) {
      setError("No fue posible cerrar el evento.");
      return;
    }
    void load();
  }

  if (!events) {
    return (
      <section className="dx-admin__section">
        {error ? (
          <p className="dx-admin__alert">{error}</p>
        ) : (
          <p className="dx-admin__loading">
            <Loader2 className="dx-admin__spin" size={18} /> Cargando bitácora…
          </p>
        )}
      </section>
    );
  }

  const open = events.filter((e) => e.status === "abierto").length;

  return (
    <section className="dx-admin__section dx-perf">
      <header className="dx-perf__head">
        <div>
          <h2>Bitácora de eventos</h2>
          <p>
            {events.length} eventos · {open} abiertos. Caídas de proveedores, despliegues, respaldos y alertas.
          </p>
        </div>
        <button type="button" className="dx-admin__btn" onClick={() => setAdding((v) => !v)} disabled={saving}>
          <Plus size={16} /> Nuevo evento
        </button>
      </header>
      {error && <p className="dx-admin__alert">{error}</p>}

      <BackupCard events={events} />

      {adding && (
        <form className="dx-admin__form dx-perf__editor" onSubmit={add}>
          <label>
            Inicio
            <input type="datetime-local" value={draft.occurred_at} onChange={(e) => setDraft({ ...draft, occurred_at: e.target.value })} required />
          </label>
          <label>
            Origen
            <select value={draft.source} onChange={(e) => setDraft({ ...draft, source: e.target.value as Source })}>
              {SOURCES.map((s) => (
                <option key={s} value={s}>{SOURCE_LABEL[s]}</option>
              ))}
            </select>
          </label>
          <label>
            Gravedad
            <select value={draft.severity} onChange={(e) => setDraft({ ...draft, severity: e.target.value as Severity })}>
              {SEVERITIES.map((s) => (
                <option key={s} value={s}>{SEVERITY_LABEL[s]}</option>
              ))}
            </select>
          </label>
          <label className="dx-admin__full">
            Título
            <input value={draft.title} maxLength={200} onChange={(e) => setDraft({ ...draft, title: e.target.value })} required />
          </label>
          <label className="dx-admin__full">
            Detalle
            <textarea rows={3} value={draft.detail} onChange={(e) => setDraft({ ...draft, detail: e.target.value })} />
          </label>
          <div className="dx-admin__full">
            <button type="button" className="dx-admin__btn dx-admin__btn--ghost" onClick={() => setAdding(false)}>Cancelar</button>
            <button type="submit" className="dx-admin__btn" disabled={saving}>{saving ? "Guardando…" : "Guardar"}</button>
          </div>
        </form>
      )}

      <div className="dx-admin__form">
        <label>
          Origen
          <select value={fSource} onChange={(e) => setFSource(e.target.value as Source | "")}>
            <option value="">Todos</option>
            {SOURCES.map((s) => (
              <option key={s} value={s}>{SOURCE_LABEL[s]}</option>
            ))}
          </select>
        </label>
        <label>
          Estado
          <select value={fStatus} onChange={(e) => setFStatus(e.target.value as Status | "")}>
            <option value="">Todos</option>
            <option value="abierto">Abierto</option>
            <option value="resuelto">Resuelto</option>
          </select>
        </label>
        <label>
          Buscar
          <input value={fText} onChange={(e) => setFText(e.target.value)} placeholder="Texto en título o detalle" />
        </label>
      </div>

      <div className="dx-admin__table-wrap">
        <table className="dx-admin__table dx-perf__table">
          <thead>
            <tr>
              <th>Inicio</th>
              <th>Origen</th>
              <th>Gravedad</th>
              <th>Evento</th>
              <th>Estado</th>
              <th>Fin</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {visible.length === 0 && (
              <tr>
                <td colSpan={7}>Sin eventos con estos filtros.</td>
              </tr>
            )}
            {visible.map((e) => (
              <tr key={e.id}>
                <td>{when(e.occurred_at)}</td>
                <td>{SOURCE_LABEL[e.source] ?? e.source}</td>
                <td><span className="dx-admin__pill">{SEVERITY_LABEL[e.severity] ?? e.severity}</span></td>
                <td>
                  <strong>{e.title}</strong>
                  {e.detail && <div>{e.detail}</div>}
                  {e.meta?.run_url && (
                    <a href={e.meta.run_url} target="_blank" rel="noreferrer">Ver corrida en GitHub</a>
                  )}
                </td>
                <td>{e.status === "abierto" ? "Abierto" : "Resuelto"}</td>
                <td>{when(e.ended_at)}</td>
                <td>
                  {e.status === "abierto" && (
                    <button type="button" className="dx-admin__btn dx-admin__btn--ghost" onClick={() => void close(e)} disabled={saving}>
                      <CheckCircle2 size={16} /> Cerrar
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
