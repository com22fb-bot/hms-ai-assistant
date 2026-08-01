"use client";

import { useCallback, useEffect, useState } from "react";

import type { GoogleConnectionStatus } from "@/types/mail";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
  "/api/hms";

export function useGoogleStatus() {
  const [connection, setConnection] =
    useState<GoogleConnectionStatus | null>(null);
  const [loadingConnection, setLoadingConnection] =
    useState(true);
  const [connectionError, setConnectionError] =
    useState<string | null>(null);

  const loadGoogleStatus = useCallback(async () => {
    setLoadingConnection(true);
    setConnectionError(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/auth/google/status`,
        {
          cache: "no-store",
        },
      );

      if (!response.ok) {
        throw new Error(
          `El backend respondió ${response.status}.`,
        );
      }

      setConnection(
        (await response.json()) as GoogleConnectionStatus,
      );
    } catch (requestError) {
      setConnection(null);
      setConnectionError(
        requestError instanceof Error
          ? requestError.message
          : "No fue posible consultar Google.",
      );
    } finally {
      setLoadingConnection(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadGoogleStatus();
    }, 0);

    return () => window.clearTimeout(timer);
  }, [loadGoogleStatus]);

  return {
    connection,
    loadingConnection,
    connectionError,
    loadGoogleStatus,
  };
}
