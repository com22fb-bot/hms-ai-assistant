"use client";

import { useMemo, useState } from "react";

import { NucleoApp } from "@/components/nucleo/NucleoApp";
import { buildLifeItems, type InboxCase, type InboxThread } from "@/lib/nucleo/lifeAreas";
import type { NucleoTheme } from "@/lib/nucleo/prefs";

const NOW = "2026-10-05T14:42:00.000Z";

const CASES: InboxCase[] = [
  {
    id: "ua1547",
    title: "Haz check-in de tu vuelo United a Denver",
    case_type: "general",
    status: "in_progress",
    priority: "high",
    summary: "UA 1547 · mié 7 oct · EWR → DEN. Haz check-in en la app de United en las próximas 24 h.",
    requested_action: "Haz check-in en la app de United en las próximas 24 h.",
    requester_name: "United",
    requester_email: "united@united.com",
    last_activity_at: NOW,
    due_at: "2026-10-06T15:05:00.000Z",
    source_count: 1,
  },
  {
    id: "coned",
    title: "Tu factura de Con Edison de $84.20 vence el jueves",
    case_type: "invoice",
    status: "new",
    priority: "high",
    summary: "Luz · vence 8 oct · +$6.10 vs. septiembre. Paga en coned.com antes del 8 oct.",
    requested_action: "Paga en coned.com antes del 8 oct.",
    requester_name: "Con Edison",
    requester_email: "billing@coned.com",
    last_activity_at: "2026-10-05T12:10:00.000Z",
    due_at: "2026-10-08T23:00:00.000Z",
    source_count: 1,
  },
  {
    id: "netflix",
    title: "Netflix sube a $17.99 al mes",
    case_type: "general",
    status: "new",
    priority: "normal",
    summary: "Antes $15.49 · se renueva 12 oct · +$30 al año. Mantén, cambia de plan o cancela antes de renovar.",
    requested_action: "Decide antes del 12 oct.",
    requester_name: "Netflix",
    requester_email: "info@netflix.com",
    last_activity_at: "2026-10-04T18:00:00.000Z",
    due_at: "2026-10-12T16:00:00.000Z",
    source_count: 1,
  },
  {
    id: "amazon",
    title: "Tu pedido de Amazon fue enviado y llega el jueves",
    case_type: "general",
    status: "in_progress",
    priority: "normal",
    summary: "Pedido Amazon. Llega jue 8 oct. $58.47.",
    requested_action: null,
    requester_name: "Amazon",
    requester_email: "shipment-tracking@amazon.com",
    last_activity_at: "2026-10-05T14:42:00.000Z",
    due_at: null,
    source_count: 2,
  },
  {
    id: "chase",
    title: "El cargo de $129.99 en Chase coincide con tu recibo de Best Buy",
    case_type: "payment",
    status: "resolved",
    priority: "normal",
    summary: "Cargo Chase $129.99 conciliado con el recibo de Best Buy.",
    requested_action: null,
    requester_name: "Chase",
    requester_email: "no-reply@chase.com",
    last_activity_at: "2026-10-05T13:15:00.000Z",
    due_at: null,
    source_count: 2,
  },
  {
    id: "kaiser",
    title: "Recordatorio de tu cita en Kaiser Permanente el viernes",
    case_type: "meeting",
    status: "new",
    priority: "normal",
    summary: "Salud · Kaiser Permanente · vie 9 oct · 10:30 a.m.",
    requested_action: "Confirma la cita si sigue en pie.",
    requester_name: "Kaiser Permanente",
    requester_email: "appointments@kp.org",
    last_activity_at: "2026-10-04T12:20:00.000Z",
    due_at: "2026-10-09T16:30:00.000Z",
    source_count: 1,
  },
  {
    id: "google",
    title: "Nuevo inicio de sesión en tu cuenta de Google desde una Mac",
    case_type: "general",
    status: "new",
    priority: "high",
    summary: "Seguridad · Google. ¿Fuiste tú?",
    requested_action: "Revisa el inicio de sesión.",
    requester_name: "Google",
    requester_email: "no-reply@accounts.google.com",
    last_activity_at: "2026-10-04T15:03:00.000Z",
    due_at: null,
    source_count: 1,
  },
  {
    id: "lincoln",
    title: "El día de fotos en Lincoln Elementary cambió al 14 de octubre",
    case_type: "general",
    status: "new",
    priority: "normal",
    summary: "Hogar y familia · Lincoln Elementary · mié 14 oct.",
    requested_action: null,
    requester_name: "Lincoln Elementary",
    requester_email: "office@lincoln.example",
    last_activity_at: "2026-10-03T17:10:00.000Z",
    due_at: "2026-10-14T15:00:00.000Z",
    source_count: 1,
  },
];

const THREADS: InboxThread[] = [
  {
    latest_message_id: "delta",
    subject: "Tu vuelo Delta cambió de horario",
    summary: "Viajes · Delta · nuevo horario 7 oct.",
    sender: "Delta",
    latest_received_at: "2026-10-05T16:00:00.000Z",
    triage_category: "action_required",
  },
];

const THEMES: NucleoTheme[] = ["nucleo", "nucleo-claro", "command", "day"];

export function NucleoPreviewClient() {
  const items = useMemo(() => buildLifeItems(CASES, THREADS), []);
  const [theme, setTheme] = useState<NucleoTheme>("nucleo");
  const [screen, setScreen] = useState<"today" | "settings" | "onboarding">("today");

  return (
    <>
      <div className="nx-preview-bar">
        <strong>Vista de diseño · datos de ejemplo</strong>
        {THEMES.map((item) => (
          <button key={item} type="button" onClick={() => setTheme(item)} aria-pressed={theme === item}>
            {item}
          </button>
        ))}
        <button type="button" onClick={() => setScreen("today")}>Hoy</button>
        <button type="button" onClick={() => setScreen("settings")}>Ajustes</button>
        <button type="button" onClick={() => setScreen("onboarding")}>Avisos</button>
      </div>
      <NucleoApp
        key={`${theme}-${screen}`}
        userId="preview"
        email="maya@example.com"
        name="Maya Calder"
        connected
        mailboxEmail="maya@outlook.com"
        provider="microsoft"
        syncing={false}
        yahooPending={false}
        gmailPending={false}
        showPlan={false}
        planBusy={false}
        planNotice={null}
        importPending={false}
        onSignOut={() => undefined}
        onConnect={() => undefined}
        onRefreshMail={() => undefined}
        onOpenInbox={() => undefined}
        onOpenImport={() => undefined}
        onPlan={() => undefined}
        preview
        previewScreen={screen}
        previewTheme={theme}
        fixtureItems={items}
      />
    </>
  );
}
