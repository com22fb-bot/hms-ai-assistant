"use client";

import {
  AlarmClock,
  Bell,
  Briefcase,
  CalendarClock,
  Check,
  ChevronRight,
  GraduationCap,
  HeartPulse,
  House,
  Landmark,
  Package,
  Plane,
  Receipt,
  Repeat,
  ShieldAlert,
  Ticket,
  TrendingUp,
  Umbrella,
  Volume2,
  Wallet,
  type LucideIcon,
} from "lucide-react";

import type { ReactNode } from "react";

import type { AppLanguage } from "@/lib/i18n/languages";
import type { NxKey } from "@/lib/nucleo/copy";
import {
  DASHBOARD_AREAS,
  ORDER_STEPS,
  needsActionToday,
  recentAlerts,
  summarizeAreas,
  summarizeOrders,
  summarizeSubscriptions,
  upcomingDue,
  type AlertReason,
  type OrderStage,
} from "@/lib/nucleo/commandCenter";
import {
  areaChip,
  isOpenStatus,
  monthMoney,
  urgencyOf,
  type LifeAreaId,
  type LifeItem,
} from "@/lib/nucleo/lifeAreas";
import type { AppNotification } from "@/lib/nucleo/pushClient";
import { speakText } from "@/lib/nucleo/speech";

type T = (key: NxKey, vars?: Record<string, string | number>) => string;

const AREA_ICONS: Record<LifeAreaId, LucideIcon> = {
  money: Wallet,
  orders: Package,
  subscriptions: Repeat,
  work: Briefcase,
  home: House,
  health: HeartPulse,
  bills: Receipt,
  travel: Plane,
  security: ShieldAlert,
  government: Landmark,
  insurance: Umbrella,
  education: GraduationCap,
  social: Bell,
  events: Ticket,
  promos: Bell,
  other: Bell,
};

const AREA_KEYS: Record<LifeAreaId, NxKey> = {
  money: "areaMoney",
  orders: "areaOrders",
  subscriptions: "areaSubscriptions",
  work: "areaWork",
  home: "areaHome",
  health: "areaHealth",
  bills: "areaBills",
  travel: "areaTravel",
  security: "areaSecurity",
  government: "areaGovernment",
  insurance: "areaInsurance",
  education: "areaEducation",
  social: "areaSocial",
  events: "areaEvents",
  promos: "areaPromos",
  other: "areaOther",
};

export function areaLabel(t: T, area: LifeAreaId): string {
  return t(AREA_KEYS[area]);
}

const STAGE_KEYS: Record<OrderStage, NxKey> = {
  confirmed: "orderConfirmed",
  shipped: "orderShipped",
  delivered: "orderDelivered",
  cancelled: "orderCancelled",
  refunded: "orderRefunded",
};

const REASON_KEYS: Record<AlertReason | "push", NxKey> = {
  security: "alertWhySecurity",
  priority: "alertWhyPriority",
  priceIncrease: "alertWhyPrice",
  rule: "alertWhyRule",
  push: "alertWhyPush",
};

export type CommandCenterProps = {
  t: T;
  locale: string;
  language: AppLanguage;
  items: LifeItem[];
  notes: AppNotification[];
  loading: boolean;
  connected: boolean;
  readAloud: boolean;
  speechRate: number;
  badges: boolean;
  now: number;
  eyebrow: string;
  summary: string;
  snoozed: (item: LifeItem) => boolean;
  matchesRule: (item: LifeItem) => boolean;
  snoozeFor: string | null;
  onSnoozeOpen: (id: string | null) => void;
  onSnooze: (item: LifeItem, hours: number) => void;
  onDone: (item: LifeItem) => void;
  onOpen: (item: LifeItem) => void;
  onReadNote: (id: string) => void;
  onPickArea: (area: LifeAreaId | "all") => void;
  onViewAlerts: () => void;
  onViewOpen: () => void;
  onConnect: () => void;
  onCaption: (text: string) => void;
};

const ACTION_ROWS = 4;
const UPCOMING_ROWS = 4;
const ALERT_ROWS = 4;

