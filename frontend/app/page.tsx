"use client";

import {
  Activity,
  AlertTriangle,
  BarChart3,
  Bell,
  BriefcaseBusiness,
  CheckCircle2,
  ChevronRight,
  Clock3,
  Eye,
  EyeOff,
  FileBarChart,
  Home,
  Inbox,
  KeyRound,
  LogOut,
  Mail,
  Menu,
  Plus,
  RefreshCw,
  Search,
  Settings,
  ShieldCheck,
  Sparkles,
  Users,
  X,
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { useCases } from "@/hooks/useCases";
import { useGoogleStatus } from "@/hooks/useGoogleStatus";
import { useAppAuth } from "@/hooks/useAppAuth";
import type {
  CaseEvent,
  CasePriority,
  IntelligentCase,
} from "@/types/cases";

type ThemeId =
  | "midnight"
  | "aurora"
  | "accessible"
  | "graphite";

type AppSession = {
  id: string;
  email: string;
  name: string;
};

const THEMES: Array<{
  id: ThemeId;
  label: string;
}> = [
  { id: "midnight", label: "Midnight Social" },
  { id: "aurora", label: "Aurora Collaboration" },
  { id: "accessible", label: "Focus Accessible" },
  { id: "graphite", label: "Soft Graphite" },
];

const NAV_ITEMS = [
  { id: "home", label: "Inicio", icon: Home },
  { id: "cases", label: "Casos", icon: BriefcaseBusiness },
  { id: "tasks", label: "Tareas", icon: CheckCircle2 },
  { id: "people", label: "Responsables", icon: Users },
  { id: "activity", label: "Actividad", icon: Activity },
  { id: "reports", label: "Reportes", icon: FileBarChart },
  { id: "metrics", label: "Métricas", icon: BarChart3 },
  { id: "settings", label: "Ajustes", icon: Settings },
];

function priorityLabel(priority: CasePriority): string {
  const labels: Record<CasePriority, string> = {
    critical: "Crítico",
    high: "Alto",
    normal: "Medio",
    low: "Bajo",
  };

  return labels[priority];
}

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    new: "Nuevo",
    analyzing: "Analizando",
    in_progress: "En proceso",
    delegated: "Delegado",
    waiting_internal: "Espera interna",
    waiting_external: "Espera externa",
    resolved: "Resuelto",
    closed: "Cerrado",
    archived: "Archivado",
  };

  return labels[status] ?? status;
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("es-MX", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function displayName(email: string): string {
  const local = email.split("@")[0];

  return local
    .split(/[._-]/)
    .filter(Boolean)
    .map((part) =>
      part.charAt(0).toUpperCase() + part.slice(1)
    )
    .join(" ");
}

function initials(value?: string | null): string {
  if (!value) {
    return "HS";
  }

  const name = value.includes("@")
    ? displayName(value)
    : value;

  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join("")
    .slice(0, 2);
}

function LoginScreen({
  theme,
  setTheme,
  onSignIn,
  onSignUp,
  onResetPassword,
}: {
  theme: ThemeId;
  setTheme: (theme: ThemeId) => void;
  onSignIn: (email: string, password: string) => Promise<void>;
  onSignUp: (
    email: string,
    password: string,
    fullName: string,
  ) => Promise<{ requiresConfirmation: boolean }>;
  onResetPassword: (email: string) => Promise<void>;
}) {
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);

    const cleanEmail = email.trim().toLowerCase();

    if (!cleanEmail || !cleanEmail.includes("@")) {
      setError("Escribe un correo electrónico válido.");
      return;
    }

    if (password.length < 8) {
      setError("La contraseña debe tener al menos 8 caracteres.");
      return;
    }

    if (mode === "signup" && fullName.trim().length < 2) {
      setError("Escribe tu nombre completo.");
      return;
    }

    setBusy(true);

    try {
      if (mode === "signin") {
        await onSignIn(cleanEmail, password);
      } else {
        const result = await onSignUp(
          cleanEmail,
          password,
          fullName.trim(),
        );

        if (result.requiresConfirmation) {
          setMessage(
            "Cuenta creada. Revisa tu correo para confirmar el acceso.",
          );
          setMode("signin");
          setPassword("");
        }
      }
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "No fue posible completar el acceso.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function resetPassword() {
    const cleanEmail = email.trim().toLowerCase();

    if (!cleanEmail || !cleanEmail.includes("@")) {
      setError("Escribe primero el correo de la cuenta.");
      return;
    }

    setBusy(true);
    setError(null);
    setMessage(null);

    try {
      await onResetPassword(cleanEmail);
      setMessage(
        "Te enviamos un enlace para restablecer tu contraseña.",
      );
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "No fue posible enviar el enlace.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-screen" data-theme={theme}>
      <div className="auth-backdrop" />

      <section className="auth-presentation">
        <div className="auth-product">
          <span className="auth-logo">
            <Sparkles size={29} />
          </span>
          <div>
            <strong>HMS AI Assistant</strong>
            <small>Centro de Control Inteligente</small>
          </div>
        </div>

        <div className="auth-presentation-copy">
          <span>ACCESO PARA CUALQUIER CORREO</span>
          <h1>
            Tu cuenta HMS,
            <strong> separada de tu buzón.</strong>
          </h1>
          <p>
            Regístrate con Gmail, Outlook, Hotmail, Yahoo o cualquier
            correo empresarial. Después podrás conectar los buzones que
            quieras supervisar.
          </p>
        </div>

        <div className="auth-benefits">
          <article><ShieldCheck size={20} /><div><strong>Autenticación real</strong><span>Sesión segura administrada por Supabase Auth.</span></div></article>
          <article><Mail size={20} /><div><strong>Cualquier proveedor</strong><span>El correo de acceso no tiene que ser Gmail.</span></div></article>
          <article><Users size={20} /><div><strong>Cuenta personal</strong><span>Perfil propio y separación futura por workspace.</span></div></article>
        </div>
      </section>

      <section className="auth-panel">
        <div className="auth-panel-top">
          <div className="auth-panel-brand">
            <span className="auth-logo"><Sparkles size={25} /></span>
            <div><strong>HMS AI Assistant</strong><small>Centro de Operaciones</small></div>
          </div>

          <label className="auth-theme">
            <span>Tema</span>
            <select value={theme} onChange={(event) => setTheme(event.target.value as ThemeId)}>
              {THEMES.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
            </select>
          </label>
        </div>

        <div className="auth-card">
          <div className="auth-card-heading">
            <span>{mode === "signin" ? "INICIAR SESIÓN" : "CREAR CUENTA"}</span>
            <h2>{mode === "signin" ? "Bienvenido de nuevo 👋" : "Comienza con HMS AI"}</h2>
            <p>{mode === "signin" ? "Accede con tu correo y contraseña." : "Aceptamos correos de cualquier proveedor."}</p>
          </div>

          <div className="auth-mode-tabs" role="tablist">
            <button type="button" className={mode === "signin" ? "is-active" : ""} onClick={() => { setMode("signin"); setError(null); setMessage(null); }}>Iniciar sesión</button>
            <button type="button" className={mode === "signup" ? "is-active" : ""} onClick={() => { setMode("signup"); setError(null); setMessage(null); }}>Crear cuenta</button>
          </div>

          <form onSubmit={submit}>
            {mode === "signup" ? (
              <label className="auth-field">
                <span>Nombre completo</span>
                <div><Users size={18} /><input type="text" value={fullName} autoComplete="name" placeholder="Nombre y apellidos" onChange={(event) => setFullName(event.target.value)} /></div>
              </label>
            ) : null}

            <label className="auth-field">
              <span>Correo electrónico</span>
              <div><Mail size={18} /><input type="email" value={email} autoComplete="email" placeholder="usuario@empresa.com" onChange={(event) => setEmail(event.target.value)} /></div>
            </label>

            <label className="auth-field">
              <span>Contraseña</span>
              <div><KeyRound size={18} /><input type={showPassword ? "text" : "password"} value={password} autoComplete={mode === "signin" ? "current-password" : "new-password"} placeholder="Mínimo 8 caracteres" onChange={(event) => setPassword(event.target.value)} /><button type="button" aria-label={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"} onClick={() => setShowPassword((current) => !current)}>{showPassword ? <EyeOff size={18} /> : <Eye size={18} />}</button></div>
            </label>

            {mode === "signin" ? (
              <div className="auth-options"><span /><button type="button" onClick={() => { void resetPassword(); }}>¿Olvidaste tu contraseña?</button></div>
            ) : null}

            {error ? <div className="auth-error"><AlertTriangle size={17} />{error}</div> : null}
            {message ? <div className="auth-success"><CheckCircle2 size={17} />{message}</div> : null}

            <button type="submit" className="auth-submit" disabled={busy}>
              {busy ? "Procesando..." : mode === "signin" ? "Iniciar sesión" : "Crear cuenta"}
            </button>
          </form>

          <div className="auth-security">
            <ShieldCheck size={18} />
            <div><strong>Autenticación real con Supabase</strong><span>El correo de acceso y la conexión de Gmail son procesos distintos.</span></div>
          </div>
        </div>
      </section>
    </main>
  );
}

function CaseRow({
  item,
}: {
  item: IntelligentCase;
}) {
  return (
    <article className="app-case-row">
      <div
        className={`app-priority app-priority-${item.priority}`}
      >
        {item.risk_score}
      </div>

      <div className="app-case-copy">
        <div className="app-case-heading">
          <span
            className={`app-priority-label app-priority-label-${item.priority}`}
          >
            {priorityLabel(item.priority)}
          </span>
          <h3>{item.title}</h3>
        </div>

        <p>
          {item.summary ??
            item.requested_action ??
            "Caso pendiente de análisis detallado."}
        </p>

        <div className="app-case-meta">
          <span>
            {item.requester_name ??
              item.requester_email ??
              "Origen no identificado"}
          </span>
          <span>{item.source_count} evidencias</span>
          <time>{formatDate(item.last_activity_at)}</time>
        </div>
      </div>

      <span
        className={`app-case-status app-case-status-${item.status}`}
      >
        {statusLabel(item.status)}
      </span>

      <button
        type="button"
        className="app-row-arrow"
        aria-label={`Abrir ${item.title}`}
      >
        <ChevronRight size={20} />
      </button>
    </article>
  );
}

function EventRow({
  item,
}: {
  item: CaseEvent;
}) {
  return (
    <article className="app-event-row">
      <span
        className={`app-event-icon app-event-level-${item.level}`}
      >
        <Activity size={17} />
      </span>

      <div>
        <strong>{item.title}</strong>
        <p>
          {item.description ??
            "Evento operativo registrado por HMS AI."}
        </p>
        <time>{formatDate(item.created_at)}</time>
      </div>

      <ChevronRight size={18} />
    </article>
  );
}

function Dashboard({
  theme,
  setTheme,
  session,
  onLogout,
}: {
  theme: ThemeId;
  setTheme: (theme: ThemeId) => void;
  session: AppSession;
  onLogout: () => void;
}) {
  const {
    dashboard,
    cases,
    search,
    loading,
    syncing,
    syncProgress,
    error,
    setSearch,
    loadDashboard,
    syncAllMessages,
  } = useCases();

  const {
    connection,
    loadingConnection,
    connectionError,
    loadGoogleStatus,
  } = useGoogleStatus();

  const [mobileOpen, setMobileOpen] = useState(false);

  const busy =
    loading || syncing || loadingConnection;

  const metrics = useMemo(
    () => [
      {
        label: "Casos abiertos",
        value: dashboard.metrics.total_open,
        icon: Inbox,
        tone: "blue",
      },
      {
        label: "Críticos",
        value: dashboard.metrics.critical,
        icon: AlertTriangle,
        tone: "red",
      },
      {
        label: "Esperando respuesta",
        value:
          dashboard.metrics.waiting_internal +
          dashboard.metrics.waiting_external,
        icon: Clock3,
        tone: "violet",
      },
      {
        label: "Vencidos",
        value: dashboard.metrics.overdue,
        icon: Bell,
        tone: "green",
      },
      {
        label: "Resueltos hoy",
        value: dashboard.metrics.resolved_today,
        icon: CheckCircle2,
        tone: "cyan",
      },
    ],
    [dashboard.metrics],
  );

  const visibleCases = cases.slice(0, 7);
  const visibleEvents =
    dashboard.recent_events.slice(0, 6);

  return (
    <div className="app-shell" data-theme={theme}>
      <button
        type="button"
        className={
          mobileOpen
            ? "app-mobile-overlay is-visible"
            : "app-mobile-overlay"
        }
        onClick={() => setMobileOpen(false)}
        aria-label="Cerrar menú"
      />

      <aside
        className={
          mobileOpen
            ? "app-sidebar is-open"
            : "app-sidebar"
        }
      >
        <div className="app-brand">
          <span className="app-brand-icon">
            <Sparkles size={25} />
          </span>
          <div>
            <strong>HMS AI Assistant</strong>
            <small>Centro de Operaciones</small>
          </div>

          <button
            type="button"
            className="app-sidebar-close"
            onClick={() => setMobileOpen(false)}
            aria-label="Cerrar menú"
          >
            <X size={21} />
          </button>
        </div>

        <nav className="app-navigation">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;

            return (
              <button
                key={item.id}
                type="button"
                className={
                  item.id === "home"
                    ? "app-nav-item is-active"
                    : "app-nav-item"
                }
              >
                <Icon size={19} />
                <span>{item.label}</span>
                {item.id === "cases" ? (
                  <b>{dashboard.metrics.total_open}</b>
                ) : null}
              </button>
            );
          })}
        </nav>

        <div className="app-sidebar-bottom">
          <div className="app-sync-state">
            <RefreshCw
              size={20}
              className={syncing ? "app-spin" : undefined}
            />
            <div>
              <strong>
                {syncing
                  ? `Lote ${syncProgress.currentBatch}`
                  : "Sincronizado"}
              </strong>
              <small>
                {syncProgress.completed
                  ? `${syncProgress.found} revisados`
                  : "Sistema disponible"}
              </small>
            </div>
            <span />
          </div>

          <button
            type="button"
            className="app-sidebar-primary"
            disabled={
              syncing ||
              !connection?.connected
            }
            onClick={() => {
              void syncAllMessages();
            }}
          >
            <RefreshCw
              size={19}
              className={syncing ? "app-spin" : undefined}
            />
            {syncing
              ? `Procesando lote ${syncProgress.currentBatch}`
              : "Sincronizar y analizar"}
          </button>

          <button
            type="button"
            className="app-sidebar-secondary"
            disabled={busy}
            onClick={() => {
              void Promise.all([
                loadDashboard(),
                loadGoogleStatus(),
              ]);
            }}
          >
            <RefreshCw size={18} />
            Actualizar panel
          </button>

          <button
            type="button"
            className="app-logout"
            onClick={onLogout}
          >
            <LogOut size={18} />
            Cerrar sesión
          </button>
        </div>
      </aside>

      <main className="app-main">
        <header className="app-topbar">
          <div className="app-topbar-first">
            <button
              type="button"
              className="app-mobile-menu"
              onClick={() => setMobileOpen(true)}
              aria-label="Abrir menú"
            >
              <Menu size={22} />
            </button>

            <label className="app-search">
              <Search size={19} />
              <input
                type="search"
                value={search}
                placeholder="Buscar casos, personas, asuntos o remitentes..."
                onChange={(event) =>
                  setSearch(event.target.value)
                }
              />
              <kbd>⌘ K</kbd>
            </label>

            <div className="app-top-actions">
              <div
                className={
                  connection?.connected
                    ? "app-connected is-online"
                    : "app-connected is-offline"
                }
              >
                <span />
                {connection?.connected
                  ? "Gmail conectado"
                  : "Sin conexión"}
              </div>

              <div className="app-ai-pill">
                <Sparkles size={16} />
                IA activa
              </div>

              <label className="app-theme-select">
                <span>Tema</span>
                <select
                  value={theme}
                  onChange={(event) =>
                    setTheme(
                      event.target.value as ThemeId,
                    )
                  }
                >
                  {THEMES.map((item) => (
                    <option
                      key={item.id}
                      value={item.id}
                    >
                      {item.label}
                    </option>
                  ))}
                </select>
              </label>

              <button
                type="button"
                className="app-icon-button"
                aria-label="Notificaciones"
              >
                <Bell size={19} />
              </button>

              <div className="app-user">
                <span>{initials(session.name)}</span>
                <div>
                  <strong>{session.name}</strong>
                  <small>Administrador</small>
                </div>
              </div>
            </div>
          </div>

          <div className="app-mobile-status">
            <div
              className={
                connection?.connected
                  ? "app-connected is-online"
                  : "app-connected is-offline"
              }
            >
              <span />
              {connection?.connected
                ? "Gmail conectado"
                : "Sin conexión"}
            </div>

            <div className="app-ai-pill">
              <Sparkles size={16} />
              IA activa
            </div>
          </div>
        </header>

        <div className="app-content">
          <section className="app-welcome">
            <div>
              <h1>
                Buenos días, {session.name.split(" ")[0]} 👋
              </h1>
              <p>
                Centro Inteligente de Operaciones de Comunicación
              </p>
            </div>

            <button type="button">
              <Settings size={17} />
              Personalizar vista
            </button>
          </section>

          {(connectionError || error) ? (
            <section className="app-alert">
              <AlertTriangle size={19} />
              <div>
                <strong>
                  No fue posible completar la operación.
                </strong>
                <span>
                  {connectionError ?? error}
                </span>
              </div>
            </section>
          ) : null}

          {(syncing || syncProgress.completed) ? (
            <section className="app-progress">
              <div>
                <span>
                  {syncing
                    ? `LOTE ${syncProgress.currentBatch} EN CURSO`
                    : "SINCRONIZACIÓN COMPLETA"}
                </span>
                <strong>
                  {syncProgress.found} mensajes revisados
                </strong>
              </div>

              <div className="app-progress-track">
                <span
                  className={
                    syncing ? "is-running" : ""
                  }
                />
              </div>

              <b>
                {syncProgress.pagesCompleted} lotes
              </b>
            </section>
          ) : null}

          <section className="app-metrics">
            {metrics.map((metric) => {
              const Icon = metric.icon;

              return (
                <article
                  key={metric.label}
                  className={`app-metric app-metric-${metric.tone}`}
                >
                  <div>
                    <span>{metric.label}</span>
                    <strong>{metric.value}</strong>
                    <small>↑ Información actualizada</small>
                  </div>

                  <Icon size={29} />
                </article>
              );
            })}
          </section>

          <section className="app-team">
            <div className="app-section-heading">
              <div>
                <span>EQUIPO Y RESPONSABLES</span>
                <h2>Personas conectadas</h2>
              </div>

              <button type="button">Administrar</button>
            </div>

            <div className="app-team-list">
              {[
                ["Tú", session.name, "Administrador"],
                ["CR", "Carlos Ruiz", "Coordinador"],
                ["AT", "Ana Torres", "Analista"],
                ["ML", "Miguel López", "Agente"],
                ["LF", "Lucía Fernández", "Agente"],
                ["HS", "Héctor Salcido", "Especialista"],
              ].map(([avatar, name, role], index) => (
                <article key={`${name}-${index}`}>
                  <span>{avatar}</span>
                  <strong>{name}</strong>
                  <small>{role}</small>
                </article>
              ))}

              <button type="button" className="app-add-person">
                <Plus size={24} />
                <span>Agregar</span>
              </button>
            </div>
          </section>

          <section className="app-dashboard-grid">
            <div className="app-panel">
              <div className="app-panel-heading">
                <div>
                  <span>PRIORIDAD OPERATIVA</span>
                  <h2>Casos importantes</h2>
                </div>

                <button type="button">Ver todos</button>
              </div>

              <div className="app-case-list">
                {loading ? (
                  <div className="app-empty">
                    <RefreshCw
                      size={23}
                      className="app-spin"
                    />
                    Cargando casos...
                  </div>
                ) : visibleCases.length === 0 ? (
                  <div className="app-empty">
                    <CheckCircle2 size={26} />
                    No hay casos pendientes.
                  </div>
                ) : (
                  visibleCases.map((item) => (
                    <CaseRow
                      key={item.id}
                      item={item}
                    />
                  ))
                )}
              </div>
            </div>

            <div className="app-panel">
              <div className="app-panel-heading">
                <div>
                  <span>ACTIVIDAD RECIENTE</span>
                  <h2>Últimos eventos</h2>
                </div>

                <button type="button">Ver toda</button>
              </div>

              <div className="app-event-list">
                {visibleEvents.length === 0 ? (
                  <div className="app-empty">
                    <Activity size={26} />
                    Aún no hay eventos.
                  </div>
                ) : (
                  visibleEvents.map((item) => (
                    <EventRow
                      key={item.id}
                      item={item}
                    />
                  ))
                )}
              </div>
            </div>
          </section>

          <section className="app-quick-actions">
            <button
              type="button"
              disabled={
                syncing ||
                !connection?.connected
              }
              onClick={() => {
                void syncAllMessages();
              }}
            >
              <RefreshCw
                size={22}
                className={syncing ? "app-spin" : undefined}
              />
              <div>
                <strong>Sincronizar</strong>
                <span>Actualizar Gmail</span>
              </div>
            </button>

            <button
              type="button"
              onClick={() => {
                void loadDashboard();
              }}
            >
              <RefreshCw size={22} />
              <div>
                <strong>Actualizar panel</strong>
                <span>Datos en tiempo real</span>
              </div>
            </button>

            <button type="button">
              <Plus size={25} />
              <div>
                <strong>Nuevo caso</strong>
                <span>Crear solicitud</span>
              </div>
            </button>

            <button type="button">
              <Users size={22} />
              <div>
                <strong>Asignar</strong>
                <span>Delegar tarea</span>
              </div>
            </button>

            <button type="button">
              <FileBarChart size={22} />
              <div>
                <strong>Generar reporte</strong>
                <span>Exportar datos</span>
              </div>
            </button>
          </section>
        </div>

        <nav className="app-mobile-nav">
          <button type="button" className="is-active">
            <Home size={21} />
            <span>Inicio</span>
          </button>

          <button type="button">
            <BriefcaseBusiness size={21} />
            <span>Casos</span>
          </button>

          <button type="button" className="app-mobile-plus">
            <Plus size={27} />
          </button>

          <button type="button">
            <Activity size={21} />
            <span>Actividad</span>
          </button>

          <button type="button">
            <Menu size={21} />
            <span>Más</span>
          </button>
        </nav>
      </main>
    </div>
  );
}

export default function HomePage() {
  const [theme, setTheme] = useState<ThemeId>("midnight");
  const { session, loading, signIn, signUp, signOut, resetPassword } =
    useAppAuth();

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const savedTheme = window.localStorage.getItem(
        "hms-approved-theme",
      ) as ThemeId | null;

      if (
        savedTheme &&
        THEMES.some((item) => item.id === savedTheme)
      ) {
        setTheme(savedTheme);
      }
    }, 0);

    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    window.localStorage.setItem("hms-approved-theme", theme);
  }, [theme]);

  if (loading) {
    return (
      <div className="app-loading-screen">
        <Sparkles size={34} />
        <span>Verificando sesión segura...</span>
      </div>
    );
  }

  if (!session) {
    return (
      <LoginScreen
        theme={theme}
        setTheme={setTheme}
        onSignIn={signIn}
        onSignUp={signUp}
        onResetPassword={resetPassword}
      />
    );
  }

  return (
    <Dashboard
      theme={theme}
      setTheme={setTheme}
      session={session}
      onLogout={() => {
        void signOut();
      }}
    />
  );
}
