"use client";

import {
  Bell,
  Bot,
  Menu,
  RefreshCw,
  Search,
  Wifi,
} from "lucide-react";
import clsx from "clsx";

type TopbarProps = {
  title?: string;
  subtitle?: string;
  accountEmail?: string | null;
  connected?: boolean;
  loading?: boolean;
  searchValue?: string;
  onSearchChange?: (value: string) => void;
  onRefresh?: () => void;
  onMenuOpen: () => void;
};

function getInitials(email?: string | null): string {
  if (!email) {
    return "HS";
  }

  const name = email.split("@")[0];
  const parts = name.split(/[._-]/).filter(Boolean);

  if (parts.length === 1) {
    return parts[0].slice(0, 2).toUpperCase();
  }

  return parts
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join("");
}

export default function Topbar({
  title = "Mission Control",
  subtitle = "Supervisión inteligente de comunicaciones y tareas",
  accountEmail,
  connected = false,
  loading = false,
  searchValue = "",
  onSearchChange,
  onRefresh,
  onMenuOpen,
}: TopbarProps) {
  return (
    <header className="quantum-topbar">
      <div className="quantum-topbar-heading">
        <button
          type="button"
          className="quantum-menu-button"
          aria-label="Abrir navegación"
          onClick={onMenuOpen}
        >
          <Menu size={21} />
        </button>

        <div>
          <div className="quantum-page-context">
            <span className="quantum-context-dot" />
            HMS AI COMMAND CENTER
          </div>
          <h1>{title}</h1>
          <p>{subtitle}</p>
        </div>
      </div>

      <div className="quantum-topbar-tools">
        <label className="quantum-search">
          <Search size={17} aria-hidden="true" />
          <input
            type="search"
            value={searchValue}
            placeholder="Buscar correos, remitentes o tareas…"
            aria-label="Buscar"
            onChange={(event) => onSearchChange?.(event.target.value)}
          />
          <kbd>⌘ K</kbd>
        </label>

        <div
          className={clsx(
            "quantum-connection-pill",
            connected
              ? "quantum-connection-pill-online"
              : "quantum-connection-pill-offline",
          )}
        >
          <Wifi size={15} />
          <span>{connected ? "Conectado" : "Sin conexión"}</span>
        </div>

        <div className="quantum-ai-pill">
          <Bot size={16} />
          <span>IA activa</span>
        </div>

        <button
          type="button"
          className="quantum-icon-button"
          aria-label="Sincronizar"
          title="Sincronizar"
          disabled={loading}
          onClick={onRefresh}
        >
          <RefreshCw
            size={18}
            className={loading ? "quantum-spin" : undefined}
          />
        </button>

        <button
          type="button"
          className="quantum-icon-button quantum-notification-button"
          aria-label="Notificaciones"
        >
          <Bell size={18} />
          <span className="quantum-notification-dot" />
        </button>

        <button type="button" className="quantum-profile">
          <span className="quantum-profile-avatar">
            {getInitials(accountEmail)}
          </span>
          <span className="quantum-profile-copy">
            <strong>Héctor Salcido</strong>
            <small>{accountEmail ?? "Administrador"}</small>
          </span>
        </button>
      </div>
    </header>
  );
}
