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

import ThemeSelector from "@/components/theme/ThemeSelector";

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

  return email
    .split("@")[0]
    .split(/[._-]/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join("")
    .slice(0, 2);
}

export default function Topbar({
  title = "Donexto",
  subtitle = "Cargos, pedidos, seguridad y familia",
  accountEmail,
  connected = false,
  loading = false,
  searchValue = "",
  onSearchChange,
  onRefresh,
  onMenuOpen,
}: TopbarProps) {
  return (
    <header className="premium-header">
      <div className="premium-header-main">
        <button
          type="button"
          className="quantum-menu-button"
          aria-label="Abrir navegación"
          onClick={onMenuOpen}
        >
          <Menu size={21} />
        </button>

        <div className="premium-header-title">
          <span>Donexto · Do Next To…</span>
          <h1>{title}</h1>
          <p>{subtitle}</p>
        </div>

        <label className="premium-header-search">
          <Search size={17} />
          <input
            type="search"
            value={searchValue}
            placeholder="Buscar casos, personas o tareas"
            aria-label="Buscar"
            onChange={(event) =>
              onSearchChange?.(event.target.value)
            }
          />
        </label>
      </div>

      <div className="premium-header-actions">
        <div
          className={clsx(
            "premium-status-pill",
            connected ? "online" : "offline",
          )}
        >
          <Wifi size={15} />
          {connected ? "Conectado" : "Sin conexión"}
        </div>

        <div className="premium-ai-pill">
          <Bot size={16} />
          IA activa
        </div>

        <ThemeSelector />

        <button
          type="button"
          className="premium-icon-button"
          aria-label="Actualizar"
          disabled={loading}
          onClick={onRefresh}
        >
          <RefreshCw
            size={18}
            className={
              loading ? "quantum-spin" : undefined
            }
          />
        </button>

        <button
          type="button"
          className="premium-icon-button"
          aria-label="Notificaciones"
        >
          <Bell size={18} />
        </button>

        <div className="premium-user">
          <span>{getInitials(accountEmail)}</span>
          <div>
            <strong>Héctor Salcido</strong>
            <small>
              {accountEmail ?? "Administrador"}
            </small>
          </div>
        </div>
      </div>
    </header>
  );
}
