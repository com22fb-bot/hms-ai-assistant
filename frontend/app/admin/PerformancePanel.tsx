"use client";

import { Loader2, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { hmsJson } from "@/lib/hmsApi";
import { KIND_LABEL, type HealthPayload } from "@/lib/adminHealth";

type Missing = { available: false; status: string; variable?: string; steps?: string[]; message?: string; kind?: string };

type Railway = (Missing | { available: true; status: "ok" }) & {
  region?: string | null;
  replica_id?: string | null;
  cpu_vcpu?: number | null;
  cpu_vcpu_peak_24h?: number | null;
  cpu_limit?: number | null;
  memory_gb?: number | null;
  memory_gb_peak_24h?: number | null;
  memory_limit_gb?: number | null;
  cpu_series?: number[];
  memory_series?: number[];
  last_deploy?: { status?: string; created_at?: string };
};

type Database = (Missing | { available: true; status: "ok" }) & {
  db_size_bytes?: number;
  used_pct?: number | null;
  emails_total?: number;
  emails_first_at?: string | null;
  emails_last_30d?: number;
  mailboxes_active?: number;
  users_total?: number;
  users_active_30d?: number;
  connections_active?: number;
  connections_total?: number;
  top_tables?: Array<{ name: string; bytes: number }>;
  slow_queries?: Array<{ query?: string | null; calls?: number | null; mean_ms?: number | null; total_s?: number | null }> | null;
};

type Cloudflare = (Missing | { available: true; status: "ok" }) & {
  requests_7d?: number;
  threats_7d?: number;
  cached_pct?: number | null;
  period?: string;
  days?: Array<{ date: string; requests: number; threats: number }>;
};

type Site = { label: string; url: string; ok: boolean; status: number | null; ms: number | null };

type Perf = {
  railway: Railway;
  database: Database;
  cloudflare: Cloudflare;
  sites: Site[];
  generated_at: string;
  cache_seconds: number;
  health?: HealthPayload | null;
  process: {
    uptime_seconds: number;
    memory_rss_mb: number | null;
    cpu_percent_avg: number;
    sample_size: number;
    p50_ms: number | null;
    p95_ms: number | null;
    error_rate_pct: number | null;
    started_at?: number;
    window?: string;
    counters_reset?: string;
    routes: Array<{ route: string; count: number; avg_ms: number; p95_ms: number }>;
    counters: Record<string, number>;
  };
};

const nf = new Intl.NumberFormat("es-MX");

function mb(bytes?: number): string {
  if (!bytes && bytes !== 0) return "—";
  return `${nf.format(Math.round(bytes / 1024 / 1024))} MB`;
}

function CheckBadge({ health, ids }: { health?: HealthPayload | null; ids: string[] }) {
  const checks = (health?.checks || []).filter((c) => ids.includes(c.id));
  if (!health || checks.length === 0) return <span className="dx-admin__pill">No verificado</span>;
  const order = ["falla", "sin_verificar", "degradado", "ok"];
  const worst = checks.slice().sort((a, b) => order.indexOf(a.status) - order.indexOf(b.status))[0];
  const cls = worst.status === "ok" ? "is-ok" : "is-warn";
  return (
    <span className={`dx-admin__pill ${cls}`} title={worst.evidence}>
      {worst.status === "ok" ? "Verificado" : KIND_LABEL[worst.kind] || worst.status}
    </span>
  );
}

function val(v: number | null | undefined, unit: string): string {
  return v == null ? "Sin datos" : `${v}${unit}`;
}

function num(v: number | null | undefined): string {
  return v == null ? "Sin datos" : nf.format(v);
}

function uptime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return h >= 24 ? `${Math.floor(h / 24)} d ${h % 24} h` : `${h} h ${m} min`;
}

function when(value?: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("es-MX", { dateStyle: "short", timeStyle: "short" });
}

function Spark({ values }: { values?: number[] }) {
  if (!values || values.length < 2) return null;
  const max = Math.max(...values) || 1;
  const points = values
    .map((v, i) => `${(i / (values.length - 1)) * 100},${28 - (v / max) * 26}`)
    .join(" ");
  return (
    <svg className="dx-perf__spark" viewBox="0 0 100 30" preserveAspectRatio="none" aria-hidden>
      <polyline points={points} />
    </svg>
  );
}

function Meter({ pct }: { pct?: number | null }) {
  const value = Math.min(Math.max(pct ?? 0, 0), 100);
  const tone = value >= 80 ? "is-bad" : value >= 60 ? "is-warn" : "is-ok";
  return (
    <div className={`dx-perf__meter ${tone}`} role="meter" aria-valuenow={value} aria-valuemin={0} aria-valuemax={100}>
      <i style={{ width: `${value}%` }} />
    </div>
  );
}

