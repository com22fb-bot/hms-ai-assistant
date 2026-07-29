"use client";

import {
  CheckCircle2,
  LogOut,
  RefreshCw,
  WifiOff,
} from "lucide-react";

interface ConnectionCardProps {
  connected: boolean;
  loading: boolean;
  disconnecting?: boolean;
  email?: string | null;
  message?: string | null;
  onConnect: () => void;
  onDisconnect: () => void;
}

export default function ConnectionCard({
  connected,
  loading,
  disconnecting = false,
  email,
  message,
  onConnect,
  onDisconnect,
}: ConnectionCardProps) {
  return (
    <section className="connection-card">
      <div className="connection-main">
        <div className="google-icon">G</div>

        <div>
          <div className="connection-title-row">
            <h2>Cuenta de Google</h2>

            <span
              className={
                loading
                  ? "status-pill status-loading"
                  : connected
                    ? "status-pill status-connected"
                    : "status-pill status-disconnected"
              }
            >
              {loading ? (
                <>
                  <RefreshCw size={14} className="spinning" />
                  Verificando…
                </>
              ) : connected ? (
                <>
                  <CheckCircle2 size={14} />
                  Conectada
                </>
              ) : (
                <>
                  <WifiOff size={14} />
                  Desconectada
                </>
              )}
            </span>
          </div>

          <p>
            {connected
              ? email || "Cuenta autorizada correctamente"
              : message ||
                "Conecta una cuenta para comenzar a revisar correos."}
          </p>
        </div>
      </div>

      {!loading && !connected ? (
        <button
          className="primary-button"
          type="button"
          onClick={onConnect}
        >
          Conectar con Google
        </button>
      ) : connected ? (
        <button
          className="secondary-button"
          type="button"
          onClick={onDisconnect}
          disabled={disconnecting}
        >
          <LogOut size={16} />
          {disconnecting ? "Desconectando…" : "Desconectar"}
        </button>
      ) : (
        <div className="connection-permission">
          <span>Comprobando autorización</span>
          <strong>Espera un momento</strong>
        </div>
      )}
    </section>
  );
}
