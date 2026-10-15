/** /admin está fijo en español: traduce valores crudos del backend a etiquetas en español. */
const ES: Record<string, string> = {
  // tipos de queja/idea
  suggestion: "Sugerencia", complaint: "Queja", bug: "Falla", other: "Otro",
  // estados genéricos
  open: "Abierta", closed: "Cerrada", resolved: "Resuelta", new: "Nuevo", pending: "Pendiente",
  in_progress: "En curso", draft_ready: "Borrador listo", replied: "Respondido", archived: "Archivado",
  ok: "Funcionando", healthy: "Funcionando", degraded: "Con fallas", down: "Caído", error: "Error",
  // planes y suscripciones
  monthly: "Mensual", annual: "Anual", trial: "Prueba", trialing: "En prueba", active: "Activa",
  past_due: "Pago vencido", canceled: "Cancelada", cancelled: "Cancelada", unpaid: "Sin pagar",
  incomplete: "Incompleta", incomplete_expired: "Vencida", paused: "En pausa", owner: "Equipo", none: "Sin plan",
};

export function adminLabel(raw: string | null | undefined): string {
  if (!raw) return "—";
  const key = String(raw).trim().toLowerCase();
  return ES[key] ?? raw;
}
