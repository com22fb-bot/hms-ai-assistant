"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { hmsFetch } from "@/lib/hmsApi";

import type {
  CaseDashboardResponse,
  FullSyncProgress,
} from "@/types/cases";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
  "/api/hms";

const SYNC_BATCH_SIZE = 50;
const POLL_INTERVAL_MS = 2000;

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

type SyncJobStatus =
  | "queued"
  | "running"
  | "paused"
  | "interrupted"
  | "completed"
  | "failed"
  | "cancelled";

type DurableSyncJob = {
  id: string;
  status: SyncJobStatus;
  mode: "historical" | "incremental" | "custom";
  query: string | null;
  next_page_token: string | null;
  batch_size: number;
  pages_completed: number;
  messages_found: number;
  messages_inserted: number;
  duplicates: number;
  cases_processed: number;
  created_cases: number;
  linked_cases: number;
  errors: number;
  retry_count: number;
  max_retries: number;
  last_error: string | null;
  completed_at: string | null;
  reused?: boolean;
};

type JobResponse = {
  status: string;
  job: DurableSyncJob | null;
};

function errorMessage(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "No fue posible completar la operación.";
}

function friendlyBackendError(
  status: number,
  payload: unknown,
  rawText: string,
): string {
  const text = JSON.stringify(payload ?? rawText).toLowerCase();

  if (text.includes("invalid_grant")) {
    return "La autorización de Google expiró o fue revocada. Vuelve a conectar Gmail.";
  }

  if (text.includes("scope") && text.includes("gmail")) {
    return "La cuenta de Google no tiene el permiso requerido para leer Gmail.";
  }

  if (status === 502) {
    return "El backend no pudo comunicarse temporalmente con Gmail. El trabajo conservará su progreso.";
  }

  if (status >= 500) {
    return `El backend respondió ${status}. La falla quedó registrada en la bitácora.`;
  }

  if (
    typeof payload === "object" &&
    payload !== null &&
    "detail" in payload
  ) {
    const detail = (payload as { detail?: unknown }).detail;

    if (
      typeof detail === "object" &&
      detail !== null &&
      "message" in detail
    ) {
      return String((detail as { message?: unknown }).message);
    }

    if (typeof detail === "string") {
      return detail;
    }
  }

  return `La operación respondió HTTP ${status}.`;
}

async function parseResponse<T>(response: Response): Promise<T> {
  const rawText = await response.text();
  let payload: unknown = null;

  if (rawText.trim()) {
    try {
      payload = JSON.parse(rawText) as unknown;
    } catch {
      payload = { message: rawText.trim() };
    }
  }

  if (!response.ok) {
    throw new Error(
      friendlyBackendError(response.status, payload, rawText),
    );
  }

  return payload as T;
}

function progressFromJob(job: DurableSyncJob): FullSyncProgress {
  const running = job.status === "queued" || job.status === "running";

  return {
    running,
    currentBatch:
      running ? job.pages_completed + 1 : job.pages_completed,
    pagesCompleted: job.pages_completed,
    found: job.messages_found,
    inserted: job.messages_inserted,
    duplicates: job.duplicates,
    processed: job.cases_processed,
    createdCases: job.created_cases,
    linkedCases: job.linked_cases,
    errors: job.errors,
    completed: job.status === "completed",
  };
}

