"use client";

import { ChevronDown, ChevronUp, Loader2, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { hmsJson } from "@/lib/hmsApi";
import {
  EXPENSES_CHANGED_EVENT,
  PAYMENTS_AGENDA_PATH,
  REFRESH_MS,
  SEVERITY_COLOR,
  SEVERITY_TITLE,
  daysPhrase,
  donutSegments,
  fmtDate,
  fmtDateShort,
  fxText,
  groupBySeverity,
  mxn,
  timelinePct,
  updatedAgo,
  usd,
  type PayItem,
  type PaymentsAgenda as Agenda,
} from "@/lib/paymentsAgenda";

const COLLAPSE_KEY = "dx-pay-collapsed";

function useLiveAgenda() {
  const [data, setData] = useState<Agenda | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fetchedAt, setFetchedAt] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const inflight = useRef(false);

  const load = useCallback(async () => {
    if (inflight.current) return;
    inflight.current = true;
    setBusy(true);
    try {
      const result = await hmsJson<Agenda>(PAYMENTS_AGENDA_PATH, { cache: "no-store" });
      setData(result);
      setError(null);
      setFetchedAt(Date.now());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "No se pudo actualizar la agenda.");
    } finally {
      inflight.current = false;
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    const first = window.requestAnimationFrame(() => void load());
    // Tiempo real: cada 60 s con la pestaña visible, al volver a ella y cuando cambia Mis gastos.
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") void load();
    }, REFRESH_MS);
    const onVisible = () => {
      if (document.visibilityState === "visible") void load();
    };
    const onChange = () => void load();
    document.addEventListener("visibilitychange", onVisible);
    window.addEventListener("focus", onVisible);
    window.addEventListener(EXPENSES_CHANGED_EVENT, onChange);
    return () => {
      window.cancelAnimationFrame(first);
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisible);
      window.removeEventListener("focus", onVisible);
      window.removeEventListener(EXPENSES_CHANGED_EVENT, onChange);
    };
  }, [load]);

  return { data, error, fetchedAt, busy, load };
}

function useNow(stepMs = 15_000): number {
  const [now, setNow] = useState(0);
  useEffect(() => {
    const first = window.requestAnimationFrame(() => setNow(Date.now()));
    const id = window.setInterval(() => setNow(Date.now()), stepMs);
    return () => {
      window.cancelAnimationFrame(first);
      window.clearInterval(id);
    };
  }, [stepMs]);
  return now;
}

function Timeline({ data }: { data: Agenda }) {
  const horizon = data.timeline_days;
  const marks = data.items
    .map((item) => ({ item, pct: timelinePct(item.days, horizon) }))
    .filter((m): m is { item: PayItem; pct: number } => m.pct !== null);
  // Etiquetas cercanas se apilan en niveles para no encimarse (como en la imagen).
  const lastAt: number[] = [];
  const placed = marks.map((m) => {
    let level = 0;
    while (lastAt[level] !== undefined && m.pct - lastAt[level] < 20 && level < 2) level += 1;
    lastAt[level] = m.pct;
    return { ...m, level };
  });
  const end = new Date(`${data.today}T12:00:00Z`);
  end.setUTCDate(end.getUTCDate() + horizon);
  const endIso = end.toISOString().slice(0, 10);
  const hasEstimated = marks.some((m) => m.item.estimated);

  return (
    <div className="dx-pay__card dx-pay__timeline" aria-label={`Próximos ${horizon} días`}>
      <div className="dx-pay__track-wrap">
        <div className="dx-pay__track" />
        <span className="dx-pay__tick dx-pay__tick--start" />
        <span className="dx-pay__tick dx-pay__tick--end" />
        {placed.map(({ item, pct, level }) => (
          <div
            key={item.id}
            className="dx-pay__mark"
            style={{ left: `${pct}%`, ["--sev" as string]: SEVERITY_COLOR[item.severity] }}
            title={`${item.servicio} · ${fmtDate(item.on)} · ${daysPhrase(item.days)}`}
          >
            <span className="dx-pay__mark-label" style={{ bottom: `${22 + level * 34}px` }}>
              <strong>{item.servicio}</strong>
              <em>{fmtDateShort(item.on)}{item.estimated ? "*" : ""}</em>
            </span>
            <span className="dx-pay__mark-stem" style={{ height: `${10 + level * 34}px` }} />
            <span className="dx-pay__dot" />
          </div>
        ))}
      </div>
      <div className="dx-pay__track-legend">
        <span>hoy</span>
        <span>{fmtDateShort(endIso)}</span>
      </div>
      {hasEstimated && <p className="dx-pay__foot">* fecha estimada</p>}
    </div>
  );
}

