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
import { useLanguage } from "@/lib/i18n/LanguageProvider";
import { importCategoryLabel, importText, type ImportKey } from "@/lib/i18n/importWizard";
import { downloadPlan } from "@/lib/importPlan";


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
  worlds?: { hogar: number; ocupacion: number; personal: number };
  areas?: Record<string, number>;
  review?: number;
  area_protected?: Record<string, Record<string, number>>;
  security?: number;
  protected?: Record<string, number>;
  social_platforms: Record<string, number>;
  scale: number;
  history_days: number;
  plan: PlanStatus;
  unavailable?: boolean;
  examples?: Record<string, string[]>;
  exact?: boolean;
  partial?: boolean;
  coverage?: number;
};

type World = "ocupacion" | "hogar" | "personal";
/** Taxonomía v2 (docs/TAXONOMIA_V2.md): 3 mundos · 7 áreas. Seguridad es alerta, no área; no hay "Otros". */
const AREAS: Array<{ id: string; label: string; sphere: World }> = [
  { id: "trabajo", label: "Trabajo y negocios", sphere: "ocupacion" },
  { id: "hogar", label: "Hogar y familia", sphere: "hogar" },
  { id: "dinero", label: "Dinero y facturas", sphere: "hogar" },
  { id: "compras", label: "Compras y suscripciones", sphere: "hogar" },
  { id: "salud", label: "Salud y seguros", sphere: "personal" },
  { id: "viajes", label: "Viajes y eventos", sphere: "personal" },
  { id: "promociones", label: "Promociones y social", sphere: "personal" },
];
const SPHERES: Array<{ id: World; label: string }> = [
  { id: "ocupacion", label: "Ocupación" },
  { id: "hogar", label: "Hogar" },
  { id: "personal", label: "Personal" },
];
/** Siempre se descargan (aunque su área esté desmarcada) mientras sigan encendidas. */
const PROTECTED: Array<{ id: string; label: string }> = [
  { id: "seguridad", label: "Seguridad" },
  { id: "bancos", label: "Bancos" },
  { id: "gobierno", label: "Gobierno" },
  { id: "facturas", label: "Facturas" },
  { id: "salud", label: "Salud" },
];
const PROTECT = "proteger:";
/** Redes que Donexto reconoce por el dominio del remitente. */
const SOCIAL_LIST = [
  "YouTube", "Instagram", "Facebook", "TikTok", "LinkedIn", "X/Twitter", "Snapchat", "Telegram",
  "WhatsApp", "Pinterest", "Reddit", "Discord", "Threads", "WeChat", "VK", "Twitch", "Tumblr",
  "Quora", "Bluesky", "LINE", "Weibo",
];

function planLabel(plan: PlanStatus | undefined, T: (key: ImportKey, vars?: Record<string, string | number>) => string): string {
  if (!plan) return "…";
  if (plan.state === "trial") {
    if (plan.days_left === null) return T("planTrial");
    return plan.days_left === 1 ? T("planTrialDay") : T("planTrialDays", { n: plan.days_left });
  }
  if (plan.state === "active") return plan.plan_code === "annual" ? T("planAnnual") : T("planMonthly");
  if (plan.state === "owner") return T("planOwner");
  return T("planNone");
}

