/**
 * Mail insights computed by the backend (`backend/app/services/mail_insights.py`):
 * event type, life area, a one-sentence main idea in 5 languages built only
 * from extracted facts, and 1–3 exact quotes from the cleaned email. The
 * frontend never re-derives these from keywords: when an insight exists, it
 * wins over local keyword scoring.
 */

import type { LifeAreaId } from "./lifeAreas.ts";

export type InsightLang = "es" | "en" | "fr" | "it" | "pt";

export type MailInsightFacts = {
  brand?: string | null;
  amount?: string | null;
  due_date?: string | null;
  date?: string | null;
  merchant?: string | null;
  reference?: string | null;
  card_last4?: string | null;
};

export type MailInsight = {
  version?: string;
  kind: string;
  area?: string | null;
  main_idea?: Partial<Record<InsightLang, string>> | null;
  excerpts?: string[] | null;
  facts?: MailInsightFacts | null;
  preview?: string | null;
};

const AREAS = new Set<string>([
  "money", "orders", "subscriptions", "work", "home", "health", "bills", "travel", "security",
  "government", "insurance", "education", "social", "events", "promos", "other",
]);

/** Backend area when it is a known one; otherwise the local fallback. */
export function insightArea(insight: MailInsight | null | undefined, fallback: LifeAreaId): LifeAreaId {
  const area = insight?.area;
  return area && AREAS.has(area) ? (area as LifeAreaId) : fallback;
}

/** Main idea in `lang` (Spanish, then any language, as fallback). */
export function insightLine(insight: MailInsight | null | undefined, lang: InsightLang = "es"): string | null {
  const ideas = insight?.main_idea;
  if (!ideas) return null;
  const value = ideas[lang] || ideas.es || Object.values(ideas).find(Boolean);
  return value ? value.trim() : null;
}

/** Up to three non-empty quotes, exactly as the backend returned them. */
export function insightExcerpts(insight: MailInsight | null | undefined): string[] {
  return (insight?.excerpts ?? []).filter((quote): quote is string => typeof quote === "string" && quote.trim().length > 0).slice(0, 3);
}
