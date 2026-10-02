/**
 * "Tus 10 pendientes principales": a rule-based ranking (no AI) of the open
 * items Donexto found in the user's mail, by urgency, due date and
 * importance. Shown once after the first completed mail classification and
 * reachable later from Hoy.
 */

import { dueBucket, type DueBucket } from "./commandCenter.ts";
import { isOpenStatus, type LifeAreaId, type LifeItem } from "./lifeAreas.ts";

const HOUR = 36e5;

/** Why an item made the list (shown as a small chip). */
export type TopReason = "overdue" | "today" | "tomorrow" | "week" | "security" | "money" | "priority" | "recent";

export type TopItem = { item: LifeItem; score: number; reason: TopReason; bucket: DueBucket };

const PRIORITY_POINTS: Record<string, number> = { critical: 60, high: 40, normal: 12, medium: 12, low: 0 };

const DUE_POINTS: Record<DueBucket, number> = { overdue: 70, today: 65, tomorrow: 50, week: 32, later: 10, none: 0 };

const AREA_POINTS: Record<LifeAreaId, number> = {
  security: 34, bills: 32, government: 32, money: 24, health: 26, insurance: 22, travel: 22,
  work: 20, education: 18, subscriptions: 16, orders: 14, home: 14, events: 12,
  other: 6, social: -30, promos: -60,
};

/** Event types from explain.ts; transient or informational ones sink. */
const KIND_POINTS: Record<string, number> = {
  bill_due: 30, security_alert: 26, app_access: 24, password: 24, security_copy: 16,
  recovery_email: 12, price_increase: 22, subscription_renewal: 14, travel: 18, meeting: 14,
  order_shipped: 10, order_placed: 6, payment: 10, refund: 10, order_delivered: -4,
  verification_code: -26, magic_link: -26, welcome: -30, social_suggest: -40, social: -34,
  promo: -60, unknown: 0,
};

function ageHours(item: LifeItem, now: Date): number {
  const time = new Date(item.when).getTime();
  return Number.isNaN(time) ? 1e6 : (now.getTime() - time) / HOUR;
}

export function scoreItem(item: LifeItem, now = new Date()): { score: number; reason: TopReason; bucket: DueBucket } {
  const bucket = dueBucket(item, now);
  const kind = item.kind ?? "unknown";
  const age = ageHours(item, now);
  let score = (PRIORITY_POINTS[item.priority] ?? 12) + DUE_POINTS[bucket] + (AREA_POINTS[item.area] ?? 0) + (KIND_POINTS[kind] ?? 0);
  if (item.requestedAction) score += 8;
  if (item.priceIncrease) score += 10;
  if (item.amount !== null && (item.area === "money" || item.area === "bills")) score += 6;
  // Fresh mail matters more; security notices go stale fast.
  if (age < 24) score += 12;
  else if (age < 72) score += 6;
  else if (age > 24 * 30) score -= 10;
  if ((kind === "security_alert" || kind === "security_copy") && age > 24 * 7) score -= 18;
  const reason: TopReason =
    bucket === "overdue" || bucket === "today" || bucket === "tomorrow" || bucket === "week"
      ? bucket
      : item.area === "security" || kind.startsWith("security") || kind === "app_access" || kind === "password"
        ? "security"
        : item.priority === "critical" || item.priority === "high"
          ? "priority"
          : item.area === "money" || item.area === "bills" || item.area === "subscriptions"
            ? "money"
            : "recent";
  return { score, reason, bucket };
}

/**
 * Up to `max` open items, best first. Promotions, social notices, snoozed
 * and finished items never appear; one-time codes and sign-in links only
 * when they are less than an hour old.
 */
export function rankTopTen(items: LifeItem[], now = new Date(), snoozed: (item: LifeItem) => boolean = () => false, max = 10): TopItem[] {
  const seen = new Set<string>();
  const ranked: TopItem[] = [];
  for (const item of items) {
    if (!isOpenStatus(item.status) || snoozed(item)) continue;
    if (item.area === "promos" || item.area === "social") continue;
    const kind = item.kind ?? "unknown";
    if (kind === "promo" || kind === "social" || kind === "social_suggest" || kind === "welcome") continue;
    if ((kind === "verification_code" || kind === "magic_link") && ageHours(item, now) > 1) continue;
    // One row per case/message (threads already merged into cases upstream).
    const key = item.caseId ?? item.messageId ?? item.id;
    if (seen.has(key)) continue;
    seen.add(key);
    ranked.push({ item, ...scoreItem(item, now) });
  }
  ranked.sort((left, right) =>
    right.score - left.score
    || (left.item.dueAt && right.item.dueAt ? left.item.dueAt.localeCompare(right.item.dueAt) : left.item.dueAt ? -1 : right.item.dueAt ? 1 : 0)
    || right.item.when.localeCompare(left.item.when),
  );
  return ranked.slice(0, max);
}

/** First run: the user never saw the list and Donexto already classified mail. */
export function shouldShowTopTen(input: { seenAt: string | null | undefined; ready: boolean; loading: boolean; blocked: boolean; count: number }): boolean {
  return !input.seenAt && input.ready && !input.loading && !input.blocked && input.count > 0;
}
