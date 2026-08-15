"use client";

import {
  Activity,
  ArrowLeft,
  CreditCard,
  Loader2,
  MessageSquareWarning,
  RefreshCw,
  Server,
  Shield,
  Tag,
  Users,
} from "lucide-react";
import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { ConfirmEmailGate } from "@/components/auth/ConfirmEmailGate";
import { LoginScreen } from "@/components/auth/LoginScreen";
import { useAppAuth } from "@/hooks/useAppAuth";
import { HmsApiError, hmsJson } from "@/lib/hmsApi";
import "@/app/admin/admin.css";

type AdminTab =
  | "overview"
  | "users"
  | "billing"
  | "feedback"
  | "promotions"
  | "system";

type OverviewResponse = {
  status: string;
  counts: {
    users: number;
    trials_active: number;
    active_paid: number;
    mailbox_connected: number;
    feedback_open: number;
    signed_up_no_product_use_24h: number;
  };
  schema?: {
    migrations_hint?: string | null;
  };
  product_health?: string;
  notes?: {
    account_vs_mailbox?: string;
  };
};

type UsersResponse = {
  users: Array<{
    id: string;
    email?: string | null;
    full_name?: string | null;
    is_active?: boolean;
    created_at?: string;
    country_code?: string | null;
    mailbox_connected?: boolean;
    subscription_status?: string | null;
    plan_code?: string | null;
    first_product_use_at?: string | null;
  }>;
  total: number;
};

type BillingResponse = {
  stub?: boolean;
  note?: string;
  summary: {
    customers: number;
    subscriptions_active: number;
    subscriptions_trialing: number;
    events_recorded: number;
    charges_cents: number;
    deposits_cents: number;
    app_expenses_cents: number;
    net_cash_cents_stub: number;
    currency_default: string;
  };
  geo_subscribed_stub: Array<{ country_code: string; users: number }>;
};

type FeedbackResponse = {
  feedback: Array<{
    id: string;
    kind: string;
    status: string;
    subject?: string;
    body: string;
    contact_email?: string | null;
    created_at?: string;
  }>;
  total: number;
};

type PromotionsResponse = {
  promotions: Array<{
    id: string;
    code: string;
    title?: string;
    discount_type: string;
    discount_value: number;
    is_active: boolean;
    redemption_count?: number;
    max_redemptions?: number | null;
    created_at?: string;
  }>;
  total: number;
};

type HealthResponse = {
  status: string;
  version?: string;
  deploy_marker?: string;
  database?: { ok?: boolean; detail?: string };
  process?: {
    process_uptime_seconds?: number;
    process_memory_rss_mb?: number | null;
    process_cpu_percent?: number | null;
    source?: string;
    host?: string;
    external_apm?: {
      sentry?: boolean;
      datadog?: boolean;
      note?: string;
    };
  };
  admin_configured?: boolean;
  admin_allowlist_count?: number;
};

const TABS: Array<{ id: AdminTab; label: string; icon: typeof Activity }> = [
  { id: "overview", label: "Resumen", icon: Activity },
  { id: "users", label: "Usuarios", icon: Users },
  { id: "billing", label: "Cobros", icon: CreditCard },
  { id: "feedback", label: "Quejas y ideas", icon: MessageSquareWarning },
  { id: "promotions", label: "Promociones", icon: Tag },
  { id: "system", label: "Sistema", icon: Server },
];

function moneyMx(cents: number): string {
  return new Intl.NumberFormat("es-MX", {
    style: "currency",
    currency: "MXN",
  }).format((cents || 0) / 100);
}

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

