"use client";

import Image from "next/image";
import {
  AlertTriangle,
  CheckCircle2,
  Clock3,
  Inbox,
  LoaderCircle,
  Mail,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { hmsJson } from "@/lib/hmsApi";


type Breakdown = {
  key: string;
  count: number;
};

type Inventory = {
  email: string;
  provider_label: string;
  eligible_messages: number;
  period_start_local: string;
  period_end_local: string;
  timezone: string;
  breakdown: Breakdown[];
  excluded: {
    drafts: number;
    spam: number;
    trash: number;
  };
  notice: string;
};

type ImportProgress = {
  expected: number;
  found: number;
  downloaded: number;
  duplicates: number;
  classified: number;
  created_cases: number;
  linked_cases: number;
  without_case: number;
  errors: number;
  download_percent: number;
  classification_percent: number;
  categories: Record<string, number>;
};

type ImportStatus = {
  status: string;
  guided_import_enabled: boolean;
  provider: string;
  email: string;
  needs_initial_import: boolean;
  initial_import_complete: boolean;
  phase:
    | "initial_review"
    | "downloading"
    | "classifying"
    | "ready"
    | "failed";
  active: Record<string, unknown> | null;
  latest: Record<string, unknown> | null;
  progress: ImportProgress;
  message: string;
};

const API = "/api/hms/gmail/import";

const LABELS: Record<string, string> = {
  received: "Recibidos",
  sent: "Enviados",
  unread: "No leídos",
  important: "Importantes",
  updates: "Actualizaciones",
  promotions: "Promociones",
  social: "Social",
  forums: "Foros",
  action_required: "Requieren atención",
  critical_action: "Críticos",
  case_followup: "Seguimientos de casos",
  informational: "Informativos",
  automated: "Automatizados",
  promotional: "Promocionales",
};

function readableError(reason: unknown, fallback: string): string {
  return reason instanceof Error ? reason.message : fallback;
}

function formatLocalDate(value: string): string {
  return new Intl.DateTimeFormat("es-MX", {
    dateStyle: "medium",
  }).format(new Date(value));
}

export function GuidedImportWizard({
  onClose,
  onComplete,
}: {
  onClose: () => void;
  onComplete: () => void;
}) {
  const [status, setStatus] = useState<ImportStatus | null>(null);
  const [inventory, setInventory] = useState<Inventory | null>(null);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const processingSeen = useRef(false);
  const completionSent = useRef(false);

  async function loadStatus(): Promise<ImportStatus> {
    const data = await hmsJson<ImportStatus>(
      `${API}/status`,
      { cache: "no-store" },
    );
    setStatus(data);
    return data;
  }

  async function loadInventory() {
    const data = await hmsJson<Inventory>(
      `${API}/inventory`,
      { cache: "no-store" },
    );
    setInventory(data);
  }

  useEffect(() => {
    let cancelled = false;

    async function initialize() {
      setLoading(true);
      setError(null);

      try {
        const current = await loadStatus();
        if (
          !cancelled
          && current.needs_initial_import
          && !current.active
        ) {
          await loadInventory();
        }
      } catch (reason) {
        if (!cancelled) {
          setError(
            readableError(
              reason,
              "No fue posible preparar la importación inicial.",
            ),
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void initialize();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!status?.active) {
      return;
    }

    processingSeen.current = true;
    const timer = window.setInterval(() => {
      void loadStatus().catch((reason) => {
        setError(
          readableError(
            reason,
            "No fue posible actualizar el progreso.",
          ),
        );
      });
    }, 1500);

    return () => window.clearInterval(timer);
  }, [status?.active]);

  useEffect(() => {
    if (
      !status
      || status.phase !== "ready"
      || !processingSeen.current
      || completionSent.current
    ) {
      return;
    }

    completionSent.current = true;
    const timer = window.setTimeout(onComplete, 2200);
    return () => window.clearTimeout(timer);
  }, [status, onComplete]);

  async function start(mode: "initial" | "incremental") {
    setStarting(true);
    setError(null);
    completionSent.current = false;
    processingSeen.current = true;

    try {
      await hmsJson(`${API}/start`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ mode }),
      });
      await loadStatus();
    } catch (reason) {
      setError(
        readableError(
          reason,
          "No fue posible iniciar la descarga.",
        ),
      );
    } finally {
      setStarting(false);
    }
  }

  const progress = status?.progress;

  return (
    <div
      className="hms-import-backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="hms-import-title"
    >
      <section className="hms-import-modal">
        <button
          className="hms-import-close"
          type="button"
          onClick={onClose}
          aria-label="Cerrar"
        >
          <X size={22} />
        </button>

        {loading ? (
          <div className="hms-logistics-loading">
            <LoaderCircle className="app-spin" size={38} />
            <h2>Preparando tu correo</h2>
            <p>
              Donexto está verificando el estado de la cuenta y contando
              el historial disponible.
            </p>
          </div>
        ) : null}

        {error ? (
          <div className="hms-import-error" role="alert">
            <AlertTriangle size={20} />
            <span>{error}</span>
          </div>
        ) : null}

        {!loading
        && status?.needs_initial_import
        && !status.active
        && inventory ? (
          <div className="hms-import-review">
            <div className="hms-import-review-scroll">
              <div className="hms-import-hero">
                <Image
                  src="/hms-import-robot.png"
                  alt="Robot Donexto organizando correo hacia una laptop"
                  width={1536}
                  height={1024}
                  priority
                  sizes="(max-width: 760px) 100vw, 430px"
                />

                <div>
                  <span className="hms-import-kicker">Donexto · Do Next To…</span>
                  <h2 id="hms-import-title">
                    Tu historial de seis meses está listo.
                  </h2>
                  <p>
                    Donexto descargará los mensajes elegibles de los últimos
                    6 meses, incluidos en tu cuenta, y después los clasificará
                    automáticamente.
                  </p>
                </div>
              </div>

              <section className="hms-import-summary">
                <div>
                  <Mail size={22} />
                  <span>Cuenta conectada</span>
                  <strong>{inventory.email}</strong>
                </div>
                <div>
                  <Clock3 size={22} />
                  <span>Periodo incluido</span>
                  <strong>
                    {formatLocalDate(inventory.period_start_local)}
                    {" – "}
                    {formatLocalDate(inventory.period_end_local)}
                  </strong>
                </div>
                <div className="is-primary">
                  <Inbox size={22} />
                  <span>Mensajes que se descargarán ahora</span>
                  <strong>
                    {inventory.eligible_messages.toLocaleString()}
                  </strong>
                </div>
              </section>

              <div className="hms-import-breakdown">
                {inventory.breakdown.map((item) => (
                  <article key={item.key}>
                    <span>{LABELS[item.key] ?? item.key}</span>
                    <strong>{item.count.toLocaleString()}</strong>
                  </article>
                ))}
              </div>

              <section className="hms-import-exclusions">
                <ShieldCheck size={22} />
                <div>
                  <strong>Exclusiones automáticas</strong>
                  <span>
                    Borradores {inventory.excluded.drafts.toLocaleString()}
                    {" · "}Spam {inventory.excluded.spam.toLocaleString()}
                    {" · "}Papelera {inventory.excluded.trash.toLocaleString()}
                  </span>
                  <small>
                    Donexto no borrará, archivará, marcará ni modificará
                    mensajes en el proveedor.
                  </small>
                </div>
              </section>

              <aside className="hms-import-plan-note">
                <strong>Qué incluye tu cuenta</strong>
                <p>
                  Cualquier usuario descarga y clasifica <b>6 meses</b> de
                  correo. Si más adelante quieres <b>12 meses</b>, lo cobramos
                  aparte; el precio lo definiremos cuando cerremos el costo
                  real de esa descarga. Si quieres <b>todo tu archivo</b>,
                  aplicamos una tarifa distinta según cuántos correos tengas
                  en total.
                </p>
              </aside>
            </div>

            <div className="hms-import-actions hms-import-actions--sticky">
              <button
                type="button"
                className="secondary"
                onClick={onClose}
              >
                Cancelar por ahora
              </button>
              <button
                type="button"
                disabled={starting}
                onClick={() => void start("initial")}
              >
                {starting ? (
                  <LoaderCircle className="app-spin" size={20} />
                ) : (
                  <Sparkles size={20} />
                )}
                {starting
                  ? "Iniciando…"
                  : `Descargar y clasificar ${inventory.eligible_messages.toLocaleString()} mensajes`}
              </button>
            </div>
          </div>
        ) : null}

        {!loading && status?.active && progress ? (
          <section className="hms-processing">
            <header>
              <span className="hms-import-kicker">Donexto · Do Next To…</span>
              <h2 id="hms-import-title">
                {status.phase === "classifying"
                  ? "Organizando tus pendientes"
                  : "Descargando tu correo"}
              </h2>
              <p>
                El proceso continúa aunque cierres esta pantalla.
                No vuelvas a iniciar otra descarga.
              </p>
            </header>

            <div className="hms-processing-robot" aria-hidden="true">
              <Image
                src="/hms-import-robot.png"
                alt=""
                width={1536}
                height={1024}
                priority
                sizes="(max-width: 760px) 94vw, 760px"
              />
            </div>

            <div className="hms-progress-block">
              <div className="hms-progress-heading">
                <span>Descarga</span>
                <strong>
                  {progress.downloaded.toLocaleString()}
                  {" de "}
                  {progress.expected
                    ? progress.expected.toLocaleString()
                    : "…"}
                </strong>
              </div>
              <div className="hms-progress-track">
                <span
                  style={{
                    width: `${progress.download_percent}%`,
                  }}
                />
              </div>
              <small>{progress.download_percent}% completado</small>
            </div>

            <div className="hms-progress-block">
              <div className="hms-progress-heading">
                <span>Clasificación</span>
                <strong>
                  {progress.classified.toLocaleString()}
                  {" analizados"}
                </strong>
              </div>
              <div className="hms-progress-track is-classification">
                <span
                  style={{
                    width: `${progress.classification_percent}%`,
                  }}
                />
              </div>
              <small>
                {progress.created_cases.toLocaleString()} casos nuevos
                {" · "}
                {progress.without_case.toLocaleString()} sin caso
              </small>
            </div>

            <div className="hms-live-categories">
              {Object.entries(progress.categories).map(
                ([key, value]) => (
                  <article key={key}>
                    <span>{LABELS[key] ?? key}</span>
                    <strong>{value.toLocaleString()}</strong>
                  </article>
                ),
              )}
            </div>

            {progress.errors > 0 ? (
              <div className="hms-import-error">
                <AlertTriangle size={20} />
                <span>
                  Se registraron {progress.errors} incidencias.
                  Donexto continuará con los mensajes restantes.
                </span>
              </div>
            ) : null}
          </section>
        ) : null}

        {!loading
        && status?.initial_import_complete
        && !status.active
        && status.phase === "ready" ? (
          <section className="hms-import-ready">
            <CheckCircle2 size={48} />
            <span className="hms-import-kicker">Donexto · Correo preparado</span>
            <h2 id="hms-import-title">
              Tu primera descarga ya está completa.
            </h2>
            <p>
              A partir de ahora Donexto descargará únicamente mensajes
              nuevos y volverá al dashboard al terminar.
            </p>

            <div className="hms-ready-stats">
              <article>
                <span>Descargados</span>
                <strong>
                  {status.progress.downloaded.toLocaleString()}
                </strong>
              </article>
              <article>
                <span>Clasificados</span>
                <strong>
                  {status.progress.classified.toLocaleString()}
                </strong>
              </article>
              <article>
                <span>Casos nuevos</span>
                <strong>
                  {status.progress.created_cases.toLocaleString()}
                </strong>
              </article>
              <article>
                <span>Sin caso</span>
                <strong>
                  {status.progress.without_case.toLocaleString()}
                </strong>
              </article>
            </div>

            <div className="hms-import-actions">
              <button
                type="button"
                className="secondary"
                onClick={onClose}
              >
                Volver al dashboard
              </button>
              <button
                type="button"
                disabled={starting}
                onClick={() => void start("incremental")}
              >
                {starting ? (
                  <LoaderCircle className="app-spin" size={20} />
                ) : (
                  <RefreshCw size={20} />
                )}
                {starting
                  ? "Buscando correo nuevo…"
                  : "Descargar correos nuevos"}
              </button>
            </div>
          </section>
        ) : null}

        {!loading && status?.phase === "failed" ? (
          <section className="hms-import-ready is-failed">
            <AlertTriangle size={48} />
            <span>REVISIÓN NECESARIA</span>
            <h2 id="hms-import-title">
              La descarga no pudo concluir.
            </h2>
            <p>
              El avance quedó guardado. Reabre esta pantalla para
              continuar desde el último lote.
            </p>
            <button
              type="button"
              onClick={() => void loadStatus()}
            >
              Reintentar
            </button>
          </section>
        ) : null}
      </section>
    </div>
  );
}
