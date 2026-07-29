"use client";

import { ReactNode, useState } from "react";
import Sidebar, { NavigationItem } from "./Sidebar";
import Topbar from "./Topbar";

type AppShellProps = {
  children: ReactNode;
  activeItem?: NavigationItem;
  title?: string;
  subtitle?: string;
  accountEmail?: string | null;
  connected?: boolean;
  loading?: boolean;
  searchValue?: string;
  onSearchChange?: (value: string) => void;
  onRefresh?: () => void;
  onNavigate?: (item: NavigationItem) => void;
};

export default function AppShell({
  children,
  activeItem = "dashboard",
  title,
  subtitle,
  accountEmail,
  connected,
  loading,
  searchValue,
  onSearchChange,
  onRefresh,
  onNavigate,
}: AppShellProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div
      className={
        collapsed
          ? "quantum-app-shell quantum-app-shell-collapsed"
          : "quantum-app-shell"
      }
    >
      <Sidebar
        activeItem={activeItem}
        collapsed={collapsed}
        mobileOpen={mobileOpen}
        onCollapsedChange={setCollapsed}
        onMobileClose={() => setMobileOpen(false)}
        onNavigate={onNavigate}
      />

      <div className="quantum-workspace">
        <Topbar
          title={title}
          subtitle={subtitle}
          accountEmail={accountEmail}
          connected={connected}
          loading={loading}
          searchValue={searchValue}
          onSearchChange={onSearchChange}
          onRefresh={onRefresh}
          onMenuOpen={() => setMobileOpen(true)}
        />

        <main className="quantum-main">{children}</main>
      </div>
    </div>
  );
}
