"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import type {
  CaseDashboardResponse,
  CaseProcessResponse,
} from "@/types/cases";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "";

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

function errorMessage(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "No fue posible consultar los Casos Inteligentes.";
}

export function useCases() {
  const [dashboard, setDashboard] =
    useState<CaseDashboardResponse>(EMPTY_DASHBOARD);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastProcess, setLastProcess] =
    useState<CaseProcessResponse | null>(null);

  const loadDashboard = useCallback(async () => {
    if (!API_BASE_URL) {
      setError(
        "No se configuró NEXT_PUBLIC_API_BASE_URL en frontend/.env.local.",
      );
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/cases/dashboard`,
        {
          cache: "no-store",
        },
      );

      const payload = (await response.json()) as
        | CaseDashboardResponse
        | { detail?: unknown };

      if (!response.ok) {
        throw new Error(
          "detail" in payload
            ? JSON.stringify(payload.detail)
            : `El backend respondió ${response.status}.`,
        );
      }

      setDashboard(payload as CaseDashboardResponse);
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }, []);

  const processCases = useCallback(async () => {
    if (!API_BASE_URL) {
      setError(
        "No se configuró NEXT_PUBLIC_API_BASE_URL en frontend/.env.local.",
      );
      return;
    }

    setProcessing(true);
    setError(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/cases/process?limit=500`,
        {
          method: "POST",
          cache: "no-store",
        },
      );

      const payload = (await response.json()) as
        | CaseProcessResponse
        | { detail?: unknown };

      if (!response.ok) {
        throw new Error(
          "detail" in payload
            ? JSON.stringify(payload.detail)
            : `El backend respondió ${response.status}.`,
        );
      }

      setLastProcess(payload as CaseProcessResponse);
      await loadDashboard();
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setProcessing(false);
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
    processing,
    error,
    lastProcess,
    setSearch,
    loadDashboard,
    processCases,
  };
}
