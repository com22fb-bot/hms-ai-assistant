"use client";

import {
  AlertTriangle,
  Eye,
  EyeOff,
  KeyRound,
  ShieldCheck,
} from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

import { DonextoMark } from "@/components/brand/DonextoMark";
import { GuidedImportWizard } from "@/components/GuidedImportWizard";
import { ConfirmEmailGate } from "@/components/auth/ConfirmEmailGate";
import { LoginScreen } from "@/components/auth/LoginScreen";
import { MailboxConnectModal } from "@/components/MailboxConnectModal";
import "@/components/hms-mobile-shell.css";
import "@/components/guided-import.css";
import { MailInbox, type MailAppearance } from "@/components/MailInbox";
import { NucleoApp } from "@/components/nucleo/NucleoApp";
import { LanguageProvider } from "@/lib/i18n/LanguageProvider";
import "@/components/mail-inbox.css";
import { useCases } from "@/hooks/useCases";
import { useGoogleStatus } from "@/hooks/useGoogleStatus";
import { useAppAuth } from "@/hooks/useAppAuth";
import { ACCOUNT_VS_MAILBOX } from "@/lib/accountVsMailbox";
import { mailboxConnectModeFromEmail } from "@/lib/mailboxSignup";
import { HmsApiError, hmsJson } from "@/lib/hmsApi";
import { DEFAULT_PREFS, readLocalPrefs } from "@/lib/nucleo/prefs";
import { supabase } from "@/lib/supabase";

/** The reading view follows the Núcleo IA theme and accessibility prefs. */
function mailAppearance(userId: string): MailAppearance {
  const prefs = readLocalPrefs(userId) ?? DEFAULT_PREFS;
  return {
    theme: prefs.theme === "nucleo-claro" || prefs.theme === "day" ? "light" : "dark",
    highContrast: prefs.highContrast,
    reducedMotion: prefs.reducedMotion,
    fontScale: prefs.fontScale,
    readAloud: prefs.readAloud,
    speechRate: prefs.speechRate,
  };
}

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


const THEMES: Array<{
  id: ThemeId;
  label: string;
}> = [
  { id: "accessible", label: "Confianza · slate & teal" },
  { id: "aurora", label: "Colaboración · cielo" },
  { id: "graphite", label: "Institucional · grafito" },
  { id: "midnight", label: "Noche · indigo" },
];

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
            <DonextoMark className="auth-logo" size={72} />
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

