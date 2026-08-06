"use client";

import {
  ArrowLeft,
  Bell,
  ChevronLeft,
  ChevronRight,
  Heart,
  Inbox,
  LoaderCircle,
  Mail,
  MessageSquareText,
  Paperclip,
  RefreshCw,
  Search,
  Send,
  Settings2,
  ShieldCheck,
  X,
} from "lucide-react";
import {
  FormEvent,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import { hmsJson } from "@/lib/hmsApi";


type FavoriteRule = {
  id: string;
  match_type: "sender" | "subject" | "sender_subject";
  is_active: boolean;
};

type ConversationRow = {
  conversation_key: string;
  latest_message_id: string;
  message_count: number;
  unread_count: number;
  latest_received_at: string;
  sender: string | null;
  recipients: unknown;
  subject: string | null;
  normalized_subject: string | null;
  summary: string;
  triage_category: string;
  direction: string;
  has_attachments: boolean;
  favorite: boolean;
  participants: string | null;
};

type ThreadListResponse = {
  status: string;
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
  conversations: ConversationRow[];
};

type MessageDetail = {
  id: string;
  sender: string | null;
  recipients: unknown;
  cc: unknown;
  bcc: unknown;
  subject: string | null;
  summary: string;
  body_text: string | null;
  body_html: string | null;
  received_at: string;
  direction: string;
  triage_category: string;
  triage_reason: string | null;
  has_attachments: boolean;
  favorite: FavoriteRule | null;
  related_cases: Array<{
    id: string;
    title: string;
    status: string;
    priority: string;
    risk_score: number;
  }>;
};

type ConversationDetail = {
  status: string;
  message_count: number;
  latest_message_id: string;
  subject: string | null;
  normalized_subject: string | null;
  summary: string;
  participants: string[];
  messages: MessageDetail[];
};

type FilterOption = {
  key: string;
  label: string;
  category?: string;
  direction?: string;
  favorites?: boolean;
};

const PAGE_SIZE = 32;

const FILTERS: FilterOption[] = [
  { key: "all", label: "Todos" },
  { key: "action_required", label: "Requieren atención", category: "action_required" },
  { key: "review", label: "Revisión humana", category: "review" },
  { key: "notice", label: "Avisos importantes", category: "notice" },
  { key: "social", label: "Social", category: "social" },
  { key: "promotional", label: "Publicidad", category: "promotional" },
  { key: "automated", label: "Automatizados", category: "automated" },
  { key: "informational", label: "Informativos", category: "informational" },
  { key: "unreviewed", label: "Por clasificar", category: "unreviewed" },
  { key: "sent", label: "Enviados", direction: "outbound" },
  { key: "favorites", label: "Favoritos", favorites: true },
];

const CATEGORY_LABELS: Record<string, string> = {
  action_required: "Requiere atención",
  waiting_external: "Esperando respuesta",
  review: "Revisión humana",
  notice: "Aviso importante",
  social: "Social",
  promotional: "Publicidad",
  automated: "Automatizado",
  informational: "Informativo",
  unreviewed: "Por clasificar",
};

const RULE_CATEGORIES = [
  ["action_required", "Requiere atención"],
  ["review", "Revisión humana"],
  ["notice", "Aviso importante"],
  ["social", "Social"],
  ["promotional", "Publicidad"],
  ["automated", "Automatizado"],
  ["informational", "Informativo"],
] as const;

function readableError(reason: unknown): string {
  return reason instanceof Error
    ? reason.message
    : "No fue posible consultar los correos descargados.";
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("es-MX", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function textList(value: unknown): string {
  if (!value) return "—";
  if (typeof value === "string") return value;
  if (Array.isArray(value)) {
    return value
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object") {
          const entry = item as { name?: unknown; email?: unknown };
          return [entry.name, entry.email].filter(Boolean).join(" ");
        }
        return String(item);
      })
      .filter(Boolean)
      .join(", ");
  }
  return String(value);
}

