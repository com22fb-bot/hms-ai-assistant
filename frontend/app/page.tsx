"use client";

import {
  Activity,
  AlertTriangle,
  BarChart3,
  Bell,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock3,
  Eye,
  EyeOff,
  FileBarChart,
  Home,
  Inbox,
  KeyRound,
  Languages,
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

import { GuidedImportWizard } from "@/components/GuidedImportWizard";
import { ConfirmEmailGate } from "@/components/auth/ConfirmEmailGate";
import { LoginScreen } from "@/components/auth/LoginScreen";
import { LiveMailPanel } from "@/components/LiveMailPanel";
import { MailboxConnectModal } from "@/components/MailboxConnectModal";
import "@/components/hms-mobile-shell.css";
import "@/components/guided-import.css";
import { AttentionHome } from "@/components/AttentionHome";
import "@/components/attention-home.css";
import { MailCategoriesPanel } from "@/components/MailCategoriesPanel";
import "@/components/mail-categories.css";
import { MailInbox } from "@/components/MailInbox";
import { PushNotificationsPanel } from "@/components/PushNotificationsPanel";
import { UserSettingsPanel } from "@/components/UserSettingsPanel";
import { LanguageProvider, useLanguage } from "@/lib/i18n/LanguageProvider";
import type { MessageKey } from "@/lib/i18n/messages";
import "@/components/mail-inbox.css";
import "@/components/push-notifications.css";
import "@/components/logistica-responsive.css";
import { useCases } from "@/hooks/useCases";
import { useGoogleStatus } from "@/hooks/useGoogleStatus";
import { useAppAuth } from "@/hooks/useAppAuth";
import { ACCOUNT_VS_MAILBOX, mailboxServiceLabel } from "@/lib/accountVsMailbox";
import { mailboxConnectModeFromEmail } from "@/lib/mailboxSignup";
import { hmsJson } from "@/lib/hmsApi";
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

type ImportFlowStatus = {
  needs_initial_import: boolean;
  initial_import_complete: boolean;
  phase: "initial_review" | "downloading" | "classifying" | "ready" | "failed";
  active: Record<string, unknown> | null;
};


type ControlState =
  | "active"
  | "testing"
  | "evaluation"
  | "blocked";

type ControlDefinition = {
  key: string;
  title: string;
  state: ControlState;
  summary: string;
  expectedResult: string;
  dependencies: string;
  activationOrder: string;
};

const CONTROL_STATE_LABELS: Record<ControlState, string> = {
  active: "Activo",
  testing: "En prueba",
  evaluation: "En evaluación",
  blocked: "Bloqueado",
};

const CONTROL_CATALOG: Record<string, ControlDefinition> = {
  cases: {
    key: "cases",
    title: "Módulo Casos",
    state: "evaluation",
    summary: "Vista completa para consultar, filtrar y administrar los casos accionables.",
    expectedResult: "Lista paginada, filtros reales, selección y acceso al detalle de cada caso.",
    dependencies: "Clasificador depurado, búsqueda global y aislamiento por usuario.",
    activationOrder: "1 · Primer módulo funcional después de la depuración.",
  },
  tasks: {
    key: "tasks",
    title: "Módulo Tareas",
    state: "evaluation",
    summary: "Concentrará solicitudes, compromisos, fechas límite y responsables.",
    expectedResult: "Crear, asignar, completar y auditar tareas derivadas de comunicaciones.",
    dependencies: "Modelo de tareas y relación segura con casos y usuarios.",
    activationOrder: "5 · Después de detalle, búsqueda y notificaciones.",
  },
  activity: {
    key: "activity",
    title: "Actividad",
    state: "evaluation",
    summary: "Historial operativo de cambios, sincronizaciones y acciones relevantes.",
    expectedResult: "Cronología filtrable con eventos reales y trazabilidad.",
    dependencies: "Catálogo definitivo de eventos y permisos por workspace.",
    activationOrder: "6 · Después de Tareas.",
  },
  reports: {
    key: "reports",
    title: "Reportes",
    state: "evaluation",
    summary: "Generación de reportes operativos y ejecutivos.",
    expectedResult: "Vista previa y exportación basada en datos validados.",
    dependencies: "Métricas confiables, filtros y permisos de exportación.",
    activationOrder: "7 · Después de Actividad.",
  },
  metrics: {
    key: "metrics",
    title: "Métricas",
    state: "evaluation",
    summary: "Análisis de pendientes, tiempos de respuesta y carga operativa.",
    expectedResult: "Indicadores exactos, series de tiempo y criterios transparentes.",
    dependencies: "Clasificación confiable e historial suficiente.",
    activationOrder: "8 · Después de Reportes.",
  },
  settings: {
    key: "settings",
    title: "Ajustes",
    state: "blocked",
    summary: "Preferencias, cuentas conectadas, seguridad y configuración del workspace.",
    expectedResult: "Administrar perfil, conexiones, alertas y permisos.",
    dependencies: "Autenticación backend y aislamiento multiusuario.",
    activationOrder: "9 · Se activa al completar la seguridad multiusuario.",
  },
  notifications: {
    key: "notifications",
    title: "Notificaciones",
    state: "evaluation",
    summary: "Bandeja de alertas que realmente requieren atención.",
    expectedResult: "Ver, marcar como leídas y abrir el asunto relacionado.",
    dependencies: "Depuración de notificaciones históricas y reglas de relevancia.",
    activationOrder: "4 · Después de la búsqueda global.",
  },
  personalize: {
    key: "personalize",
    title: "Personalizar vista",
    state: "evaluation",
    summary: "Permitirá ordenar, mostrar u ocultar bloques del tablero.",
    expectedResult: "Preferencias persistentes de distribución, densidad y accesibilidad.",
    dependencies: "Esquema de preferencias por usuario.",
    activationOrder: "10 · Después de los módulos operativos.",
  },
  search: {
    key: "search",
    title: "Búsqueda",
    state: "testing",
    summary: "Actualmente filtra únicamente los casos prioritarios visibles.",
    expectedResult: "Búsqueda global por asunto, persona, remitente, caso y tarea.",
    dependencies: "Endpoint paginado y autenticado de búsqueda.",
    activationOrder: "3 · Después del detalle del caso.",
  },
  "cases-all": {
    key: "cases-all",
    title: "Ver todos los casos",
    state: "evaluation",
    summary: "Acceso a la lista completa de casos.",
    expectedResult: "Abrir el módulo Casos conservando filtros y paginación.",
    dependencies: "Módulo Casos.",
    activationOrder: "1 · Se activa junto con el módulo Casos.",
  },
  "activity-all": {
    key: "activity-all",
    title: "Ver toda la actividad",
    state: "evaluation",
    summary: "Acceso a la cronología completa del sistema.",
    expectedResult: "Abrir la actividad con filtros por fecha, evento y actor.",
    dependencies: "Módulo Actividad.",
    activationOrder: "6 · Se activa junto con Actividad.",
  },
  "case-detail": {
    key: "case-detail",
    title: "Detalle del caso",
    state: "evaluation",
    summary: "Pantalla para comprender y gestionar un caso específico.",
    expectedResult: "Mensajes relacionados, evidencias, estado, prioridad, responsable y eventos.",
    dependencies: "Lectura autenticada por caso y clasificación depurada.",
    activationOrder: "2 · Inmediatamente después del módulo Casos.",
  },
  "event-detail": {
    key: "event-detail",
    title: "Detalle del evento",
    state: "evaluation",
    summary: "Explicará el origen y los cambios asociados con cada evento.",
    expectedResult: "Mostrar datos auditables sin exponer información sensible.",
    dependencies: "Módulo Actividad y sanitización de metadatos.",
    activationOrder: "6 · Se activa junto con Actividad.",
  },
  "new-case": {
    key: "new-case",
    title: "Nuevo caso",
    state: "evaluation",
    summary: "Creación manual de un asunto operativo.",
    expectedResult: "Formulario validado con responsable, prioridad, vencimiento y evidencia inicial.",
    dependencies: "Permisos, modelo de participantes y auditoría.",
    activationOrder: "2 · Después de aprobar el detalle del caso.",
  },
  "generate-report": {
    key: "generate-report",
    title: "Generar reporte",
    state: "evaluation",
    summary: "Exportación de información seleccionada.",
    expectedResult: "Elegir periodo, contenido y formato antes de generar el archivo.",
    dependencies: "Módulo Reportes y datos depurados.",
    activationOrder: "7 · Se activa con Reportes.",
  },
  "mobile-more": {
    key: "mobile-more",
    title: "Menú móvil Más",
    state: "evaluation",
    summary: "Acceso móvil a los módulos secundarios.",
    expectedResult: "Menú accesible con navegación y estados de implementación.",
    dependencies: "Definición final de navegación móvil.",
    activationOrder: "Después de validar la navegación de escritorio.",
  },
};

const THEMES: Array<{
  id: ThemeId;
  label: string;
}> = [
  { id: "accessible", label: "Confianza · slate & teal" },
  { id: "aurora", label: "Colaboración · cielo" },
  { id: "graphite", label: "Institucional · grafito" },
  { id: "midnight", label: "Noche · indigo" },
];

const NAV_ITEMS: Array<{
  id: string;
  labelKey: MessageKey;
  icon: typeof Home;
  state: ControlState;
}> = [
  { id: "home", labelKey: "navHome", icon: Home, state: "active" },
  { id: "mail", labelKey: "navMail", icon: Mail, state: "active" },
  { id: "push", labelKey: "navAlerts", icon: Bell, state: "active" },
  { id: "cases", labelKey: "navCases", icon: Inbox, state: "active" },
  { id: "tasks", labelKey: "navTasks", icon: CheckCircle2, state: "active" },
  { id: "activity", labelKey: "navActivity", icon: Activity, state: "active" },
  { id: "reports", labelKey: "navReports", icon: FileBarChart, state: "active" },
  { id: "metrics", labelKey: "navMetrics", icon: BarChart3, state: "active" },
  { id: "settings", labelKey: "navSettings", icon: Settings, state: "active" },
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

function ControlStateBadge({
  state,
  compact = false,
}: {
  state: ControlState;
  compact?: boolean;
}) {
  return (
    <span
      className={`app-control-state app-control-state-${state}${compact ? " is-compact" : ""}`}
    >
      {CONTROL_STATE_LABELS[state]}
    </span>
  );
}

function ControlEvaluationDialog({
  control,
  onClose,
}: {
  control: ControlDefinition;
  onClose: () => void;
}) {
  useEffect(() => {
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }

    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [onClose]);

  return (
    <div className="app-evaluation-overlay" role="presentation" onMouseDown={onClose}>
      <section
        className="app-evaluation-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="evaluation-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="app-evaluation-heading">
          <div>
            <span>LABORATORIO DE CONTROLES</span>
            <h2 id="evaluation-title">{control.title}</h2>
          </div>
          <button type="button" aria-label="Cerrar ficha" onClick={onClose}>
            <X size={23} />
          </button>
        </div>

        <ControlStateBadge state={control.state} />
        <p className="app-evaluation-summary">{control.summary}</p>

        <dl className="app-evaluation-grid">
          <div>
            <dt>Resultado esperado</dt>
            <dd>{control.expectedResult}</dd>
          </div>
          <div>
            <dt>Dependencias</dt>
            <dd>{control.dependencies}</dd>
          </div>
          <div>
            <dt>Orden propuesto</dt>
            <dd>{control.activationOrder}</dd>
          </div>
        </dl>

        <div className="app-evaluation-footer">
          <p>
            Este control permanece visible para evaluar nombre, ubicación y utilidad.
            Su estado no implica que la operación esté implementada.
          </p>
          <button type="button" onClick={onClose}>Entendido</button>
        </div>
      </section>
    </div>
  );
}

function PasswordRecoveryScreen({
  theme,
  setTheme,
  onUpdatePassword,
  onCancel,
}: {
  theme: ThemeId;
  setTheme: (theme: ThemeId) => void;
  onUpdatePassword: (password: string) => Promise<void>;
  onCancel: () => Promise<void>;
}) {
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (password.length < 8) {
      setError("La nueva contraseña Donexto debe tener al menos 8 caracteres.");
      return;
    }

    if (password !== confirmation) {
      setError("Las dos contraseñas no coinciden.");
      return;
    }

    setBusy(true);

    try {
      await onUpdatePassword(password);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "No fue posible actualizar la contraseña Donexto.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-screen" data-theme={theme}>
      <div className="auth-backdrop" />

      <section className="auth-recovery-shell">
        <div className="auth-panel-top">
          <div className="auth-panel-brand">
            <span className="auth-logo">
              <Sparkles size={25} />
            </span>
            <div>
              <strong>Donexto</strong>
              <small>Recuperación segura</small>
            </div>
          </div>

          <label className="auth-theme">
            <span>Tema</span>
            <select
              value={theme}
              onChange={(event) =>
                setTheme(event.target.value as ThemeId)
              }
            >
              {THEMES.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <section className="auth-card auth-recovery-card">
          <div className="auth-card-heading">
            <span>NUEVA CONTRASEÑA DONEXTO</span>
            <h2>Protege tu cuenta</h2>
            <p>
              Esta contraseña pertenece a Donexto. No modifica la contraseña
              de Yahoo, Gmail, Outlook ni de tu proveedor de correo.
            </p>
          </div>

          <form onSubmit={submit}>
            <label className="auth-field">
              <span>Nueva contraseña Donexto</span>
              <div>
                <KeyRound size={18} />
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  autoComplete="new-password"
                  autoCapitalize="none"
                  autoCorrect="off"
                  spellCheck={false}
                  placeholder="Mínimo 8 caracteres"
                  onChange={(event) =>
                    setPassword(event.target.value)
                  }
                />
                <button
                  type="button"
                  aria-label={
                    showPassword
                      ? "Ocultar contraseña"
                      : "Mostrar contraseña"
                  }
                  onClick={() =>
                    setShowPassword((current) => !current)
                  }
                >
                  {showPassword ? (
                    <EyeOff size={18} />
                  ) : (
                    <Eye size={18} />
                  )}
                </button>
              </div>
            </label>

            <label className="auth-field">
              <span>Confirmar nueva contraseña</span>
              <div>
                <ShieldCheck size={18} />
                <input
                  type={showPassword ? "text" : "password"}
                  value={confirmation}
                  autoComplete="new-password"
                  autoCapitalize="none"
                  autoCorrect="off"
                  spellCheck={false}
                  placeholder="Escríbela nuevamente"
                  onChange={(event) =>
                    setConfirmation(event.target.value)
                  }
                />
              </div>
            </label>

            {error ? (
              <div className="auth-error">
                <AlertTriangle size={17} />
                {error}
              </div>
            ) : null}

            <button
              type="submit"
              className="auth-submit"
              disabled={busy}
            >
              {busy
                ? "Actualizando..."
                : "Guardar contraseña Donexto"}
            </button>

            <button
              type="button"
              className="auth-cancel-recovery"
              disabled={busy}
              onClick={() => {
                void onCancel();
              }}
            >
              Cancelar y volver al acceso
            </button>
          </form>
        </section>
      </section>
    </main>
  );
}


function CaseRow({
  item,
  onEvaluate,
}: {
  item: IntelligentCase;
  onEvaluate: (key: string) => void;
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
        aria-label={`Evaluar apertura de ${item.title}`}
        onClick={() => onEvaluate("case-detail")}
        data-control-state="evaluation"
      >
        <ChevronRight size={20} />
      </button>
    </article>
  );
}

function EventRow({
  item,
  onEvaluate,
}: {
  item: CaseEvent;
  onEvaluate: (key: string) => void;
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
            "Evento operativo registrado por Donexto."}
        </p>
        <time>{formatDate(item.created_at)}</time>
      </div>

      <button
        type="button"
        className="app-event-arrow"
        aria-label={`Evaluar detalle de ${item.title}`}
        onClick={() => onEvaluate("event-detail")}
        data-control-state="evaluation"
      >
        <ChevronRight size={19} />
      </button>
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
  const { t } = useLanguage();
  const {
    connection,
    loadingConnection,
    connectionError,
    connectingYahoo,
    loadGoogleStatus,
    startGoogleConnection,
    startYahooConnection,
  } = useGoogleStatus();

  const isGoogleMailbox =
    connection?.connected &&
    (connection.provider == null || connection.provider === "google");
  const isYahooMailbox =
    connection?.connected && connection.provider === "yahoo";
  const yahooIdentityReady =
    connection?.provider === "yahoo" && Boolean(connection.has_access_token);
  const yahooMailPending = yahooIdentityReady && !Boolean(connection?.connected);
  const usesGuidedImport = Boolean(isGoogleMailbox || isYahooMailbox);

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
  } = useCases(Boolean(connection?.connected));

  const [mobileOpen, setMobileOpen] = useState(false);
  const [activeView, setActiveView] = useState("home");
  const [profileOpen, setProfileOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [evaluationKey, setEvaluationKey] = useState<string | null>(null);
  const [guidedImportOpen, setGuidedImportOpen] = useState(false);
  const [mailboxPickerOpen, setMailboxPickerOpen] = useState(false);
  const [liveMailOpen, setLiveMailOpen] = useState(false);
  const [mailOpen, setMailOpen] = useState(false);
  const [mailInitialMessageId, setMailInitialMessageId] = useState<string | null>(null);
  const [pushOpen, setPushOpen] = useState(false);
  const [mailCategory, setMailCategory] = useState<string | null>(null);
  const [importFlowStatus, setImportFlowStatus] =
    useState<ImportFlowStatus | null>(null);
  const [initialFlowOpened, setInitialFlowOpened] = useState(false);

  // Tras verificar Donexto sin buzón: autorizar lectura del mismo correo.
  useEffect(() => {
    if (loadingConnection) {
      return;
    }
    if (connection?.connected || yahooIdentityReady) {
      setMailboxPickerOpen(false);
      return;
    }
    setMailboxPickerOpen(true);
  }, [connection?.connected, loadingConnection, yahooIdentityReady]);

  useEffect(() => {
    if (
      loadingConnection
      || !usesGuidedImport
      || initialFlowOpened
    ) {
      return;
    }

    let cancelled = false;

    void hmsJson<ImportFlowStatus>(
      "/api/hms/gmail/import/status",
      { cache: "no-store" },
    )
      .then((current) => {
        if (cancelled) {
          return;
        }

        setImportFlowStatus(current);

        if (
          current.needs_initial_import
          || Boolean(current.active)
        ) {
          setGuidedImportOpen(true);
        }

        setInitialFlowOpened(true);
      })
      .catch((requestError) => {
        if (!cancelled) {
          setNotice(
            requestError instanceof Error
              ? requestError.message
              : "No fue posible preparar la descarga inicial.",
          );
          setInitialFlowOpened(true);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [
    usesGuidedImport,
    initialFlowOpened,
    loadingConnection,
  ]);

  const evaluatedControl = evaluationKey
    ? CONTROL_CATALOG[evaluationKey]
    : null;

  function evaluateControl(key: string) {
    setEvaluationKey(key);
    setMobileOpen(false);
    setProfileOpen(false);
  }

  function openMailboxConnect() {
    setMailboxPickerOpen(true);
    setNotice(null);
  }

  function requestMailboxOrExplain() {
    if (connection?.connected) {
      openConnectedMailboxActions();
      return;
    }
    if (yahooMailPending) {
      setNotice(ACCOUNT_VS_MAILBOX.yahooWaitingMailBody);
      return;
    }
    openMailboxConnect();
  }

  function openConnectedMailboxActions() {
    setGuidedImportOpen(true);
  }

  function openMailView() {
    setMailCategory(null);
    setMailInitialMessageId(null);
    if (!connection?.connected) {
      requestMailboxOrExplain();
      return;
    }
    if (usesGuidedImport && !importFlowStatus?.initial_import_complete) {
      setGuidedImportOpen(true);
      return;
    }
    setMailOpen(true);
  }

  function selectView(view: string, label: string) {
    setMobileOpen(false);
    setProfileOpen(false);

    if (view === "push") {
      setPushOpen(true);
      return;
    }

    if (view === "mail") {
      openMailView();
      return;
    }

    if (view === "home") {
      setActiveView("home");
      setNotice(null);
      return;
    }

    if (view === "cases" || view === "tasks" || view === "activity") {
      setActiveView("home");
      setNotice(
        view === "cases"
          ? "Casos: se generan al clasificar el correo descargado."
          : view === "tasks"
            ? "Tareas: se alimentan desde casos y correos clasificados."
            : "Actividad: verás eventos cuando haya clasificación en curso.",
      );
      void loadDashboard();
      return;
    }

    if (view === "metrics" || view === "reports") {
      setActiveView("home");
      setNotice(
        "Las métricas se llenan con casos clasificados. Si ves ceros, descarga y clasifica correo primero.",
      );
      void loadDashboard();
      return;
    }

    if (view === "settings") {
      setSettingsOpen(true);
      setNotice(null);
      return;
    }

    setActiveView("home");
    setNotice(`${label} listo en el panel principal.`);
  }

  const busy =
    loading || syncing || loadingConnection;

  const metrics = useMemo(
    () => {
      const emptyHint = connection?.connected
        ? "Aparecen al clasificar el correo"
        : ACCOUNT_VS_MAILBOX.step2Title;

      return [
        {
          label: "Casos por revisar",
          value: dashboard.metrics.total_open,
          icon: Inbox,
          tone: "blue",
          hint: dashboard.metrics.total_open
            ? "Conteo en vivo"
            : emptyHint,
        },
        {
          label: "Marcados críticos",
          value: dashboard.metrics.critical,
          icon: AlertTriangle,
          tone: "red",
          hint: dashboard.metrics.critical
            ? "Conteo en vivo"
            : emptyHint,
        },
        {
          label: "Marcados en espera",
          value:
            dashboard.metrics.waiting_internal +
            dashboard.metrics.waiting_external,
          icon: Clock3,
          tone: "violet",
          hint:
            dashboard.metrics.waiting_internal +
              dashboard.metrics.waiting_external
              ? "Conteo en vivo"
              : emptyHint,
        },
        {
          label: "Vencidos",
          value: dashboard.metrics.overdue,
          icon: Bell,
          tone: "green",
          hint: dashboard.metrics.overdue
            ? "Conteo en vivo"
            : emptyHint,
        },
        {
          label: "Resueltos hoy",
          value: dashboard.metrics.resolved_today,
          icon: CheckCircle2,
          tone: "cyan",
          hint: dashboard.metrics.resolved_today
            ? "Conteo en vivo"
            : emptyHint,
        },
      ];
    },
    [connection?.connected, dashboard.metrics, isYahooMailbox],
  );

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const params = new URLSearchParams(window.location.search);
      const messageId = params.get("mail");
      if (!messageId) return;
      setMailCategory(null);
      setMailInitialMessageId(messageId);
      setMailOpen(true);
      params.delete("mail");
      const next = params.toString();
      window.history.replaceState({}, "", next ? `/?${next}` : "/");
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  const visibleCases = cases;
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
        aria-label={t("closeMenu")}
      />

      <aside
        className={
          mobileOpen
            ? "app-sidebar is-open"
            : "app-sidebar"
        }
      >
        <div className="app-brand">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            className="app-brand-icon"
            src="/brand/donexto-mark.svg"
            width={42}
            height={42}
            alt=""
          />
          <div>
            <strong>Donexto</strong>
            <small>Do Next To…</small>
          </div>

          <button
            type="button"
            className="app-sidebar-close"
            onClick={() => setMobileOpen(false)}
            aria-label={t("closeMenu")}
          >
            <X size={21} />
          </button>
        </div>

        <nav className="app-navigation">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const label = t(item.labelKey);

            return (
              <button
                key={item.id}
                type="button"
                className={
                  activeView === item.id
                    ? "app-nav-item is-active"
                    : "app-nav-item"
                }
                aria-current={activeView === item.id ? "page" : undefined}
                onClick={() => selectView(item.id, label)}
                data-control-state={item.state}
              >
                <Icon size={21} />
                <span>{label}</span>
                {item.id === "cases" && dashboard.metrics.total_open > 0 ? (
                  <span className="app-nav-item-state">
                    <b>{dashboard.metrics.total_open}</b>
                  </span>
                ) : null}
              </button>
            );
          })}
        </nav>

        <div className="app-sidebar-bottom">
          <button
            type="button"
            className="app-sidebar-primary"
            aria-label={
              connection?.connected
                ? "Descargar correos nuevos"
                : ACCOUNT_VS_MAILBOX.connectMailboxLabel
            }
            disabled={
              loadingConnection ||
              yahooMailPending ||
              Boolean(connection?.connected && syncing)
            }
            onClick={() => {
              requestMailboxOrExplain();
            }}
          >
            {connection?.connected ? (
              <RefreshCw
                size={19}
                className={syncing ? "app-spin" : undefined}
              />
            ) : (
              <Mail size={19} />
            )}
            {loadingConnection
              ? "Verificando…"
              : syncing
                ? `Lote ${syncProgress.currentBatch}…`
                : connection?.connected
                  ? "Actualizar correo"
                  : yahooMailPending
                    ? "Lectura pendiente"
                    : ACCOUNT_VS_MAILBOX.connectMailboxLabel}
          </button>

          {connection?.connected ? (
            <button
              type="button"
              className="app-logout"
              onClick={() => openMailboxConnect()}
            >
              <Mail size={18} />
              {ACCOUNT_VS_MAILBOX.changeMailboxLabel}
            </button>
          ) : null}

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
                placeholder="Buscar correos, personas o avisos…"
                onChange={(event) =>
                  setSearch(event.target.value)
                }
              />
              {search ? (
                <button
                  type="button"
                  className="app-search-clear"
                  aria-label="Limpiar búsqueda"
                  onClick={() => setSearch("")}
                >
                  <X size={16} />
                </button>
              ) : null}
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
                  ? ACCOUNT_VS_MAILBOX.mailboxConnected
                  : ACCOUNT_VS_MAILBOX.mailboxMissing}
              </div>

              <div className="app-user-menu">
                <button type="button" className="app-user" aria-haspopup="menu" aria-expanded={profileOpen} onClick={() => setProfileOpen((current) => !current)}>
                  <span>{initials(session.name)}</span>
                  <div>
                    <strong>{session.name.split(" ")[0]}</strong>
                    <small>{session.email}</small>
                  </div>
                  <ChevronDown size={16} />
                </button>

                {profileOpen ? (
                  <div className="app-profile-dropdown" role="menu">
                    <div className="app-profile-summary">
                      <span>{initials(session.name)}</span>
                      <div><strong>{session.name}</strong><small>{session.email}</small></div>
                    </div>
                    <button
                      type="button"
                      role="menuitem"
                      onClick={() => {
                        setProfileOpen(false);
                        setSettingsOpen(true);
                      }}
                    >
                      <Languages size={17} />
                      {t("profileSettings")}
                    </button>
                    <button type="button" role="menuitem" className="is-danger" onClick={onLogout}>
                      <LogOut size={17} />
                      {t("profileSignOut")}
                    </button>
                  </div>
                ) : null}
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
                ? ACCOUNT_VS_MAILBOX.mailboxConnected
                : ACCOUNT_VS_MAILBOX.mailboxMissing}
            </div>
          </div>
        </header>

        <div className="app-content">
          {usesGuidedImport && !importFlowStatus?.initial_import_complete ? (
            <section className="app-alert app-historical-alert" role="status">
              <Sparkles size={20} />
              <div>
                <strong>
                  {importFlowStatus?.active
                    ? "Preparando tu correo…"
                    : `Importa tu buzón ${mailboxServiceLabel(
                        connection?.provider === "yahoo" ? "yahoo" : "gmail",
                      )}`}
                </strong>
                <span>
                  {importFlowStatus?.active
                    ? "Clasificamos mensajes útiles y separamos el ruido. Esto puede tomar unos minutos."
                    : "Tu cuenta Donexto ya está lista. Completa la importación de los últimos seis meses."}
                </span>
              </div>
            </section>
          ) : null}

          {notice ? (
            <section className="app-navigation-notice" role="status">
              <CheckCircle2 size={18} />
              <span>{notice}</span>
              <button type="button" aria-label="Cerrar aviso" onClick={() => setNotice(null)}><X size={17} /></button>
            </section>
          ) : null}

          <section className="app-welcome dx-attention-welcome">
            <AttentionHome
              personName={session.name.split(" ")[0] || ""}
              accountEmail={session.email}
              mailboxEmail={connection?.email}
              mailboxConnected={Boolean(connection?.connected)}
              mailboxLoading={loadingConnection}
              yahooMailPending={yahooMailPending}
              onConnectMailbox={() => openMailboxConnect()}
              onChangeMailbox={() => openMailboxConnect()}
              onRefreshMailbox={() => {
                if (connection?.connected) {
                  openConnectedMailboxActions();
                  return;
                }
                openMailboxConnect();
              }}
              onOpenAllMail={() => openMailView()}
              onOpenCategory={(category) => {
                if (!usesGuidedImport) {
                  openMailView();
                  return;
                }
                if (!importFlowStatus?.initial_import_complete) {
                  setGuidedImportOpen(true);
                  return;
                }
                setMailCategory(category);
                setMailInitialMessageId(null);
                setMailOpen(true);
              }}
            />
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

          {connection?.connected && usesGuidedImport ? (
            <details className="dx-home-more">
              <summary>Clasificación completa del correo</summary>
              <MailCategoriesPanel
                onOpenCategory={(category) => {
                  setMailCategory(category);
                  setMailInitialMessageId(null);
                  setMailOpen(true);
                }}
              />
            </details>
          ) : null}

          {connection?.connected ? (
          <details className="dx-home-more">
            <summary>Casos y actividad (vista operativa)</summary>
            <section className="app-metrics" style={{ marginTop: "0.85rem" }}>
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
                      <small>{metric.hint}</small>
                    </div>

                    <Icon size={29} />
                  </article>
                );
              })}
            </section>

            <section className="app-dashboard-grid">
              <div className="app-panel">
                <div className="app-panel-heading">
                  <div>
                    <h2>Casos por revisar</h2>
                  </div>
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
                      {search ? (
                        <div className="app-empty-search">
                          <Search size={24} />
                          <span>
                            No hay coincidencias para “{search}”. Los casos no se eliminaron.
                          </span>
                          <button type="button" onClick={() => setSearch("")}>Limpiar búsqueda</button>
                        </div>
                      ) : (
                        <>
                          <CheckCircle2 size={26} />
                          No hay casos pendientes.
                        </>
                      )}
                    </div>
                  ) : (
                    visibleCases.map((item) => (
                      <CaseRow
                        key={item.id}
                        item={item}
                        onEvaluate={evaluateControl}
                      />
                    ))
                  )}
                </div>
              </div>

              <div className="app-panel">
                <div className="app-panel-heading">
                  <div>
                    <h2>Últimos eventos</h2>
                  </div>
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
                        onEvaluate={evaluateControl}
                      />
                    ))
                  )}
                </div>
              </div>
            </section>
          </details>
          ) : null}

          {connection?.connected ? (
          <section className="app-actions-block" aria-label="Acciones rápidas">
            <div className="app-actions-heading">
              <h2>Acciones rápidas</h2>
            </div>
            <div className="app-quick-actions">
              <button
                type="button"
                onClick={() => openMailView()}
              >
                <Mail size={22} />
                <div>
                  <strong>Abrir correos</strong>
                  <span>Bandeja del buzón conectado</span>
                </div>
              </button>

              <button
                type="button"
                disabled={
                  loadingConnection ||
                  yahooMailPending ||
                  Boolean(connection?.connected && syncing)
                }
                onClick={() => {
                  requestMailboxOrExplain();
                }}
              >
                {connection?.connected ? (
                  <RefreshCw
                    size={22}
                    className={syncing ? "app-spin" : undefined}
                  />
                ) : (
                  <Mail size={22} />
                )}
                <div>
                  <strong>
                    {connection?.connected
                      ? "Actualizar buzón"
                      : yahooMailPending
                        ? "Lectura pendiente"
                        : ACCOUNT_VS_MAILBOX.connectMailboxLabel}
                  </strong>
                  <span>
                    {connection?.connected
                      ? "Traer mensajes nuevos"
                      : "Gmail o Yahoo"}
                  </span>
                </div>
              </button>

              <button
                type="button"
                onClick={() => openMailboxConnect()}
              >
                <Mail size={22} />
                <div>
                  <strong>{ACCOUNT_VS_MAILBOX.changeMailboxLabel}</strong>
                  <span>Otro Gmail o Yahoo</span>
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
                  <span>Datos al momento</span>
                </div>
              </button>
            </div>
          </section>
          ) : null}
        </div>

        <nav className="app-mobile-nav" aria-label={t("navMenu")}>
          <button type="button" className="is-active" onClick={() => selectView("home", t("navHome"))}>
            <Home size={23} />
            <span>{t("navHome")}</span>
          </button>

          <button type="button" onClick={() => selectView("cases", t("navCases"))}>
            <Inbox size={23} />
            <span>{t("navCases")}</span>
          </button>

          <button
            type="button"
            className="app-mobile-plus"
            aria-label="Conectar o refrescar correo"
            onClick={() => {
              if (connection?.connected) {
                openConnectedMailboxActions();
                return;
              }
              openMailboxConnect();
            }}
          >
            <Plus size={29} />
          </button>

          <button
            type="button"
            onClick={() => {
              openMailView();
            }}
          >
            <Mail size={23} />
            <span>{t("navMail")}</span>
          </button>

          <button type="button" onClick={() => setMobileOpen(true)}>
            <Menu size={23} />
            <span>{t("navMenu")}</span>
          </button>
        </nav>

        {settingsOpen ? (
          <UserSettingsPanel
            email={session.email}
            name={session.name}
            onClose={() => setSettingsOpen(false)}
            onSignOut={onLogout}
          />
        ) : null}

        {pushOpen ? (
          <PushNotificationsPanel onClose={() => setPushOpen(false)} />
        ) : null}

        {mailboxPickerOpen ? (
          <MailboxConnectModal
            open={mailboxPickerOpen}
            connectingYahoo={connectingYahoo}
            required={!connection?.connected && !yahooIdentityReady}
            accountEmail={session.email}
            mode={mailboxConnectModeFromEmail(session.email)}
            onClose={() => {
              if (!connection?.connected) {
                return;
              }
              setMailboxPickerOpen(false);
            }}
            onConnectGoogle={async () => {
              setNotice(
                `Te llevamos a Google para autorizar la lectura de ${session.email}…`,
              );
              try {
                await startGoogleConnection();
              } catch (requestError) {
                const message =
                  requestError instanceof Error
                    ? requestError.message
                    : "No fue posible iniciar la conexión con Google.";
                setNotice(message);
                throw requestError instanceof Error
                  ? requestError
                  : new Error(message);
              }
            }}
            onConnectYahoo={async () => {
              setNotice("Te llevamos a Yahoo para firmar ahí…");
              try {
                await startYahooConnection();
              } catch (requestError) {
                const message =
                  requestError instanceof Error
                    ? requestError.message
                    : "No fue posible abrir Yahoo.";
                setNotice(message);
                throw requestError instanceof Error
                  ? requestError
                  : new Error(message);
              }
            }}
            onSignOut={onLogout}
          />
        ) : null}

        {liveMailOpen ? (
          <LiveMailPanel
            open={liveMailOpen}
            mailboxLabel={connection?.email}
            onClose={() => setLiveMailOpen(false)}
          />
        ) : null}

        {mailOpen ? (
          <MailInbox
            initialCategory={mailCategory}
            initialMessageId={mailInitialMessageId}
            onClose={() => {
              setMailOpen(false);
              setMailInitialMessageId(null);
              void loadDashboard();
              window.dispatchEvent(new Event("hms:data-changed"));
            }}
          />
        ) : null}

        {guidedImportOpen ? (
          <GuidedImportWizard
            onClose={() => setGuidedImportOpen(false)}
            onComplete={() => {
              setGuidedImportOpen(false);
              setImportFlowStatus({
                needs_initial_import: false,
                initial_import_complete: true,
                phase: "ready",
                active: null,
              });
              void Promise.all([
                loadDashboard(),
                loadGoogleStatus(),
              ]);
            }}
          />
        ) : null}

        {evaluatedControl ? (
          <ControlEvaluationDialog
            control={evaluatedControl}
            onClose={() => setEvaluationKey(null)}
          />
        ) : null}
      </main>
    </div>
  );
}

