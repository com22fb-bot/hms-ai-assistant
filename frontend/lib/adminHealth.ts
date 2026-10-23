// Estado mostrado por el semáforo de /admin, derivado SOLO de GET /admin/health (evaluación única).
export type HealthCheck = {
  id: string; label: string; critical: boolean;
  status: "ok" | "degradado" | "falla" | "sin_verificar";
  kind: string; evidence: string; checked_at: string; data_at?: string | null;
  source?: string; period?: string; threshold?: string; action?: string; impact?: string;
  hypothesis?: string; owner?: string; link?: string;
};
export type HealthIncident = {
  id: string; title: string; severity: string; status: string; occurred_at: string;
  meta?: { component?: string; kind?: string; check_status?: string; evidence?: string; hypothesis?: string;
    impact?: string; action?: string; owner?: string; link?: string; last_ok_at?: string | null;
    ok_streak?: number; transitions?: Array<{ at: string; to: string }> };
};
export type HealthPayload = {
  overall: { state: "VERDE" | "AMARILLO" | "ROJO"; reason: string };
  evaluated_at: string; cache_age_s: number; stale_after_s: number; recovery_policy: string;
  checks: HealthCheck[]; incidents: HealthIncident[];
};
export type LightState = "VERIFICANDO" | "VERDE" | "AMARILLO" | "ROJO";

/** Nunca verde con datos vencidos o sin respuesta. */
export function lightState(payload: HealthPayload | null, fetchFailed: boolean, nowMs: number): {
  state: LightState; note: string;
} {
  if (!payload) {
    return fetchFailed
      ? { state: "AMARILLO", note: "No se pudo obtener la evaluación de salud: estado no verificado." }
      : { state: "VERIFICANDO", note: "Verificando los servicios…" };
  }
  const age = (nowMs - Date.parse(payload.evaluated_at)) / 1000;
  if (!Number.isFinite(age) || age > payload.stale_after_s) {
    return { state: payload.overall.state === "ROJO" ? "ROJO" : "AMARILLO",
      note: `Evaluación vencida (hace ${Math.round(age / 60)} min): no se puede confirmar que todo esté bien.` };
  }
  if (fetchFailed && payload.overall.state === "VERDE") {
    return { state: "AMARILLO", note: "La última actualización falló; se muestra la evaluación anterior." };
  }
  return { state: payload.overall.state, note: payload.overall.reason };
}

export const KIND_LABEL: Record<string, string> = {
  ok: "Verificado", falla_propia: "Falla propia", proveedor_caido: "Proveedor caído",
  permiso: "Error de permisos", monitoreo: "Falla del monitoreo", vencido: "Datos vencidos",
  timeout: "Sin respuesta (timeout)", sin_datos: "Sin datos",
};
