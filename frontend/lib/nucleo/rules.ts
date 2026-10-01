import type { LifeItem } from "@/lib/nucleo/lifeAreas";
import type { AlertRule } from "@/lib/nucleo/prefs";

export function ruleMatches(rule: AlertRule, item: LifeItem): boolean {
  if (!rule.enabled) return false;
  const value = rule.value.trim().toLowerCase();
  if (!value) return false;
  if (rule.kind === "sender") {
    return item.sender.toLowerCase().includes(value);
  }
  if (rule.kind === "case_type") {
    return item.area === value || item.title.toLowerCase().includes(value);
  }
  if (rule.kind === "subject") {
    return item.title.toLowerCase().includes(value);
  }
  return [item.line, item.title, item.requestedAction, item.sender]
    .filter(Boolean)
    .join(" ")
    .toLowerCase()
    .includes(value);
}

export function itemMatchesRules(item: LifeItem, rules: AlertRule[]): boolean {
  return rules.some((rule) => ruleMatches(rule, item));
}
