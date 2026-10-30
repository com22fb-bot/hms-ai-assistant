"use client";

import { AlertTriangle, LoaderCircle, Square } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { hmsJson } from "@/lib/hmsApi";
import { useLanguage } from "@/lib/i18n/LanguageProvider";

/** Estado REAL de la importación guiada, leído del job en el servidor (nada simulado). */
type Status = {
  phase?: string;
  job_status?: string | null;
  last_error?: string | null;
  heartbeat_at?: string | null;
  server_time?: string;
  active?: unknown;
  failure?: { message?: string } | null;
  recent_cases?: { id: string; title: string; priority?: string }[];
  progress?: {
    expected: number;
    processed?: number;
    downloaded: number;
    classified: number;
    created_cases: number;
    errors: number;
    rate_per_min?: number;
    eta_seconds?: number | null;
  };
};

const TXT = {
  es: {
    title: "Descarga de tu correo",
    identifying: "Identificando casos",
    of: "de",
    rate: "{n} mensajes/min",
    eta: "Faltan ~{t}",
    etaCalc: "Calculando tiempo restante…",
    cases: "Casos encontrados",
    identified: "identificados",
    stop: "Detener descarga",
    stopping: "Deteniendo…",
    stopped: "Descarga detenida. Lo ya descargado se conserva.",
    close: "Cerrar",
    resume: "Continuar descarga",
    resuming: "Continuando…",
    pending: "{n} descargados aún sin identificar; se identificarán al continuar.",
    done: "Descarga terminada.",
    offline: "Sin conexión con el servidor. Reintentando; la descarga sigue en el servidor.",
    restart: "El servicio se reinició; la descarga se reanudará donde quedó.",
    stale: "Sin señal del proceso desde hace {t}.",
    failed: "La descarga falló.",
    lastError: "Último error: {e}",
    errors: "{n} incidencias",
  },
  en: {
    title: "Downloading your mail",
    identifying: "Identifying cases",
    of: "of",
    rate: "{n} messages/min",
    eta: "~{t} left",
    etaCalc: "Estimating time left…",
    cases: "Cases found",
    identified: "identified",
    stop: "Stop download",
    stopping: "Stopping…",
    stopped: "Download stopped. What was already downloaded is kept.",
    close: "Close",
    resume: "Continue download",
    resuming: "Continuing…",
    pending: "{n} downloaded but not yet identified; they will be identified when you continue.",
    done: "Download finished.",
    offline: "No connection to the server. Retrying; the download keeps running on the server.",
    restart: "The service restarted; the download will resume where it left off.",
    stale: "No signal from the process for {t}.",
    failed: "The download failed.",
    lastError: "Last error: {e}",
    errors: "{n} issues",
  },
};

function fmt(s: string, vars: Record<string, string | number>) {
  return s.replace(/\{(\w+)\}/g, (_, k) => String(vars[k] ?? ""));
}

function duration(seconds: number) {
  if (seconds < 60) return `${Math.max(1, Math.round(seconds))} s`;
  const m = Math.round(seconds / 60);
  return m < 60 ? `${m} min` : `${Math.floor(m / 60)} h ${m % 60} min`;
}

