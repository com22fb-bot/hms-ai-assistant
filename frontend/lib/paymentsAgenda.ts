// Agenda de pagos y vencimientos de /admin: tipos y formato (sin React, probado con node --test).
// Datos: GET /api/hms/admin/payments-agenda (hora CDMX, semáforo calculado en el backend).

export type PaySeverity = "rojo" | "naranja" | "verde" | "luego";

export type PayItem = {
  id: string;
  servicio: string;
  tipo: "pago" | "renovación" | "llave";
  on: string;
  usd: number;
  mxn: number;
  currency: string;
  estimated: boolean;
  cost_estimated: boolean;
  period: string;
  label: string;
  action: string;
  source: string;
  days: number;
  severity: PaySeverity;
};

export type PaymentsAgenda = {
  today: string;
  timezone: string;
  generated_at: string;
  timeline_days: number;
  headline: string;
  status: PaySeverity;
  counts: Record<PaySeverity, number>;
  severity_labels: Record<PaySeverity, string>;
  fx: { usd_mxn: number; source: string; date: string | null };
  items: PayItem[];
  monthly: { usd: number; mxn: number; fx: number; parts: Array<{ servicio: string; usd: number; mxn: number }> };
  notes: string[];
};

export const PAYMENTS_AGENDA_PATH = "/api/hms/admin/payments-agenda";
export const REFRESH_MS = 60_000;
/** Evento que disparan Mis gastos (alta, edición, borrado, TC) para refrescar la agenda al instante. */
export const EXPENSES_CHANGED_EVENT = "dx-admin-expenses-changed";

export const SEVERITY_ORDER: PaySeverity[] = ["rojo", "naranja", "verde", "luego"];
export const SEVERITY_TITLE: Record<PaySeverity, string> = {
  rojo: "Vencido o en 3 días",
  naranja: "En 4–14 días",
  verde: "En 15–60 días",
  luego: "Más adelante",
};
export const SEVERITY_COLOR: Record<PaySeverity, string> = {
  rojo: "#f0534a",
  naranja: "#f5a524",
  verde: "#2fbf8b",
  luego: "#8d9aad",
};
/** Colores de la dona del gasto mensual (mismo orden que la imagen aprobada). */
export const DONUT_COLORS = ["#4fdec4", "#f5a524", "#5b9cf5", "#c4b5fd", "#f0534a", "#2fbf8b", "#8d9aad"];

const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];

function parts(iso: string): [number, number, number] {
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return [y, m, d];
}

/** 7-dic-2026 */
export function fmtDate(iso: string): string {
  const [y, m, d] = parts(iso);
  return `${d}-${MESES[m - 1]}-${y}`;
}

/** 7 dic */
export function fmtDateShort(iso: string): string {
  const [, m, d] = parts(iso);
  return `${d} ${MESES[m - 1]}`;
}

const NUM = new Intl.NumberFormat("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
export const usd = (v: number) => `US$${NUM.format(v || 0)}`;
export const mxn = (v: number) => `MXN ${NUM.format(v || 0)}`;
export const fxText = (v: number) => String(Math.round(v * 1e6) / 1e6);

export function daysPhrase(days: number): string {
  if (days < 0) return -days === 1 ? "vencido hace 1 día" : `vencido hace ${-days} días`;
  if (days === 0) return "vence hoy";
  if (days === 1) return "en 1 día";
  return `en ${days} días`;
}

export function tipoText(item: PayItem): string {
  return item.tipo === "llave" ? "llave" : item.tipo;
}

/** "Actualizado hace X" a partir de la hora del último refresco. */
export function updatedAgo(fetchedAt: number | null, now: number): string {
  if (fetchedAt === null) return "Actualizando…";
  const s = Math.max(0, Math.round((now - fetchedAt) / 1000));
  if (s < 10) return "Actualizado justo ahora";
  if (s < 60) return `Actualizado hace ${s} s`;
  const m = Math.floor(s / 60);
  if (m < 60) return `Actualizado hace ${m} min`;
  const h = Math.floor(m / 60);
  return `Actualizado hace ${h} h`;
}

export function groupBySeverity(items: PayItem[]): Array<[PaySeverity, PayItem[]]> {
  return SEVERITY_ORDER.map((sev) => [sev, items.filter((i) => i.severity === sev)] as [PaySeverity, PayItem[]])
    .filter(([, list]) => list.length > 0);
}

/** Posición (0–100 %) en la línea de tiempo de N días; null si cae fuera. Vencidos se fijan en 0. */
export function timelinePct(days: number, horizon: number): number | null {
  if (days > horizon) return null;
  return Math.max(0, Math.min(100, (days / horizon) * 100));
}

/** Segmentos de la dona (fracciones que suman 1). */
export function donutSegments(parts: Array<{ servicio: string; usd: number }>): Array<{ servicio: string; usd: number; frac: number; start: number; color: string }> {
  const total = parts.reduce((s, p) => s + Math.max(0, p.usd), 0);
  if (total <= 0) return [];
  let start = 0;
  return parts.map((p, i) => {
    const frac = Math.max(0, p.usd) / total;
    const seg = { ...p, frac, start, color: DONUT_COLORS[i % DONUT_COLORS.length] };
    start += frac;
    return seg;
  });
}

/** Semáforo de un gasto de Mis gastos por su próximo cobro (mismos umbrales que la agenda). */
export function severityForDays(days: number): PaySeverity {
  if (days <= 3) return "rojo";
  if (days <= 14) return "naranja";
  if (days <= 60) return "verde";
  return "luego";
}

/** Días entre hoy (CDMX) y una fecha ISO (AAAA-MM-DD). */
export function daysUntil(iso: string, todayIso: string): number {
  const a = Date.UTC(...(parts(todayIso).map((v, i) => (i === 1 ? v - 1 : v)) as [number, number, number]));
  const b = Date.UTC(...(parts(iso).map((v, i) => (i === 1 ? v - 1 : v)) as [number, number, number]));
  return Math.round((b - a) / 86_400_000);
}

/** Fecha de hoy en Ciudad de México (AAAA-MM-DD). */
export function todayCdmx(now: Date = new Date()): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Mexico_City", year: "numeric", month: "2-digit", day: "2-digit" }).format(now);
}
