"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "";

type GoogleConnectionStatus = {
  status: string;
  connected: boolean;
  email: string | null;
  has_access_token: boolean;
  has_refresh_token: boolean;
  scopes: string[];
  login_url: string | null;
  message: string | null;
};

type GmailMessage = {
  id: string;
  thread_id: string;
  subject: string;
  sender: string;
  sender_email: string | null;
  recipient: string | null;
  received_at: string | null;
  snippet: string;
  is_unread: boolean;
  labels: string[];
};

type GmailMessagesResponse = {
  status: string;
  connected: boolean;
  total: number;
  messages: GmailMessage[];
};

type MailFilter =
  | "all"
  | "unread"
  | "personal"
  | "promotions"
  | "social"
  | "updates";

const FILTERS: Array<{ id: MailFilter; label: string }> = [
  { id: "all", label: "Todos" },
  { id: "unread", label: "No leídos" },
  { id: "personal", label: "Personal" },
  { id: "promotions", label: "Promociones" },
  { id: "social", label: "Social" },
  { id: "updates", label: "Actualizaciones" },
];

function containsLabel(message: GmailMessage, label: string): boolean {
  return message.labels.includes(label);
}

function getCategory(message: GmailMessage): {
  label: string;
  className: string;
} {
  if (containsLabel(message, "CATEGORY_PERSONAL")) {
    return {
      label: "Personal",
      className: "category category-personal",
    };
  }

  if (containsLabel(message, "CATEGORY_PROMOTIONS")) {
    return {
      label: "Promoción",
      className: "category category-promotions",
    };
  }

  if (containsLabel(message, "CATEGORY_SOCIAL")) {
    return {
      label: "Social",
      className: "category category-social",
    };
  }

  if (containsLabel(message, "CATEGORY_UPDATES")) {
    return {
      label: "Actualización",
      className: "category category-updates",
    };
  }

  return {
    label: "General",
    className: "category category-general",
  };
}