export default function AdminPage() {
  const [theme, setTheme] = useState<"midnight" | "aurora" | "accessible" | "graphite">(
    "accessible",
  );
  const {
    session,
    loading: authLoading,
    needsEmailConfirm,
    signIn,
    signInWithGoogle,
    signInWithProvider,
    signUp,
    resendSignupEmail,
    sendDonextoVerifyEmail,
    signInWithMagicLink,
    signOut,
    resetPassword,
    refreshSession,
  } = useAppAuth();
  const [tab, setTab] = useState<AdminTab>("overview");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [forbidden, setForbidden] = useState(false);

  const [overview, setOverview] = useState<OverviewResponse | null>(null);
  const [users, setUsers] = useState<UsersResponse | null>(null);
  const [billing, setBilling] = useState<BillingResponse | null>(null);
  const [feedback, setFeedback] = useState<FeedbackResponse | null>(null);
  const [promotions, setPromotions] = useState<PromotionsResponse | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);

  const [feedbackForm, setFeedbackForm] = useState({
    kind: "suggestion",
    subject: "",
    body: "",
  });
  const [promoForm, setPromoForm] = useState({
    code: "",
    title: "",
    discount_type: "percent",
    discount_value: 10,
  });
  const [saving, setSaving] = useState(false);

  const sessionEmail = session?.email ?? "";

  const loadTab = useCallback(
    async (target: AdminTab) => {
      if (!session) return;
      setLoading(true);
      setError(null);
      setForbidden(false);

      try {
        if (target === "overview") {
          const data = await hmsJson<OverviewResponse>(
            "/api/hms/admin/overview",
            { cache: "no-store" },
          );
          setOverview(data);
        } else if (target === "users") {
          const data = await hmsJson<UsersResponse>(
            "/api/hms/admin/users?limit=80",
            { cache: "no-store" },
          );
          setUsers(data);
        } else if (target === "billing") {
          const data = await hmsJson<BillingResponse>(
            "/api/hms/admin/billing/summary",
            { cache: "no-store" },
          );
          setBilling(data);
        } else if (target === "feedback") {
          const data = await hmsJson<FeedbackResponse>(
            "/api/hms/admin/feedback?limit=80",
            { cache: "no-store" },
          );
          setFeedback(data);
        } else if (target === "promotions") {
          const data = await hmsJson<PromotionsResponse>(
            "/api/hms/admin/promotions?limit=80",
            { cache: "no-store" },
          );
          setPromotions(data);
        } else if (target === "system") {
          const data = await hmsJson<HealthResponse>(
            "/api/hms/admin/health-extended",
            { cache: "no-store" },
          );
          setHealth(data);
        }
      } catch (err) {
        if (err instanceof HmsApiError) {
          if (err.status === 403 || err.status === 503) {
            setForbidden(true);
          }
          setError(err.message);
        } else {
          setError(
            err instanceof Error
              ? err.message
              : "No fue posible cargar el panel de administración.",
          );
        }
      } finally {
        setLoading(false);
      }
    },
    [session],
  );

  useEffect(() => {
    if (authLoading) return;
    if (!session) return;
    void loadTab(tab);
  }, [authLoading, session, tab, loadTab]);

  const headerMeta = useMemo(() => {
    if (!sessionEmail) return "Sin sesión";
    return sessionEmail;
  }, [sessionEmail]);

  async function onCreateFeedback(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await hmsJson("/api/hms/admin/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(feedbackForm),
      });
      setFeedbackForm({ kind: "suggestion", subject: "", body: "" });
      await loadTab("feedback");
    } catch (err) {
      setError(
        err instanceof HmsApiError
          ? err.message
          : "No se pudo registrar el feedback.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function onCreatePromo(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await hmsJson("/api/hms/admin/promotions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(promoForm),
      });
      setPromoForm({
        code: "",
        title: "",
        discount_type: "percent",
        discount_value: 10,
      });
      await loadTab("promotions");
    } catch (err) {
      setError(
        err instanceof HmsApiError
          ? err.message
          : "No se pudo crear la promoción.",
      );
    } finally {
      setSaving(false);
    }
  }

  if (authLoading) {
    return (
      <div className="dx-admin dx-admin--center">
        <Loader2 className="dx-admin__spin" size={28} />
        <p>Cargando sesión Donexto…</p>
      </div>
    );
  }

  if (!session) {
    return (
      <div className="dx-admin-login">
        <LoginScreen
          theme={theme}
          setTheme={setTheme}
          onSignIn={signIn}
          onSignUp={signUp}
          onSignInWithGoogle={signInWithGoogle}
          onSignInWithProvider={signInWithProvider}
          onResendSignupEmail={resendSignupEmail}
          onMagicLink={signInWithMagicLink}
          onResetPassword={resetPassword}
        />
      </div>
    );
  }

  if (needsEmailConfirm) {
    return (
      <ConfirmEmailGate
        email={session.email}
        onResend={sendDonextoVerifyEmail}
        onRefresh={refreshSession}
        onSignOut={signOut}
      />
    );
  }

  return (
    <div className="dx-admin">
      <header className="dx-admin__header">
        <div className="dx-admin__brand">
          <Shield size={22} aria-hidden />
          <div>
            <p className="dx-admin__eyebrow">Donexto · Operaciones</p>
            <h1>Panel de administración</h1>
          </div>
        </div>
        <div className="dx-admin__header-actions">
          <span className="dx-admin__session" title={headerMeta}>
            {headerMeta}
          </span>
          <button
            type="button"
            className="dx-admin__btn dx-admin__btn--ghost"
            onClick={() => void loadTab(tab)}
            disabled={loading}
          >
            <RefreshCw size={16} />
            Actualizar
          </button>
          <Link href="/" className="dx-admin__btn dx-admin__btn--ghost">
            <ArrowLeft size={16} />
            App
          </Link>
          <button
            type="button"
            className="dx-admin__btn"
            onClick={() => void signOut()}
          >
            Cerrar sesión
          </button>
        </div>
      </header>

      <nav className="dx-admin__nav" aria-label="Secciones de administración">
        {TABS.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              type="button"
              className={
                tab === item.id
                  ? "dx-admin__tab is-active"
                  : "dx-admin__tab"
              }
              onClick={() => setTab(item.id)}
            >
              <Icon size={16} />
              {item.label}
            </button>
          );
        })}
      </nav>

      <main className="dx-admin__main">
        {error && (
          <div
            className={
              forbidden
                ? "dx-admin__alert is-warn"
                : "dx-admin__alert is-error"
            }
            role="alert"
          >
            {error}
            {forbidden && (
              <p className="dx-admin__hint">
                Tu correo debe estar en <code>ADMIN_EMAILS</code> del backend
                (p. ej. <code>hmcelinfo@gmail.com</code>).
              </p>
            )}
          </div>
        )}

        {loading && !forbidden && (
          <div className="dx-admin__loading">
            <Loader2 className="dx-admin__spin" size={20} />
            Cargando…
          </div>
        )}

        {!forbidden && tab === "overview" && overview && (
          <section className="dx-admin__section">
            <header className="dx-admin__section-head">
              <h2>Resumen operativo</h2>
              <p>
                Salud del producto, pruebas free 24&nbsp;h, cobros y quejas.
                Cuenta Donexto ≠ buzón conectado.
              </p>
            </header>
            <div className="dx-admin__kpis">
              <article>
                <span>Usuarios</span>
                <strong>{overview.counts.users}</strong>
              </article>
              <article>
                <span>Pruebas activas</span>
                <strong>{overview.counts.trials_active}</strong>
              </article>
              <article>
                <span>Pagos activos</span>
                <strong>{overview.counts.active_paid}</strong>
              </article>
              <article>
                <span>Buzones conectados</span>
                <strong>{overview.counts.mailbox_connected}</strong>
              </article>
              <article>
                <span>Feedback abierto</span>
                <strong>{overview.counts.feedback_open}</strong>
              </article>
              <article>
                <span>Sin uso en 24&nbsp;h</span>
                <strong>
                  {overview.counts.signed_up_no_product_use_24h}
                </strong>
              </article>
            </div>
            {overview.schema?.migrations_hint && (
              <p className="dx-admin__hint">
                Esquema: {overview.schema.migrations_hint}
              </p>
            )}
            {overview.notes?.account_vs_mailbox && (
              <p className="dx-admin__note">
                {overview.notes.account_vs_mailbox}
              </p>
            )}
          </section>
        )}

        {!forbidden && tab === "users" && users && (
          <section className="dx-admin__section">
            <header className="dx-admin__section-head">
              <h2>Usuarios recientes</h2>
              <p>
                Perfiles Donexto, estado de buzón y suscripción (si hay filas
                de billing).
              </p>
            </header>
            <div className="dx-admin__table-wrap">
              <table className="dx-admin__table">
                <thead>
                  <tr>
                    <th>Correo</th>
                    <th>Nombre</th>
                    <th>Buzón</th>
                    <th>Plan / estado</th>
                    <th>País</th>
                    <th>Alta</th>
                  </tr>
                </thead>
                <tbody>
                  {users.users.length === 0 && (
                    <tr>
                      <td colSpan={6}>Sin usuarios en profiles aún.</td>
                    </tr>
                  )}
                  {users.users.map((user) => (
                    <tr key={user.id}>
                      <td>{user.email || "—"}</td>
                      <td>{user.full_name || "—"}</td>
                      <td>
                        {user.mailbox_connected ? (
                          <span className="dx-admin__pill is-ok">Conectado</span>
                        ) : (
                          <span className="dx-admin__pill">Sin buzón</span>
                        )}
                      </td>
                      <td>
                        {user.plan_code || "—"}{" "}
                        {user.subscription_status
                          ? `(${user.subscription_status})`
                          : ""}
                      </td>
                      <td>{user.country_code || "—"}</td>
                      <td>{formatWhen(user.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {!forbidden && tab === "billing" && billing && (
          <section className="dx-admin__section">
            <header className="dx-admin__section-head">
              <h2>Cobros y gastos</h2>
              <p>
                Stub provider-agnostic (Stripe/PayPal después). No hay Checkout
                real todavía.
              </p>
            </header>
            {billing.stub && (
              <p className="dx-admin__note">{billing.note}</p>
            )}
            <div className="dx-admin__kpis">
              <article>
                <span>Clientes</span>
                <strong>{billing.summary.customers}</strong>
              </article>
              <article>
                <span>Activos pagados</span>
                <strong>{billing.summary.subscriptions_active}</strong>
              </article>
              <article>
                <span>En prueba</span>
                <strong>{billing.summary.subscriptions_trialing}</strong>
              </article>
              <article>
                <span>Cargos</span>
                <strong>{moneyMx(billing.summary.charges_cents)}</strong>
              </article>
              <article>
                <span>Depósitos</span>
                <strong>{moneyMx(billing.summary.deposits_cents)}</strong>
              </article>
              <article>
                <span>Gastos app</span>
                <strong>{moneyMx(billing.summary.app_expenses_cents)}</strong>
              </article>
            </div>
            <h3 className="dx-admin__subhead">Geo (stub de suscriptores)</h3>
            <ul className="dx-admin__list">
              {billing.geo_subscribed_stub.length === 0 && (
                <li>Sin country_code en clientes/perfiles todavía.</li>
              )}
              {billing.geo_subscribed_stub.map((row) => (
                <li key={row.country_code}>
                  <strong>{row.country_code}</strong> — {row.users} usuario(s)
                </li>
              ))}
            </ul>
          </section>
        )}

        {!forbidden && tab === "feedback" && (
          <section className="dx-admin__section">
            <header className="dx-admin__section-head">
              <h2>Quejas y sugerencias</h2>
              <p>
                Registro manual por ahora. El endpoint público de usuarios
                llegará después.
              </p>
            </header>
            <form className="dx-admin__form" onSubmit={onCreateFeedback}>
              <label>
                Tipo
                <select
                  value={feedbackForm.kind}
                  onChange={(e) =>
                    setFeedbackForm((prev) => ({
                      ...prev,
                      kind: e.target.value,
                    }))
                  }
                >
                  <option value="suggestion">Sugerencia</option>
                  <option value="complaint">Queja</option>
                  <option value="bug">Bug</option>
                  <option value="other">Otro</option>
                </select>
              </label>
              <label>
                Asunto
                <input
                  value={feedbackForm.subject}
                  onChange={(e) =>
                    setFeedbackForm((prev) => ({
                      ...prev,
                      subject: e.target.value,
                    }))
                  }
                  placeholder="Breve"
                />
              </label>
              <label className="dx-admin__full">
                Detalle
                <textarea
                  required
                  rows={3}
                  value={feedbackForm.body}
                  onChange={(e) =>
                    setFeedbackForm((prev) => ({
                      ...prev,
                      body: e.target.value,
                    }))
                  }
                  placeholder="Describe la queja o idea…"
                />
              </label>
              <button
                type="submit"
                className="dx-admin__btn"
                disabled={saving}
              >
                {saving ? "Guardando…" : "Registrar"}
              </button>
            </form>
            <div className="dx-admin__table-wrap">
              <table className="dx-admin__table">
                <thead>
                  <tr>
                    <th>Tipo</th>
                    <th>Estado</th>
                    <th>Asunto</th>
                    <th>Contacto</th>
                    <th>Fecha</th>
                  </tr>
                </thead>
                <tbody>
                  {(feedback?.feedback || []).length === 0 && (
                    <tr>
                      <td colSpan={5}>Sin feedback todavía.</td>
                    </tr>
                  )}
                  {(feedback?.feedback || []).map((row) => (
                    <tr key={row.id}>
                      <td>{row.kind}</td>
                      <td>{row.status}</td>
                      <td title={row.body}>
                        {row.subject || row.body.slice(0, 80)}
                      </td>
                      <td>{row.contact_email || "—"}</td>
                      <td>{formatWhen(row.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {!forbidden && tab === "promotions" && (
          <section className="dx-admin__section">
            <header className="dx-admin__section-head">
              <h2>Cupones y ofertas</h2>
              <p>
                Alta de códigos stub. Redención en Checkout llegará con Stripe.
              </p>
            </header>
            <form className="dx-admin__form" onSubmit={onCreatePromo}>
              <label>
                Código
                <input
                  required
                  minLength={3}
                  value={promoForm.code}
                  onChange={(e) =>
                    setPromoForm((prev) => ({
                      ...prev,
                      code: e.target.value.toUpperCase(),
                    }))
                  }
                  placeholder="BIENVENIDA10"
                />
              </label>
              <label>
                Título
                <input
                  value={promoForm.title}
                  onChange={(e) =>
                    setPromoForm((prev) => ({
                      ...prev,
                      title: e.target.value,
                    }))
                  }
                  placeholder="Descuento de lanzamiento"
                />
              </label>
              <label>
                Tipo
                <select
                  value={promoForm.discount_type}
                  onChange={(e) =>
                    setPromoForm((prev) => ({
                      ...prev,
                      discount_type: e.target.value,
                    }))
                  }
                >
                  <option value="percent">Porcentaje</option>
                  <option value="fixed_cents">Monto fijo (centavos)</option>
                  <option value="trial_extension_hours">
                    Extender prueba (horas)
                  </option>
                </select>
              </label>
              <label>
                Valor
                <input
                  type="number"
                  min={0}
                  value={promoForm.discount_value}
                  onChange={(e) =>
                    setPromoForm((prev) => ({
                      ...prev,
                      discount_value: Number(e.target.value) || 0,
                    }))
                  }
                />
              </label>
              <button
                type="submit"
                className="dx-admin__btn"
                disabled={saving}
              >
                {saving ? "Creando…" : "Crear cupón"}
              </button>
            </form>
            <div className="dx-admin__table-wrap">
              <table className="dx-admin__table">
                <thead>
                  <tr>
                    <th>Código</th>
                    <th>Título</th>
                    <th>Descuento</th>
                    <th>Activo</th>
                    <th>Usos</th>
                  </tr>
                </thead>
                <tbody>
                  {(promotions?.promotions || []).length === 0 && (
                    <tr>
                      <td colSpan={5}>Sin promociones.</td>
                    </tr>
                  )}
                  {(promotions?.promotions || []).map((row) => (
                    <tr key={row.id}>
                      <td>
                        <code>{row.code}</code>
                      </td>
                      <td>{row.title || "—"}</td>
                      <td>
                        {row.discount_type}: {row.discount_value}
                      </td>
                      <td>{row.is_active ? "Sí" : "No"}</td>
                      <td>
                        {row.redemption_count ?? 0}
                        {row.max_redemptions != null
                          ? ` / ${row.max_redemptions}`
                          : ""}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {!forbidden && tab === "system" && health && (
          <section className="dx-admin__section">
            <header className="dx-admin__section-head">
              <h2>Salud del sistema</h2>
              <p>
                Métricas del proceso backend (no CPU del host Railway). APM
                externo es opcional.
              </p>
            </header>
            <div className="dx-admin__kpis">
              <article>
                <span>Estado</span>
                <strong>{health.status}</strong>
              </article>
              <article>
                <span>Versión</span>
                <strong>{health.version || "—"}</strong>
              </article>
              <article>
                <span>Uptime (s)</span>
                <strong>
                  {health.process?.process_uptime_seconds ?? "—"}
                </strong>
              </article>
              <article>
                <span>Memoria RSS (MB)</span>
                <strong>
                  {health.process?.process_memory_rss_mb ?? "—"}
                </strong>
              </article>
              <article>
                <span>CPU proceso %</span>
                <strong>
                  {health.process?.process_cpu_percent ?? "—"}
                </strong>
              </article>
              <article>
                <span>Origen métrica</span>
                <strong>{health.process?.source || "—"}</strong>
              </article>
            </div>
            <ul className="dx-admin__list">
              <li>
                Marker: <code>{health.deploy_marker || "—"}</code>
              </li>
              <li>
                Base de datos:{" "}
                {health.database?.ok ? "conectada" : "con problemas"}{" "}
                {health.database?.detail
                  ? `(${health.database.detail})`
                  : ""}
              </li>
              <li>
                ADMIN_EMAILS:{" "}
                {health.admin_configured
                  ? `${health.admin_allowlist_count} correo(s)`
                  : "no configurado"}
              </li>
              <li>
                Host: {health.process?.host || "—"}
              </li>
              <li>
                Sentry:{" "}
                {health.process?.external_apm?.sentry
                  ? "DSN detectado"
                  : "no configurado"}{" "}
                · Datadog:{" "}
                {health.process?.external_apm?.datadog
                  ? "clave detectada"
                  : "no configurado"}
              </li>
            </ul>
            {health.process?.external_apm?.note && (
              <p className="dx-admin__hint">
                {health.process.external_apm.note}
              </p>
            )}
          </section>
        )}
      </main>
    </div>
  );
}