export function CommandCenter(props: CommandCenterProps) {
  const { t, locale, items } = props;
  const now = new Date(props.now);
  const action = needsActionToday(items, now, props.snoozed);
  const upcoming = upcomingDue(items, now, 7, props.snoozed);
  const upcomingCount = upcoming.reduce((sum, day) => sum + day.items.length, 0);
  const alerts = mergeAlerts(recentAlerts(items, now, props.matchesRule), props.notes, now);
  const areas = summarizeAreas(items, now, props.snoozed);
  const orders = summarizeOrders(items, now);
  const subs = summarizeSubscriptions(items, now);
  const money = monthMoney(items, now);
  const totalOpen = items.filter((item) => isOpenStatus(item.status) && item.area !== "promos" && !props.snoozed(item)).length;
  const speak = (text: string) => {
    speakText(text, props.language, props.speechRate);
    props.onCaption(text);
  };

  return (
    <div className="cc">
      <div className="summary cc-summary" data-help-title={t("listenSummary")} data-help={props.summary}>
        <div className="cc-summary-text">
          <div className="eyebrow">{props.eyebrow}</div>
          <div className="ai-line"><Spark /><span>{props.summary}</span></div>
        </div>
        {props.readAloud ? (
          <button type="button" className="listen" onClick={() => speak(props.summary)}>
            <Volume2 className="i" />{t("listenSummary")}
          </button>
        ) : null}
      </div>

      <div className="cc-top">
        <section className="card cc-card cc-action" aria-labelledby="cc-action-h" data-help-title={t("actionToday")} data-help={t("helpDoNow")}>
          <header className="cc-h">
            <h2 id="cc-action-h"><Spark />{t("actionToday")}{action.length > 0 && props.badges ? <span className="badge-n">{action.length}</span> : null}</h2>
            <span className="cc-note">{t("sortedBy")}</span>
          </header>
          {props.loading ? <Skeleton /> : action.length === 0 ? (
            <CardEmpty icon={Check} text={props.connected ? t("actionTodayEmpty") : t("emptyBody")} action={!props.connected ? <button type="button" className="btn primary sm" onClick={props.onConnect}>{t("emptyConnect")}</button> : null} />
          ) : (
            <ul className="cc-list">
              {action.slice(0, ACTION_ROWS).map((item) => {
                const urgency = urgencyOf(item, now);
                const line = item.line || item.title;
                return (
                  <li key={item.id} className="cc-row">
                    <button type="button" className="cc-row-main" onClick={() => props.onOpen(item)}>
                      <span className={`cc-urg u-${urgency}`} aria-hidden />
                      <span className="cc-row-text">
                        <b>{line}</b>
                        <small>{[dueText(t, item, now, locale), item.sender, item.amountRaw].filter(Boolean).join(" · ")}</small>
                      </span>
                      <span className={`chip ${areaChip(item.area)}`}>{areaLabel(t, item.area)}</span>
                    </button>
                    <span className="cc-row-acts">
                      {props.readAloud ? (
                        <button type="button" className="cc-icon" aria-label={t("listen")} onClick={() => speak(line)}><Volume2 className="i sm" /></button>
                      ) : null}
                      <button type="button" className="cc-icon" aria-label={t("remind")} aria-expanded={props.snoozeFor === item.id} onClick={() => props.onSnoozeOpen(props.snoozeFor === item.id ? null : item.id)}><AlarmClock className="i sm" /></button>
                      <button type="button" className="cc-icon" aria-label={t("done")} onClick={() => props.onDone(item)}><Check className="i sm" /></button>
                    </span>
                    {props.snoozeFor === item.id ? (
                      <div className="card snooze-pop" role="menu">
                        <button type="button" className="btn sm" role="menuitem" onClick={() => props.onSnooze(item, 1)}>{t("snoozeHour")}</button>
                        <button type="button" className="btn sm" role="menuitem" onClick={() => props.onSnooze(item, 15)}>{t("snoozeTomorrow")}</button>
                        <button type="button" className="btn sm" role="menuitem" onClick={() => props.onSnooze(item, 72)}>{t("snooze3d")}</button>
                      </div>
                    ) : null}
                  </li>
                );
              })}
            </ul>
          )}
          {action.length > ACTION_ROWS ? (
            <button type="button" className="cc-more" onClick={props.onViewOpen}>{t("moreCount", { count: action.length - ACTION_ROWS })}<ChevronRight className="i sm" /></button>
          ) : null}
        </section>

        <section className="card cc-card cc-upcoming" aria-labelledby="cc-up-h">
          <header className="cc-h">
            <h2 id="cc-up-h"><CalendarClock className="i" />{t("upcomingTitle")}{upcomingCount > 0 && props.badges ? <span className="badge-n">{upcomingCount}</span> : null}</h2>
            <span className="cc-note cc-note-opt">{t("upcomingNote")}</span>
          </header>
          {props.loading ? <Skeleton /> : upcomingCount === 0 ? (
            <CardEmpty icon={CalendarClock} text={t("upcomingEmpty")} />
          ) : (
            <ol className="cc-days">
              {limitDays(upcoming, UPCOMING_ROWS).map((day) => (
                <li key={day.offset}>
                  <div className={day.offset < 0 ? "cc-day is-late" : "cc-day"}>{dayLabel(t, day.offset, day.date, locale)}</div>
                  <ul className="cc-list">
                    {day.items.map((item) => (
                      <li key={item.id}>
                        <button type="button" className="cc-ev" onClick={() => props.onOpen(item)}>
                          <span className="cc-time">{day.offset < 0 ? formatDay(item.dueAt, locale) : formatClock(item.dueAt, locale)}</span>
                          <span className={`cc-dot ${areaChip(item.area)}`} aria-hidden />
                          <span className="cc-row-text"><b>{item.line || item.title}</b><small>{[areaLabel(t, item.area), item.sender].filter(Boolean).join(" · ")}</small></span>
                          {item.amountRaw ? <span className="pill num">{item.amountRaw}</span> : null}
                        </button>
                      </li>
                    ))}
                  </ul>
                </li>
              ))}
            </ol>
          )}
          {upcomingCount > UPCOMING_ROWS ? (
            <button type="button" className="cc-more" onClick={props.onViewOpen}>{t("moreCount", { count: upcomingCount - UPCOMING_ROWS })}<ChevronRight className="i sm" /></button>
          ) : null}
        </section>

        <section className="card cc-card cc-alerts" aria-labelledby="cc-al-h">
          <header className="cc-h">
            <h2 id="cc-al-h"><ShieldAlert className="i" />{t("alertsRecent")}{alerts.length > 0 && props.badges ? <span className="badge-n hot">{alerts.length}</span> : null}</h2>
            <button type="button" className="cc-link" onClick={props.onViewAlerts}>{t("viewAll")}</button>
          </header>
          {props.loading ? <Skeleton /> : alerts.length === 0 ? (
            <CardEmpty icon={ShieldAlert} text={t("alertsRecentEmpty")} />
          ) : (
            <ul className="cc-list">
              {alerts.slice(0, ALERT_ROWS).map((alert) => (
                <li key={alert.key}>
                  <button
                    type="button"
                    className="cc-ev cc-alert"
                    onClick={() => (alert.item ? props.onOpen(alert.item) : alert.noteId ? props.onReadNote(alert.noteId) : undefined)}
                  >
                    <span className={`cc-al-ic r-${alert.reason}`} aria-hidden>{alert.reason === "priceIncrease" ? <TrendingUp className="i sm" /> : alert.reason === "security" ? <ShieldAlert className="i sm" /> : <Bell className="i sm" />}</span>
                    <span className="cc-row-text"><b>{alert.title}</b><small>{[t(REASON_KEYS[alert.reason]), alert.sender, formatAgo(alert.when, locale, now)].filter(Boolean).join(" · ")}</small></span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <section className="cc-areas" aria-labelledby="cc-areas-h" data-help-title={t("areas")} data-help={t("helpAreas")}>
        <header className="cc-h">
          <h2 id="cc-areas-h">{t("areas")}<span className="cc-note">{t("areasHint")}</span></h2>
          <button type="button" className="cnt all" onClick={() => props.onPickArea("all")}>{t("all")} <b>{totalOpen}</b></button>
        </header>
        <div className="cc-grid">
          {DASHBOARD_AREAS.map((area) => {
            const Icon = AREA_ICONS[area];
            const summary = areas[area];
            const open = summary?.open ?? 0;
            const name = areaLabel(t, area);
            const insight = areaInsight(t, area, summary, { money, orders, subs, locale, now });
            return (
              <button
                key={area}
                type="button"
                className={open > 0 ? `cc-tile ${areaChip(area)}` : `cc-tile ${areaChip(area)} is-quiet`}
                onClick={() => props.onPickArea(area)}
                aria-label={`${name}: ${t("areaOpen", { count: open })}. ${insight.text}${insight.note ? `. ${insight.note}` : ""}`}
                title={insight.note || undefined}
              >
                <span className="cc-tile-top">
                  <span className="cc-tile-ic"><Icon className="i sm" aria-hidden /></span>
                  <span className="cc-tile-name">{name}</span>
                  <span className="cc-tile-n">{open}</span>
                </span>
                {area === "orders" && orders.latest ? (
                  <OrderThread t={t} stage={orders.latest.stage} />
                ) : (
                  <span className="cc-tile-line">{insight.text}</span>
                )}
                {insight.note ? <span className="cc-tile-note">{insight.note}</span> : null}
              </button>
            );
          })}
        </div>
      </section>
    </div>
  );
}

function Spark() {
  return (
    <svg className="i spark" viewBox="0 0 24 24" aria-hidden>
      <path d="M10 2.5c.55 4.9 2.6 6.95 7.5 7.5-4.9.55-6.95 2.6-7.5 7.5-.55-4.9-2.6-6.95-7.5-7.5 4.9-.55 6.95-2.6 7.5-7.5Z" />
    </svg>
  );
}

function Skeleton() {
  return (
    <div className="cc-skel" aria-hidden>
      <i className="skeleton" /><i className="skeleton" /><i className="skeleton" />
    </div>
  );
}

function CardEmpty({ icon: Icon, text, action }: { icon: LucideIcon; text: string; action?: ReactNode }) {
  return (
    <div className="cc-empty">
      <span className="cc-empty-ic"><Icon className="i" aria-hidden /></span>
      <p>{text}</p>
      {action}
    </div>
  );
}

function OrderThread({ t, stage }: { t: T; stage: OrderStage }) {
  const index = ORDER_STEPS.indexOf(stage);
  if (index < 0) {
    return <span className="cc-tile-line cc-stage-off">{t(STAGE_KEYS[stage])}</span>;
  }
  return (
    <span className="cc-thread" aria-label={t(STAGE_KEYS[stage])}>
      {ORDER_STEPS.map((step, position) => (
        <span key={step} className={position <= index ? "on" : undefined} title={t(STAGE_KEYS[step])} />
      ))}
      <em>{t(STAGE_KEYS[stage])}</em>
    </span>
  );
}

type Insight = { text: string; note?: string };

function areaInsight(
  t: T,
  area: LifeAreaId,
  summary: ReturnType<typeof summarizeAreas>[LifeAreaId] | undefined,
  context: {
    money: ReturnType<typeof monthMoney>;
    orders: ReturnType<typeof summarizeOrders>;
    subs: ReturnType<typeof summarizeSubscriptions>;
    locale: string;
    now: Date;
  },
): Insight {
  if (area === "money") {
    if (context.money.movements === 0) return { text: t("moneyTileEmpty"), note: t("moneyNotBalance") };
    const cash = new Intl.NumberFormat(context.locale, { style: "currency", currency: "USD", currencyDisplay: "narrowSymbol" }).format(context.money.outflows);
    return { text: `${cash} · ${t("moneyTile", { count: context.money.movements })}`, note: t("moneyNotBalance") };
  }
  if (area === "orders") {
    const parts = [];
    if (context.orders.inTransit) parts.push(t("ordersTransit", { count: context.orders.inTransit }));
    if (context.orders.delivered) parts.push(t("ordersDelivered", { count: context.orders.delivered }));
    return { text: parts.join(" · ") || t("areaNone") };
  }
  if (area === "subscriptions") {
    const parts = [];
    if (context.subs.renewingSoon) parts.push(t("subsRenew", { count: context.subs.renewingSoon }));
    if (context.subs.priceIncreases) parts.push(t("subsIncrease", { count: context.subs.priceIncreases }));
    if (!parts.length && context.subs.active) parts.push(t("activeSubs", { count: context.subs.active }));
    return { text: parts.join(" · ") || t("areaNone") };
  }
  const note = area === "health" ? t("healthInfo") : undefined;
  if (summary?.next?.dueAt) {
    return { text: t("areaNext", { when: formatDay(summary.next.dueAt, context.locale) }), note };
  }
  if (summary?.dueSoon) return { text: t("areaDueSoon", { count: summary.dueSoon }), note };
  if (summary?.open) return { text: t("areaOpen", { count: summary.open }), note };
  return { text: t("areaNone"), note };
}

type MergedAlert = {
  key: string;
  reason: AlertReason | "push";
  title: string;
  sender: string;
  when: string;
  item: LifeItem | null;
  noteId: string | null;
};

function mergeAlerts(
  alerts: ReturnType<typeof recentAlerts>,
  notes: AppNotification[],
  now: Date,
): MergedAlert[] {
  const since = now.getTime() - 7 * 864e5;
  const rows: MergedAlert[] = alerts.map((alert) => ({
    key: alert.item.id,
    reason: alert.reason,
    title: alert.item.line || alert.item.title,
    sender: alert.item.sender,
    when: alert.item.when,
    item: alert.item,
    noteId: null,
  }));
  for (const note of notes) {
    if (note.read_at) continue;
    const time = new Date(note.created_at).getTime();
    if (Number.isNaN(time) || time < since) continue;
    rows.push({ key: `note:${note.id}`, reason: "push", title: note.title, sender: note.body, when: note.created_at, item: null, noteId: note.id });
  }
  return rows.sort((left, right) => right.when.localeCompare(left.when));
}

function limitDays<T extends { items: LifeItem[] }>(days: T[], max: number): T[] {
  const out: T[] = [];
  let left = max;
  for (const day of days) {
    if (left <= 0) break;
    out.push({ ...day, items: day.items.slice(0, left) });
    left -= day.items.length;
  }
  return out;
}

function dayLabel(t: T, offset: number, iso: string, locale: string): string {
  if (offset < 0) return t("dayOverdue");
  if (offset === 0) return t("dayToday");
  if (offset === 1) return t("dayTomorrow");
  return new Intl.DateTimeFormat(locale, { weekday: "long", day: "numeric", month: "short" }).format(new Date(iso));
}

function dueText(t: T, item: LifeItem, now: Date, locale: string): string {
  if (!item.dueAt) return urgencyOf(item, now) === "high" ? t("urgentHigh") : "";
  const due = new Date(item.dueAt);
  if (Number.isNaN(due.getTime())) return "";
  if (due.getTime() < now.getTime()) return t("overdue");
  return t("dueIn", { when: formatDay(item.dueAt, locale) });
}

function formatDay(iso: string | null, locale: string): string {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat(locale, { weekday: "short", day: "numeric", month: "short" }).format(date);
}

function formatClock(iso: string | null, locale: string): string {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat(locale, { hour: "numeric", minute: "2-digit" }).format(date);
}

function formatAgo(iso: string, locale: string, now: Date): string {
  const time = new Date(iso).getTime();
  if (Number.isNaN(time)) return "";
  const minutes = Math.round((time - now.getTime()) / 60000);
  const format = new Intl.RelativeTimeFormat(locale, { numeric: "auto", style: "short" });
  if (Math.abs(minutes) < 60) return format.format(minutes, "minute");
  const hours = Math.round(minutes / 60);
  if (Math.abs(hours) < 24) return format.format(hours, "hour");
  return format.format(Math.round(hours / 24), "day");
}
