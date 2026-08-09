"use client";

import { LoaderCircle, RefreshCw, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { hmsFetch } from "@/lib/hmsApi";
import type { GmailMessage, GmailMessagesResponse } from "@/types/mail";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
  "/api/hms";

type LiveMailPanelProps = {
  open: boolean;
  onClose: () => void;
  mailboxLabel?: string | null;
};

export function LiveMailPanel({
  open,
  onClose,
  mailboxLabel,
}: LiveMailPanelProps) {
  const [messages, setMessages] = useState<GmailMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await hmsFetch(
        `${API_BASE_URL}/gmail/messages?limit=50`,
        { method: "GET", cache: "no-store" },
      );
      const data = (await response.json()) as GmailMessagesResponse & {
        detail?: { message?: string } | string;
      };

      if (!response.ok) {
        const detail = data.detail;
        const message =
          typeof detail === "string"
            ? detail
            : detail && typeof detail === "object" && "message" in detail
              ? String(detail.message)
              : "No fue posible cargar los correos.";
        throw new Error(message);
      }

      setMessages(Array.isArray(data.messages) ? data.messages : []);
    } catch (requestError) {
      setMessages([]);
      setError(
        requestError instanceof Error
          ? requestError.message
          : "No fue posible cargar los correos.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!open) {
      return;
    }
    const timer = window.setTimeout(() => {
      void load();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [open, load]);

  if (!open) {
    return null;
  }

  return (
    <div className="hms-mailbox-overlay" role="dialog" aria-modal="true">
      <section className="hms-mailbox-shell">
        <header className="hms-mailbox-header">
          <div>
            <strong>Correos en vivo</strong>
            <p style={{ margin: "6px 0 0", fontSize: 14, opacity: 0.8 }}>
              {mailboxLabel || "Buzón conectado"} · lectura directa del proveedor
            </p>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button
              type="button"
              className="hms-mailbox-refresh"
              onClick={() => void load()}
              disabled={loading}
              aria-label="Actualizar"
            >
              <RefreshCw size={18} className={loading ? "app-spin" : undefined} />
            </button>
            <button type="button" onClick={onClose} aria-label="Cerrar">
              <X size={20} />
            </button>
          </div>
        </header>

        {error ? <div className="hms-mailbox-error">{error}</div> : null}

        <div className="hms-mailbox-list">
          {loading && messages.length === 0 ? (
            <div className="hms-mailbox-empty">
              <LoaderCircle className="app-spin" size={22} />
              Cargando correos…
            </div>
          ) : messages.length === 0 ? (
            <div className="hms-mailbox-empty">
              No hay mensajes recientes en este buzón.
            </div>
          ) : (
            messages.map((message) => (
              <article
                key={message.id}
                className={
                  message.is_unread
                    ? "hms-mailbox-row is-unread"
                    : "hms-mailbox-row"
                }
                style={{
                  padding: "12px 16px",
                  borderBottom: "1px solid rgba(15,40,48,0.08)",
                }}
              >
                <strong style={{ display: "block" }}>
                  {message.sender || "Remitente"}
                </strong>
                <span style={{ display: "block", marginTop: 4 }}>
                  {message.subject}
                </span>
                <p
                  style={{
                    margin: "6px 0 0",
                    fontSize: 13,
                    opacity: 0.75,
                  }}
                >
                  {message.snippet}
                </p>
              </article>
            ))
          )}
        </div>
      </section>
    </div>
  );
}