function Dashboard({
  session,
  onLogout,
}: {
  session: AppSession;
  onLogout: () => void;
}) {
  const {
    connection,
    loadingConnection,
    connectingYahoo,
    connectingMicrosoft,
    connectingIcloud,
    connectingYahooImap,
    loadGoogleStatus,
    startGoogleConnection,
    startYahooConnection,
    startMicrosoftConnection,
    connectIcloud,
    connectYahooImap,
  } = useGoogleStatus();

  const isGoogleMailbox =
    connection?.connected &&
    (connection.provider == null || connection.provider === "google");
  const isYahooMailbox =
    connection?.connected && connection.provider === "yahoo";
  const isMicrosoftMailbox =
    connection?.connected && connection.provider === "microsoft";
  const yahooIdentityReady =
    connection?.provider === "yahoo" && Boolean(connection.has_access_token);
  const microsoftIdentityReady =
    connection?.provider === "microsoft" && Boolean(connection.has_access_token);
  const yahooMailPending = yahooIdentityReady && !Boolean(connection?.connected);
  const microsoftMailPending =
    microsoftIdentityReady && !Boolean(connection?.connected);
  const yahooMailReadAvailable = Boolean(connection?.mail_read_available);
  const gmailIdentityWithoutRead =
    Boolean(session.email) &&
    mailboxConnectModeFromEmail(session.email) === "gmail" &&
    !isGoogleMailbox &&
    !isMicrosoftMailbox;
  const yahooIdentityWithoutRead =
    mailboxConnectModeFromEmail(session.email) === "yahoo" &&
    !isYahooMailbox &&
    !isMicrosoftMailbox;
  const isIcloudMailbox =
    connection?.connected && connection.provider === "icloud";
  const usesGuidedImport = Boolean(
    isGoogleMailbox || isYahooMailbox || isMicrosoftMailbox || isIcloudMailbox,
  );

  const { syncing, syncAllMessages, loadDashboard } = useCases(
    Boolean(connection?.connected),
  );

  const [notice, setNotice] = useState<string | null>(null);
  const [guidedImportOpen, setGuidedImportOpen] = useState(false);
  const [mailboxPickerOpen, setMailboxPickerOpen] = useState(false);
  const [mailOpen, setMailOpen] = useState(false);
  const [mailInitialMessageId, setMailInitialMessageId] = useState<string | null>(null);
  const [mailCategory, setMailCategory] = useState<string | null>(null);
  const [importFlowStatus, setImportFlowStatus] =
    useState<ImportFlowStatus | null>(null);
  const [initialFlowOpened, setInitialFlowOpened] = useState(false);
  const [billingBusy, setBillingBusy] = useState(false);
  const [planNotice, setPlanNotice] = useState<string | null>(null);

  useEffect(() => {
    if (loadingConnection) {
      return;
    }
    const timer = window.setTimeout(() => {
      if (connection?.connected || yahooIdentityReady || microsoftIdentityReady) {
        setMailboxPickerOpen(false);
        return;
      }
      setMailboxPickerOpen(true);
    }, 0);
    return () => window.clearTimeout(timer);
  }, [connection?.connected, loadingConnection, yahooIdentityReady, microsoftIdentityReady]);

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

  async function startNormalPlanCheckout() {
    setBillingBusy(true);
    setPlanNotice(null);
    try {
      const result = await hmsJson<{ checkout_url?: string; message?: string }>(
        "/api/hms/billing/checkout",
        { method: "POST" },
      );
      if (result.checkout_url) {
        window.location.assign(result.checkout_url);
        return;
      }
      setPlanNotice(result.message || ACCOUNT_VS_MAILBOX.planNormalMissingKey);
    } catch (requestError) {
      setPlanNotice(
        requestError instanceof HmsApiError
          ? requestError.message
          : ACCOUNT_VS_MAILBOX.planNormalMissingKey,
      );
    } finally {
      setBillingBusy(false);
    }
  }

  function openMailboxConnect() {
    setMailboxPickerOpen(true);
    setNotice(null);
  }

  function stayOnYahooPending() {
    setGuidedImportOpen(false);
    setMailboxPickerOpen(true);
    setNotice(null);
  }

  function requestMailboxOrExplain() {
    if (connection?.connected) {
      setGuidedImportOpen(true);
      return;
    }
    if (yahooMailPending) {
      if (yahooMailReadAvailable) {
        void startYahooConnection({
          intent: "mailbox",
          loginHint: session.email,
        });
        return;
      }
      stayOnYahooPending();
      return;
    }
    if (microsoftMailPending) {
      void startMicrosoftConnection({
        intent: "mailbox",
        loginHint: session.email,
      });
      return;
    }
    openMailboxConnect();
  }

  function openMailView(messageId?: string | null) {
    setMailCategory(null);
    setMailInitialMessageId(messageId ?? null);
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

  return (
    <>
      <NucleoApp
        userId={session.id}
        email={session.email}
        name={session.name}
        connected={Boolean(connection?.connected)}
        mailboxEmail={connection?.email ?? null}
        provider={connection?.provider ?? null}
        syncing={syncing}
        yahooPending={yahooMailPending || yahooIdentityWithoutRead}
        gmailPending={gmailIdentityWithoutRead}
        showPlan={Boolean(isMicrosoftMailbox)}
        planBusy={billingBusy}
        planNotice={planNotice}
        importPending={Boolean(
          usesGuidedImport && importFlowStatus && !importFlowStatus.initial_import_complete,
        )}
        onSignOut={onLogout}
        onConnect={requestMailboxOrExplain}
        onRefreshMail={() => {
          void syncAllMessages();
        }}
        onOpenInbox={openMailView}
        onOpenImport={() => setGuidedImportOpen(true)}
        onPlan={() => {
          void startNormalPlanCheckout();
        }}
      />
      {notice ? (
        <p className="nx-external-notice" role="status">{notice}</p>
      ) : null}

        {mailboxPickerOpen ? (
          <MailboxConnectModal
            open={mailboxPickerOpen}
            connectingYahoo={connectingYahoo}
            connectingMicrosoft={connectingMicrosoft}
            connectingIcloud={connectingIcloud}
            connectingYahooImap={connectingYahooImap}
            required={!connection?.connected && !yahooIdentityReady && !microsoftIdentityReady}
            accountEmail={session.email}
            mode={mailboxConnectModeFromEmail(session.email)}
            onClose={() => {
              if (!connection?.connected && !yahooIdentityReady && !microsoftIdentityReady) {
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
            onConnectIcloud={async (email, appPassword) => {
              await connectIcloud(email, appPassword);
              setMailboxPickerOpen(false);
              setNotice(null);
            }}
            onConnectYahooImap={async (email, appPassword) => {
              await connectYahooImap(email, appPassword);
              setMailboxPickerOpen(false);
              setNotice(null);
            }}
            onConnectMicrosoft={async () => {
              setNotice("Te llevamos a Microsoft para firmar ahí…");
              try {
                await startMicrosoftConnection({
                  intent: microsoftIdentityReady ? "mailbox" : "login",
                  loginHint: session.email,
                });
              } catch (requestError) {
                const message =
                  requestError instanceof Error
                    ? requestError.message
                    : "No fue posible abrir Microsoft.";
                setNotice(message);
                throw requestError instanceof Error
                  ? requestError
                  : new Error(message);
              }
            }}
            onSignOut={onLogout}
          />
        ) : null}

        {mailOpen ? (
          <MailInbox
            initialCategory={mailCategory}
            initialMessageId={mailInitialMessageId}
            appearance={mailAppearance(session.id)}
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

    </>
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
    signInWithMicrosoft,
    signInWithProvider,
    adoptIcloudSession,
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
          <DonextoMark className="app-loading-mark" size={96} alt="Donexto — Do Next To…" />
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
          onSignInWithMicrosoft={signInWithMicrosoft}
          onSignInWithProvider={signInWithProvider}
          onIcloudSession={adoptIcloudSession}
          onYahooSession={adoptIcloudSession}
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
          session={session}
          onLogout={() => {
            // Sign out with Supabase; if the network call fails, still drop the
            // local session so the user is never stuck inside the app.
            void signOut()
              .catch(() => supabase.auth.signOut({ scope: "local" }).catch(() => undefined))
              .finally(() => window.location.replace("/"));
          }}
        />
      )}
    </LanguageProvider>
  );
}
