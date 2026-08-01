"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import type {
  CaseDashboardResponse,
  CaseProcessResponse,
  FullSyncPageResponse,
  FullSyncProgress,
} from "@/types/cases";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
  "/api/hms";

const SYNC_BATCH_SIZE = 50;
const CASE_BATCH_SIZE = 50;

const EMPTY_DASHBOARD: CaseDashboardResponse = {
  status: "ok",
  metrics: {
    total_open: 0,
    critical: 0,
    waiting_internal: 0,
    waiting_external: 0,
    overdue: 0,
    resolved_today: 0,
    unread_notifications: 0,
  },
  attention: [],
  recent_events: [],
};

const EMPTY_PROGRESS: FullSyncProgress = {
  running: false,
  currentBatch: 0,
  pagesCompleted: 0,
  found: 0,
  inserted: 0,
  duplicates: 0,
  processed: 0,
  createdCases: 0,
  linkedCases: 0,
  errors: 0,
  completed: false,
};

function errorMessage(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "No fue posible completar la operación.";
}

async function parseResponse<T>(
  response: Response,
): Promise<T> {
  const payload = (await response.json()) as
    | T
    | { detail?: unknown; message?: string };

  if (!response.ok) {
    if (
      typeof payload === "object" &&
      payload !== null &&
      "detail" in payload
    ) {
      throw new Error(JSON.stringify(payload.detail));
    }

    throw new Error(
      `El backend respondió ${response.status}.`,
    );
  }

  return payload as T;
}

export function useCases() {
  const [dashboard, setDashboard] =
    useState<CaseDashboardResponse>(EMPTY_DASHBOARD);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [syncProgress, setSyncProgress] =
    useState<FullSyncProgress>(EMPTY_PROGRESS);
  const [error, setError] = useState<string | null>(null);

  const loadDashboard = useCallback(async () => {
    setLoading(true);

    try {
      const response = await fetch(
        `${API_BASE_URL}/cases/dashboard`,
        {
          cache: "no-store",
        },
      );

      setDashboard(
        await parseResponse<CaseDashboardResponse>(
          response,
        ),
      );
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }, []);

  const syncAllMessages = useCallback(async () => {
    setError(null);

    let pageToken: string | null = null;
    let totals: FullSyncProgress = {
      ...EMPTY_PROGRESS,
      running: true,
      currentBatch: 1,
    };

    setSyncProgress(totals);

    try {
      do {
        setSyncProgress((current) => ({
          ...current,
          running: true,
          currentBatch:
            current.pagesCompleted + 1,
        }));

        const syncParameters = new URLSearchParams({
          batch_size: String(SYNC_BATCH_SIZE),
          process_cases: "false",
        });

        if (pageToken) {
          syncParameters.set(
            "page_token",
            pageToken,
          );
        }

        const syncResponse = await fetch(
          `${API_BASE_URL}/gmail/sync-all?${syncParameters}`,
          {
            method: "POST",
            cache: "no-store",
          },
        );

        const syncPage =
          await parseResponse<FullSyncPageResponse>(
            syncResponse,
          );

        totals = {
          ...totals,
          running: true,
          currentBatch: totals.pagesCompleted + 1,
          pagesCompleted:
            totals.pagesCompleted + 1,
          found:
            totals.found + syncPage.sync.page_found,
          inserted:
            totals.inserted + syncPage.sync.inserted,
          duplicates:
            totals.duplicates +
            syncPage.sync.duplicates,
          errors:
            totals.errors + syncPage.sync.errors,
        };

        setSyncProgress(totals);

        if (syncPage.sync.inserted > 0) {
          const processResponse = await fetch(
            `${API_BASE_URL}/cases/process?limit=${CASE_BATCH_SIZE}`,
            {
              method: "POST",
              cache: "no-store",
            },
          );

          const processResult =
            await parseResponse<CaseProcessResponse>(
              processResponse,
            );

          totals = {
            ...totals,
            processed:
              totals.processed +
              processResult.processed,
            createdCases:
              totals.createdCases +
              processResult.created_cases,
            linkedCases:
              totals.linkedCases +
              processResult.linked_to_existing,
            errors:
              totals.errors +
              processResult.errors,
          };

          setSyncProgress(totals);
        }

        pageToken = syncPage.sync.next_page_token;
      } while (pageToken);

      totals = {
        ...totals,
        running: false,
        completed: true,
        currentBatch: totals.pagesCompleted,
      };

      setSyncProgress(totals);
      await loadDashboard();
    } catch (requestError) {
      setError(errorMessage(requestError));
      setSyncProgress((current) => ({
        ...current,
        running: false,
      }));
    }
  }, [loadDashboard]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadDashboard();
    }, 0);

    return () => window.clearTimeout(timer);
  }, [loadDashboard]);

  const filteredCases = useMemo(() => {
    const normalized = search.trim().toLowerCase();

    if (!normalized) {
      return dashboard.attention;
    }

    return dashboard.attention.filter((item) =>
      [
        item.title,
        item.summary,
        item.requested_action,
        item.requester_name,
        item.requester_email,
        item.case_type,
      ]
        .filter(Boolean)
        .some((value) =>
          String(value).toLowerCase().includes(normalized),
        ),
    );
  }, [dashboard.attention, search]);

  return {
    dashboard,
    cases: filteredCases,
    search,
    loading,
    syncing: syncProgress.running,
    syncProgress,
    error,
    setSearch,
    loadDashboard,
    syncAllMessages,
  };
}