export function useCases(enabled = true) {
  const [dashboard, setDashboard] =
    useState<CaseDashboardResponse>(EMPTY_DASHBOARD);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(enabled);
  const [syncProgress, setSyncProgress] =
    useState<FullSyncProgress>(EMPTY_PROGRESS);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadDashboard = useCallback(async () => {
    if (!enabled) {
      setDashboard(EMPTY_DASHBOARD);
      setError(null);
      setLoading(false);
      return;
    }

    setLoading(true);

    try {
      const response = await hmsFetch(
        `${API_BASE_URL}/cases/dashboard`,
        { cache: "no-store" },
      );

      setDashboard(
        await parseResponse<CaseDashboardResponse>(response),
      );
      setError(null);
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }, [enabled]);

  const loadActiveSyncJob = useCallback(async () => {
    if (!enabled) {
      setActiveJobId(null);
      setSyncProgress(EMPTY_PROGRESS);
      return;
    }

    try {
      const response = await hmsFetch(
        `${API_BASE_URL}/gmail/sync-jobs/active`,
        { cache: "no-store" },
      );
      const result = await parseResponse<JobResponse>(response);

      if (result.job) {
        setSyncProgress(progressFromJob(result.job));
        setActiveJobId(result.job.id);
      }
    } catch (requestError) {
      setError(errorMessage(requestError));
    }
  }, [enabled]);

  const syncAllMessages = useCallback(async () => {
    if (!enabled) {
      setError("Conecta primero el buzón que Donexto administrará.");
      return;
    }

    setError(null);

    try {
      const parameters = new URLSearchParams({
        batch_size: String(SYNC_BATCH_SIZE),
        mode: "incremental",
        process_cases: "false",
        max_retries: "3",
      });

      const response = await hmsFetch(
        `${API_BASE_URL}/gmail/sync-jobs?${parameters}`,
        {
          method: "POST",
          cache: "no-store",
        },
      );
      const result = await parseResponse<JobResponse>(response);

      if (!result.job) {
        throw new Error(
          "El backend no devolvió el trabajo de sincronización.",
        );
      }

      setSyncProgress(progressFromJob(result.job));
      setActiveJobId(result.job.id);
    } catch (requestError) {
      setError(errorMessage(requestError));
      setSyncProgress((current) => ({
        ...current,
        running: false,
      }));
    }
  }, [enabled]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      if (!enabled) {
        setDashboard(EMPTY_DASHBOARD);
        setSyncProgress(EMPTY_PROGRESS);
        setActiveJobId(null);
        setError(null);
        setLoading(false);
        return;
      }

      void loadDashboard();
      void loadActiveSyncJob();
    }, 0);

    return () => window.clearTimeout(timer);
  }, [enabled, loadActiveSyncJob, loadDashboard]);

  useEffect(() => {
    if (!enabled || !activeJobId) {
      return;
    }

    let cancelled = false;
    let timer: number | null = null;

    const poll = async () => {
      try {
        const response = await hmsFetch(
          `${API_BASE_URL}/gmail/sync-jobs/${activeJobId}`,
          { cache: "no-store" },
        );
        const result = await parseResponse<JobResponse>(response);

        if (cancelled || !result.job) {
          return;
        }

        const job = result.job;
        setSyncProgress(progressFromJob(job));

        if (job.status === "completed") {
          setActiveJobId(null);
          await loadDashboard();
          return;
        }

        if (job.status === "failed") {
          setError(
            job.last_error
              ? `La sincronización se detuvo: ${job.last_error}`
              : "La sincronización agotó sus reintentos. La falla quedó registrada.",
          );
          setActiveJobId(null);
          return;
        }

        if (job.status === "cancelled") {
          setError("La sincronización fue cancelada.");
          setActiveJobId(null);
          return;
        }

        if (job.status === "paused") {
          setError("La sincronización está en pausa.");
          setActiveJobId(null);
          return;
        }

        timer = window.setTimeout(poll, POLL_INTERVAL_MS);
      } catch (requestError) {
        if (!cancelled) {
          setError(errorMessage(requestError));
          timer = window.setTimeout(poll, POLL_INTERVAL_MS * 2);
        }
      }
    };

    void poll();

    return () => {
      cancelled = true;
      if (timer !== null) {
        window.clearTimeout(timer);
      }
    };
  }, [activeJobId, enabled, loadDashboard]);

  useEffect(() => {
    if (!enabled) return;
    const refresh = () => {
      void loadDashboard();
    };
    const interval = window.setInterval(() => {
      if (document.visibilityState === "visible") {
        void loadDashboard();
      }
    }, 30000);
    window.addEventListener("hms:data-changed", refresh);
    window.addEventListener("hms:classification-complete", refresh);
    return () => {
      window.clearInterval(interval);
      window.removeEventListener("hms:data-changed", refresh);
      window.removeEventListener("hms:classification-complete", refresh);
    };
  }, [enabled, loadDashboard]);

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
