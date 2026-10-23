"use client";

import { useEffect, useState } from "react";

import { hmsJson } from "@/lib/hmsApi";
import type { HealthPayload } from "@/lib/adminHealth";
import { SIN_DATO, dbUsage, mailboxRows, providerSummary, showValue, type MailboxIn } from "@/lib/adminControl";

function when(iso: string | null): string {
  if (!iso) return SIN_DATO;
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? SIN_DATO : d.toLocaleString("es-MX", { timeZone: "America/Mexico_City", dateStyle: "medium", timeStyle: "short" });
}

/** Sección Buzones: proveedor, estado y uso de Supabase. Sin correo, IDs ni hashes. */
export function MailboxesPanel({ users }: { users: Array<{ mailboxes?: MailboxIn[] | null }> }) {
  const [health, setHealth] = useState<HealthPayload | null>(null);
  useEffect(() => {
    hmsJson<HealthPayload>("/api/hms/admin/health").then(setHealth).catch(() => undefined);
  }, []);
  const rows = mailboxRows(users);
  const db = dbUsage(health);
  return (
    <section className="dx-admin__section">
      <header className="dx-admin__section-head">
        <h2>Buzones</h2>
        <p>Proveedor y estado de cada buzón conectado. Por privacidad no se muestran direcciones ni identificadores.</p>
      </header>
      <div className="dx-cc__kpis">
        <article className="dx-cc__card"><span className="dx-cc__label">Buzones</span><strong className="dx-cc__value">{showValue(rows.length)}</strong><span className="dx-cc__hint">1 por dirección</span></article>
        {providerSummary(rows).slice(0, 2).map(([p, n]) => (
          <article key={p} className="dx-cc__card"><span className="dx-cc__label">{p}</span><strong className="dx-cc__value">{showValue(n)}</strong><span className="dx-cc__hint">buzones</span></article>
        ))}
        <article className="dx-cc__card">
          <span className="dx-cc__label">Uso de Supabase</span>
          <strong className={db ? "dx-cc__value" : "dx-cc__value is-empty"}>{db ? `${db.usedMb} MB` : SIN_DATO}</strong>
          <span className="dx-cc__hint">{db ? `de ${db.limitMb} MB · ${db.pct} %` : "Sin evaluación"}</span>
          <div className="dx-cc__bar" aria-hidden><i style={{ width: `${Math.min(100, db?.pct ?? 0)}%` }} /></div>
        </article>
      </div>
      <div className="dx-admin__table-wrap">
        <table className="dx-admin__table">
          <thead><tr><th>Buzón</th><th>Proveedor</th><th>Estado</th><th>Última sincronización</th><th>Correos guardados</th></tr></thead>
          <tbody>
            {rows.length === 0 && <tr><td colSpan={5}>No hay buzones conectados.</td></tr>}
            {rows.map((r) => (
              <tr key={r.n}>
                <td>Buzón {r.n}</td><td>{r.provider}</td>
                <td><span className={`dx-cc__pill is-${r.tone}`}>{r.status}</span></td>
                <td>{when(r.lastSync)}</td><td>{showValue(r.messages)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