function ItemCard({ item }: { item: PayItem }) {
  const color = SEVERITY_COLOR[item.severity];
  const isKey = item.tipo === "llave";
  const meta = [item.tipo, fmtDate(item.on), isKey ? item.label : null, item.estimated ? "estimada" : null].filter(Boolean);
  return (
    <article className="dx-pay__item" style={{ ["--sev" as string]: color }} data-severity={item.severity}>
      <header>
        <h4><i aria-hidden />{item.servicio}</h4>
        <span className="dx-pay__when">{daysPhrase(item.days)}</span>
      </header>
      <p className="dx-pay__meta">{meta.join(" · ")}</p>
      {isKey ? (
        <p className="dx-pay__free">Sin costo · no es una licencia</p>
      ) : (
        <p className="dx-pay__amount">
          <strong>{item.cost_estimated ? "~" : ""}{usd(item.usd)}</strong>
          <span>{mxn(item.mxn)}</span>
        </p>
      )}
      {item.action && !isKey && <p className="dx-pay__action">{item.action}</p>}
    </article>
  );
}

function Later({ items }: { items: PayItem[] }) {
  return (
    <ul className="dx-pay__card dx-pay__later">
      {items.map((item) => (
        <li key={item.id}>
          <span className="dx-pay__later-name">
            <i aria-hidden />
            {item.servicio}
            {item.tipo === "llave" ? <em> · {item.label === "API" ? "token API" : item.label}</em> : null}
          </span>
          <span className="dx-pay__later-right">
            {item.tipo !== "llave" && item.usd > 0 ? `${item.cost_estimated ? "~" : ""}${usd(item.usd)} · ` : ""}
            {fmtDate(item.on)}
          </span>
        </li>
      ))}
    </ul>
  );
}