function examplesFor(preview: Preview | null, id: string): string {
  return (preview?.examples?.[id] ?? []).join(", ");
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


function readableError(reason: unknown, fallback: string): string {
  return reason instanceof Error ? reason.message : fallback;
}

function formatLocalDate(value: string, locale: string): string {
  return new Intl.DateTimeFormat(locale, {
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
  const { language, locale } = useLanguage();
  const T = (key: ImportKey, vars?: Record<string, string | number>) => importText(language, key, vars);
  // Los efectos de carga/sondeo leen el idioma vigente sin reiniciarse al cambiarlo.
  const languageRef = useRef(language);
  useEffect(() => {
    languageRef.current = language;
  }, [language]);
  const [status, setStatus] = useState<ImportStatus | null>(null);
  const [inventory, setInventory] = useState<Inventory | null>(null);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [choice, setChoice] = useState<"all" | "custom">("all");
  const [exclude, setExclude] = useState<string[]>([]);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [focusArea, setFocusArea] = useState<string | null>(null);
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
    setPreviewLoading(true);
    void hmsJson<Preview>(`${API}/preview`, { cache: "no-store" })
      .then((value) => setPreview(value))
      .catch(() => setPreview(null))
      .finally(() => setPreviewLoading(false));
  }

  // Números = mensajes únicos que realmente se procesarán (misma regla que el backend: skip_message).
  const plan = preview && !preview.unavailable && preview.area_protected ? downloadPlan(preview, exclude) : null;
  const approx = preview && preview.exact && !preview.partial ? "" : "~";

  function countBadge(id: string) {
    if (!preview || preview.unavailable) return null;
    const raw = id === "revisar"
      ? preview.review ?? 0
      : id.startsWith(PROTECT)
        ? preview.protected?.[id.slice(PROTECT.length)] ?? 0
        : preview.areas?.[id] ?? 0;
    const value = estimate(raw, preview.scale);
    const sample = examplesFor(preview, id);
    return (
      <em
        title={sample ? T("examplesShort", { x: sample }) : undefined}
        onClick={(event) => {
          event.preventDefault();
          event.stopPropagation();
          setFocusArea((current) => (current === id ? null : id));
        }}
      >
        {preview.exact && !preview.partial ? "" : "~"}{value.toLocaleString()}
      </em>
    );
  }

  function num(value: number | undefined): string {
    if (!preview || preview.unavailable) return previewLoading ? "…" : "—";
    return `${preview.exact && !preview.partial ? "" : "~"}${estimate(value ?? 0, preview.scale).toLocaleString()}`;
  }

  function toggleWorld(world: World) {
    const ids = AREAS.filter((area) => area.sphere === world).map((area) => area.id);
    setExclude((current) => {
      const allOff = ids.every((id) => current.includes(id));
      return allOff ? current.filter((x) => !ids.includes(x)) : [...new Set([...current, ...ids])];
    });
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
              importText(languageRef.current, "errPrepare"),
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
                importText(languageRef.current, "errProgress"),
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
          T("errStart"),
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
          aria-label={T("close")}
        >
          <X size={22} />
        </button>

        {loading ? (
          <div className="hms-logistics-loading">
            <LoaderCircle className="app-spin" size={38} />
            <h2>{T("loadingTitle")}</h2>
            <p>
{T("loadingBody")}
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
                alt={T("robotAlt")}
                width={1536}
                height={1024}
                priority
                sizes="(max-width: 760px) 100vw, 430px"
              />

              <div>
                <span className="hms-import-kicker">Donexto · Do Next To…</span>
                <h2 id="hms-import-title">
{T("heroTitle")}
                </h2>
                <p>
{T("heroBody")}
                </p>
              </div>
            </div>

            <section className="hms-import-summary is-compact">
              <div>
                <Mail size={18} />
                <span>{T("account")}</span>
                <strong>{inventory.email}</strong>
              </div>
              <div>
                <Clock3 size={18} />
                <span>{T("period")}</span>
                <strong>
                  {inventory.history_days < 0
                    ? T("allHistory")
                    : formatLocalDate(inventory.period_start_local, locale)}
                  {" – "}
                  {formatLocalDate(inventory.period_end_local, locale)}
                </strong>
              </div>
              <div className="is-primary">
                <Inbox size={18} />
                <span>{T("eligible")}</span>
                <strong>
                  {inventory.eligible_messages.toLocaleString()}
                </strong>
              </div>
              <div>
                <BadgeCheck size={18} />
                <span>{T("plan")}</span>
                <strong>{planLabel(preview?.plan, T)}</strong>
              </div>
            </section>

            <p className="hms-import-line">
              {inventory.breakdown.map((item) => `${importCategoryLabel(language, item.key)} ${item.count.toLocaleString()}`).join(" · ")}
              {" · "}{T("excluded", { d: inventory.excluded.drafts.toLocaleString(), s: inventory.excluded.spam.toLocaleString(), t: inventory.excluded.trash.toLocaleString() })}
            </p>

            <section className="hms-import-alerts" aria-label={T("alerts")}>
              <div className="is-security">
                <ShieldCheck size={16} />
                <span>{T("security")}</span>
                <strong>{num(preview?.security)}</strong>
                <small>{T("securityHint")}</small>
              </div>
              <div>
                <Inbox size={16} />
                <span>{T("review")}</span>
                <strong>{num(preview?.review)}</strong>
                <small>{T("reviewHint")}</small>
              </div>
            </section>

            <section className="hms-import-spheres" aria-label={T("worldsPreview")}>
              {SPHERES.map((sphere) => (
                <article key={sphere.id}>
                  <span>{T(`w_${sphere.id}` as ImportKey)}</span>
                  <strong>{num((preview?.worlds ?? preview?.spheres)?.[sphere.id])}</strong>
                  <ul>
                    {AREAS.filter((area) => area.sphere === sphere.id).map((area) => (
                      <li key={area.id}>
                        {T(`a_${area.id}` as ImportKey)} <b>{num(preview?.areas?.[area.id])}</b>
                      </li>
                    ))}
                  </ul>
                </article>
              ))}
            </section>

            {previewLoading ? (
              <p className="hms-import-scan" role="status">
                <span aria-hidden="true" /> {T("scanning")}
              </p>
            ) : preview?.unavailable ? (
              <p className="hms-import-scan is-warn" role="status">{T("previewUnavailable")}</p>
            ) : preview ? (
              <p className="hms-import-scan is-done">
                {preview.partial
                  ? T("previewPartial", { n: preview.sampled.toLocaleString() })
                  : preview.exact
                    ? T("previewExact", { n: preview.sampled.toLocaleString() })
                    : T("previewSample", { n: preview.sampled.toLocaleString(), p: Math.round((preview.coverage ?? 0) * 100) })}
              </p>
            ) : null}

            <div className="hms-import-choice" role="radiogroup" aria-label={T("whatToDownload")}>
              <button
                type="button"
                role="radio"
                aria-checked={choice === "all"}
                className={choice === "all" ? "is-on" : ""}
                onClick={() => setChoice("all")}
              >
                {T("all")}
              </button>
              <button
                type="button"
                role="radio"
                aria-checked={choice === "custom"}
                className={choice === "custom" ? "is-on" : ""}
                onClick={() => setChoice("custom")}
              >
                {T("custom")}
              </button>
              <small>
                <ShieldCheck size={14} /> {T("readOnly")}
              </small>
            </div>

            {choice === "custom" ? (
              <section className="hms-import-custom" aria-label={T("categoriesToImport")}>
                <p>{T("customHelp")}</p>
                {SPHERES.map((sphere) => {
                  const ids = AREAS.filter((area) => area.sphere === sphere.id).map((area) => area.id);
                  const worldOff = ids.every((id) => exclude.includes(id));
                  return (
                    <div key={sphere.id} className="hms-import-world">
                      <label className={`hms-import-world-head ${worldOff ? "is-off" : ""}`}>
                        <input type="checkbox" checked={!worldOff} onChange={() => toggleWorld(sphere.id)} />
                        <b>{T(`w_${sphere.id}` as ImportKey)}</b>
                      </label>
                      <div className="hms-import-chips">
                        {AREAS.filter((area) => area.sphere === sphere.id).map((area) => (
                          <label key={area.id} className={exclude.includes(area.id) ? "is-off" : ""}>
                            <input type="checkbox" checked={!exclude.includes(area.id)} onChange={() => toggle(area.id)} />
                            {T(`a_${area.id}` as ImportKey)}
                            {countBadge(area.id)}
                          </label>
                        ))}
                      </div>
                    </div>
                  );
                })}
                <div className="hms-import-chips">
                  <label className={exclude.includes("revisar") ? "is-off" : ""}>
                    <input type="checkbox" checked={!exclude.includes("revisar")} onChange={() => toggle("revisar")} />
                    {T("review")}
                    {countBadge("revisar")}
                  </label>
                </div>
                {focusArea && examplesFor(preview, focusArea) ? (
                  <p className="hms-import-examples" role="status">
                    {T("examples", { x: examplesFor(preview, focusArea) })}
                  </p>
                ) : null}
                <div className="hms-import-world is-protected">
                  <span className="hms-import-world-head">
                    <ShieldCheck size={14} /> <b>{T("protectedTitle")}</b> · {T("protectedSub")}
                  </span>
                  <p className="hms-import-protected-note">
{T("protectedNote")}
                  </p>
                  <div className="hms-import-chips">
                    {PROTECTED.map((item) => {
                      const key = PROTECT + item.id;
                      return (
                        <label key={key} className={exclude.includes(key) ? "is-off" : ""}>
                          <input type="checkbox" checked={!exclude.includes(key)} onChange={() => toggle(key)} />
                          {T(`p_${item.id}` as ImportKey)}
                          {countBadge(key)}
                        </label>
                      );
                    })}
                  </div>
                </div>
                <p className="hms-import-social-list">
                  {T("socialList")}{" "}
                  {(Object.keys(preview?.social_platforms ?? {}).length
                    ? Object.keys(preview?.social_platforms ?? {})
                    : SOCIAL_LIST
                  ).join(" · ")}
                </p>
              </section>
            ) : null}

            {choice === "custom" && plan && exclude.some((id) => !id.startsWith(PROTECT)) ? (
              <p className="hms-import-plan" data-testid="import-plan">
                {T("planSummary", {
                  n: `${approx}${estimate(plan.to_process, preview?.scale ?? 1).toLocaleString()}`,
                  s: `${approx}${estimate(plan.selected, preview?.scale ?? 1).toLocaleString()}`,
                  p: `${approx}${estimate(plan.protected, preview?.scale ?? 1).toLocaleString()}`,
                  x: `${approx}${estimate(plan.excluded, preview?.scale ?? 1).toLocaleString()}`,
                })}
              </p>
            ) : null}

            <div className="hms-import-actions">
              <button
                type="button"
                className="secondary"
                onClick={onClose}
              >
{T("cancel")}
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
                  ? T("starting")
                  : choice === "custom" && exclude.some((id) => !id.startsWith(PROTECT))
                    ? plan
                      ? T("startChosenN", { n: `${approx}${estimate(plan.to_process, preview?.scale ?? 1).toLocaleString()}` })
                      : T("startChosen")
                    : T("startAll", { n: inventory.eligible_messages.toLocaleString() })}
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
                  ? T("organizing")
                  : T("downloadingMail")}
              </h2>
              <p>
{T("keepsRunning")}
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
                <span>{T("download")}</span>
                <strong>
                  {progress.downloaded.toLocaleString()}
                  {` ${T("of")} `}
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
              <small>{T("completed", { p: progress.download_percent })}</small>
            </div>

            <div className="hms-progress-block">
              <div className="hms-progress-heading">
                <span>{T("classification")}</span>
                <strong>
                  {progress.classified.toLocaleString()}
                  {` ${T("analyzed")}`}
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
                {progress.created_cases.toLocaleString()} {T("newCases")}
                {" · "}
                {progress.without_case.toLocaleString()} {T("withoutCase")}
              </small>
            </div>

            <div className="hms-live-categories">
              {Object.entries(progress.categories).map(
                ([key, value]) => (
                  <article key={key}>
                    <span>{importCategoryLabel(language, key)}</span>
                    <strong>{value.toLocaleString()}</strong>
                  </article>
                ),
              )}
            </div>

            {progress.errors > 0 ? (
              <div className="hms-import-error">
                <AlertTriangle size={20} />
                <span>
{T("incidents", { n: progress.errors })}
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
            <span className="hms-import-kicker">{T("readyKicker")}</span>
            <h2 id="hms-import-title">
{T("readyTitle")}
            </h2>
            <p>
{T("readyBody")}
            </p>

            <div className="hms-ready-stats">
              <article>
                <span>{T("downloaded")}</span>
                <strong>
                  {status.progress.downloaded.toLocaleString()}
                </strong>
              </article>
              <article>
                <span>{T("classified")}</span>
                <strong>
                  {status.progress.classified.toLocaleString()}
                </strong>
              </article>
              <article>
                <span>{T("newCasesTitle")}</span>
                <strong>
                  {status.progress.created_cases.toLocaleString()}
                </strong>
              </article>
              <article>
                <span>{T("withoutCaseTitle")}</span>
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
{T("backToDashboard")}
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
                  ? T("searchingNew")
                  : T("downloadNew")}
              </button>
            </div>
          </section>
        ) : null}

        {!loading && status?.phase === "failed" ? (
          <section className="hms-import-ready is-failed">
            <AlertTriangle size={48} />
            <span>{T("reviewNeeded")}</span>
            <h2 id="hms-import-title">
              {status.failure?.reconnect_required
                ? T("reconnectTitle")
                : T("failedTitle")}
            </h2>
            <p>
              {status.failure?.message
                || T("failedBody")}
            </p>
            <div className="hms-import-actions">
              {status.failure?.reconnect_required && onReconnect ? (
                <button
                  type="button"
                  className="secondary"
                  onClick={onReconnect}
                >
{T("reconnect")}
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
                {starting ? T("retrying") : T("retry")}
              </button>
            </div>
          </section>
        ) : null}
      </section>
    </div>
  );
}
