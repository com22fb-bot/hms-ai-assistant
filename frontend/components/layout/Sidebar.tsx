"use client";

import {
  Activity,
  BrainCircuit,
  BriefcaseBusiness,
  ChevronLeft,
  ChevronRight,
  LayoutDashboard,
  ListTodo,
  Settings,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import clsx from "clsx";

export type NavigationItem =
  | "dashboard"
  | "cases"
  | "ai"
  | "tasks"
  | "activity"
  | "settings";

type SidebarProps = {
  activeItem?: NavigationItem;
  collapsed: boolean;
  mobileOpen: boolean;
  onCollapsedChange: (collapsed: boolean) => void;
  onMobileClose: () => void;
  onNavigate?: (item: NavigationItem) => void;
};

const navigation = [
  {
    id: "dashboard" as const,
    label: "Mission Control",
    icon: LayoutDashboard,
  },
  {
    id: "cases" as const,
    label: "Casos Inteligentes",
    icon: BriefcaseBusiness,
    badge: "AI",
  },
  {
    id: "ai" as const,
    label: "Inteligencia IA",
    icon: BrainCircuit,
  },
  {
    id: "tasks" as const,
    label: "Tareas",
    icon: ListTodo,
  },
  {
    id: "activity" as const,
    label: "Actividad",
    icon: Activity,
  },
];

export default function Sidebar({
  activeItem = "dashboard",
  collapsed,
  mobileOpen,
  onCollapsedChange,
  onMobileClose,
  onNavigate,
}: SidebarProps) {
  const handleNavigation = (item: NavigationItem) => {
    onNavigate?.(item);
    onMobileClose();
  };

  return (
    <>
      <button
        type="button"
        className={clsx(
          "quantum-sidebar-overlay",
          mobileOpen && "quantum-sidebar-overlay-visible",
        )}
        aria-label="Cerrar navegación"
        onClick={onMobileClose}
      />

      <aside
        className={clsx(
          "quantum-sidebar",
          collapsed && "quantum-sidebar-collapsed",
          mobileOpen && "quantum-sidebar-mobile-open",
        )}
      >
        <div className="quantum-sidebar-header">
          <div className="quantum-brand">
            <div className="quantum-brand-mark" aria-hidden="true">
              <Sparkles size={21} strokeWidth={2.2} />
            </div>

            <div className="quantum-brand-copy">
              <strong>Donexto</strong>
              <span>Do Next To…</span>
            </div>
          </div>

          <button
            type="button"
            className="quantum-mobile-close"
            aria-label="Cerrar menú"
            onClick={onMobileClose}
          >
            <X size={20} />
          </button>
        </div>

        <div className="quantum-sidebar-status">
          <span className="quantum-status-orb" />
          <div>
            <strong>Case Engine activo</strong>
            <span>Eventos, riesgos y evidencias</span>
          </div>
        </div>

        <nav className="quantum-navigation" aria-label="Navegación principal">
          <span className="quantum-navigation-label">
            CENTRO DE CONTROL
          </span>

          {navigation.map((item) => {
            const Icon = item.icon;
            const active = activeItem === item.id;

            return (
              <button
                key={item.id}
                type="button"
                className={clsx(
                  "quantum-nav-item",
                  active && "quantum-nav-item-active",
                )}
                title={collapsed ? item.label : undefined}
                aria-current={active ? "page" : undefined}
                onClick={() => handleNavigation(item.id)}
              >
                <span className="quantum-nav-icon">
                  <Icon size={19} strokeWidth={active ? 2.4 : 1.9} />
                </span>

                <span className="quantum-nav-label">
                  {item.label}
                </span>

                {item.badge ? (
                  <span className="quantum-nav-badge">
                    {item.badge}
                  </span>
                ) : null}
              </button>
            );
          })}
        </nav>

        <div className="quantum-sidebar-spacer" />

        <div className="quantum-security-card">
          <ShieldCheck size={19} />
          <div>
            <strong>Protección activa</strong>
            <span>Acciones auditables</span>
          </div>
        </div>

        <button
          type="button"
          className={clsx(
            "quantum-nav-item",
            activeItem === "settings" &&
              "quantum-nav-item-active",
          )}
          title={collapsed ? "Configuración" : undefined}
          onClick={() => handleNavigation("settings")}
        >
          <span className="quantum-nav-icon">
            <Settings size={19} />
          </span>
          <span className="quantum-nav-label">
            Configuración
          </span>
        </button>

        <div className="quantum-sidebar-footer">
          <div className="quantum-version">
            <span>Donexto Cases</span>
            <strong>v0.4.3</strong>
          </div>

          <button
            type="button"
            className="quantum-collapse-button"
            aria-label={
              collapsed
                ? "Expandir menú"
                : "Contraer menú"
            }
            onClick={() =>
              onCollapsedChange(!collapsed)
            }
          >
            {collapsed ? (
              <ChevronRight size={18} />
            ) : (
              <ChevronLeft size={18} />
            )}
          </button>
        </div>
      </aside>
    </>
  );
}
