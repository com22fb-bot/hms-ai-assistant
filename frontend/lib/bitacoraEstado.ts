// Estado de las entradas de la Bitácora de /admin (lógica pura, probada en bitacoraEstado.test.ts).
export type PedidoEstado = "pendiente" | "en_curso" | "hecho";
export type EventStatus = "abierto" | "resuelto";
export type HistorialItem = { estado: PedidoEstado; at: string };
export type EstadoEvent = {
  status: EventStatus;
  ended_at?: string | null;
  meta?: { kind?: string; estado?: PedidoEstado; historial?: HistorialItem[]; [k: string]: unknown } | null;
};

export const ESTADO_ORDER: Record<PedidoEstado, number> = { pendiente: 0, en_curso: 1, hecho: 2 };
export const ESTADO_LABEL: Record<PedidoEstado, string> = { pendiente: "Pendiente", en_curso: "En curso", hecho: "Realizado" };
export const ESTADOS = Object.keys(ESTADO_ORDER) as PedidoEstado[];

const isEstado = (v: unknown): v is PedidoEstado => typeof v === "string" && Object.prototype.hasOwnProperty.call(ESTADO_ORDER, v);

/** Estado mostrado: meta.estado si existe (seguimiento explícito); si no, se deriva de status (eventos antiguos). */
export function estadoOf(e: EstadoEvent): PedidoEstado {
  const m = e.meta?.estado;
  if (isEstado(m)) return m;
  return e.status === "resuelto" ? "hecho" : "pendiente";
}

export const isPedido = (e: EstadoEvent) => e.meta?.kind === "pedido";
export const sinTerminar = (e: EstadoEvent) => estadoOf(e) !== "hecho";

/** Filtro Estado: compara contra el mismo estado que se muestra en la fila. */
export const matchesEstado = (e: EstadoEvent, f: PedidoEstado | "") => !f || estadoOf(e) === f;

/**
 * Cambios para cerrar una entrada. Siempre status=resuelto + ended_at.
 * Si la entrada tiene seguimiento explícito (meta.estado o pedido), también meta.estado=hecho
 * y agrega {hecho, at} al historial solo si el último registrado no es ya "hecho".
 * Los eventos antiguos sin meta.estado no reciben meta (comportamiento previo).
 */
export function closePatch(item: EstadoEvent, nowIso: string): {
  status: "resuelto";
  ended_at: string;
  meta?: NonNullable<EstadoEvent["meta"]>;
} {
  const patch: { status: "resuelto"; ended_at: string; meta?: NonNullable<EstadoEvent["meta"]> } = {
    status: "resuelto",
    ended_at: item.status === "resuelto" && item.ended_at ? item.ended_at : nowIso,
  };
  const meta = item.meta;
  if (!meta || (!isEstado(meta.estado) && meta.kind !== "pedido")) return patch;
  const hist = Array.isArray(meta.historial) ? [...meta.historial] : [];
  if (hist.length === 0 || hist[hist.length - 1]?.estado !== "hecho") hist.push({ estado: "hecho", at: nowIso });
  patch.meta = { ...meta, estado: "hecho", historial: hist };
  return patch;
}