export default function HomePage() {
  const [theme, setTheme] = useState<ThemeId>("accessible");
  const {
    session,
    loading,
    passwordRecovery,
    needsEmailConfirm,
    signIn,
    signInWithGoogle,
    signInWithYahoo,
    signInWithProvider,
    signUp,
    resendSignupEmail,
    signInWithMagicLink,
    signOut,
    resetPassword,
    updatePassword,
    cancelPasswordRecovery,
    refreshSession,
    sendDonextoVerifyEmail,
  } = useAppAuth();

  useEffect(() => {
    window.localStorage.setItem("hms-approved-theme", theme);
  }, [theme]);

  return (
    <LanguageProvider userId={session?.id ?? null}>
      {loading ? (
        <div className="app-loading-screen">
          <Sparkles size={34} />
          <span>Verificando sesión segura...</span>
        </div>
      ) : passwordRecovery ? (
        <PasswordRecoveryScreen
          theme={theme}
          setTheme={setTheme}
          onUpdatePassword={updatePassword}
          onCancel={cancelPasswordRecovery}
        />
      ) : !session ? (
        <LoginScreen
          theme={theme}
          setTheme={setTheme}
          onSignIn={signIn}
          onSignUp={signUp}
          onSignInWithGoogle={signInWithGoogle}
          onSignInWithYahoo={signInWithYahoo}
          onSignInWithProvider={signInWithProvider}
          onResendSignupEmail={resendSignupEmail}
          onMagicLink={signInWithMagicLink}
          onResetPassword={resetPassword}
        />
      ) : needsEmailConfirm ? (
        <ConfirmEmailGate
          email={session.email}
          onResend={sendDonextoVerifyEmail}
          onRefresh={refreshSession}
          onSignOut={signOut}
        />
      ) : (
        <Dashboard
          theme={theme}
          setTheme={setTheme}
          session={session}
          onLogout={() => {
            void signOut();
          }}
        />
      )}
    </LanguageProvider>
  );
}
