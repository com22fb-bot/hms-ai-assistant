"use client";

import { Loader2, RefreshCw, Send } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { hmsJson } from "@/lib/hmsApi";

type Row = {
  user_id: string;
  email: string;
  plan_code: string | null;
  status: string | null;
  protected: boolean;
  phase: "en_prueba" | "por_borrar";
  trial_ends_at?: string | null;
  ended_at?: string;
  delete_at?: string | null;
  days_left: number | null;
};

type Run = {
  id: string;
  ran_at: string;
  dry_run: boolean;
  trial_due: number;
  lapsed_due: number;
  deleted: number;
  skipped_protected: number;
  reminders_mid: number;
  reminders_final: number;
};

type Lifecycle = {
  trials: Row[];
  lapsed: Row[];
  deletion_enabled: boolean;
  auto_reminders_enabled: boolean;
  next_cleanup_at: string;
  rules: { trial_grace_days: number; lapsed_grace_days: number; monthly_history_days: number; annual_history_days: number };
  recent_runs?: Run[];
};

type RemindResult = { sent: number; skipped_protected: number; skipped_no_email: number; failed: number };

const MX = "America/Mexico_City";

function fmt(value?: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("es-MX", { timeZone: MX, dateStyle: "medium", timeStyle: "short" });
}

function Table({ rows, emptyText }: { rows: Row[]; emptyText: string }) {
  if (!rows.length) return <p className="dx-perf__hint">{emptyText}</p>;
  return (
    <div className="dx-admin__table-wrap">
      <table className="dx-admin__table">
        <thead>
          <tr>
            <th>Correo</th>
            <th>Plan</th>
            <th>Estado</th>
            <th>Se borra</th>
            <th>Días restantes</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.user_id}>
              <td>
                {row.email || row.user_id}
                {row.protected ? " (protegida, no se borra)" : ""}
              </td>
              <td>{row.plan_code ?? "—"}</td>
              <td>{row.phase === "en_prueba" ? `En prueba hasta ${fmt(row.trial_ends_at)}` : `Terminó ${fmt(row.ended_at)}`}</td>
              <td>{fmt(row.delete_at)}</td>
              <td>{row.days_left ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function InfoPanel() {
  const [data, setData] = useState<Lifecycle | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<"trial" | "lapsed" | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setData(await hmsJson<Lifecycle>("/api/hms/admin/lifecycle"));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cargar.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => void load());
    return () => window.cancelAnimationFrame(frame);
  }, [load]);

  const remind = async (group: "trial" | "lapsed") => {
    const label = group === "trial" ? "las cuentas en prueba" : "las suscripciones no renovadas";
    if (!window.confirm(`¿Enviar el recordatorio para suscribirse a ${label}? Sale por correo (Resend).`)) return;
    setBusy(group);
    setNotice(null);
    try {
      const result = await hmsJson<RemindResult>(`/api/hms/admin/lifecycle/remind/${group}`, { method: "POST" });
      setNotice(
        `Enviados: ${result.sent}. Protegidas omitidas: ${result.skipped_protected}. Sin correo: ${result.skipped_no_email}. Fallidos: ${result.failed}.`,
      );
      await load();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "No se pudo enviar.");
    } finally {
      setBusy(null);
    }
  };

  return (
    <section className="dx-admin__section">
      <header className="dx-admin__section-head">
        <h2>Info: pruebas y suscripciones</h2>
        <p>
          Prueba: la cuenta se conserva {data?.rules.trial_grace_days ?? 7} días después de terminar. Suscripción no
          renovada: {data?.rules.lapsed_grace_days ?? 30} días. La limpieza corre cada día a las 3:00 a. m. (Ciudad de
          México). Importación: mensual {data?.rules.monthly_history_days ?? 90} días, anual{" "}
          {data?.rules.annual_history_days ?? 183} días. hmcelinfo@gmail.com nunca se borra.
        </p>
        <button type="button" className="dx-admin__btn dx-admin__btn--ghost" onClick={() => {
            setLoading(true);
            void load();
          }} disabled={loading}>
          {loading ? <Loader2 size={16} className="dx-admin__spin" /> : <RefreshCw size={16} />} Actualizar
        </button>
      </header>
      {error && <p className="dx-admin__alert">{error}</p>}
      {data && (
        <>
          <p>
            Borrado real: <strong>{data.deletion_enabled ? "ACTIVADO" : "apagado (solo simulación)"}</strong> ·
            Recordatorios automáticos: <strong>{data.auto_reminders_enabled ? "activados" : "apagados"}</strong> ·
            Próxima limpieza: <strong>{fmt(data.next_cleanup_at)}</strong>
          </p>
          {notice && <p className="dx-perf__hint">{notice}</p>}

          <h3>Cuentas en prueba ({data.trials.length})</h3>
          <button type="button" className="dx-admin__btn" disabled={busy !== null || !data.trials.length} onClick={() => void remind("trial")}>
            {busy === "trial" ? <Loader2 size={16} className="dx-admin__spin" /> : <Send size={16} />} Enviar recordatorio a cuentas en prueba
          </button>
          <Table rows={data.trials} emptyText="No hay cuentas en prueba." />

          <h3>Suscripciones no renovadas ({data.lapsed.length})</h3>
          <button type="button" className="dx-admin__btn" disabled={busy !== null || !data.lapsed.length} onClick={() => void remind("lapsed")}>
            {busy === "lapsed" ? <Loader2 size={16} className="dx-admin__spin" /> : <Send size={16} />} Enviar recordatorio a suscripciones vencidas
          </button>
          <Table rows={data.lapsed} emptyText="No hay suscripciones vencidas." />

          <h3>Últimas corridas de limpieza</h3>
          {data.recent_runs && data.recent_runs.length ? (
            <ul>
              {data.recent_runs.map((run) => (
                <li key={run.id}>
                  {fmt(run.ran_at)} · {run.dry_run ? "simulación" : "real"} · por borrar: prueba {run.trial_due}, vencidas{" "}
                  {run.lapsed_due} · borradas {run.deleted} · protegidas {run.skipped_protected} · recordatorios{" "}
                  {run.reminders_mid + run.reminders_final}
                </li>
              ))}
            </ul>
          ) : (
            <p className="dx-perf__hint">Todavía no ha corrido la limpieza.</p>
          )}
        </>
      )}
    </section>
  );
}
