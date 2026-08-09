"use client";

import {
  AlertTriangle,
  BellRing,
  CheckCircle2,
  ChevronRight,
  LoaderCircle,
  Mail,
  Package,
  RefreshCw,
  Shield,
  VolumeX,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { hmsJson } from "@/lib/hmsApi";

import "./attention-home.css";

type TriageMessage = {
  id: string;
  sender?: string | null;
  subject?: string | null;
  snippet?: string | null;
  received_at?: string | null;
  triage_category?: string | null;
  triage_reason?: string | null;
  actionability_score?: number | null;
};

type TriageCategory = {
  key: string;
  count: number;
  messages?: TriageMessage[];
};

type TriageSummary = {
  status: string;
  total: number;
  categories: TriageCategory[];
};

/** N1 EE.UU.: dinero/seguridad/logística/acción — push candidate */
const N1_KEYS = ["action_required", "notice", "review"] as const;
/** N2: digest / opt-in */
const N2_KEYS = ["waiting_external", "informational"] as const;
/** N3: silencio / sin push */
const N3_KEYS = ["social", "promotional", "automated"] as const;

const LEVEL_LABEL: Record<string, { title: string; why: string }> = {
  action_required: {
    title: "Te necesitan",
    why: "Solicitud o respuesta pendiente de ti",
  },
  notice: {
    title: "Dinero, seguridad o avisos",
    why: "Pagos, seguridad, plazos o cambios de servicio",
  },
  review: {
    title: "Revisión humana",
    why: "Donexto no decide solo; conviene que lo mires",
  },
  waiting_external: {
    title: "Esperando al otro",
    why: "Ya enviaste; el siguiente paso es externo",
  },
  informational: {
    title: "Informativos",
    why: "Útiles, sin urgencia inmediata",
  },
  social: {
    title: "Social",
    why: "Redes y menciones masivas",
  },
  promotional: {
    title: "Publicidad",
    why: "Promos y campañas — sin push",
  },
  automated: {
    title: "Automatizados",
    why: "Sistemas sin pedido humano directo",
  },
  unreviewed: {
    title: "Por clasificar",
    why: "Aún en proceso de clasificación",
  },
};

function errorMessage(reason: unknown): string {
  return reason instanceof Error
    ? reason.message
    : "No fue posible cargar lo que requiere atención.";
}

function senderLabel(value?: string | null): string {
  if (!value) return "Remitente";
  const match = value.match(/<([^>]+)>/);
  const email = (match?.[1] ?? value).trim();
  const name = value.replace(/<[^>]+>/, "").trim().replace(/^"|"$/g, "");
  if (name && name !== email) return name.slice(0, 48);
  return email.slice(0, 48);
}

function formatWhen(value?: string | null): string {
  if (!value) return "";
  try {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    return new Intl.DateTimeFormat("es-MX", {
      day: "numeric",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    }).format(date);
  } catch {
    return "";
  }
}

export function AttentionHome({
  mailboxEmail,
  mailboxConnected,
  mailboxLoading,
  personName,
  onConnectMailbox,
  onChangeMailbox,
  onRefreshMailbox,
  onOpenCategory,
  onOpenAllMail,
}: {
  mailboxEmail?: string | null;
  mailboxConnected: boolean;
  mailboxLoading: boolean;
  personName: string;
  onConnectMailbox: () => void;
  onChangeMailbox: () => void;
  onRefreshMailbox: () => void;
  onOpenCategory: (category: string | null) => void;
  onOpenAllMail: () => void;
}) {
  const [summary, setSummary] = useState<TriageSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [noiseOpen, setNoiseOpen] = useState(false);
  const [laterOpen, setLaterOpen] = useState(false);

  const loadSummary = useCallback(async () => {
    if (!mailboxConnected) {
      setSummary(null);
      setError(null);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const data = await hmsJson<TriageSummary>(
        "/api/hms/messages/triage-summary?limit_per_category=6",
        { cache: "no-store" },
      );
      setSummary(data);
    } catch (reason) {
      setSummary(null);
      setError(errorMessage(reason));
    } finally {
      setLoading(false);
    }
  }, [mailboxConnected]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadSummary();
    }, 0);
    const onRefresh = () => {
      void loadSummary();
    };
    window.addEventListener("hms:classification-complete", onRefresh);
    window.addEventListener("hms:data-changed", onRefresh);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener("hms:classification-complete", onRefresh);
      window.removeEventListener("hms:data-changed", onRefresh);
    };
  }, [loadSummary]);

  const byKey = useMemo(() => {
    const map = new Map<string, TriageCategory>();
    for (const row of summary?.categories ?? []) {
      map.set(row.key, row);
    }
    return map;
  }, [summary]);

  const countOf = (keys: readonly string[]) =>
    keys.reduce((sum, key) => sum + (byKey.get(key)?.count ?? 0), 0);

  const n1Items = useMemo(() => {
    const items: Array<TriageMessage & { category: string }> = [];
    for (const key of N1_KEYS) {
      const cat = byKey.get(key);
      for (const message of cat?.messages ?? []) {
        items.push({ ...message, category: key });
      }
    }
    return items
      .sort((a, b) => {
        const ta = a.received_at ? Date.parse(a.received_at) : 0;
        const tb = b.received_at ? Date.parse(b.received_at) : 0;
        return tb - ta;
      })
      .slice(0, 12);
  }, [byKey]);

  const n1Count = countOf(N1_KEYS);
  const n2Count = countOf(N2_KEYS);
  const n3Count = countOf(N3_KEYS);
  const unreviewed = byKey.get("unreviewed")?.count ?? 0;

  return (
    <section className="dx-attention" aria-label="Lo que requiere atención">
      <header className="dx-attention__hero">
        <div>
          <p className="dx-attention__kicker">Hoy en tu bandeja</p>
          <h1>
            {personName ? `Hola, ${personName}` : "Hola"}
          </h1>
          <p className="dx-attention__lede">
            Dinero, seguridad y lo que te espera — sin el ruido promocional.
          </p>
        </div>
      </header>

      <div className="dx-attention__mailbox">
        <div
          className={
            mailboxConnected
              ? "dx-attention__mailbox-chip is-on"
              : "dx-attention__mailbox-chip is-off"
          }
        >
          <span className="dx-attention__dot" />
          <div>
            <strong>
              {mailboxLoading
                ? "Verificando buzón…"
                : mailboxConnected
                  ? "Buzón conectado"
                  : "Sin buzón"}
            </strong>
            <small>
              {mailboxConnected
                ? mailboxEmail || "Correo activo"
                : "Conecta Gmail o Yahoo (distinto del login Donexto)"}
            </small>
          </div>
        </div>

        <div className="dx-attention__mailbox-actions">
          {mailboxConnected ? (
            <>
              <button type="button" onClick={onChangeMailbox}>
                Cambiar buzón
              </button>
              <button
                type="button"
                className="is-secondary"
                onClick={() => {
                  onRefreshMailbox();
                  void loadSummary();
                }}
                disabled={loading}
              >
                {loading ? (
                  <LoaderCircle className="app-spin" size={16} />
                ) : (
                  <RefreshCw size={16} />
                )}
                Actualizar
              </button>
            </>
          ) : (
            <button type="button" onClick={onConnectMailbox}>
              <Mail size={16} />
              Conectar correo
            </button>
          )}
        </div>
      </div>

      {!mailboxConnected ? (
        <div className="dx-attention__empty">
          <Mail size={28} />
          <p>
            Conecta tu buzón para ver lo que requiere atención. La cuenta Donexto
            no es la contraseña de Gmail ni Yahoo.
          </p>
          <button type="button" onClick={onConnectMailbox}>
            Conectar Gmail o Yahoo
          </button>
        </div>
      ) : null}

      {mailboxConnected && error ? (
        <div className="dx-attention__error" role="alert">
          <AlertTriangle size={18} />
          <div>
            <strong>No hay clasificación almacenada aún</strong>
            <span>
              {error} Si usas Yahoo en vivo, abre la bandeja. Con Gmail, completa
              la importación guiada.
            </span>
          </div>
          <button type="button" onClick={onOpenAllMail}>
            Abrir correos
          </button>
        </div>
      ) : null}

      {mailboxConnected && !error ? (
        <>
          <div className="dx-attention__levels" aria-hidden>
            <article>
              <Shield size={18} />
              <div>
                <strong>{n1Count}</strong>
                <span>Ahora (N1)</span>
              </div>
            </article>
            <article>
              <BellRing size={18} />
              <div>
                <strong>{n2Count}</strong>
                <span>Después (N2)</span>
              </div>
            </article>
            <article>
              <VolumeX size={18} />
              <div>
                <strong>{n3Count}</strong>
                <span>Silencio (N3)</span>
              </div>
            </article>
          </div>

          <div className="dx-attention__section">
            <header className="dx-attention__section-head">
              <div>
                <h2>Te necesita ahora</h2>
                <p>Prioridad alta · candidatos a alerta inmediata</p>
              </div>
              <button
                type="button"
                className="dx-attention__text-btn"
                onClick={() => onOpenCategory("action_required")}
              >
                Ver en correos
              </button>
            </header>

            {loading && n1Items.length === 0 ? (
              <div className="dx-attention__loading">
                <LoaderCircle className="app-spin" size={22} />
                Cargando…
              </div>
            ) : n1Items.length === 0 ? (
              <div className="dx-attention__peace">
                <CheckCircle2 size={22} />
                <div>
                  <strong>Nada urgente en N1</strong>
                  <span>
                    {unreviewed > 0
                      ? `${unreviewed.toLocaleString()} mensajes aún por clasificar.`
                      : "El ruido no aparece aquí. Puedes revisar la bandeja cuando quieras."}
                  </span>
                </div>
              </div>
            ) : (
              <ul className="dx-attention__list">
                {n1Items.map((item) => {
                  const meta = LEVEL_LABEL[item.category] ?? LEVEL_LABEL.review;
                  return (
                    <li key={`${item.category}-${item.id}`}>
                      <button
                        type="button"
                        className="dx-attention__row"
                        onClick={() => onOpenCategory(item.category)}
                      >
                        <span className="dx-attention__row-icon">
                          {item.category === "notice" ? (
                            <Package size={18} />
                          ) : item.category === "action_required" ? (
                            <Mail size={18} />
                          ) : (
                            <Shield size={18} />
                          )}
                        </span>
                        <span className="dx-attention__row-body">
                          <span className="dx-attention__row-top">
                            <strong>{senderLabel(item.sender)}</strong>
                            <time>{formatWhen(item.received_at)}</time>
                          </span>
                          <em>{item.subject || "(Sin asunto)"}</em>
                          <small>
                            {item.triage_reason?.trim() || meta.why}
                          </small>
                        </span>
                        <ChevronRight size={18} className="dx-attention__chev" />
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>

          <div className="dx-attention__section is-muted">
            <button
              type="button"
              className="dx-attention__collapse"
              aria-expanded={laterOpen}
              onClick={() => setLaterOpen((v) => !v)}
            >
              <span>
                <strong>Después / utilidad (N2)</strong>
                <small>
                  {n2Count.toLocaleString()} mensajes · resumen, no push inmediato
                </small>
              </span>
              <ChevronRight
                size={18}
                className={laterOpen ? "is-open" : undefined}
              />
            </button>
            {laterOpen ? (
              <div className="dx-attention__chips">
                {N2_KEYS.map((key) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => onOpenCategory(key)}
                  >
                    {LEVEL_LABEL[key]?.title ?? key}
                    <b>{(byKey.get(key)?.count ?? 0).toLocaleString()}</b>
                  </button>
                ))}
              </div>
            ) : null}
          </div>

          <div className="dx-attention__section is-muted">
            <button
              type="button"
              className="dx-attention__collapse"
              aria-expanded={noiseOpen}
              onClick={() => setNoiseOpen((v) => !v)}
            >
              <span>
                <strong>Ruido silenciado (N3)</strong>
                <small>
                  {n3Count.toLocaleString()} · promo, social y autos — sin
                  interrumpir
                </small>
              </span>
              <ChevronRight
                size={18}
                className={noiseOpen ? "is-open" : undefined}
              />
            </button>
            {noiseOpen ? (
              <div className="dx-attention__chips">
                {N3_KEYS.map((key) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => onOpenCategory(key)}
                  >
                    {LEVEL_LABEL[key]?.title ?? key}
                    <b>{(byKey.get(key)?.count ?? 0).toLocaleString()}</b>
                  </button>
                ))}
              </div>
            ) : null}
          </div>

          <footer className="dx-attention__foot">
            <span>
              Total clasificado en buzón:{" "}
              {(summary?.total ?? 0).toLocaleString()} mensajes
            </span>
            <button type="button" onClick={onOpenAllMail}>
              Ver todos los correos
            </button>
          </footer>
        </>
      ) : null}
    </section>
  );
}
