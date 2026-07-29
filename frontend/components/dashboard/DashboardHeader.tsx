"use client";

import { RefreshCw } from "lucide-react";

interface DashboardHeaderProps {
  loading: boolean;
  onRefresh: () => void;
}

export default function DashboardHeader({
  loading,
  onRefresh,
}: DashboardHeaderProps) {
  return (
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
          onClick={onRefresh}
          disabled={loading}
        >
          <RefreshCw
            size={18}
            className={loading ? "spinning" : undefined}
          />
          {loading ? "Actualizando…" : "Actualizar"}
        </button>

        <div className="user-avatar" aria-label="Usuario Héctor Marcial">
          HM
        </div>
      </div>
    </header>
  );
}
