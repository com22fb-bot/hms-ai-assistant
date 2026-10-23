// Centro de control /admin (diseño Figma aprobado): helpers puros y testeables.
// Nunca exponen correo, IDs ni hashes: solo proveedor, estado, fechas y conteos.
import type { HealthCheck, HealthPayload } from "./adminHealth";

export const SIN_DATO = "sin dato";

export function showValue(value: number | null | undefined): string {
  return value == null || !Number.isFinite(value) ? SIN_DATO : value.toLocaleString("es-MX");
}

export function checkMark(status: HealthCheck["status"]): { mark: string; tone: "ok" | "warn" | "bad"; text: string } {
  if (status === "ok") return { mark: "✓", tone: "ok", text: "verificado" };
  if (status === "falla") return { mark: "✕", tone: "bad", text: "falla" };
  if (status === "degradado") return { mark: "⚠", tone: "warn", text: "degradado" };
  return { mark: "?", tone: "warn", text: "sin verificar" };
}

/** Uso de BD desde el check db_quota de /admin/health ("21 MB de 500 MB (plan Free) = 4.2 %"). */
export function dbUsage(payload: HealthPayload | null): { usedMb: number; limitMb: number; pct: number } | null {
  const c = payload?.checks?.find((x) => x.id === "db_quota");
  if (!c || c.status === "sin_verificar") return null;
  const m = /(\d+(?:\.\d+)?)\s*MB de\s*(\d+)\s*MB.*?=\s*(\d+(?:\.\d+)?)\s*%/.exec(c.evidence || "");
  if (!m) return null;
  return { usedMb: Number(m[1]), limitMb: Number(m[2]), pct: Number(m[3]) };
}

const PROVIDER: Record<string, string> = {
  gmail: "Gmail", google: "Gmail", microsoft: "Outlook", outlook: "Outlook", yahoo: "Yahoo",
  icloud: "iCloud", imap: "IMAP",
};
export function providerLabel(p?: string | null): string {
  if (!p) return SIN_DATO;
  return PROVIDER[p.toLowerCase()] || p;
}
export function mailboxStatus(s?: string | null): { label: string; tone: "ok" | "warn" | "bad" | "info" } {
  const v = (s || "").toLowerCase();
  if (["connected", "active", "ok", "synced", "conectado"].includes(v)) return { label: "Conectado", tone: "ok" };
  if (["error", "failed", "revoked", "invalid", "expired", "needs_reauth"].includes(v)) return { label: "Error de acceso", tone: "bad" };
  if (["syncing", "pending", "queued", "importing"].includes(v)) return { label: "En cola", tone: "info" };
  if (["disconnected", "paused", "disabled"].includes(v)) return { label: "Desconectado", tone: "warn" };
  return { label: s ? s : SIN_DATO, tone: "warn" };
}

export type MailboxIn = { provider?: string | null; status?: string | null; last_sync_at?: string | null; messages?: number | null };
export type MailboxRow = { n: number; provider: string; status: string; tone: string; lastSync: string | null; messages: number | null };
/** Filas anónimas: “Buzón 1…n”, sin correo ni ID. */
export function mailboxRows(users: Array<{ mailboxes?: MailboxIn[] | null }>): MailboxRow[] {
  const rows: MailboxRow[] = [];
  for (const u of users) for (const b of u.mailboxes || []) {
    const st = mailboxStatus(b.status);
    rows.push({ n: rows.length + 1, provider: providerLabel(b.provider), status: st.label, tone: st.tone,
      lastSync: b.last_sync_at ?? null, messages: typeof b.messages === "number" ? b.messages : null });
  }
  return rows;
}
export function providerSummary(rows: MailboxRow[]): Array<[string, number]> {
  const m = new Map<string, number>();
  rows.forEach((r) => m.set(r.provider, (m.get(r.provider) || 0) + 1));
  return [...m.entries()].sort((a, b) => b[1] - a[1]);
}

export type PedidoEstado = "pendiente" | "en_curso" | "hecho";
export const ESTADO_LABEL: Record<PedidoEstado, string> = { pendiente: "Pendiente", en_curso: "En curso", hecho: "Realizado" };
const ORDER: Record<PedidoEstado, number> = { pendiente: 0, en_curso: 1, hecho: 2 };
export type PedidoIn = { title: string; occurred_at: string; status?: string; meta?: { kind?: string; estado?: string } | null };
export function estadoOf(e: PedidoIn): PedidoEstado {
  const s = e.meta?.estado as PedidoEstado | undefined;
  return s && s in ORDER ? s : e.status === "resuelto" ? "hecho" : "pendiente";
}
/** Pendiente > En curso > Realizado; dentro de cada estado, más reciente primero. */
export function orderPedidos<T extends PedidoIn>(events: T[], limit = 6): T[] {
  return events.filter((e) => e.meta?.kind === "pedido")
    .sort((a, b) => ORDER[estadoOf(a)] - ORDER[estadoOf(b)] || b.occurred_at.localeCompare(a.occurred_at))
    .slice(0, limit);
}