function sanitizeEmailHtml(value: string): string {
  const clean = value
    .replace(/<script[\s\S]*?<\/script>/gi, "")
    .replace(/<iframe[\s\S]*?<\/iframe>/gi, "")
    .replace(/<object[\s\S]*?<\/object>/gi, "")
    .replace(/<embed[^>]*>/gi, "")
    .replace(/<form[\s\S]*?<\/form>/gi, "")
    .replace(/<base[^>]*>/gi, "")
    .replace(/<meta[^>]+http-equiv[^>]*>/gi, "")
    .replace(/\son\w+\s*=\s*(["']).*?\1/gi, "")
    .replace(/\son\w+\s*=\s*[^\s>]+/gi, "");

  return `<!doctype html><html lang="es"><head><meta charset="utf-8" />
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data: cid:; style-src 'unsafe-inline'; font-src data:;" />
<style>body{font-family:Arial,sans-serif;margin:22px;color:#172126;line-height:1.55;overflow-wrap:anywhere}img,table{max-width:100%;height:auto}a{color:#087b80}</style>
</head><body>${clean}</body></html>`;
}

export function MailInbox({
  initialCategory,
  initialMessageId = null,
  onClose,
}: {
  initialCategory: string | null;
  initialMessageId?: string | null;
  onClose: () => void;
}) {
  const initialFilter = FILTERS.find(
    (item) => item.category === initialCategory,
  )?.key ?? "all";
  const [activeFilter, setActiveFilter] = useState(initialFilter);
  const [rows, setRows] = useState<ConversationRow[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [detail, setDetail] = useState<ConversationDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [favoriteTarget, setFavoriteTarget] = useState<ConversationRow | null>(null);
  const [ruleTarget, setRuleTarget] = useState<MessageDetail | null>(null);
  const [saving, setSaving] = useState(false);
  const [ruleMatchType, setRuleMatchType] = useState("sender");
  const [ruleCategory, setRuleCategory] = useState("informational");
  const [ruleValue, setRuleValue] = useState("");
  const [applyExisting, setApplyExisting] = useState(false);
  const [rulePush, setRulePush] = useState(false);

  const selectedFilter = useMemo(
    () => FILTERS.find((item) => item.key === activeFilter) ?? FILTERS[0],
    [activeFilter],
  );

  const loadThreads = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        limit: String(PAGE_SIZE),
        offset: String(offset),
      });
      if (selectedFilter.category) params.set("triage_category", selectedFilter.category);
      if (selectedFilter.direction) params.set("direction", selectedFilter.direction);
      if (selectedFilter.favorites) params.set("favorites_only", "true");
      if (search) params.set("search", search);

      const data = await hmsJson<ThreadListResponse>(
        `/api/hms/messages/threads?${params.toString()}`,
        { cache: "no-store" },
      );
      setRows(data.conversations);
      setTotal(data.total);
    } catch (reason) {
      setError(readableError(reason));
    } finally {
      setLoading(false);
    }
  }, [offset, search, selectedFilter]);

  useEffect(() => {
    const timer = window.setTimeout(() => void loadThreads(), 0);
    return () => window.clearTimeout(timer);
  }, [loadThreads]);

  function applySearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setOffset(0);
    setSearch(searchInput.trim());
  }

  const openConversation = useCallback(async (messageId: string) => {
    setLoadingDetail(true);
    setError(null);
    try {
      setDetail(
        await hmsJson<ConversationDetail>(
          `/api/hms/messages/stored/${messageId}/conversation`,
          { cache: "no-store" },
        ),
      );
    } catch (reason) {
      setError(readableError(reason));
    } finally {
      setLoadingDetail(false);
    }
  }, []);

  useEffect(() => {
    if (!initialMessageId) return;
    const timer = window.setTimeout(() => {
      void openConversation(initialMessageId);
    }, 0);
    return () => window.clearTimeout(timer);
  }, [initialMessageId, openConversation]);

  async function saveFavorite(
    target: ConversationRow,
    enabled: boolean,
    matchType: "sender" | "subject" | "sender_subject",
  ) {
    setSaving(true);
    try {
      await hmsJson(
        `/api/hms/messages/stored/${target.latest_message_id}/favorite`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ enabled, match_type: matchType }),
        },
      );
      setFavoriteTarget(null);
      await loadThreads();
      window.dispatchEvent(new Event("hms:data-changed"));
    } catch (reason) {
      setError(readableError(reason));
    } finally {
      setSaving(false);
    }
  }

  async function saveRule() {
    if (!ruleTarget) return;
    setSaving(true);
    setError(null);
    try {
      await hmsJson("/api/hms/messages/rules", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source_message_id: ruleTarget.id,
          name: `Regla: ${ruleTarget.subject || ruleTarget.sender || "correo"}`,
          match_type: ruleMatchType,
          target_category: ruleCategory,
          match_value: ruleValue.trim() || null,
          apply_existing: applyExisting,
          notify_push: rulePush,
        }),
      });
      setRuleTarget(null);
      setApplyExisting(false);
      setRulePush(false);
      setRuleValue("");
      await loadThreads();
      if (detail) await openConversation(detail.latest_message_id);
      window.dispatchEvent(new Event("hms:data-changed"));
    } catch (reason) {
      setError(readableError(reason));
    } finally {
      setSaving(false);
    }
  }

  const page = Math.floor(offset / PAGE_SIZE) + 1;
  const pageCount = Math.max(Math.ceil(total / PAGE_SIZE), 1);

  return (
    <div className="hms-mailbox-overlay" role="dialog" aria-modal="true">
      <section className="hms-mailbox-shell">
        <header className="hms-mailbox-header">
          <div>
            <span>BANDEJA INTELIGENTE</span>
            <h2>Correos</h2>
            <p>Todos los mensajes agrupados por tema y ordenados del más reciente al más antiguo.</p>
          </div>
          <button type="button" onClick={onClose} aria-label="Cerrar Correos">
            <X size={23} />
          </button>
        </header>

        <div className="hms-mailbox-toolbar">
          <form onSubmit={applySearch}>
            <Search size={19} />
            <input
              type="search"
              value={searchInput}
              placeholder="Buscar cualquier palabra en remitente, destinatarios, asunto o contenido..."
              onChange={(event) => setSearchInput(event.target.value)}
            />
            {search ? (
              <button
                className="clear"
                type="button"
                onClick={() => {
                  setSearchInput("");
                  setSearch("");
                  setOffset(0);
                }}
              >
                Limpiar
              </button>
            ) : null}
            <button type="submit">Buscar</button>
          </form>
          <button
            type="button"
            className="hms-mailbox-refresh"
            onClick={() => void loadThreads()}
            disabled={loading}
          >
            <RefreshCw className={loading ? "app-spin" : undefined} size={19} />
            Actualizar
          </button>
        </div>

        <nav className="hms-mailbox-filters" aria-label="Filtros de correos">
          {FILTERS.map((filter) => (
            <button
              key={filter.key}
              type="button"
              className={activeFilter === filter.key ? "is-active" : ""}
              onClick={() => {
                setActiveFilter(filter.key);
                setOffset(0);
              }}
            >
              {filter.key === "favorites" ? <Heart size={15} /> : null}
              {filter.label}
            </button>
          ))}
        </nav>

        {error ? <div className="hms-mailbox-error">{error}</div> : null}

        <div className="hms-mailbox-count">
          <Inbox size={18} />
          <strong>{total.toLocaleString()}</strong>
          <span>{search ? `conversaciones que contienen “${search}”` : "conversaciones"}</span>
        </div>

        <div className="hms-mailbox-list">
          {loading ? (
            <div className="hms-mailbox-empty">
              <LoaderCircle className="app-spin" size={30} />
              Buscando en todo el contenido...
            </div>
          ) : rows.length === 0 ? (
            <div className="hms-mailbox-empty">
              <Mail size={30} />
              {search ? `No se encontró “${search}” en los correos descargados.` : "No hay correos en esta vista."}
            </div>
          ) : (
            rows.map((row) => (
              <article key={row.conversation_key} className={row.unread_count > 0 ? "hms-mail-row is-unread" : "hms-mail-row"}>
                <button
                  type="button"
                  className="hms-mail-row-main"
                  onClick={() => void openConversation(row.latest_message_id)}
                >
                  <span className="hms-mail-direction">
                    {row.direction === "outbound" ? <Send size={18} /> : <Mail size={18} />}
                  </span>
                  <span className="hms-mail-row-copy">
                    <span className="hms-mail-row-top">
                      <strong>{row.sender || "Sin remitente"}</strong>
                      <time>{formatDate(row.latest_received_at)}</time>
                    </span>
                    <b>{row.subject || "Sin asunto"}</b>
                    <small>{row.summary}</small>
                    <span className="hms-mail-row-meta">
                      <em>{CATEGORY_LABELS[row.triage_category] || row.triage_category}</em>
                      <span><MessageSquareText size={13} /> {row.message_count} mensajes</span>
                      {row.unread_count > 0 ? <span>{row.unread_count} sin leer</span> : null}
                      {row.has_attachments ? <span><Paperclip size={13} /> Adjuntos</span> : null}
                    </span>
                  </span>
                </button>
                <button
                  type="button"
                  className={row.favorite ? "hms-mail-favorite is-active" : "hms-mail-favorite"}
                  aria-label={row.favorite ? "Editar favorito" : "Marcar como favorito"}
                  onClick={() => setFavoriteTarget(row)}
                >
                  <Heart size={21} fill={row.favorite ? "currentColor" : "none"} />
                </button>
              </article>
            ))
          )}
        </div>

        <footer className="hms-mailbox-pagination">
          <button type="button" disabled={offset === 0} onClick={() => setOffset(Math.max(offset - PAGE_SIZE, 0))}>
            <ChevronLeft size={18} /> Anterior
          </button>
          <span>Página {page} de {pageCount}</span>
          <button type="button" disabled={offset + PAGE_SIZE >= total} onClick={() => setOffset(offset + PAGE_SIZE)}>
            Siguiente <ChevronRight size={18} />
          </button>
        </footer>
      </section>

      {loadingDetail ? (
        <div className="hms-mail-detail-loading"><LoaderCircle className="app-spin" size={34} /> Abriendo conversación...</div>
      ) : null}

      {detail ? (
        <section className="hms-mail-detail">
          <header>
            <button type="button" onClick={() => setDetail(null)}><ArrowLeft size={19} /> Volver</button>
            <div>
              <span>{detail.message_count} mensajes</span>
              <strong>{detail.subject || "Sin asunto"}</strong>
            </div>
            <button type="button" onClick={() => setRuleTarget(detail.messages[detail.messages.length - 1] || null)}>
              <Settings2 size={18} /> Crear regla
            </button>
          </header>

          <section className="hms-mail-ai-summary">
            <ShieldCheck size={21} />
            <div><strong>Resumen de la conversación</strong><p>{detail.summary}</p><small>{detail.participants.join(" · ")}</small></div>
          </section>

          <div className="hms-conversation-timeline">
            {detail.messages.map((message, index) => (
              <details key={message.id} open={index === detail.messages.length - 1}>
                <summary>
                  <span><strong>{message.sender || "Sin remitente"}</strong><small>{message.subject || "Sin asunto"}</small></span>
                  <time>{formatDate(message.received_at)}</time>
                </summary>
                <div className="hms-message-metadata">
                  <span>Para: {textList(message.recipients)}</span>
                  {textList(message.cc) !== "—" ? <span>CC: {textList(message.cc)}</span> : null}
                  <em>{CATEGORY_LABELS[message.triage_category] || message.triage_category}</em>
                </div>
                <section className="hms-message-summary"><ShieldCheck size={18} /><div><strong>Resumen HMS</strong><p>{message.summary}</p><small>{message.triage_reason || "Sin explicación adicional."}</small></div></section>
                {message.related_cases?.length ? (
                  <div className="hms-mail-related-case">
                    <strong>Caso relacionado</strong>
                    {message.related_cases.map((item) => <span key={item.id}>{item.title} · {item.priority}</span>)}
                  </div>
                ) : null}
                <div className="hms-mail-content">
                  {message.body_html ? (
                    <iframe title={`Contenido de ${message.subject || "correo"}`} sandbox="" referrerPolicy="no-referrer" srcDoc={sanitizeEmailHtml(message.body_html)} />
                  ) : (
                    <pre>{message.body_text || "Este mensaje no contiene cuerpo disponible."}</pre>
                  )}
                </div>
              </details>
            ))}
          </div>
        </section>
      ) : null}

      {favoriteTarget ? (
        <div className="hms-favorite-dialog-backdrop">
          <section className="hms-favorite-dialog">
            <Heart size={30} />
            <h3>{favoriteTarget.favorite ? "Editar favorito" : "Seguir este correo"}</h3>
            <p>HMS te avisará únicamente por las coincidencias que elijas.</p>
            <button disabled={saving} type="button" onClick={() => void saveFavorite(favoriteTarget, true, "sender")}>Avisar por este remitente</button>
            <button disabled={saving} type="button" onClick={() => void saveFavorite(favoriteTarget, true, "subject")}>Avisar por este tema</button>
            <button disabled={saving} type="button" onClick={() => void saveFavorite(favoriteTarget, true, "sender_subject")}>Remitente y tema</button>
            {favoriteTarget.favorite ? <button disabled={saving} className="danger" type="button" onClick={() => void saveFavorite(favoriteTarget, false, "sender")}>Quitar favorito</button> : null}
            <button className="secondary" type="button" onClick={() => setFavoriteTarget(null)}>Cancelar</button>
          </section>
        </div>
      ) : null}

      {ruleTarget ? (
        <div className="hms-favorite-dialog-backdrop">
          <section className="hms-rule-dialog">
            <Settings2 size={30} />
            <h3>Crear regla automática</h3>
            <p>Esta regla se aplicará a los correos nuevos. El historial solo se modifica si lo autorizas.</p>
            <label>Coincidencia
              <select value={ruleMatchType} onChange={(event) => setRuleMatchType(event.target.value)}>
                <option value="sender">Mismo remitente</option>
                <option value="sender_domain">Mismo dominio</option>
                <option value="subject_contains">Tema contiene</option>
                <option value="body_contains">Contenido contiene</option>
                <option value="sender_subject">Remitente y tema</option>
              </select>
            </label>
            {(ruleMatchType === "body_contains" || ruleMatchType === "subject_contains") ? (
              <label>Texto de la regla<input value={ruleValue} onChange={(event) => setRuleValue(event.target.value)} placeholder="Ejemplo: factura vencida" /></label>
            ) : null}
            <label>Categoría
              <select value={ruleCategory} onChange={(event) => setRuleCategory(event.target.value)}>
                {RULE_CATEGORIES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </label>
            <label className="check"><input type="checkbox" checked={applyExisting} onChange={(event) => setApplyExisting(event.target.checked)} /> Aplicar únicamente a correos existentes que coincidan</label>
            <label className="check"><input type="checkbox" checked={rulePush} onChange={(event) => setRulePush(event.target.checked)} /> Enviar aviso push cuando coincida</label>
            <button disabled={saving} type="button" onClick={() => void saveRule()}>{saving ? <LoaderCircle className="app-spin" size={18} /> : <Bell size={18} />} Guardar regla</button>
            <button className="secondary" type="button" onClick={() => setRuleTarget(null)}>Cancelar</button>
          </section>
        </div>
      ) : null}
    </div>
  );
}
