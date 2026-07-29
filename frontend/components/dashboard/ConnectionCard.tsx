"use client";

import { CheckCircle2, WifiOff, RefreshCw } from "lucide-react";

interface ConnectionCardProps {
  connected: boolean;
  loading: boolean;
  email?: string;
  onConnect: () => void;
  onDisconnect: () => void;
}

export default function ConnectionCard({
  connected,
  loading,
  email,
  onConnect,
  onDisconnect,
}: ConnectionCardProps) {
  return (
    <section className="connection-card">
      <div className="connection-header">
        <div>
          <h2>Estado de conexión</h2>
          <p>
            Conecta tu cuenta de Gmail para comenzar a analizar tus correos.
          </p>
        </div>

        <div
          className={
            connected
              ? "status-pill connected"
              : "status-pill disconnected"
          }
        >
          {connected ? (
            <>
              <CheckCircle2 size={16} />
              Conectado
            </>
          ) : (
            <>
              <WifiOff size={16} />
              Desconectado
            </>
          )}
        </div>
      </div>

      <div className="connection-body">
        <div>
          <strong>
            {email || "Sin cuenta conectada"}
          </strong>
        </div>

        {connected ? (
          <button
            className="secondary-button"
            onClick={onDisconnect}
          >
            Desconectar
          </button>
        ) : (
          <button
            className="primary-button"
            onClick={onConnect}
            disabled={loading}
          >
            <RefreshCw size={18} />
            {loading ? "Conectando..." : "Conectar Gmail"}
          </button>
        )}
      </div>
    </section>
  );
}