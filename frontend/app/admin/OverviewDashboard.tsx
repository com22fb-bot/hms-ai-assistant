"use client";

import { useEffect, useState } from "react";

import { hmsJson } from "@/lib/hmsApi";
import { supabase } from "@/lib/supabase";
import type { HealthPayload } from "@/lib/adminHealth";
import { ESTADO_LABEL, SIN_DATO, dbUsage, estadoOf, orderPedidos, showValue, type PedidoIn } from "@/lib/adminControl";

type Counts = { users: number | null; mailbox_connected: number | null; contact_unread?: number | null };

function when(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "—" : d.toLocaleString("es-MX", { timeZone: "America/Mexico_City", dateStyle: "medium", timeStyle: "short" });
}

export function OverviewDashboard({ counts, onOpen }: { counts: Counts; onOpen: (tab: "events" | "mailboxes" | "users" | "messages") => void }) {
  const [health, setHealth] = useState<HealthPayload | null>(null);
  const [pedidos, setPedidos] = useState<Array<PedidoIn & { id: string }> | null>(null);
  const [pedErr, setPedErr] = useState(false);

  useEffect(() => {
    let alive = true;
    hmsJson<HealthPayload>("/api/hms/admin/health").then((d) => alive && setHealth(d)).catch(() => undefined);
    supabase.from("admin_events").select("id,title,occurred_at,status,meta").order("occurred_at", { ascending: false }).limit(300)
      .then(({ data, error }) => {
        if (!alive) return;
        if (error) setPedErr(true);
        else setPedidos(orderPedidos((data ?? []) as Array<PedidoIn & { id: string }>, 6));
      });
    return () => { alive = false; };
  }, []);

  const db = dbUsage(health);
  const cards: Array<{ label: string; value: string; hint: string; tab?: "users" | "mailboxes" | "messages" }> = [
    { label: "Usuarios", value: showValue(counts.users), hint: "Cuentas Donexto", tab: "users" },
    { label: "Buzones conectados", value: showValue(counts.mailbox_connected), hint: "1 por dirección", tab: "mailboxes" },
    { label: "Uso de base de datos", value: db ? `${db.usedMb} MB` : SIN_DATO, hint: db ? `de ${db.limitMb} MB · ${db.pct} %` : "Sin evaluación de /admin/health" },
    { label: "Mensajes por atender", value: showValue(counts.contact_unread), hint: "Formulario de contacto", tab: "messages" },
  ];

  return (
    <>
      <div className="dx-cc__kpis">
        {cards.map((c) => (
          <article key={c.label} className="dx-cc__card">
            <span className="dx-cc__label">{c.label}</span>
            <strong className={c.value === SIN_DATO ? "dx-cc__value is-empty" : "dx-cc__value"}>{c.value}</strong>
            <span className="dx-cc__hint">{c.hint}</span>
          </article>
        ))}
      </div>
      <div className="dx-cc__grid">
        <section className="dx-cc__card">
          <h3 className="dx-cc__head">
            Bitácora · pedidos y cambios
            <button type="button" className="dx-cc__link" onClick={() => onOpen("events")}>Click para ver todo →</button>
          </h3>
          {pedErr && <p className="dx-cc__hint">No se pudo cargar la Bitácora.</p>}
          {!pedErr && pedidos === null && <p className="dx-cc__hint">Cargando…</p>}
          {pedidos?.length === 0 && <p className="dx-cc__hint">Sin pedidos registrados.</p>}
          {pedidos?.map((p) => {
            const st = estadoOf(p);
            return (
              <div key={p.id} className="dx-cc__row">
                <div><div>{p.title}</div><div className="dx-cc__hint">{when(p.occurred_at)} (CDMX)</div></div>
                <span className={`dx-cc__pill is-${st}`}>{ESTADO_LABEL[st]}</span>
              </div>
            );
          })}
        </section>
        <section className="dx-cc__card">
          <h3 className="dx-cc__head">
            Buzones
            <button type="button" className="dx-cc__link" onClick={() => onOpen("mailboxes")}>Click para gestionar →</button>
          </h3>
          <p className="dx-cc__hint">Conectados: {showValue(counts.mailbox_connected)}</p>
          <p className="dx-cc__hint">Almacenamiento Supabase: {db ? `${db.usedMb} de ${db.limitMb} MB` : SIN_DATO}</p>
          <div className="dx-cc__bar" aria-hidden><i style={{ width: `${Math.min(100, db?.pct ?? 0)}%` }} /></div>
        </section>
      </div>
    </>
  );
}
