"use client";

import Image from "next/image";
import {
  AlertTriangle,
  BadgeCheck,
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
import { shouldSurfacePollError } from "@/lib/networkRetry";


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

type PlanStatus = {
  state: "trial" | "active" | "owner" | "none";
  plan_code: string | null;
  days_left: number | null;
  history_days: number;
};

type Preview = {
  sampled: number;
  categories: Record<string, number>;
  spheres: { hogar: number; ocupacion: number; personal: number };
  social_platforms: Record<string, number>;
  scale: number;
  history_days: number;
  plan: PlanStatus;
  unavailable?: boolean;
};

/** 13 áreas (catalogo-maestro.yaml) con su esfera por defecto. */
const AREAS: Array<{ id: string; label: string; sphere: "hogar" | "ocupacion" | "personal" }> = [
  { id: "money", label: "Dinero", sphere: "personal" },
  { id: "bills", label: "Recibos", sphere: "hogar" },
  { id: "orders", label: "Pedidos", sphere: "personal" },
  { id: "subscriptions", label: "Suscripciones", sphere: "personal" },
  { id: "work", label: "Trabajo", sphere: "ocupacion" },
  { id: "home", label: "Hogar y familia", sphere: "hogar" },
  { id: "health", label: "Salud", sphere: "personal" },
  { id: "travel", label: "Viajes", sphere: "personal" },
  { id: "security", label: "Seguridad", sphere: "personal" },
  { id: "government", label: "Trámites", sphere: "personal" },
  { id: "insurance", label: "Seguros", sphere: "hogar" },
  { id: "education", label: "Educación", sphere: "personal" },
  { id: "agenda", label: "Agenda", sphere: "ocupacion" },
];
const SPHERES: Array<{ id: "hogar" | "ocupacion" | "personal"; label: string }> = [
  { id: "hogar", label: "Hogar" },
  { id: "ocupacion", label: "Ocupación" },
  { id: "personal", label: "Personal" },
];
/** Redes que Donexto reconoce por el dominio del remitente. */
const SOCIAL_LIST = [
  "YouTube", "Instagram", "Facebook", "TikTok", "LinkedIn", "X/Twitter", "Snapchat", "Telegram",
  "WhatsApp", "Pinterest", "Reddit", "Discord", "Threads", "WeChat", "VK", "Twitch", "Tumblr",
  "Quora", "Bluesky", "LINE", "Weibo",
];

function planLabel(plan: PlanStatus | undefined): string {
  if (!plan) return "…";
  if (plan.state === "trial") {
    return plan.days_left === null ? "Prueba gratis" : `Prueba: ${plan.days_left} ${plan.days_left === 1 ? "día" : "días"}`;
  }
  if (plan.state === "active") return plan.plan_code === "annual" ? "Plan anual" : "Plan mensual";
  if (plan.state === "owner") return "Cuenta del equipo";
  return "Sin plan";
}

function estimate(count: number, scale: number): number {
  return Math.round(count * (scale || 1));
}

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
  failure?: {
    reason: "auth" | "error";
    reconnect_required: boolean;
    message: string;
  } | null;
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
  onReconnect,
}: {
  onClose: () => void;
  onComplete: () => void;
  /** Opens the mailbox picker so an expired/revoked permission can be renewed. */
  onReconnect?: () => void;
}) {
  const [status, setStatus] = useState<ImportStatus | null>(null);
  const [inventory, setInventory] = useState<Inventory | null>(null);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [choice, setChoice] = useState<"all" | "custom">("all");
  const [exclude, setExclude] = useState<string[]>([]);
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
    // Vista previa por esferas/áreas: no bloquea el botón de descarga.
    void hmsJson<Preview>(`${API}/preview`, { cache: "no-store" })
      .then((value) => setPreview(value))
      .catch(() => setPreview(null));
  }

  function toggle(id: string) {
    setExclude((current) => current.includes(id) ? current.filter((x) => x !== id) : [...current, id]);
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
    let failures = 0;
    let inFlight = false;

    // One dropped progress check (phone locked, app switched, Wi-Fi <-> data)
    // must not paint a scary error: the download keeps running on the server.
    const poll = () => {
      if (inFlight) return;
      inFlight = true;
      void loadStatus()
        .then(() => {
          failures = 0;
          setError(null);
        })
        .catch((reason) => {
          failures += 1;
          if (shouldSurfacePollError(failures)) {
            setError(
              readableError(
                reason,
                "No fue posible actualizar el progreso.",
              ),
            );
          }
        })
        .finally(() => {
          inFlight = false;
        });
    };

    const timer = window.setInterval(poll, 1500);
    const onVisible = () => {
      if (document.visibilityState === "visible") poll();
    };
    document.addEventListener("visibilitychange", onVisible);
    window.addEventListener("online", poll);

    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisible);
      window.removeEventListener("online", poll);
    };
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
        body: JSON.stringify({
          mode,
          exclude: mode === "initial" && choice === "custom" ? exclude : [],
        }),
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
      <section className={`hms-import-modal${status?.needs_initial_import && !status.active ? " is-review" : ""}`}>
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
          <>
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
                  Tu historial de correo está listo.
                </h2>
                <p>
                  Elige si traemos todo o solo lo que te importa. Después
                  Donexto lo clasifica en tus 3 esferas y 13 áreas.
                </p>
              </div>
            </div>

            <section className="hms-import-summary is-compact">
              <div>
                <Mail size={18} />
                <span>Cuenta conectada</span>
                <strong>{inventory.email}</strong>
              </div>
              <div>
                <Clock3 size={18} />
                <span>Periodo</span>
                <strong>
                  {formatLocalDate(inventory.period_start_local)}
                  {" – "}
                  {formatLocalDate(inventory.period_end_local)}
                </strong>
              </div>
              <div className="is-primary">
                <Inbox size={18} />
                <span>Mensajes elegibles</span>
                <strong>
                  {inventory.eligible_messages.toLocaleString()}
                </strong>
              </div>
              <div>
                <BadgeCheck size={18} />
                <span>Tu plan</span>
                <strong>{planLabel(preview?.plan)}</strong>
              </div>
            </section>

            <p className="hms-import-line">
              {inventory.breakdown.map((item) => `${LABELS[item.key] ?? item.key} ${item.count.toLocaleString()}`).join(" · ")}
              {" · "}Excluidos siempre: borradores {inventory.excluded.drafts.toLocaleString()}, spam {inventory.excluded.spam.toLocaleString()}, papelera {inventory.excluded.trash.toLocaleString()}
            </p>

            <section className="hms-import-spheres" aria-label="Vista previa por esferas">
              {SPHERES.map((sphere) => (
                <article key={sphere.id}>
                  <span>{sphere.label}</span>
                  <strong>{preview ? `~${estimate(preview.spheres[sphere.id], preview.scale).toLocaleString()}` : "…"}</strong>
                  <small>
                    {AREAS.filter((area) => area.sphere === sphere.id)
                      .map((area) => area.label)
                      .join(" · ")}
                  </small>
                </article>
              ))}
            </section>

            <div className="hms-import-choice" role="radiogroup" aria-label="Qué descargar">
              <button
                type="button"
                role="radio"
                aria-checked={choice === "all"}
                className={choice === "all" ? "is-on" : ""}
                onClick={() => setChoice("all")}
              >
                Bajar todo
              </button>
              <button
                type="button"
                role="radio"
                aria-checked={choice === "custom"}
                className={choice === "custom" ? "is-on" : ""}
                onClick={() => setChoice("custom")}
              >
                Personalizado
              </button>
              <small>
                <ShieldCheck size={14} /> Solo lectura: Donexto no borra, archiva, marca ni mueve nada en tu correo.
              </small>
            </div>

            {choice === "custom" ? (
              <section className="hms-import-custom" aria-label="Categorías a importar">
                <p>Desmarca lo que no quieres traer. Lo que quites no se descarga.</p>
                <div className="hms-import-chips">
                  {AREAS.map((area) => (
                    <label key={area.id} className={exclude.includes(area.id) ? "is-off" : ""}>
                      <input type="checkbox" checked={!exclude.includes(area.id)} onChange={() => toggle(area.id)} />
                      {area.label}
                      {preview?.categories[area.id] ? <em>~{estimate(preview.categories[area.id], preview.scale)}</em> : null}
                    </label>
                  ))}
                  <label className={exclude.includes("promos") ? "is-off" : ""}>
                    <input type="checkbox" checked={!exclude.includes("promos")} onChange={() => toggle("promos")} />
                    Promociones
                    {preview?.categories.promos ? <em>~{estimate(preview.categories.promos, preview.scale)}</em> : null}
                  </label>
                  <label className={exclude.includes("other") ? "is-off" : ""}>
                    <input type="checkbox" checked={!exclude.includes("other")} onChange={() => toggle("other")} />
                    Otros
                  </label>
                </div>
                <label className={`hms-import-social ${exclude.includes("social") ? "is-off" : ""}`}>
                  <input type="checkbox" checked={!exclude.includes("social")} onChange={() => toggle("social")} />
                  <span>
                    <b>Redes sociales</b>
                    {preview?.categories.social ? <em> ~{estimate(preview.categories.social, preview.scale)}</em> : null}
                    <small>
                      {(Object.keys(preview?.social_platforms ?? {}).length
                        ? Object.keys(preview?.social_platforms ?? {})
                        : SOCIAL_LIST
                      ).join(" · ")}
                    </small>
                  </span>
                </label>
              </section>
            ) : null}

            <div className="hms-import-actions">
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
                  : choice === "custom" && exclude.length
                    ? "Descargar lo elegido y clasificar"
                    : `Descargar y clasificar ${inventory.eligible_messages.toLocaleString()} mensajes`}
              </button>
            </div>
          </>
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
              {status.failure?.reconnect_required
                ? "Tu correo necesita reconectarse."
                : "La descarga no pudo concluir."}
            </h2>
            <p>
              {status.failure?.message
                || "El avance quedó guardado. Toca Reintentar para continuar con el correo nuevo."}
            </p>
            <div className="hms-import-actions">
              {status.failure?.reconnect_required && onReconnect ? (
                <button
                  type="button"
                  className="secondary"
                  onClick={onReconnect}
                >
                  Reconectar correo
                </button>
              ) : null}
              <button
                type="button"
                disabled={starting}
                onClick={() => void start(
                  status.initial_import_complete ? "incremental" : "initial",
                )}
              >
                {starting ? (
                  <LoaderCircle className="app-spin" size={20} />
                ) : (
                  <RefreshCw size={20} />
                )}
                {starting ? "Reintentando…" : "Reintentar"}
              </button>
            </div>
          </section>
        ) : null}
      </section>
    </div>
  );
}
