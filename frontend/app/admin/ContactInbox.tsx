"use client";

import { Loader2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { HmsApiError, hmsJson } from "@/lib/hmsApi";

export type ContactMessage = {
  id: string;
  name?: string | null;
  email?: string | null;
  country?: string | null;
  message?: string | null;
  language?: string | null;
  subject?: string | null;
  status?: string | null;
  draft_body?: string | null;
  draft_error?: string | null;
  reply_body?: string | null;
  replied_at?: string | null;
  created_at?: string | null;
};

type ContactListResponse = {
  messages: ContactMessage[];
  total: number;
  nuevo: number;
  unread: number;
};

type ContactActionResponse = {
  status: string;
  message?: string;
  contact?: ContactMessage;
};

const LANG_LABEL: Record<string, string> = {
  es: "Español",
  en: "English",
  fr: "Français",
  it: "Italiano",
  pt: "Português",
};

function formatWhen(value?: string | null): string {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString("es-MX", {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return value;
  }
}

function statusClass(status?: string | null): string {
  if (status === "respondido") return "dx-admin__pill is-ok";
  if (status === "borrador listo") return "dx-admin__pill is-draft";
  if (status === "nuevo") return "dx-admin__pill is-new";
  return "dx-admin__pill";
}

export function ContactInbox({
  onUnread,
  initialId,
  reloadToken = 0,
}: {
  onUnread: (count: number) => void;
  initialId?: string | null;
  reloadToken?: number;
}) {
  const [messages, setMessages] = useState<ContactMessage[]>([]);
  const [unread, setUnread] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(initialId ?? null);
  const [reply, setReply] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  const selected = messages.find((item) => item.id === selectedId) ?? null;
  const draftKey = `${selected?.id ?? ""}\0${selected?.draft_body ?? ""}`;
  const [draftKeySeen, setDraftKeySeen] = useState(draftKey);
  if (draftKey !== draftKeySeen) {
    setDraftKeySeen(draftKey);
    setReply(selected?.draft_body || "");
    setConfirming(false);
  }

  const applyList = useCallback(
    (data: ContactListResponse, preferId?: string | null) => {
      setMessages(data.messages);
      setUnread(data.unread);
      onUnread(data.unread);
      setSelectedId((current) => {
        const wanted = preferId || current;
        if (wanted && data.messages.some((item) => item.id === wanted)) {
          return wanted;
        }
        return data.messages[0]?.id ?? null;
      });
    },
    [onUnread],
  );

  const load = useCallback(
    async (preferId?: string | null) => {
      setLoading(true);
      setError(null);
      try {
        const data = await hmsJson<ContactListResponse>(
          "/api/hms/admin/contact-messages?limit=80",
          { cache: "no-store" },
        );
        applyList(data, preferId);
      } catch (err) {
        setError(
          err instanceof HmsApiError
            ? err.message
            : "No se pudo cargar la bandeja de mensajes.",
        );
      } finally {
        setLoading(false);
      }
    },
    [applyList],
  );

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => {
      void load(reloadToken === 0 ? initialId : null);
    });
    return () => window.cancelAnimationFrame(frame);
  }, [load, initialId, reloadToken]);

  function replaceContact(contact: ContactMessage | undefined, unreadCount?: number) {
    if (!contact) return;
    setMessages((current) =>
      current.map((item) => (item.id === contact.id ? { ...item, ...contact } : item)),
    );
    if (typeof unreadCount === "number") {
      setUnread(unreadCount);
      onUnread(unreadCount);
    }
  }

  async function onDraft() {
    if (!selected || busy) return;
    setBusy(true);
    setError(null);
    setNote(null);
    setConfirming(false);
    try {
      const data = await hmsJson<ContactActionResponse>(
        `/api/hms/admin/contact-messages/${encodeURIComponent(selected.id)}/draft`,
        { method: "POST" },
      );
      replaceContact(data.contact);
      if (data.contact?.draft_body) {
        setReply(data.contact.draft_body);
      }
      if (data.status === "draft_ready") {
        setNote("Borrador listo. Revísalo y edítalo antes de autorizar el envío.");
        onUnread(Math.max(0, unread));
      } else {
        setNote(data.message || "No se generó un borrador.");
      }
      if (data.status === "draft_ready") {
        await load(selected.id);
      }
    } catch (err) {
      setError(
        err instanceof HmsApiError
          ? err.message
          : "No se pudo redactar el borrador.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function onSend() {
    if (!selected || busy) return;
    const text = reply.trim();
    if (!text) {
      setError("Escribe la respuesta antes de autorizar el envío.");
      setConfirming(false);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const data = await hmsJson<ContactActionResponse>(
        `/api/hms/admin/contact-messages/${encodeURIComponent(selected.id)}/send`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ reply: text, confirm: true }),
        },
      );
      replaceContact(data.contact);
      setConfirming(false);
      setNote(data.message || "Respuesta enviada.");
      await load(selected.id);
    } catch (err) {
      setError(
        err instanceof HmsApiError
          ? err.message
          : "No se pudo enviar la respuesta.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function onArchive() {
    if (!selected || busy) return;
    setBusy(true);
    setError(null);
    setConfirming(false);
    try {
      await hmsJson<ContactActionResponse>(
        `/api/hms/admin/contact-messages/${encodeURIComponent(selected.id)}/archive`,
        { method: "POST" },
      );
      setNote("Mensaje archivado.");
      await load(selected.id);
    } catch (err) {
      setError(
        err instanceof HmsApiError
          ? err.message
          : "No se pudo archivar el mensaje.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="dx-admin__section">
      <header className="dx-admin__section-head">
        <h2>Mensajes</h2>
        <p>
          Lo que llega del formulario de donexto.com. Redactar con IA solo
          corre cuando tú lo pides, y el borrador no se envía solo. {unread}{" "}
          por atender.
        </p>
      </header>

      {error && (
        <div className="dx-admin__alert is-error" role="alert">
          {error}
        </div>
      )}
      {note && <p className="dx-admin__note">{note}</p>}
      {loading && (
        <div className="dx-admin__loading">
          <Loader2 className="dx-admin__spin" size={20} />
          Cargando mensajes…
        </div>
      )}

      {!loading && messages.length === 0 && !error && (
        <p className="dx-admin__note">Todavía no hay mensajes del formulario.</p>
      )}

      {messages.length > 0 && (
        <div className="dx-admin__inbox">
          <div className="dx-admin__inbox-list" role="list">
            {messages.map((item) => {
              const active = item.id === selectedId;
              return (
                <button
                  key={item.id}
                  type="button"
                  role="listitem"
                  className={
                    active
                      ? "dx-admin__inbox-item is-active"
                      : "dx-admin__inbox-item"
                  }
                  onClick={() => setSelectedId(item.id)}
                >
                  <span className="dx-admin__inbox-item-top">
                    <strong>{item.name || item.email || "Sin nombre"}</strong>
                    <span className={statusClass(item.status)}>
                      {item.status || "nuevo"}
                    </span>
                  </span>
                  <span className="dx-admin__inbox-preview">
                    {(item.message || "").slice(0, 90)}
                  </span>
                  <span className="dx-admin__inbox-meta">
                    {formatWhen(item.created_at)}
                  </span>
                </button>
              );
            })}
          </div>

          {selected && (
            <article className="dx-admin__inbox-detail">
              <header>
                <h3>{selected.name || "Sin nombre"}</h3>
                <p>
                  <a href={`mailto:${selected.email || ""}`}>{selected.email}</a>
                  {selected.country ? ` · ${selected.country}` : ""}
                  {" · "}
                  {LANG_LABEL[selected.language || ""] ||
                    selected.language ||
                    "idioma no indicado"}
                </p>
                <p className="dx-admin__inbox-meta">
                  {formatWhen(selected.created_at)} ·{" "}
                  <span className={statusClass(selected.status)}>
                    {selected.status}
                  </span>
                </p>
              </header>
              <blockquote className="dx-admin__quote">
                {selected.message}
              </blockquote>
              {selected.reply_body && selected.status === "respondido" && (
                <p className="dx-admin__note">
                  Respuesta enviada {formatWhen(selected.replied_at)}:{" "}
                  {selected.reply_body}
                </p>
              )}
              {selected.draft_error && (
                <p className="dx-admin__note">{selected.draft_error}</p>
              )}

              <label className="dx-admin__reply">
                Respuesta
                <textarea
                  rows={8}
                  value={reply}
                  onChange={(event) => {
                    setReply(event.target.value);
                    setConfirming(false);
                  }}
                  placeholder="Escribe o pega aquí la respuesta. No se envía hasta que la autorices."
                />
              </label>

              <div className="dx-admin__inbox-actions">
                <button
                  type="button"
                  className="dx-admin__btn dx-admin__btn--ghost"
                  onClick={() => void onDraft()}
                  disabled={busy}
                >
                  {busy ? "Trabajando…" : "Redactar con IA"}
                </button>
                <button
                  type="button"
                  className="dx-admin__btn"
                  onClick={() => {
                    if (!reply.trim()) {
                      setError("Escribe la respuesta antes de autorizar el envío.");
                      return;
                    }
                    setError(null);
                    setConfirming(true);
                  }}
                  disabled={busy || selected.status === "respondido"}
                >
                  Autorizar y enviar
                </button>
                <button
                  type="button"
                  className="dx-admin__btn dx-admin__btn--ghost"
                  onClick={() => void onArchive()}
                  disabled={busy || selected.status === "archivado"}
                >
                  Archivar
                </button>
              </div>

              {confirming && (
                <div className="dx-admin__confirm" role="region" aria-label="Confirmar envío">
                  <p>
                    Vas a enviar este texto a <strong>{selected.email}</strong>{" "}
                    desde support@donexto.com. El asunto será Re:{" "}
                    {selected.subject || "el mensaje"}.
                  </p>
                  <div className="dx-admin__inbox-actions">
                    <button
                      type="button"
                      className="dx-admin__btn"
                      onClick={() => void onSend()}
                      disabled={busy}
                    >
                      {busy ? "Enviando…" : "Sí, enviar"}
                    </button>
                    <button
                      type="button"
                      className="dx-admin__btn dx-admin__btn--ghost"
                      onClick={() => setConfirming(false)}
                      disabled={busy}
                    >
                      Cancelar
                    </button>
                  </div>
                </div>
              )}
            </article>
          )}
        </div>
      )}
    </section>
  );
}
