"use client";

import { RefreshCw, Sparkles } from "lucide-react";

import CaseList from "@/components/cases/CaseList";
import CaseMetrics from "@/components/cases/CaseMetrics";
import RecentCaseEvents from "@/components/cases/RecentCaseEvents";
import AppShell from "@/components/layout/AppShell";
import { useCases } from "@/hooks/useCases";

export default function HomePage() {
  const {
    dashboard,
    cases,
    search,
    loading,
    processing,
    error,
    lastProcess,
    setSearch,
    loadDashboard,
    processCases,
  } = useCases();

  return (
    <AppShell
      activeItem="cases"
      title="Centro Inteligente de Atención"
      subtitle="Casos, riesgos, responsables y trabajo esperando respuesta."
      loading={loading || processing}
      searchValue={search}
      onSearchChange={setSearch}
      onRefresh={() => {
        void loadDashboard();
      }}
    >
      <div className="case-dashboard-page">
        <section className="case-hero">
          <div>
            <span className="case-eyebrow">
              INTELLIGENT CASE ENGINE
            </span>

            <h1>Lo que requiere tu atención</h1>

            <p>
              HMS AI Assistant correlaciona mensajes y los convierte
              en Casos Inteligentes. Un correo enviado no equivale
              automáticamente a un caso resuelto.
            </p>
          </div>

          <div className="case-hero-actions">
            <button
              type="button"
              className="case-secondary-button"
              disabled={loading || processing}
              onClick={() => {
                void loadDashboard();
              }}
            >
              <RefreshCw
                size={17}
                className={loading ? "case-spin" : undefined}
              />
              Actualizar panel
            </button>

            <button
              type="button"
              className="case-primary-button"
              disabled={processing}
              onClick={() => {
                void processCases();
              }}
            >
              <Sparkles
                size={17}
                className={processing ? "case-spin" : undefined}
              />
              {processing
                ? "Procesando…"
                : "Procesar mensajes"}
            </button>
          </div>
        </section>

        {error ? (
          <section className="case-error" role="alert">
            <strong>No fue posible completar la operación.</strong>
            <span>{error}</span>
          </section>
        ) : null}

        {lastProcess ? (
          <section className="case-process-result">
            <strong>Última ejecución del motor:</strong>
            <span>{lastProcess.processed} mensajes procesados</span>
            <span>{lastProcess.created_cases} casos creados</span>
            <span>
              {lastProcess.linked_to_existing} evidencias correlacionadas
            </span>
            <span>{lastProcess.errors} errores</span>
          </section>
        ) : null}

        <CaseMetrics metrics={dashboard.metrics} />

        <div className="case-dashboard-grid">
          <section className="case-attention-panel">
            <div className="case-section-heading">
              <div>
                <span className="case-eyebrow">
                  PRIORIDAD OPERATIVA
                </span>
                <h2>Casos que requieren atención</h2>
              </div>

              <span className="case-count">
                {cases.length}
              </span>
            </div>

            <CaseList
              cases={cases}
              loading={loading}
            />
          </section>

          <RecentCaseEvents
            events={dashboard.recent_events}
          />
        </div>
      </div>
    </AppShell>
  );
}