function formatMessageDate(value: string | null): string {
  if (!value) {
    return "Fecha no disponible";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("es-MX", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function getInitials(name: string): string {
  const initials = name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join("");

  return initials || "✉";
}

function normalizeText(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

export default function Home() {
  const [connection, setConnection] =
    useState<GoogleConnectionStatus | null>(null);
  const [messages, setMessages] = useState<GmailMessage[]>([]);
  const [activeFilter, setActiveFilter] = useState<MailFilter>("all");
  const [searchTerm, setSearchTerm] = useState("");
  const [loadingStatus, setLoadingStatus] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const loadMessages = useCallback(async () => {
    if (!API_BASE_URL) {
      setError(
        "No se configuró NEXT_PUBLIC_API_BASE_URL en frontend/.env.local.",
      );
      return;
    }

    setLoadingMessages(true);
    setError(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/gmail/messages?max_results=50`,
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

      setMessages(gmailData.messages);
      setLastUpdated(new Date());
    } catch (requestError) {
      const message =
        requestError instanceof Error
          ? requestError.message
          : "Ocurrió un error al consultar Gmail.";

      setError(message);
    } finally {
      setLoadingMessages(false);
    }
  }, []);

  const loadConnectionStatus = useCallback(async () => {
    if (!API_BASE_URL) {
      setLoadingStatus(false);
      setError(
        "No se configuró NEXT_PUBLIC_API_BASE_URL en frontend/.env.local.",
      );
      return;
    }

    setLoadingStatus(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/auth/google/status`, {
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
      }
    } catch (requestError) {
      const message =
        requestError instanceof Error
          ? requestError.message
          : "No fue posible conectar con el backend.";

      setError(message);
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

  const unreadCount = useMemo(
    () => messages.filter((message) => message.is_unread).length,
    [messages],
  );

  const personalCount = useMemo(
    () =>
      messages.filter((message) =>
        containsLabel(message, "CATEGORY_PERSONAL"),
      ).length,
    [messages],
  );

  const promotionsCount = useMemo(
    () =>
      messages.filter((message) =>
        containsLabel(message, "CATEGORY_PROMOTIONS"),
      ).length,
    [messages],
  );

  const filteredMessages = useMemo(() => {
    const normalizedSearch = normalizeText(searchTerm.trim());

    return messages.filter((message) => {
      let matchesFilter = true;

      switch (activeFilter) {
        case "unread":
          matchesFilter = message.is_unread;
          break;
        case "personal":
          matchesFilter = containsLabel(message, "CATEGORY_PERSONAL");
          break;
        case "promotions":
          matchesFilter = containsLabel(message, "CATEGORY_PROMOTIONS");
          break;
        case "social":
          matchesFilter = containsLabel(message, "CATEGORY_SOCIAL");
          break;
        case "updates":
          matchesFilter = containsLabel(message, "CATEGORY_UPDATES");
          break;
        default:
          matchesFilter = true;
      }

      if (!matchesFilter) {
        return false;
      }

      if (!normalizedSearch) {
        return true;
      }

      const searchableText = normalizeText(
        [
          message.subject,
          message.sender,
          message.sender_email ?? "",
          message.snippet,
        ].join(" "),
      );

      return searchableText.includes(normalizedSearch);
    });
  }, [activeFilter, messages, searchTerm]);

  function connectGoogle(): void {
    window.location.href = `${API_BASE_URL}/auth/google/login`;
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">H</div>

          <div>
            <p className="brand-name">HMS AI</p>
            <p className="brand-subtitle">Email Assistant</p>
          </div>
        </div>

        <nav className="navigation" aria-label="Navegación principal">
          <button className="nav-item nav-item-active" type="button">
            <span className="nav-icon">⌂</span>
            <span>Panel principal</span>
          </button>

          <button className="nav-item" type="button">
            <span className="nav-icon">✉</span>
            <span>Correos</span>
          </button>

          <button className="nav-item" type="button">
            <span className="nav-icon">✓</span>
            <span>Tareas</span>
          </button>

          <button className="nav-item" type="button">
            <span className="nav-icon">⌛</span>
            <span>Pendientes</span>
          </button>

          <button className="nav-item" type="button">
            <span className="nav-icon">▥</span>
            <span>Reportes</span>
          </button>
        </nav>

        <div className="sidebar-footer">
          <button className="nav-item" type="button">
            <span className="nav-icon">⚙</span>
            <span>Configuración</span>
          </button>

          <div className="version-box">
            <span>Versión</span>
            <strong>0.4.0 alpha</strong>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <p className="eyebrow">ASISTENTE EJECUTIVO DE CORREO</p>
            <h1>Panel principal</h1>
            <p className="topbar-description">
              Supervisa correos, pendientes y tareas desde un solo lugar.
            </p>
          </div>

          <div className="topbar-actions">
            <button
              className="refresh-button"
              type="button"
              onClick={() => void loadConnectionStatus()}
              disabled={loadingStatus || loadingMessages}
            >
              <span
                className={
                  loadingStatus || loadingMessages ? "spinning" : undefined
                }
              >
                ↻
              </span>
              Actualizar
            </button>

            <div className="user-avatar">HM</div>
          </div>
        </header>

        {error ? (
          <section className="alert alert-error" role="alert">
            <div>
              <strong>No fue posible completar la operación.</strong>
              <p>{error}</p>
            </div>

            <button
              type="button"
              onClick={() => void loadConnectionStatus()}
            >
              Reintentar
            </button>
          </section>
        ) : null}

        <section className="connection-card">
          <div className="connection-main">
            <div className="google-icon">G</div>

            <div>
              <div className="connection-title-row">
                <h2>Cuenta de Google</h2>

                {loadingStatus ? (
                  <span className="status-pill status-loading">
                    Verificando…
                  </span>
                ) : connection?.connected ? (
                  <span className="status-pill status-connected">
                    <span className="status-dot" />
                    Conectada
                  </span>
                ) : (
                  <span className="status-pill status-disconnected">
                    Desconectada
                  </span>
                )}
              </div>

              <p>
                {connection?.connected
                  ? connection.email || "Cuenta autorizada correctamente"
                  : connection?.message ||
                    "Conecta una cuenta para comenzar a revisar correos."}
              </p>
            </div>
          </div>

          {!loadingStatus && !connection?.connected ? (
            <button
              className="primary-button"
              type="button"
              onClick={connectGoogle}
            >
              Conectar con Google
            </button>
          ) : (
            <div className="connection-permission">
              <span>Acceso autorizado</span>
              <strong>Solo lectura</strong>
            </div>
          )}
        </section>

        <section className="metrics-grid" aria-label="Resumen del buzón">
          <article className="metric-card">
            <div className="metric-icon metric-icon-blue">✉</div>
            <div>
              <p>Total consultado</p>
              <strong>{messages.length}</strong>
              <span>Últimos correos obtenidos</span>
            </div>
          </article>

          <article className="metric-card">
            <div className="metric-icon metric-icon-orange">●</div>
            <div>
              <p>No leídos</p>
              <strong>{unreadCount}</strong>
              <span>Requieren revisión</span>
            </div>
          </article>

          <article className="metric-card">
            <div className="metric-icon metric-icon-green">☺</div>
            <div>
              <p>Personales</p>
              <strong>{personalCount}</strong>
              <span>Conversaciones directas</span>
            </div>
          </article>

          <article className="metric-card">
            <div className="metric-icon metric-icon-purple">★</div>
            <div>
              <p>Promociones</p>
              <strong>{promotionsCount}</strong>
              <span>Publicidad y campañas</span>
            </div>
          </article>
        </section>

        <section className="mail-panel">
          <div className="mail-panel-header">
            <div>
              <h2>Correos recientes</h2>
              <p>
                Revisa los mensajes recuperados directamente desde Gmail.
              </p>
            </div>

            <div className="mail-header-meta">
              {lastUpdated ? (
                <span>
                  Actualizado{" "}
                  {new Intl.DateTimeFormat("es-MX", {
                    hour: "2-digit",
                    minute: "2-digit",
                  }).format(lastUpdated)}
                </span>
              ) : null}

              <span>{filteredMessages.length} resultados</span>
            </div>
          </div>

          <div className="mail-toolbar">
            <div className="filters" aria-label="Filtros de correo">
              {FILTERS.map((filter) => (
                <button
                  key={filter.id}
                  className={
                    activeFilter === filter.id
                      ? "filter-button filter-button-active"
                      : "filter-button"
                  }
                  type="button"
                  onClick={() => setActiveFilter(filter.id)}
                >
                  {filter.label}
                </button>
              ))}
            </div>

            <label className="search-box">
              <span>⌕</span>
              <input
                type="search"
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
                placeholder="Buscar asunto o remitente"
                aria-label="Buscar correos"
              />
            </label>
          </div>

          <div className="mail-list">
            {loadingMessages ? (
              <div className="empty-state">
                <div className="loader" />
                <h3>Consultando Gmail</h3>
                <p>Estamos recuperando los mensajes más recientes.</p>
              </div>
            ) : !connection?.connected ? (
              <div className="empty-state">
                <div className="empty-icon">✉</div>
                <h3>Conecta tu cuenta de Google</h3>
                <p>
                  Autoriza Gmail para visualizar los correos en este panel.
                </p>

                <button
                  className="primary-button"
                  type="button"
                  onClick={connectGoogle}
                >
                  Conectar Gmail
                </button>
              </div>
            ) : filteredMessages.length === 0 ? (
              <div className="empty-state">
                <div className="empty-icon">⌕</div>
                <h3>No encontramos correos</h3>
                <p>
                  Modifica el filtro o la búsqueda para ver otros resultados.
                </p>
              </div>
            ) : (
              filteredMessages.map((message) => {
                const category = getCategory(message);

                return (
                  <article
                    key={message.id}
                    className={
                      message.is_unread
                        ? "mail-item mail-item-unread"
                        : "mail-item"
                    }
                  >
                    <div className="sender-avatar">
                      {getInitials(message.sender)}
                    </div>

                    <div className="mail-body">
                      <div className="mail-primary-row">
                        <div className="mail-sender-row">
                          {message.is_unread ? (
                            <span
                              className="unread-dot"
                              title="Correo no leído"
                            />
                          ) : null}

                          <strong>{message.sender}</strong>

                          <span className={category.className}>
                            {category.label}
                          </span>
                        </div>

                        <time>{formatMessageDate(message.received_at)}</time>
                      </div>

                      <h3>{message.subject || "Sin asunto"}</h3>

                      <p>{message.snippet || "Sin vista previa disponible."}</p>

                      <div className="mail-footer">
                        <span>{message.sender_email || "Correo no disponible"}</span>

                        {message.is_unread ? (
                          <span className="unread-label">No leído</span>
                        ) : (
                          <span>Leído</span>
                        )}
                      </div>
                    </div>
                  </article>
                );
              })
            )}
          </div>
        </section>
      </main>
    </div>
  );
}