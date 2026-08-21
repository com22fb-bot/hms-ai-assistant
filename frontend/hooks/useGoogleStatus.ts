"use client";

import { useCallback, useEffect, useState } from "react";

import { hmsFetch } from "@/lib/hmsApi";

import type { GoogleConnectionStatus } from "@/types/mail";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
  "/api/hms";

async function parseStatus(
  response: Response,
): Promise<GoogleConnectionStatus> {
  const raw = await response.text();
  let payload: unknown = null;

  if (raw) {
    try {
      payload = JSON.parse(raw);
    } catch {
      payload = null;
    }
  }

  if (!response.ok) {
    if (response.status === 502) {
      throw new Error(
        "No fue posible comunicar con el backend. Verifica el puerto 8000.",
      );
    }

    throw new Error(
      `No fue posible consultar el buzón. Código ${response.status}.`,
    );
  }

  if (!payload || typeof payload !== "object") {
    throw new Error(
      "El backend devolvió un estado de correo no válido.",
    );
  }

  return payload as GoogleConnectionStatus;
}

function detailMessage(payload: {
  detail?: { message?: string } | string;
}): string | undefined {
  const detail = payload.detail;
  if (typeof detail === "string") return detail;
  return detail?.message;
}

export function useGoogleStatus() {
  const [connection, setConnection] =
    useState<GoogleConnectionStatus | null>(null);
  const [loadingConnection, setLoadingConnection] = useState(true);
  const [connectionError, setConnectionError] =
    useState<string | null>(null);
  const [connectingYahoo, setConnectingYahoo] = useState(false);

  const loadGoogleStatus = useCallback(async () => {
    setLoadingConnection(true);
    setConnectionError(null);

    try {
      const response = await hmsFetch(
        `${API_BASE_URL}/auth/google/status`,
        { cache: "no-store" },
      );

      setConnection(await parseStatus(response));
    } catch (requestError) {
      setConnection(null);
      setConnectionError(
        requestError instanceof Error
          ? requestError.message
          : "No fue posible consultar el buzón.",
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

  const startGoogleConnection = useCallback(async () => {
    setConnectionError(null);

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

    let payload: {
      authorization_url?: string;
      detail?: { message?: string; status?: string } | string;
    } = {};

    try {
      payload = (await response.json()) as typeof payload;
    } catch {
      throw new Error(
        `No fue posible leer la respuesta de Google OAuth (HTTP ${response.status}).`,
      );
    }

    if (!response.ok || !payload.authorization_url) {
      const detail =
        typeof payload.detail === "string"
          ? payload.detail
          : payload.detail?.message;
      throw new Error(
        detail ??
          "No fue posible iniciar la conexión segura con Gmail. " +
            "Si Google dice access_denied, publica la app OAuth " +
            "en estado En producción (Google Cloud) y usa el nombre Donexto.",
      );
    }

    window.location.assign(payload.authorization_url);
  }, []);

  const startYahooConnection = useCallback(async () => {
    setConnectingYahoo(true);
    setConnectionError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/auth/yahoo/login`, {
        method: "POST",
        cache: "no-store",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          return_to: window.location.origin,
          intent: "login",
        }),
      });

      let payload: {
        authorization_url?: string;
        detail?: { message?: string } | string;
      } = {};

      try {
        payload = (await response.json()) as typeof payload;
      } catch {
        throw new Error(
          `No fue posible abrir Yahoo (HTTP ${response.status}).`,
        );
      }

      if (!response.ok || !payload.authorization_url) {
        const detail =
          typeof payload.detail === "string"
            ? payload.detail
            : payload.detail?.message;
        throw new Error(
          detail ?? "No fue posible abrir el inicio de sesión de Yahoo.",
        );
      }

      window.location.assign(payload.authorization_url);
    } finally {
      setConnectingYahoo(false);
    }
  }, []);

  return {
    connection,
    loadingConnection,
    connectionError,
    connectingYahoo,
    loadGoogleStatus,
    startGoogleConnection,
    startYahooConnection,
  };
}
