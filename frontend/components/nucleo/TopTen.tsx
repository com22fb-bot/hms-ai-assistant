"use client";

import { ChevronRight, ListChecks, X } from "lucide-react";
import { useEffect, useRef } from "react";

import type { NxKey } from "@/lib/nucleo/copy";
import { areaChip } from "@/lib/nucleo/lifeAreas";
import type { TopItem, TopReason } from "@/lib/nucleo/topTen";

import { areaLabel } from "@/components/nucleo/CommandCenter";

type T = (key: NxKey, vars?: Record<string, string | number>) => string;

const REASON_KEYS: Record<TopReason, NxKey> = {
  overdue: "topReasonOverdue",
  today: "topReasonToday",
  tomorrow: "topReasonTomorrow",
  week: "topReasonWeek",
  security: "topReasonSecurity",
  money: "topReasonMoney",
  priority: "topReasonPriority",
  recent: "topReasonRecent",
};

function formatDay(iso: string, locale: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat(locale, { weekday: "short", day: "numeric", month: "short" }).format(date);
}

/**
 * First-run welcome summary: "Tus 10 pendientes principales". Fits one
 * screen at 1366×768 (the list scrolls inside the card if needed).
 */
export function TopTen(props: {
  t: T;
  locale: string;
  rows: TopItem[];
  onOpen: (row: TopItem) => void;
  onClose: () => void;
}) {
  const { t } = props;
  const closeRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    closeRef.current?.focus({ preventScroll: true });
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") props.onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [props]);
  return (
    <div className="onboard top10-wrap" role="dialog" aria-modal="true" aria-labelledby="top10-title">
      <section className="card top10">
        <header className="top10-h">
          <span className="top10-ic" aria-hidden><ListChecks className="i" /></span>
          <div>
            <h2 id="top10-title">{t("topTitle")}</h2>
            <p>{t("topSubtitle")}</p>
          </div>
          <button type="button" className="x top10-x" aria-label={t("close")} onClick={props.onClose}><X className="i" /></button>
        </header>
        {props.rows.length === 0 ? (
          <p className="empty">{t("topEmpty")}</p>
        ) : (
          <ol className="top10-list">
            {props.rows.map((row, index) => {
              const { item } = row;
              const due = item.dueAt
                ? row.bucket === "overdue"
                  ? t("topOverdue", { date: formatDay(item.dueAt, props.locale) })
                  : t("topDue", { date: formatDay(item.dueAt, props.locale) })
                : t("topNoDue");
              return (
                <li key={item.id} className="top10-row">
                  <span className="top10-n" aria-hidden>{index + 1}</span>
                  <div className="top10-main">
                    <p className="top10-line">{item.line}</p>
                    <div className="top10-meta">
                      <span className={`chip ${areaChip(item.area)}`}>{areaLabel(t, item.area)}</span>
                      <span className={`top10-why r-${row.reason}`}>{t(REASON_KEYS[row.reason])}</span>
                      <span className={item.dueAt ? "top10-due has-due" : "top10-due"}>{due}</span>
                      {item.sender ? <span className="top10-from">{item.sender}</span> : null}
                    </div>
                  </div>
                  <button type="button" className="btn sm top10-go" data-help-key="openCase" onClick={() => props.onOpen(row)}>
                    {t("topOpen")}<ChevronRight className="i sm" aria-hidden />
                  </button>
                </li>
              );
            })}
          </ol>
        )}
        <footer className="top10-f">
          <small>{t("topRuleNote")} {t("topLater")}</small>
          <button ref={closeRef} type="button" className="btn primary" onClick={props.onClose}>{t("topDismiss")}</button>
        </footer>
      </section>
    </div>
  );
}
