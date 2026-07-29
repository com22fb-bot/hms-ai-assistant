"use client";

import ConnectionCard from "@/components/dashboard/ConnectionCard";
import DashboardHeader from "@/components/dashboard/DashboardHeader";
import ExecutiveCharts from "@/components/dashboard/ExecutiveCharts";
import MailList from "@/components/dashboard/MailList";
import MailToolbar from "@/components/dashboard/MailToolbar";
import MetricsGrid from "@/components/dashboard/MetricsGrid";
import AppShell from "@/components/layout/AppShell";
import { useConnection } from "@/hooks/useConnection";
import { useMailAnalysis } from "@/hooks/useMailAnalysis";
import { useMailFilters } from "@/hooks/useMailFilters";

function formatLastUpdated(value: Date | null): string {
  if (!value) {
    return "Aún no se ha realizado una actualización.";
  }

  return new Intl.DateTimeFormat("es-MX", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(value);
}

export default function HomePage() {
  const {
    connection,
    messages,
    loadingStatus,
    loadingMessages,
    disconnecting,
    error,
    lastUpdated,
    connectGoogle,
    disconnectGoogle,
    loadConnectionStatus,
    loadMessages,
  } = useConnection();

  const {
    activeFilter,
    searchTerm,
    filteredMessages,
    setActiveFilter,
    setSearchTerm,
  } = useMailFilters(messages);

  const mailAnalysis = useMailAnalysis(messages);

  const connected = connection?.connected ?? false;
  const loading = loadingStatus || loadingMessages;

  async function handleRefresh(): Promise<void> {
    if (connected) {
      await loadMessages();
      return;
    }

    await loadConnectionStatus();
  }

  return (
    <AppShell
      activeItem="dashboard"
      title="Panel principal"
      subtitle="Supervisa correos, pendientes y tareas desde un solo lugar."
      accountEmail={connection?.email}
      connected={connected}
      loading={loading}
      searchValue={searchTerm}
      onSearchChange={setSearchTerm}
      onRefresh={() => {
        void handleRefresh();
      }}
    >
      <div className="dashboard-page">
        <DashboardHeader
          loading={loading}
          onRefresh={() => {
            void handleRefresh();
          }}
        />

        {error ? (
          <section className="error-banner" role="alert">
            <strong>
              No fue posible completar la operación.
            </strong>

            <span>{error}</span>
          </section>
        ) : null}

        <MetricsGrid
          total={mailAnalysis.metrics.total}
          requiresAction={
            mailAnalysis.metrics.requiresAction
          }
          requiresReply={
            mailAnalysis.metrics.requiresReply
          }
          highPriority={
            mailAnalysis.metrics.highPriority
          }
        />


        <ExecutiveCharts
          analyses={mailAnalysis.analyses}
        />

        <ConnectionCard
          connected={connected}
          loading={loadingStatus}
          disconnecting={disconnecting}
          email={connection?.email}
          message={connection?.message}
          onConnect={connectGoogle}
          onDisconnect={() => {
            void disconnectGoogle();
          }}
        />

        <section className="mail-panel">
          <div className="mail-panel-header">
            <div>
              <p className="eyebrow">
                BANDEJA DE ENTRADA
              </p>

              <h2>Correos recientes</h2>

              <p className="mail-panel-description">
                Consulta, filtra y localiza los mensajes
                recuperados de Gmail.
              </p>
            </div>

            <div className="mail-update-status">
              <span>Última actualización</span>

              <strong>
                {formatLastUpdated(lastUpdated)}
              </strong>
            </div>
          </div>

          <MailToolbar
            activeFilter={activeFilter}
            searchTerm={searchTerm}
            onFilterChange={setActiveFilter}
            onSearchChange={setSearchTerm}
          />

          <MailList
            messages={filteredMessages}
            analysisByMessageId={
              mailAnalysis.analysisByMessageId
            }
            loading={loadingMessages}
            connected={connected}
            onConnect={connectGoogle}
          />
        </section>
      </div>
    </AppShell>
  );
}
