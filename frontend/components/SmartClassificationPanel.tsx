"use client";

import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  LoaderCircle,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { hmsJson } from "@/lib/hmsApi";


type ReclassificationRun = {
  id: string;
  status: "running" | "completed" | "failed" | "cancelled";
  total_messages: number;
  processed_messages: number;
  removed_cases: number;
  total_cases: number;
  processed_cases: number;
  without_case: number;
  current_batch: number;
  errors: number;
  action_required: number;
  waiting_external: number;
  review: number;
  informational: number;
  automated: number;
  promotional: number;
  classifier_version: string | null;
  last_error: string | null;
  metadata: {
    phase?: string;
    categories?: Record<string, number>;
    linked_cases?: number;
    remaining?: number;
  } | null;
};

type StatusResponse = {
  status: string;
  running: boolean;
  progress_percent: number;
  run: ReclassificationRun | null;
};

function readableError(reason: unknown): string {
  return reason instanceof Error
    ? reason.message
    : "No fue posible ejecutar la clasificación inteligente.";
}

export function SmartClassificationPanel({
  onClose,
  onComplete,
}: {
  onClose: () => void;
  onComplete: () => void;
}) {
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const completedRun = useRef<string | null>(null);

  const loadStatus = useCallback(async () => {
    const current = await hmsJson<StatusResponse>(
      "/api/hms/reclassification/status",
      { cache: "no-store" },
    );
    setStatus(current);
    return current;
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadStatus()
        .catch((reason) => setError(readableError(reason)))
        .finally(() => setLoading(false));
    }, 0);
    return () => window.clearTimeout(timer);
  }, [loadStatus]);

  useEffect(() => {
    if (!status?.running) {
      return;
    }

    const timer = window.setInterval(() => {
      void loadStatus().catch((reason) => {
        setError(readableError(reason));
      });
    }, 1500);
    return () => window.clearInterval(timer);
  }, [loadStatus, status?.running]);

  useEffect(() => {
    const run = status?.run;
    if (
      !run
      || run.status !== "completed"
      || completedRun.current === run.id
    ) {
      return;
    }

    completedRun.current = run.id;
    window.dispatchEvent(
      new CustomEvent("hms:classification-complete"),
    );
    onComplete();
  }, [onComplete, status?.run]);

  async function start() {
    setStarting(true);
    setError(null);
    completedRun.current = null;

    try {
      await hmsJson("/api/hms/reclassification/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ confirmation: "RECLASIFICAR" }),
      });
      await loadStatus();
    } catch (reason) {
      setError(readableError(reason));
    } finally {
      setStarting(false);
    }
  }

  const run = status?.run;
  const categories = run?.metadata?.categories ?? {};

  return (
    <div className="hms-classification-overlay" role="dialog" aria-modal="true">
      <section className="hms-classification-panel">
        <button
          type="button"
          className="hms-classification-close"
          onClick={onClose}
          aria-label="Cerrar clasificación inteligente"
        >
          <X size={22} />
        </button>

        <header>
          <span>PRUEBA CONTROLADA</span>
          <h2>Clasificación inteligente</h2>
          <p>
            Vuelve a revisar todos los correos descargados, conserva los mensajes
            y reconstruye únicamente los casos realmente accionables.
          </p>
        </header>

        <section className="hms-classification-safety">
          <ShieldCheck size={22} />
          <div>
            <strong>Protección antes de reclasificar</strong>
            <span>
              HMS crea un respaldo interno de los casos y relaciones actuales.
              Gmail permanece en modo de solo lectura.
            </span>
          </div>
        </section>

        {loading ? (
          <div className="hms-classification-loading">
            <LoaderCircle className="app-spin" size={32} />
            Consultando el estado...
          </div>
        ) : null}

        {error ? (
          <div className="hms-classification-error">
            <AlertTriangle size={20} />
            {error}
          </div>
        ) : null}

        {run?.status === "running" ? (
          <section className="hms-classification-progress">
            <div className="hms-classification-progress-heading">
              <div>
                <span>Lote {run.current_batch}</span>
                <strong>
                  {run.processed_messages.toLocaleString()} de {run.total_messages.toLocaleString()}
                </strong>
              </div>
              <b>{status?.progress_percent ?? 0}%</b>
            </div>
            <div className="hms-classification-track">
              <span style={{ width: `${status?.progress_percent ?? 0}%` }} />
            </div>
            <small>
              La prueba continúa aunque cierres esta ventana o cierres sesión.
            </small>
          </section>
        ) : null}

        {run && run.status !== "running" ? (
          <section className={`hms-classification-result is-${run.status}`}>
            {run.status === "completed" ? (
              <CheckCircle2 size={38} />
            ) : (
              <AlertTriangle size={38} />
            )}
            <div>
              <strong>
                {run.status === "completed"
                  ? "Última reclasificación completada"
                  : "La última reclasificación requiere revisión"}
              </strong>
              <span>
                {run.last_error || `Clasificador ${run.classifier_version || "HMS"}`}
              </span>
            </div>
          </section>
        ) : null}

        {run ? (
          <div className="hms-classification-stats">
            <article><span>Procesados</span><strong>{run.processed_messages.toLocaleString()}</strong></article>
            <article><span>Casos nuevos</span><strong>{run.total_cases.toLocaleString()}</strong></article>
            <article><span>Sin caso</span><strong>{run.without_case.toLocaleString()}</strong></article>
            <article><span>Incidencias</span><strong>{run.errors.toLocaleString()}</strong></article>
          </div>
        ) : null}

        {Object.keys(categories).length > 0 ? (
          <div className="hms-classification-categories">
            {Object.entries(categories).map(([key, value]) => (
              <article key={key}>
                <span>{key.replaceAll("_", " ")}</span>
                <strong>{value.toLocaleString()}</strong>
              </article>
            ))}
          </div>
        ) : null}

        <footer>
          <button type="button" className="secondary" onClick={onClose}>
            Cerrar
          </button>
          <button
            type="button"
            disabled={Boolean(status?.running) || starting}
            onClick={() => void start()}
          >
            {status?.running || starting ? (
              <LoaderCircle className="app-spin" size={20} />
            ) : run ? (
              <RefreshCw size={20} />
            ) : (
              <Sparkles size={20} />
            )}
            {status?.running
              ? "Reclasificando..."
              : starting
                ? "Preparando..."
                : run
                  ? "Volver a reclasificar"
                  : "Iniciar prueba de reclasificación"}
          </button>
        </footer>

        <div className="hms-classification-note">
          <Bot size={18} />
          <span>
            Favoritos y reglas de seguimiento se conservan durante la prueba.
          </span>
        </div>
      </section>
    </div>
  );
}
