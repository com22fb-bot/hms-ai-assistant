import type { LifeAreaId } from "@/lib/nucleo/lifeAreas";

export const NUCLEO_THEMES = [
  "nucleo",
  "nucleo-claro",
  "command",
  "day",
] as const;

export type NucleoTheme = (typeof NUCLEO_THEMES)[number];

export type AlertRuleKind = "sender" | "case_type" | "subject" | "concept";

export type AlertRule = {
  id: string;
  kind: AlertRuleKind;
  value: string;
  enabled: boolean;
  area?: LifeAreaId | null;
};

export type NucleoPrefs = {
  theme: NucleoTheme;
  fontScale: number;
  highContrast: boolean;
  reducedMotion: boolean;
  screenReader: boolean;
  readAloud: boolean;
  speechRate: number;
  visualAlerts: boolean;
  badges: boolean;
  flash: boolean;
  vibrate: boolean;
  captions: boolean;
  transcript: boolean;
  guide: boolean;
  soundEnabled: boolean;
  volume: number;
  snooze: Record<string, string>;
  pushOnboardingCompletedAt: string | null;
  /** When the first-run "top 10" summary was dismissed (null = never shown). */
  top10SeenAt: string | null;
  alertRules: AlertRule[];
};

export const DEFAULT_PREFS: NucleoPrefs = {
  theme: "nucleo",
  fontScale: 1,
  highContrast: false,
  reducedMotion: false,
  screenReader: true,
  readAloud: true,
  speechRate: 1,
  visualAlerts: true,
  badges: true,
  flash: true,
  vibrate: true,
  captions: true,
  transcript: true,
  guide: true,
  soundEnabled: true,
  volume: 0.8,
  snooze: {},
  pushOnboardingCompletedAt: null,
  top10SeenAt: null,
  alertRules: [],
};

const SCALES = [0.9, 1, 1.25, 1.5];

export function clampScale(value: number): number {
  return SCALES.reduce((best, scale) =>
    Math.abs(scale - value) < Math.abs(best - value) ? scale : best,
  );
}

export function isTheme(value: unknown): value is NucleoTheme {
  return (
    typeof value === "string" &&
    (NUCLEO_THEMES as readonly string[]).includes(value)
  );
}

export function mergePrefs(raw: unknown): NucleoPrefs {
  const source =
    raw && typeof raw === "object" ? (raw as Partial<NucleoPrefs>) : {};
  const scale = Number(source.fontScale);
  const rate = Number(source.speechRate);
  const volume = Number(source.volume);
  const rules = Array.isArray(source.alertRules)
    ? source.alertRules.filter(isRule)
    : [];
  const snooze =
    source.snooze && typeof source.snooze === "object" ? source.snooze : {};
  return {
    ...DEFAULT_PREFS,
    ...source,
    theme: isTheme(source.theme) ? source.theme : DEFAULT_PREFS.theme,
    fontScale: Number.isFinite(scale) ? clampScale(scale) : 1,
    speechRate: Number.isFinite(rate) ? Math.min(1.4, Math.max(0.8, rate)) : 1,
    volume: Number.isFinite(volume) ? Math.min(1, Math.max(0, volume)) : 0.8,
    highContrast: Boolean(source.highContrast),
    reducedMotion: Boolean(source.reducedMotion),
    screenReader: source.screenReader !== false,
    readAloud: source.readAloud !== false,
    visualAlerts: source.visualAlerts !== false,
    badges: source.badges !== false,
    flash: source.flash !== false,
    vibrate: source.vibrate !== false,
    captions: source.captions !== false,
    transcript: source.transcript !== false,
    guide: source.guide !== false,
    soundEnabled: source.soundEnabled !== false,
    snooze: Object.fromEntries(
      Object.entries(snooze).filter(
        (entry): entry is [string, string] => typeof entry[1] === "string",
      ),
    ),
    pushOnboardingCompletedAt:
      typeof source.pushOnboardingCompletedAt === "string"
        ? source.pushOnboardingCompletedAt
        : null,
    top10SeenAt:
      typeof source.top10SeenAt === "string" ? source.top10SeenAt : null,
    alertRules: rules,
  };
}

function isRule(value: unknown): value is AlertRule {
  if (!value || typeof value !== "object") return false;
  const rule = value as AlertRule;
  return (
    typeof rule.id === "string" &&
    typeof rule.value === "string" &&
    (rule.kind === "sender" ||
      rule.kind === "case_type" ||
      rule.kind === "subject" ||
      rule.kind === "concept")
  );
}

export function prefsKey(userId: string): string {
  return `donexto.nucleo.v1:${userId || "local"}`;
}

export function readLocalPrefs(userId: string): NucleoPrefs | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(prefsKey(userId));
    return raw ? mergePrefs(JSON.parse(raw)) : null;
  } catch {
    return null;
  }
}

export function writeLocalPrefs(userId: string, prefs: NucleoPrefs): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(prefsKey(userId), JSON.stringify(prefs));
  } catch {
    /* private mode */
  }
}

export function themeAttribute(theme: NucleoTheme): string {
  return theme === "day" ? "light" : theme;
}
