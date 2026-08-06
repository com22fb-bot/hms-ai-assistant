"use client";

import Image from "next/image";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Bell,
  BriefcaseBusiness,
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
import "@/components/guided-import.css";
import { MailCategoriesPanel } from "@/components/MailCategoriesPanel";
import "@/components/mail-categories.css";
import { MailInbox } from "@/components/MailInbox";
import { PushNotificationsPanel } from "@/components/PushNotificationsPanel";
import "@/components/mail-inbox.css";
import "@/components/push-notifications.css";
import "@/components/logistica-responsive.css";
import { useCases } from "@/hooks/useCases";
import { useGoogleStatus } from "@/hooks/useGoogleStatus";
import { useAppAuth } from "@/hooks/useAppAuth";
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
  { id: "midnight", label: "Midnight Social" },
  { id: "aurora", label: "Aurora Collaboration" },
  { id: "accessible", label: "4D Focus Turquesa" },
  { id: "graphite", label: "Soft Graphite" },
];

const NAV_ITEMS: Array<{
  id: string;
  label: string;
  icon: typeof Home;
  state: ControlState;
}> = [
  { id: "home", label: "Inicio", icon: Home, state: "active" },
  { id: "mail", label: "Correos", icon: Mail, state: "active" },
  { id: "push", label: "Avisos", icon: Bell, state: "active" },
  { id: "cases", label: "Casos", icon: BriefcaseBusiness, state: "evaluation" },
  { id: "tasks", label: "Tareas", icon: CheckCircle2, state: "evaluation" },
  { id: "activity", label: "Actividad", icon: Activity, state: "evaluation" },
  { id: "reports", label: "Reportes", icon: FileBarChart, state: "evaluation" },
  { id: "metrics", label: "Métricas", icon: BarChart3, state: "evaluation" },
  { id: "settings", label: "Ajustes", icon: Settings, state: "blocked" },
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

function LoginScreen({
  theme,
  setTheme,
  onSignIn,
  onMagicLink,
  onResetPassword,
}: {
  theme: ThemeId;
  setTheme: (theme: ThemeId) => void;
  onSignIn: (email: string, password: string) => Promise<void>;
  onMagicLink: (email: string) => Promise<void>;
  onResetPassword: (email: string) => Promise<void>;
}) {
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [acceptedTerms, setAcceptedTerms] = useState(false);
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

    if (mode === "signup") {
      setError(
        "El registro está temporalmente bloqueado hasta completar la separación segura por usuario.",
      );
      return;
    }

    setBusy(true);

    try {
      await onSignIn(cleanEmail, password);
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

  async function sendMagicLink() {
    const cleanEmail = email.trim().toLowerCase();

    if (!cleanEmail || !cleanEmail.includes("@")) {
      setError("Escribe primero el correo de tu cuenta HMS.");
      return;
    }

    setBusy(true);
    setError(null);
    setMessage(null);

    try {
      await onMagicLink(cleanEmail);
      setMessage(
        "Te enviamos a tu correo un enlace para entrar a HMS sin contraseña.",
      );
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "No fue posible enviar el enlace de acceso.",
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

        <div className="auth-robot-showcase">
          <Image
            src="/hms-import-robot.png"
            alt="Robot HMS organizando correo entre un maletero y una laptop"
            width={1536}
            height={1024}
            priority
            sizes="(max-width: 900px) 92vw, 520px"
          />
          <div>
            <Sparkles size={19} />
            <span>Tu copiloto organiza el correo antes de mostrarte los pendientes.</span>
          </div>
        </div>

        <div className="auth-presentation-copy">
          <span>ACCESO CON CUENTA HMS REGISTRADA</span>
          <h1>
            Tu cuenta HMS,
            <strong> separada de tu buzón.</strong>
          </h1>
          <p>
            Tu cuenta HMS sirve para entrar a la aplicación. Después,
            en una pantalla independiente, autorizas el buzón que HMS
            analizará directamente en Google, Microsoft o Yahoo.
          </p>
        </div>

        <div className="auth-benefits">
          <article><ShieldCheck size={20} /><div><strong>Autenticación real</strong><span>Sesión segura administrada por Supabase Auth.</span></div></article>
          <article><Mail size={20} /><div><strong>Cuenta HMS independiente</strong><span>La contraseña HMS nunca es la contraseña de tu correo.</span></div></article>
          <article><Users size={20} /><div><strong>Workspace por usuario</strong><span>Cada cuenta se vincula con su propio espacio y buzones autorizados.</span></div></article>
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
            <p>{mode === "signin" ? "Ingresa con el correo y la contraseña que creaste para HMS." : "Este es el diseño funcional del alta. La activación permanece bloqueada hasta terminar las pruebas de aislamiento."}</p>
          </div>

          <div className="auth-mode-tabs" role="tablist">
            <button type="button" className={mode === "signin" ? "is-active" : ""} onClick={() => { setMode("signin"); setError(null); setMessage(null); }}>Iniciar sesión</button>
            <button type="button" className={mode === "signup" ? "is-active" : ""} onClick={() => { setMode("signup"); setError(null); setMessage(null); }}>Crear cuenta</button>
          </div>

          {mode === "signup" ? (
            <form
              className="auth-signup-preview"
              onSubmit={(event) => {
                event.preventDefault();
                setError(
                  "El registro todavía está bloqueado mientras verificamos el aislamiento entre usuarios.",
                );
              }}
            >
              <div className="auth-registration-status" aria-live="polite">
                <ShieldCheck size={22} />
                <div>
                  <strong>Diseño listo · alta todavía bloqueada</strong>
                  <span>
                    Puedes revisar la información que solicitaremos. No se
                    creará ninguna cuenta desde esta pantalla todavía.
                  </span>
                </div>
              </div>

              <label className="auth-field">
                <span>Nombre completo</span>
                <div><Users size={18} /><input
                  type="text"
                  value={fullName}
                  autoComplete="name"
                  placeholder="Nombre que se mostrará en HMS"
                  onChange={(event) => setFullName(event.target.value)}
                /></div>
              </label>

              <label className="auth-field">
                <span>Correo para tu cuenta HMS</span>
                <div><Mail size={18} /><input
                  type="email"
                  value={email}
                  inputMode="email"
                  autoComplete="email"
                  autoCapitalize="none"
                  autoCorrect="off"
                  spellCheck={false}
                  placeholder="tu-cuenta@empresa.com"
                  onChange={(event) => setEmail(event.target.value)}
                /></div>
                <small>
                  Este correo identificará tu cuenta HMS y recibirá enlaces
                  de verificación y recuperación.
                </small>
              </label>

              <label className="auth-field">
                <span>Crear contraseña HMS</span>
                <div><KeyRound size={18} /><input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  autoComplete="new-password"
                  autoCapitalize="none"
                  autoCorrect="off"
                  spellCheck={false}
                  placeholder="Mínimo 8 caracteres"
                  onChange={(event) => setPassword(event.target.value)}
                /><button type="button" aria-label={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"} onClick={() => setShowPassword((current) => !current)}>{showPassword ? <EyeOff size={18} /> : <Eye size={18} />}</button></div>
                <small>
                  Esta contraseña será únicamente para entrar a HMS. No uses
                  aquí la contraseña de Gmail, Yahoo, Outlook ni Hotmail.
                </small>
              </label>

              <label className="auth-field">
                <span>Confirmar contraseña HMS</span>
                <div><ShieldCheck size={18} /><input
                  type={showPassword ? "text" : "password"}
                  value={confirmation}
                  autoComplete="new-password"
                  autoCapitalize="none"
                  autoCorrect="off"
                  spellCheck={false}
                  placeholder="Escríbela nuevamente"
                  onChange={(event) => setConfirmation(event.target.value)}
                /></div>
              </label>

              <label className="auth-consent">
                <input
                  type="checkbox"
                  checked={acceptedTerms}
                  onChange={(event) => setAcceptedTerms(event.target.checked)}
                />
                <span>
                  Acepto el aviso de privacidad y entiendo que HMS nunca
                  solicitará la contraseña de mi correo dentro de este formulario.
                </span>
              </label>

              <div className="auth-onboarding-next">
                <Mail size={20} />
                <div>
                  <strong>Después de crear la cuenta HMS</strong>
                  <span>
                    Verificarás este correo y luego HMS te enviará al sitio
                    oficial de tu proveedor para autorizar el buzón que deseas analizar.
                  </span>
                </div>
              </div>

              {error ? <div className="auth-error"><AlertTriangle size={17} />{error}</div> : null}

              <button type="submit" className="auth-submit auth-submit-blocked">
                Crear mi cuenta HMS · Bloqueado
              </button>
            </form>
          ) : (
            <form onSubmit={submit}>
              <label className="auth-field">
                <span>Correo de tu cuenta HMS</span>
                <div><Mail size={18} /><input
                  type="email"
                  value={email}
                  inputMode="email"
                  autoComplete="email"
                  autoCapitalize="none"
                  autoCorrect="off"
                  spellCheck={false}
                  placeholder="correo-usado-para-registrarte@empresa.com"
                  onChange={(event) => setEmail(event.target.value)}
                /></div>
              </label>

              <label className="auth-field">
                <span>Contraseña HMS</span>
                <div><KeyRound size={18} /><input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  autoComplete="current-password"
                  autoCapitalize="none"
                  autoCorrect="off"
                  spellCheck={false}
                  placeholder="Contraseña de tu cuenta HMS"
                  onChange={(event) => setPassword(event.target.value)}
                /><button type="button" aria-label={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"} onClick={() => setShowPassword((current) => !current)}>{showPassword ? <EyeOff size={18} /> : <Eye size={18} />}</button></div>
              </label>

              <div className="auth-mode-help">
                <ShieldCheck size={18} />
                <span>
                  Escribe la contraseña que creaste para HMS. No escribas
                  aquí la contraseña de Yahoo, Gmail, Outlook ni Hotmail.
                </span>
              </div>

              <div className="auth-access-alternatives">
                <button
                  type="button"
                  className="auth-secondary-action"
                  disabled={busy}
                  onClick={() => {
                    void sendMagicLink();
                  }}
                >
                  <Mail size={18} />
                  Enviarme un enlace de acceso
                </button>

                <button
                  type="button"
                  className="auth-text-action"
                  disabled={busy}
                  onClick={() => {
                    void resetPassword();
                  }}
                >
                  ¿Olvidaste tu contraseña HMS?
                </button>
              </div>

              {error ? <div className="auth-error"><AlertTriangle size={17} />{error}</div> : null}
              {message ? <div className="auth-success"><CheckCircle2 size={17} />{message}</div> : null}

              <button type="submit" className="auth-submit" disabled={busy}>
                {busy ? "Procesando..." : "Ingresar a HMS"}
              </button>
            </form>
          )}

          <div className="auth-security">
            <ShieldCheck size={18} />
            <div><strong>Dos accesos completamente separados</strong><span>Primero entras a HMS; después autorizas tu correo en el sitio oficial del proveedor.</span></div>
          </div>
        </div>
      </section>
    </main>
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
      setError("La nueva contraseña HMS debe tener al menos 8 caracteres.");
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
          : "No fue posible actualizar la contraseña HMS.",
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
              <strong>HMS AI Assistant</strong>
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
            <span>NUEVA CONTRASEÑA HMS</span>
            <h2>Protege tu cuenta</h2>
            <p>
              Esta contraseña pertenece a HMS. No modifica la contraseña
              de Yahoo, Gmail, Outlook ni de tu proveedor de correo.
            </p>
          </div>

          <form onSubmit={submit}>
            <label className="auth-field">
              <span>Nueva contraseña HMS</span>
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
                : "Guardar contraseña HMS"}
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
            "Evento operativo registrado por HMS AI."}
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
  const {
    connection,
    loadingConnection,
    connectionError,
    loadGoogleStatus,
    startGoogleConnection,
  } = useGoogleStatus();

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
  const [notice, setNotice] = useState<string | null>(null);
  const [evaluationKey, setEvaluationKey] = useState<string | null>(null);
  const [guidedImportOpen, setGuidedImportOpen] = useState(false);
  const [mailOpen, setMailOpen] = useState(false);
  const [mailInitialMessageId, setMailInitialMessageId] = useState<string | null>(null);
  const [pushOpen, setPushOpen] = useState(false);
  const [mailCategory, setMailCategory] = useState<string | null>(null);
  const [importFlowStatus, setImportFlowStatus] =
    useState<ImportFlowStatus | null>(null);
  const [initialFlowOpened, setInitialFlowOpened] = useState(false);

  useEffect(() => {
    if (
      loadingConnection
      || !connection?.connected
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
    connection?.connected,
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

  function selectView(view: string, label: string) {
    setMobileOpen(false);
    setProfileOpen(false);

    if (view === "push") {
      setPushOpen(true);
      return;
    }

    if (view === "mail") {
      setMailCategory(null);
      setMailInitialMessageId(null);
      setMailOpen(true);
      return;
    }

    if (view === "home") {
      setActiveView("home");
      setNotice(null);
      return;
    }

    setActiveView("home");
    setNotice(`${label} permanece visible para evaluar su orden y alcance.`);
    evaluateControl(view);
  }

  const busy =
    loading || syncing || loadingConnection;

  const metrics = useMemo(
    () => [
      {
        label: "Casos por revisar",
        value: dashboard.metrics.total_open,
        icon: Inbox,
        tone: "blue",
      },
      {
        label: "Marcados críticos",
        value: dashboard.metrics.critical,
        icon: AlertTriangle,
        tone: "red",
      },
      {
        label: "Marcados en espera",
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
                  activeView === item.id
                    ? "app-nav-item is-active"
                    : "app-nav-item"
                }
                aria-current={activeView === item.id ? "page" : undefined}
                onClick={() => selectView(item.id, item.label)}
                data-control-state={item.state}
              >
                <Icon size={21} />
                <span>{item.label}</span>
                <span className="app-nav-item-state">
                  {item.id === "cases" ? (
                    <b>{dashboard.metrics.total_open}</b>
                  ) : null}
                  {item.id !== "home" ? (
                    <ControlStateBadge state={item.state} compact />
                  ) : null}
                </span>
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
                  : connection?.connected
                    ? "Correo conectado"
                    : "Correo desconectado"}
              </strong>
              <small>
                {syncProgress.completed
                  ? `${syncProgress.found} revisados`
                  : connection?.connected
                    ? "Sistema disponible"
                    : "Conecta tu cuenta de correo"}
              </small>
            </div>
            <span />
          </div>

          <button
            type="button"
            className="app-sidebar-primary"
            aria-label={
              connection?.connected
                ? "Descargar correos nuevos"
                : "Conectar correo"
            }
            disabled={
              loadingConnection ||
              Boolean(connection?.connected && syncing)
            }
            onClick={() => {
              if (connection?.connected) {
                setGuidedImportOpen(true);
                return;
              }

              setNotice("Abriendo la autorización segura de Google...");

              void startGoogleConnection().catch((requestError) => {
                setNotice(
                  requestError instanceof Error
                    ? requestError.message
                    : "No fue posible iniciar la conexión con Google.",
                );
              });
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
              ? "Verificando correo..."
              : syncing
                ? `Procesando lote ${syncProgress.currentBatch}`
                : connection?.connected
                  ? "Descargar correos nuevos"
                  : "Conectar correo"}
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
                placeholder="Filtrar casos prioritarios visibles..."
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
              <kbd>⌘ K</kbd>
              <button
                type="button"
                className="app-search-state"
                onClick={() => evaluateControl("search")}
                aria-label="Ver estado de la búsqueda"
              >
                En prueba
              </button>
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
                  ? "Correo conectado"
                  : "Sin conexión"}
              </div>

              <div className="app-ai-pill is-active"><Sparkles size={17} />Clasificación automática</div>

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
                aria-label="Evaluar notificaciones"
                onClick={() => evaluateControl("notifications")}
                data-control-state="evaluation"
              >
                <Bell size={19} />
              </button>

              <div className="app-user-menu">
                <button type="button" className="app-user" aria-haspopup="menu" aria-expanded={profileOpen} onClick={() => setProfileOpen((current) => !current)}>
                  <span>{initials(session.name)}</span>
                  <div>
                    <strong>{session.name}</strong>
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
                    <button type="button" role="menuitem" onClick={() => evaluateControl("settings")}><Settings size={19} />Ajustes de la cuenta <ControlStateBadge state="blocked" compact /></button>
                    <button type="button" role="menuitem" className="is-danger" onClick={onLogout}><LogOut size={17} />Cerrar sesión</button>
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
                ? "Correo conectado"
                : "Sin conexión"}
            </div>

            <div className="app-ai-pill is-active"><Sparkles size={17} />Clasificación automática</div>
          </div>
        </header>

        <div className="app-content">
          <section className="app-alert app-historical-alert" role="status">
            <Sparkles size={23} />
            <div>
              <strong>
                {importFlowStatus?.initial_import_complete
                  ? "Correo preparado"
                  : importFlowStatus?.active
                    ? "Descarga y clasificación en proceso"
                    : "Primera descarga pendiente"}
              </strong>
              <span>
                {importFlowStatus?.initial_import_complete
                  ? "HMS descargará únicamente correo nuevo y mantendrá separados los casos de los mensajes informativos."
                  : "HMS preparará automáticamente los últimos seis meses, excluirá Spam, Papelera y Borradores, y clasificará cada mensaje antes de mostrar el dashboard final."}
              </span>
            </div>
          </section>

          {notice ? (
            <section className="app-navigation-notice" role="status">
              <CheckCircle2 size={18} />
              <span>{notice}</span>
              <button type="button" aria-label="Cerrar aviso" onClick={() => setNotice(null)}><X size={17} /></button>
            </section>
          ) : null}

          <section className="app-welcome">
            <div>
              <h1>
                Buenos días, {session.name.split(" ")[0]} 👋
              </h1>
              <p>
                4D Focus · Centro Inteligente de Operaciones
              </p>
            </div>

            <button
              type="button"
              onClick={() => evaluateControl("personalize")}
              data-control-state="evaluation"
            >
              <Settings size={20} />
              <span>Personalizar vista</span>
              <ControlStateBadge state="evaluation" compact />
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
                    <small>Conteo exacto · clasificación pendiente</small>
                  </div>

                  <Icon size={29} />
                </article>
              );
            })}
          </section>



          <MailCategoriesPanel
            onOpenCategory={(category) => {
              setMailCategory(category);
              setMailInitialMessageId(null);
              setMailOpen(true);
            }}
          />

          <section className="app-dashboard-grid">
            <div className="app-panel">
              <div className="app-panel-heading">
                <div>
                  <span>PRIORIDAD OPERATIVA</span>
                  <h2>Casos generados por revisar</h2>
                </div>

                <button
                  type="button"
                  onClick={() => evaluateControl("cases-all")}
                  data-control-state="evaluation"
                >
                  Ver todos
                  <ControlStateBadge state="evaluation" compact />
                </button>
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
                  <span>ACTIVIDAD RECIENTE</span>
                  <h2>Últimos eventos</h2>
                </div>

                <button
                  type="button"
                  onClick={() => evaluateControl("activity-all")}
                  data-control-state="evaluation"
                >
                  Ver toda
                  <ControlStateBadge state="evaluation" compact />
                </button>
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

          <section className="app-quick-actions">
            <button
              type="button"
              disabled={
                loadingConnection ||
                Boolean(connection?.connected && syncing)
              }
              onClick={() => {
                if (connection?.connected) {
                  setGuidedImportOpen(true);
                  return;
                }

                void startGoogleConnection().catch((requestError) => {
                  setNotice(
                    requestError instanceof Error
                      ? requestError.message
                      : "No fue posible iniciar la conexión con Google.",
                  );
                });
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
                    ? "Descargar correos nuevos"
                    : "Conectar cuenta de correo"}
                </strong>
                <span>
                  {connection?.connected
                    ? "Revisa únicamente los mensajes nuevos"
                    : "Autorización en el sitio oficial del proveedor"}
                </span>
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

            <button
              type="button"
              onClick={() => evaluateControl("new-case")}
              data-control-state="evaluation"
            >
              <Plus size={27} />
              <div>
                <strong>Nuevo caso</strong>
                <span>En evaluación · crear solicitud</span>
              </div>
            </button>



            <button
              type="button"
              onClick={() => evaluateControl("generate-report")}
              data-control-state="evaluation"
            >
              <FileBarChart size={25} />
              <div>
                <strong>Generar reporte</strong>
                <span>En evaluación · exportar datos</span>
              </div>
            </button>
          </section>
        </div>

        <nav className="app-mobile-nav" aria-label="Navegación móvil">
          <button type="button" className="is-active" data-control-state="active">
            <Home size={23} />
            <span>Inicio</span>
          </button>

          <button type="button" onClick={() => evaluateControl("cases")} data-control-state="evaluation">
            <BriefcaseBusiness size={23} />
            <span>Casos</span>
          </button>

          <button
            type="button"
            className="app-mobile-plus"
            aria-label="Evaluar creación de caso"
            onClick={() => evaluateControl("new-case")}
            data-control-state="evaluation"
          >
            <Plus size={29} />
          </button>

          <button
            type="button"
            onClick={() => {
              setMailCategory(null);
              setMailOpen(true);
            }}
            data-control-state="active"
          >
            <Mail size={23} />
            <span>Correos</span>
          </button>

          <button type="button" onClick={() => evaluateControl("mobile-more")} data-control-state="evaluation">
            <Menu size={23} />
            <span>Más</span>
          </button>
        </nav>

        {pushOpen ? (
          <PushNotificationsPanel onClose={() => setPushOpen(false)} />
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
    signIn,
    signInWithMagicLink,
    signOut,
    resetPassword,
    updatePassword,
    cancelPasswordRecovery,
  } = useAppAuth();

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

  if (passwordRecovery) {
    return (
      <PasswordRecoveryScreen
        theme={theme}
        setTheme={setTheme}
        onUpdatePassword={updatePassword}
        onCancel={cancelPasswordRecovery}
      />
    );
  }

  if (!session) {
    return (
      <LoginScreen
        theme={theme}
        setTheme={setTheme}
        onSignIn={signIn}
        onMagicLink={signInWithMagicLink}
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
