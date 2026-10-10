/**
 * Agrupación de avisos repetidos (catalogo-maestro.yaml · agrupacion).
 * Clave de evento = marca + tema + ventana de tiempo, por usuario (todos sus
 * buzones). El mismo aviso de seguridad de Google en 10 correos o 3 buzones
 * se ve como UN caso ×N. Los códigos de verificación se agrupan por marca en
 * 24 h, van a "Cuando puedas" (prioridad baja) y nunca muestran el código.
 */
import { brandFromEmail } from "./explain.ts";
import type { LifeItem } from "./lifeAreas.ts";

const DAY = 864e5;
const SECURITY_KINDS = new Set(["security_alert", "security_copy", "app_access", "recovery_email", "password"]);
const WINDOW_DAYS: Record<string, number> = { security_alert: 7, verification_code: 1, social: 1, default: 3 };
const PRIORITY_RANK: Record<string, number> = { low: 0, normal: 1, high: 2, critical: 3 };
const CODE_DIGITS = /(?<![\d-])\d{4,8}(?![\d-])/g;

export function maskCodes<T extends string | null | undefined>(text: T): T {
  return (typeof text === "string" ? text.replace(CODE_DIGITS, "••••••") : text) as T;
}

function fold(value: string): string {
  return value.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

function subjectKey(value: string): string {
  return fold(value)
    .replace(/^\s*((re|rv|fw|fwd)\s*:\s*)+/g, "")
    .replace(/\b(para|for|pour|per)\s+\S+@\S+/g, "")
    .replace(/\S+@\S+/g, "")
    .replace(/\d+/g, "#")
    .replace(/[^\p{L}#]+/gu, " ")
    .trim();
}

export function topicOf(item: LifeItem): string {
  const kind = item.kind || item.insight?.kind || "";
  if (kind === "verification_code") return "verification_code";
  if (SECURITY_KINDS.has(kind)) return "security_alert";
  if (kind === "social") return "social";
  return "";
}

export function eventKeyOf(item: LifeItem): { key: string; windowDays: number } {
  const brand = (brandFromEmail(item.senderEmail) || item.sender || "").toLowerCase().trim();
  const topic = topicOf(item);
  if (topic && brand) return { key: `${brand}:${topic}`, windowDays: WINDOW_DAYS[topic] };
  const subject = subjectKey(item.subject ?? item.title);
  return { key: `${brand}:subject:${subject}`, windowDays: WINDOW_DAYS.default };
}

export function isVerificationCode(item: LifeItem): boolean {
  return topicOf(item) === "verification_code";
}

function time(value: string): number {
  const t = Date.parse(value);
  return Number.isNaN(t) ? 0 : t;
}

/** Une los avisos del mismo evento. El más reciente representa al grupo. */
export function groupLifeItems(items: LifeItem[]): LifeItem[] {
  const sorted = [...items].sort((a, b) => time(b.when) - time(a.when));
  const groups: Array<{ key: string; windowDays: number; oldest: number; rep: LifeItem; members: LifeItem[] }> = [];
  for (const item of sorted) {
    const { key, windowDays } = eventKeyOf(item);
    // Sin asunto ni marca: no hay evidencia para agrupar.
    if (key.endsWith(":subject:") || key === ":subject:") {
      groups.push({ key: `${key}${item.id}`, windowDays, oldest: time(item.when), rep: item, members: [item] });
      continue;
    }
    const at = time(item.when);
    const group = groups.find((g) => g.key === key && g.oldest - at <= windowDays * DAY);
    if (group) {
      group.members.push(item);
      group.oldest = Math.min(group.oldest, at);
    } else {
      groups.push({ key, windowDays, oldest: at, rep: item, members: [item] });
    }
  }
  return groups.map(({ rep, members }) => {
    const code = isVerificationCode(rep);
    const count = members.reduce((sum, m) => sum + Math.max(1, m.sourceCount || 1), 0);
    const priority = code
      ? "low"
      : members.reduce((best, m) => ((PRIORITY_RANK[m.priority] ?? 1) > (PRIORITY_RANK[best] ?? 1) ? m.priority : best), rep.priority);
    const open = members.find((m) => m.status !== "resolved" && m.status !== "closed");
    const next: LifeItem = {
      ...rep,
      priority,
      status: open ? open.status : rep.status,
      sourceCount: count,
      groupCount: members.length,
      groupIds: members.map((m) => m.id),
    };
    if (members.length > 1 && !/×\d+$/.test(next.line)) next.line = `${next.line} ×${members.length}`;
    if (code) {
      next.title = maskCodes(next.title);
      next.line = maskCodes(next.line);
      next.subject = maskCodes(next.subject);
      next.preview = maskCodes(next.preview);
    }
    return next;
  }).sort((a, b) => b.when.localeCompare(a.when));
}
