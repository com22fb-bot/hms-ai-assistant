"use client";

import { useCallback, useEffect, useState } from "react";

import { hmsFetch } from "@/lib/hmsApi";

import type {
  GmailMessage,
  GmailMessagesResponse,
  GoogleConnectionStatus,
} from "@/types/mail";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
  "/api/hms";

function getErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

export function useConnection() {
  const [connection, setConnection] =
    useState<GoogleConnectionStatus | null>(null);
  const [messages, setMessages] = useState<GmailMessage[]>([]);
  const [loadingStatus, setLoadingStatus] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const loadMessages = useCallback(async () => {
    setLoadingMessages(true);
    setError(null);

    try {
      const response = await hmsFetch(
        `${API_BASE_URL}/gmail/messages?limit=100`,
        {
          method: "GET",
          cache: "no-store",
        },
      );

      const data = (await response.json()) as
        | GmailMessagesResponse
        | { detail?: unknown };

      if (!response.ok) {
        const detail =
          "detail" in data
            ? typeof data.detail === "string"
              ? data.detail
              : JSON.stringify(data.detail)
            : "No fue posible consultar los correos.";

        throw new Error(detail);
      }

      const gmailData = data as GmailMessagesResponse;

      setMessages(
        Array.isArray(gmailData.messages) ? gmailData.messages : [],
      );
      setLastUpdated(new Date());
    } catch (requestError) {
      setError(
        getErrorMessage(
          requestError,
          "Ocurrió un error al consultar Gmail.",
        ),
      );
    } finally {
      setLoadingMessages(false);
    }
  }, []);

  const loadConnectionStatus = useCallback(async () => {
    setLoadingStatus(true);
    setError(null);

    try {
      const response = await hmsFetch(`${API_BASE_URL}/auth/google/status`, {
        method: "GET",
        cache: "no-store",
      });

      if (!response.ok) {
        throw new Error(
          `El backend respondió con el código ${response.status}.`,
        );
      }

      const data = (await response.json()) as GoogleConnectionStatus;

      setConnection(data);

      if (data.connected) {
        await loadMessages();
      } else {
        setMessages([]);
        setLastUpdated(null);
      }
    } catch (requestError) {
      setError(
        getErrorMessage(
          requestError,
          "No fue posible conectar con el backend.",
        ),
      );
    } finally {
      setLoadingStatus(false);
    }
  }, [loadMessages]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadConnectionStatus();
    }, 0);

    return () => window.clearTimeout(timer);
  }, [loadConnectionStatus]);

  const connectGoogle = useCallback(async () => {
    setError(null);

    const response = await hmsFetch(
      `${API_BASE_URL}/auth/google/start`,
      {
        method: "POST",
        cache: "no-store",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          return_to: window.location.origin,
        }),
      },
    );
    const payload = (await response.json()) as {
      authorization_url?: string;
      detail?: { message?: string };
    };

    if (!response.ok || !payload.authorization_url) {
      throw new Error(
        payload.detail?.message ??
          "No fue posible iniciar la conexión segura con Google.",
      );
    }

    window.location.assign(payload.authorization_url);
  }, []);

  const disconnectGoogle = useCallback(async () => {
    setDisconnecting(true);
    setError(null);

    try {
      const response = await hmsFetch(
        `${API_BASE_URL}/auth/google/disconnect`,
        {
          method: "POST",
          cache: "no-store",
        },
      );

      if (!response.ok) {
        throw new Error(
          `No fue posible desconectar Google. Código ${response.status}.`,
        );
      }

      const data = (await response.json()) as GoogleConnectionStatus;

      setConnection(data);
      setMessages([]);
      setLastUpdated(null);
    } catch (requestError) {
      setError(
        getErrorMessage(
          requestError,
          "No fue posible desconectar la cuenta.",
        ),
      );
    } finally {
      setDisconnecting(false);
    }
  }, []);

  return {
    connection,
    messages,
    loadingStatus,
    loadingMessages,
    disconnecting,
    error,
    lastUpdated,
    connectGoogle,
    disconnectGoogle,
    loadConnectionStatus,
    loadMessages,
  };
}