function MissingToken({ data }: { data: Missing }) {
  if (data.status !== "falta_token") {
    return (
      <p className="dx-perf__warn">
        {data.kind === "permiso"
          ? "Error de permisos del monitoreo (no indica caída del proveedor): "
          : data.kind === "proveedor_caido"
            ? "El proveedor no responde: "
            : "Error de consulta: "}
        {data.message || data.status}
      </p>
    );
  }
  return (
    <details className="dx-perf__missing">
      <summary>
        Falta token <code>{data.variable}</code> — ver pasos
      </summary>
      <ol>
        {(data.steps || []).map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ol>
    </details>
  );
}

/** Acepta solo filas objeto; cualquier otra forma cuenta como "Sin datos" (evita <li> vacíos). */
function slowList(v: unknown): Array<{ query?: string | null; calls?: number | null; mean_ms?: number | null; total_s?: number | null }> {
  return Array.isArray(v) ? v.filter((x) => x && typeof x === "object") : [];
}

export function PerformancePanel() {
  const [data, setData] = useState<Perf | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await hmsJson<Perf>("/api/hms/admin/performance", { cache: "no-store" }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "No fue posible cargar el rendimiento.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => void load());
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") void load();
    }, 60_000);
    return () => {
      window.cancelAnimationFrame(frame);
      window.clearInterval(timer);
    };
  }, [load]);

  if (!data) {
    return (
      <section className="dx-admin__section">
        {error ? <p className="dx-admin__alert">{error}</p> : <p className="dx-admin__loading"><Loader2 className="dx-admin__spin" size={18} /> Cargando rendimiento…</p>}
      </section>
    );
  }

  const { railway: rw, database: db, cloudflare: cf, process: pr } = data;
  const cpuPct = rw.cpu_vcpu != null && rw.cpu_limit ? (rw.cpu_vcpu / rw.cpu_limit) * 100 : null;
  const memPct = rw.memory_gb != null && rw.memory_limit_gb ? (rw.memory_gb / rw.memory_limit_gb) * 100 : null;

  return (
    <section className="dx-admin__section dx-perf">
      <header className="dx-perf__head">
        <div>
          <h2>Rendimiento</h2>
          <p>Datos en vivo · se renuevan cada {data.cache_seconds} s · {when(data.generated_at)}</p>
        </div>
        <button type="button" className="dx-admin__btn dx-admin__btn--ghost" onClick={() => void load()} disabled={loading}>
          {loading ? <Loader2 className="dx-admin__spin" size={16} /> : <RefreshCw size={16} />} Actualizar
        </button>
      </header>
      {error && <p className="dx-admin__alert">{error}</p>}

      <div className="dx-perf__grid">
        <article className="dx-perf__card">
          <h3>Servidor (Railway) <CheckBadge health={data.health} ids={["railway"]} /></h3>
          {rw.available ? (
            <>
              <div className="dx-perf__row"><span>CPU</span><strong>{rw.cpu_vcpu == null ? "Sin datos" : `${rw.cpu_vcpu.toFixed(3)} / ${rw.cpu_limit ?? "?"} vCPU`}</strong></div>
              <Meter pct={cpuPct} />
              <Spark values={rw.cpu_series} />
              <div className="dx-perf__row"><span>Memoria</span><strong>{rw.memory_gb == null ? "Sin datos" : `${(rw.memory_gb * 1024).toFixed(0)} MB / ${rw.memory_limit_gb ?? "?"} GB`}</strong></div>
              <Meter pct={memPct} />
              <Spark values={rw.memory_series} />
              <div className="dx-perf__row"><span>Pico 24 h</span><strong>{rw.memory_gb_peak_24h == null ? "Sin datos" : `${(rw.memory_gb_peak_24h * 1024).toFixed(0)} MB`}</strong></div>
              <div className="dx-perf__row"><span>Último deploy</span><strong>{rw.last_deploy?.status || "—"} · {when(rw.last_deploy?.created_at)}</strong></div>
            </>
          ) : (
            <MissingToken data={rw as Missing} />
          )}
          <div className="dx-perf__row"><span>Región · réplica</span><strong>{rw.region || "—"} · {rw.replica_id || "—"}</strong></div>
        </article>

        <article className="dx-perf__card">
          <h3>Proceso backend <CheckBadge health={data.health} ids={["api", "errors"]} /></h3>
          <div className="dx-perf__kpis">
            <div><span>p50</span><strong>{val(pr.p50_ms, " ms")}</strong></div>
            <div><span>p95</span><strong>{val(pr.p95_ms, " ms")}</strong></div>
            <div><span>Errores</span><strong>{val(pr.error_rate_pct, "%")}</strong></div>
            <div><span>Encendido</span><strong>{uptime(pr.uptime_seconds)}</strong></div>
          </div>
          <p className="dx-perf__hint">Periodo: {pr.window || "últimas 24 h"}; encendido desde {pr.started_at ? when(new Date(pr.started_at * 1000).toISOString()) : "—"}.</p>
          <div className="dx-perf__row"><span>Peticiones (24 h)</span><strong>{nf.format(pr.sample_size)}</strong></div>
          <div className="dx-perf__row"><span>Memoria proceso</span><strong>{pr.memory_rss_mb ?? "—"} MB</strong></div>
          <ul className="dx-perf__routes">
            {pr.routes.slice(0, 5).map((r) => (
              <li key={r.route}><code>{r.route}</code><span>{r.count} · {r.avg_ms} ms · p95 {r.p95_ms}</span></li>
            ))}
          </ul>
        </article>

        <article className="dx-perf__card">
          <h3>Base de datos (Supabase) <CheckBadge health={data.health} ids={["database", "db_quota"]} /></h3>
          {db.available ? (
            <>
              <div className="dx-perf__row"><span>Tamaño</span><strong>{mb(db.db_size_bytes)} / 500 MB ({val(db.used_pct, "%")}) · plan Free verificado</strong></div>
              <Meter pct={db.used_pct} />
              <div className="dx-perf__kpis">
                <div><span>Correos</span><strong>{num(db.emails_total)}</strong></div>
                <div><span>Últimos 30 d</span><strong>{num(db.emails_last_30d)}</strong></div>
                <div><span>Buzones</span><strong>{num(db.mailboxes_active)}</strong></div>
                <div><span>Usuarios</span><strong>{num(db.users_total)}</strong></div>
              </div>
              <div className="dx-perf__row"><span>Desde</span><strong>{when(db.emails_first_at)}</strong></div>
              <div className="dx-perf__row"><span>Conexiones</span><strong>{db.connections_active} activas / {db.connections_total}</strong></div>
              <ul className="dx-perf__routes">
                {(db.top_tables || []).slice(0, 4).map((t) => (
                  <li key={t.name}><code>{t.name}</code><span>{mb(t.bytes)}</span></li>
                ))}
              </ul>
              <details className="dx-perf__missing" data-testid="slow-queries">
                <summary>Consultas más lentas ({slowList(db.slow_queries).length || "—"})</summary>
                {db.slow_queries === null || db.slow_queries === undefined ? (
                  <p>Error de consulta (sin acceso a pg_stat_statements)</p>
                ) : slowList(db.slow_queries).length === 0 ? (
                  <p>Sin datos</p>
                ) : (
                  <ol>
                    {slowList(db.slow_queries).map((q, i) => (
                      <li key={i}>
                        <code>{q.query || "(texto no disponible)"}</code>
                        {" — "}promedio {q.mean_ms ?? "Sin datos"} ms · total {q.total_s ?? "Sin datos"} s · {q.calls ?? "Sin datos"} llamadas
                      </li>
                    ))}
                  </ol>
                )}
                <p className="dx-perf__hint">Fuente: pg_stat_statements (texto normalizado, sin valores; acumulado desde el último reinicio de estadísticas).</p>
              </details>
            </>
          ) : (
            <MissingToken data={db as Missing} />
          )}
        </article>

        <article className="dx-perf__card">
          <h3>Seguridad</h3>
          <div className="dx-perf__kpis">
            <div><span>Accesos directos bloqueados</span><strong>{num(pr.counters.direct_access_403)}</strong></div>
            <div><span>Límite de intentos</span><strong>{num(pr.counters.rate_limit_blocks)}</strong></div>
            <div><span>Sin sesión (401)</span><strong>{num(pr.counters.unauthorized_401)}</strong></div>
            <div><span>Errores 5xx</span><strong>{num(pr.counters.errors_5xx)}</strong></div>
          </div>
          <p className="dx-perf__hint">{pr.counters_reset || "Contadores desde el último encendido del servidor."} Un 0 aquí no prueba que no hubo incidentes antes de ese momento.</p>
          <h4><CheckBadge health={data.health} ids={["cloudflare"]} /> Cloudflare ({cf.period || "7 días"})</h4>
          {cf.available ? (
            <div className="dx-perf__kpis">
              <div><span>Peticiones</span><strong>{num(cf.requests_7d)}</strong></div>
              <div><span>Amenazas</span><strong>{num(cf.threats_7d)}</strong></div>
              <div><span>Desde caché</span><strong>{val(cf.cached_pct, "%")}</strong></div>
            </div>
          ) : (
            <MissingToken data={cf as Missing} />
          )}
        </article>

        <article className="dx-perf__card dx-perf__card--wide">
          <h3>Sitio donexto.com <CheckBadge health={data.health} ids={["frontend", "landing"]} /></h3>
          <ul className="dx-perf__sites">
            {data.sites.map((s) => (
              <li key={s.url} className={s.ok ? "is-ok" : "is-bad"}>
                <i aria-hidden />
                <span>{s.label}</span>
                <strong>{s.status ?? "sin respuesta"}</strong>
                <em>{s.ms != null ? `${s.ms} ms` : "—"}</em>
              </li>
            ))}
          </ul>
        </article>
      </div>
    </section>
  );
}
