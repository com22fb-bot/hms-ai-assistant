"use client";

import { useCallback, useEffect, useState } from "react";

import { hmsJson } from "@/lib/hmsApi";
import { KIND_LABEL, lightState, type HealthPayload } from "@/lib/adminHealth";

const POLL_MS = 60_000;
const STATE_TEXT = {
  VERIFICANDO: "Verificando",
  VERDE: "Todo verificado",
  AMARILLO: "Degradado o sin verificar",
  ROJO: "Incidencia crítica",
} as const;

function when(iso?: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? "—"
    : d.toLocaleString("es-MX", { timeZone: "America/Mexico_City", dateStyle: "short", timeStyle: "short" }) + " (CDMX)";
}

export function HealthBar() {
  const [payload, setPayload] = useState<HealthPayload | null>(null);
  const [failed, setFailed] = useState(false);
  const [open, setOpen] = useState(false);
  const [now, setNow] = useState(() => Date.now());

  const load = useCallback(async (force = false) => {
    try {
      const data = await hmsJson<HealthPayload>(`/api/hms/admin/health${force ? "?force=true" : ""}`);
      setPayload(data);
      setFailed(false);
    } catch {
      setFailed(true);
    }
    setNow(Date.now());
  }, []);

  useEffect(() => {
    void load();
    const id = window.setInterval(() => void load(), POLL_MS);
    const tick = window.setInterval(() => setNow(Date.now()), 15_000);
    return () => { window.clearInterval(id); window.clearInterval(tick); };
  }, [load]);

  const { state, note } = lightState(payload, failed, now);
  const problems = (payload?.checks || []).filter((c) => c.status !== "ok");

  return (
    <section className={`dx-health dx-health--${state.toLowerCase()}`} aria-live="polite" data-testid="admin-health">
      <button type="button" className="dx-health__bar" onClick={() => setOpen((v) => !v)} aria-expanded={open}>
        <span className="dx-health__dot" aria-hidden />
        <strong>{state}</strong>
        <span className="dx-health__label">{STATE_TEXT[state]}</span>
        <span className="dx-health__note">{note}</span>
        <span className="dx-health__meta">
          {payload ? `Evaluado ${when(payload.evaluated_at)} · caché ${Math.round(payload.cache_age_s)} s` : ""}
        </span>
      </button>
      {open && payload && (
        <div className="dx-health__detail">
          {payload.incidents.length > 0 && (
            <>
              <h3>Incidentes abiertos</h3>
              <ul className="dx-health__list">
                {payload.incidents.map((i) => (
                  <li key={i.id}>
                    <strong>{i.title}</strong> · {i.severity} · {i.meta?.check_status || i.status}
                    <div>Detectado: {when(i.occurred_at)} · Última comprobación OK: {when(i.meta?.last_ok_at)}</div>
                    <div>Categoría: {KIND_LABEL[i.meta?.kind || ""] || i.meta?.kind} · Evidencia: {i.meta?.evidence}</div>
                    {i.meta?.hypothesis && <div>Causa / hipótesis: {i.meta.hypothesis}</div>}
                    {i.meta?.impact && <div>Impacto: {i.meta.impact}</div>}
                    {i.meta?.action && <div>Acción: {i.meta.action} · Responsable: {i.meta.owner || "—"}</div>}
                    {i.meta?.link && <a href={i.meta.link} target="_blank" rel="noreferrer">Abrir servicio</a>}
                  </li>
                ))}
              </ul>
            </>
          )}
          <h3>Comprobaciones</h3>
          <ul className="dx-health__list">
            {payload.checks.map((c) => (
              <li key={c.id} className={`is-${c.status}`}>
                <strong>{c.label}</strong>{c.critical ? " (crítico)" : ""}: {c.status.replace("_", " ")} ·{" "}
                {KIND_LABEL[c.kind] || c.kind}
                <div>{c.evidence}</div>
                <small>
                  Fuente: {c.source || "—"}{c.period ? ` · Periodo: ${c.period}` : ""} · Comprobado: {when(c.checked_at)}
                  {" · Dato de: "}{c.data_at ? when(c.data_at) : "sin datos"}
                  {c.threshold ? ` · Umbral: ${c.threshold}` : ""}
                </small>
                {c.status !== "ok" && c.action && <div>Acción: {c.action}</div>}
              </li>
            ))}
          </ul>
          <p className="dx-health__policy">
            {problems.length === 0 ? "Sin problemas detectados. " : ""}Recuperación de incidentes: {payload.recovery_policy}.
          </p>
          <button type="button" className="dx-admin__btn dx-admin__btn--ghost" onClick={() => void load(true)}>
            Volver a verificar
          </button>
        </div>
      )}
    </section>
  );
}