function Donut({ data }: { data: Agenda }) {
  const segs = donutSegments(data.monthly.parts);
  const r = 42;
  const c = 2 * Math.PI * r;
  return (
    <div className="dx-pay__card dx-pay__donut">
      <div className="dx-pay__donut-chart">
        <svg viewBox="0 0 120 120" role="img" aria-label={`Gasto mensual ${usd(data.monthly.usd)}`}>
          <circle cx="60" cy="60" r={r} fill="none" stroke="#243048" strokeWidth="18" />
          {segs.map((s) => (
            <circle
              key={s.servicio}
              cx="60" cy="60" r={r} fill="none" stroke={s.color} strokeWidth="18"
              strokeDasharray={`${Math.max(0, s.frac * c - 1.2)} ${c}`}
              strokeDashoffset={-s.start * c}
              transform="rotate(-90 60 60)"
            />
          ))}
        </svg>
        <div className="dx-pay__donut-center">
          <strong>{usd(data.monthly.usd)}</strong>
          <span>al mes</span>
        </div>
      </div>
      <div className="dx-pay__donut-info">
        <span className="dx-pay__muted">Total</span>
        <strong className="dx-pay__total">{usd(data.monthly.usd)}</strong>
        <span className="dx-pay__total-mxn">{mxn(data.monthly.mxn)}</span>
        <span className="dx-pay__muted dx-pay__small">
          TC {fxText(data.fx.usd_mxn)}{data.fx.date ? ` · ${fmtDate(data.fx.date)}` : ""} · {data.fx.source}
        </span>
        <ul className="dx-pay__legend">
          {segs.map((s) => (
            <li key={s.servicio}><i style={{ background: s.color }} aria-hidden />{s.servicio} <b>{usd(s.usd)}</b></li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export function PaymentsAgenda() {
  const { data, error, fetchedAt, busy, load } = useLiveAgenda();
  const now = useNow();
  return <PaymentsAgendaView data={data} error={error} fetchedAt={fetchedAt} busy={busy} now={now} onRefresh={() => void load()} />;
}

type ViewProps = {
  data: Agenda | null;
  error: string | null;
  fetchedAt: number | null;
  busy: boolean;
  now: number;
  onRefresh: () => void;
};

/** Vista pura (sin red): la usa el panel en vivo y el render de vista previa. */
export function PaymentsAgendaView({ data, error, fetchedAt, busy, now, onRefresh }: ViewProps) {
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => {
      try {
        setCollapsed(window.localStorage.getItem(COLLAPSE_KEY) === "1");
      } catch {
        /* almacenamiento bloqueado: se queda abierta */
      }
    });
    return () => window.cancelAnimationFrame(frame);
  }, []);

  function toggle() {
    const next = !collapsed;
    setCollapsed(next);
    try {
      window.localStorage.setItem(COLLAPSE_KEY, next ? "1" : "0");
    } catch {
      /* sin almacenamiento */
    }
  }

  const groups = data ? groupBySeverity(data.items) : [];
  const soon = groups.filter(([sev]) => sev !== "luego");
  const later = groups.find(([sev]) => sev === "luego")?.[1] ?? [];
  const statusColor = data ? SEVERITY_COLOR[data.counts.rojo ? "rojo" : "verde"] : SEVERITY_COLOR.verde;

  return (
    <section className="dx-pay" aria-labelledby="dx-pay-title" data-testid="payments-agenda">
      <header className="dx-pay__head">
        <div>
          <p className="dx-pay__eyebrow">Donexto</p>
          <h2 id="dx-pay-title">Agenda de pagos y vencimientos</h2>
          {data && <p className="dx-pay__date">{fmtDate(data.today)} · hora CDMX</p>}
        </div>
        <div className="dx-pay__head-actions">
          <span className="dx-pay__live" aria-live="polite">
            <i className={busy ? "is-busy" : ""} aria-hidden />
            {updatedAgo(fetchedAt, now || fetchedAt || 0)}
          </span>
          <button type="button" className="dx-pay__icon" onClick={onRefresh} disabled={busy} aria-label="Actualizar agenda">
            <RefreshCw size={15} className={busy ? "dx-admin__spin" : undefined} />
          </button>
          <button type="button" className="dx-pay__icon" onClick={toggle} aria-expanded={!collapsed} aria-label={collapsed ? "Mostrar agenda" : "Ocultar agenda"}>
            {collapsed ? <ChevronDown size={16} /> : <ChevronUp size={16} />}
          </button>
        </div>
      </header>

      {data && (
        <p className="dx-pay__status" style={{ ["--sev" as string]: statusColor }}>{data.headline}</p>
      )}
      {error && <p className="dx-pay__error" role="alert">No se pudo actualizar: {error}{data ? " · se muestran los últimos datos" : ""}</p>}
      {!data && !error && (
        <p className="dx-pay__muted"><Loader2 size={14} className="dx-admin__spin" aria-hidden /> Cargando agenda…</p>
      )}

      {data && !collapsed && (
        <div className="dx-pay__grid">
          <div className="dx-pay__col">
            <h3 className="dx-pay__section">Próximos {data.timeline_days} días</h3>
            <Timeline data={data} />
            {soon.length === 0 && <p className="dx-pay__muted">Nada por pagar ni por vencer en los próximos {data.timeline_days} días.</p>}
            {soon.map(([sev, list]) => (
              <div key={sev} className="dx-pay__group">
                <h3 className="dx-pay__section"><i style={{ background: SEVERITY_COLOR[sev] }} aria-hidden />{SEVERITY_TITLE[sev]}</h3>
                <div className="dx-pay__items">
                  {list.map((item) => <ItemCard key={item.id} item={item} />)}
                </div>
              </div>
            ))}
          </div>
          <div className="dx-pay__col">
            {later.length > 0 && (
              <div className="dx-pay__group">
                <h3 className="dx-pay__section"><i style={{ background: SEVERITY_COLOR.luego }} aria-hidden />Más adelante</h3>
                <Later items={later} />
              </div>
            )}
            <div className="dx-pay__group">
              <h3 className="dx-pay__section"><i style={{ background: "#4fdec4" }} aria-hidden />Gasto mensual fijo</h3>
              <Donut data={data} />
            </div>
            <p className="dx-pay__foot">
              Montos en US$ y MXN · las llaves no son un cargo · 🔴 vencido o ≤3 días · 🟠 4–14 · 🟢 15–60
            </p>
          </div>
        </div>
      )}
    </section>
  );
}