export function ImportStatusPanel({ onFinished }: { onFinished?: () => void }) {
  const { language } = useLanguage();
  const t = language === "es" ? TXT.es : TXT.en;
  const [status, setStatus] = useState<Status | null>(null);
  const [offline, setOffline] = useState(false);
  const [stopping, setStopping] = useState(false);
  const [visible, setVisible] = useState(false);
  const [resuming, setResuming] = useState(false);
  const wasActive = useRef(false);

  const load = useCallback(async () => {
    try {
      const data = await hmsJson<Status>("/api/hms/gmail/import/status", { cache: "no-store" });
      setOffline(false);
      setStatus(data);
      const active = Boolean(data.active);
      if (active) {
        wasActive.current = true;
        setVisible(true);
      } else if (wasActive.current) {
        wasActive.current = false;
        onFinished?.();
      }
      return active;
    } catch {
      setOffline(true);
      return wasActive.current;
    }
  }, [onFinished]);

  useEffect(() => {
    let stop = false;
    let timer: number | undefined;
    const tick = async () => {
      const active = await load();
      if (!stop) timer = window.setTimeout(tick, active ? 2500 : 20000);
    };
    void tick();
    const kick = () => {
      window.clearTimeout(timer);
      void tick();
    };
    window.addEventListener("hms:import-started", kick);
    return () => {
      stop = true;
      window.clearTimeout(timer);
      window.removeEventListener("hms:import-started", kick);
    };
  }, [load]);

  async function stopDownload() {
    setStopping(true);
    try {
      await hmsJson("/api/hms/gmail/import/cancel", { method: "POST" });
      await load();
    } finally {
      setStopping(false);
    }
  }

  async function resumeDownload() {
    setResuming(true);
    try {
      // Nuevo job inicial: lo ya guardado se omite (no se descarga de nuevo) y el
      // barrido final identifica lo pendiente.
      await hmsJson("/api/hms/gmail/import/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: "initial", exclude: [] }),
      });
      await load();
    } finally {
      setResuming(false);
    }
  }

  if (!visible || !status) return null;
  const p = status.progress;
  const active = Boolean(status.active);
  const js = status.job_status ?? "";
  const hbAge = status.heartbeat_at && status.server_time
    ? (Date.parse(status.server_time) - Date.parse(status.heartbeat_at)) / 1000
    : 0;
  const expected = p?.expected || 0;
  const processed = p?.processed ?? p?.downloaded ?? 0;
  const pct = expected ? Math.min(100, Math.round((processed * 100) / expected)) : 0;

  return (
    <section className="hms-import-status-panel" aria-live="polite" style={{
      position: "fixed", left: 16, bottom: 16, zIndex: 40, width: "min(380px, calc(100vw - 32px))",
      padding: 16, borderRadius: 16, border: "1px solid rgba(127,127,127,.35)",
      background: "var(--nx-surface, #10141c)", color: "var(--nx-text, #f3f5f8)", boxShadow: "0 12px 32px rgba(0,0,0,.35)",
    }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
        <strong>{t.title}</strong>
        {active ? (
          <button type="button" onClick={() => void stopDownload()} disabled={stopping}>
            {stopping ? <LoaderCircle className="app-spin" size={16} /> : <Square size={16} />}
            {" "}{stopping ? t.stopping : t.stop}
          </button>
        ) : null}
      </header>

      {p ? (
        <>
          <div className="hms-progress-heading" style={{ marginTop: 8 }}>
            <span>{processed.toLocaleString()} {t.of} {expected ? expected.toLocaleString() : "…"}</span>
            <span>{pct}%</span>
          </div>
          <div className="hms-progress-track"><span style={{ width: `${pct}%` }} /></div>
          {active ? (
            <small>
              {fmt(t.rate, { n: Math.round(p.rate_per_min ?? 0) })}
              {" · "}
              {p.eta_seconds != null ? fmt(t.eta, { t: duration(p.eta_seconds) }) : t.etaCalc}
              {" · "}{t.identifying}: {p.classified.toLocaleString()} {t.identified}
            </small>
          ) : null}
          <div style={{ marginTop: 10 }}>
            <strong>{t.cases}: {p.created_cases.toLocaleString()}</strong>
            {status.recent_cases && status.recent_cases.length ? (
              <ul style={{ margin: "6px 0 0", paddingLeft: 18 }}>
                {status.recent_cases.map((c) => <li key={c.id}>{c.title}</li>)}
              </ul>
            ) : null}
          </div>
          {p.errors > 0 ? <small>{fmt(t.errors, { n: p.errors })}</small> : null}
        </>
      ) : null}

      {offline ? <p role="alert"><AlertTriangle size={16} /> {t.offline}</p> : null}
      {js === "interrupted" ? <p role="alert"><AlertTriangle size={16} /> {t.restart}</p> : null}
      {active && !offline && hbAge > 90 ? <p role="alert"><AlertTriangle size={16} /> {fmt(t.stale, { t: duration(hbAge) })}</p> : null}
      {js === "failed" ? <p role="alert"><AlertTriangle size={16} /> {status.failure?.message || t.failed}</p> : null}
      {status.last_error && (js === "failed" || js === "interrupted") ? <small>{fmt(t.lastError, { e: status.last_error.slice(0, 200) })}</small> : null}
      {js === "cancelled" && !active ? (
        <div data-testid="import-stopped">
          <p>{t.stopped}</p>
          {p && p.downloaded > p.classified ? <small>{fmt(t.pending, { n: p.downloaded - p.classified })}</small> : null}
          <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
            <button type="button" onClick={() => setVisible(false)}>{t.close}</button>
            <button type="button" onClick={() => void resumeDownload()} disabled={resuming}>
              {resuming ? t.resuming : t.resume}
            </button>
          </div>
        </div>
      ) : null}
      {(js === "completed" || js === "failed") && !active ? (
        <button type="button" onClick={() => setVisible(false)}>{t.close}</button>
      ) : null}
      {js === "completed" ? <p>{t.done}</p> : null}
    </section>
  );
}
