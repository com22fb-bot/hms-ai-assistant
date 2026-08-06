"use client";

import {
  Bell,
  BellRing,
  CheckCircle2,
  LoaderCircle,
  MonitorSmartphone,
  Send,
  ShieldCheck,
  Smartphone,
  X,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { hmsJson } from "@/lib/hmsApi";


type PushStatus = {
  status: string;
  configured: boolean;
  public_key: string;
  sender_available: boolean;
  devices: number;
  unread: number;
  subscriptions: Array<{
    id: string;
    device_label: string | null;
    is_active: boolean;
    last_success_at: string | null;
    last_error: string | null;
  }>;
};

type HmsNotification = {
  id: string;
  title: string;
  body: string;
  notification_type: string;
  created_at: string;
  read_at: string | null;
};

function urlBase64ToUint8Array(value: string): Uint8Array {
  const padding = "=".repeat((4 - (value.length % 4)) % 4);
  const base64 = (value + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = window.atob(base64);
  return Uint8Array.from([...raw].map((char) => char.charCodeAt(0)));
}

function readableError(reason: unknown): string {
  return reason instanceof Error ? reason.message : "No fue posible configurar las notificaciones.";
}

function deviceLabel(): string {
  const ua = navigator.userAgent;
  if (/Android/i.test(ua)) return "Android";
  if (/iPhone|iPad|iPod/i.test(ua)) return "iPhone o iPad";
  if (/Windows/i.test(ua)) return "PC Windows";
  if (/Mac/i.test(ua)) return "Mac";
  return "Navegador web";
}

export function PushNotificationsPanel({ onClose }: { onClose: () => void }) {
  const [status, setStatus] = useState<PushStatus | null>(null);
  const [notifications, setNotifications] = useState<HmsNotification[]>([]);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const supported = typeof window !== "undefined"
    && "serviceWorker" in navigator
    && "PushManager" in window
    && "Notification" in window;

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [statusData, notificationData] = await Promise.all([
        hmsJson<PushStatus>("/api/hms/push/status", { cache: "no-store" }),
        hmsJson<{ notifications: HmsNotification[] }>("/api/hms/push/notifications?limit=30", { cache: "no-store" }),
      ]);
      setStatus(statusData);
      setNotifications(notificationData.notifications);
    } catch (reason) {
      setError(readableError(reason));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  async function enablePush() {
    setWorking(true);
    setError(null);
    setMessage(null);
    try {
      if (!supported) throw new Error("Este navegador no admite Web Push.");
      const permission = await Notification.requestPermission();
      if (permission !== "granted") throw new Error("El dispositivo no autorizó las notificaciones.");

      const registration = await navigator.serviceWorker.register("/hms-sw.js", { scope: "/" });
      await navigator.serviceWorker.ready;
      const keyData = await hmsJson<{ configured: boolean; public_key: string }>(
        "/api/hms/push/vapid-public-key",
        { cache: "no-store" },
      );
      if (!keyData.configured || !keyData.public_key) {
        throw new Error("El servidor push todavía no tiene llaves VAPID.");
      }

      let subscription = await registration.pushManager.getSubscription();
      if (!subscription) {
        subscription = await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey:
            urlBase64ToUint8Array(keyData.public_key).buffer as ArrayBuffer,
        });
      }
      const serialized = subscription.toJSON();
      if (!serialized.endpoint || !serialized.keys?.p256dh || !serialized.keys?.auth) {
        throw new Error("El navegador devolvió una suscripción incompleta.");
      }
      await hmsJson("/api/hms/push/subscriptions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          endpoint: serialized.endpoint,
          keys: serialized.keys,
          device_label: deviceLabel(),
        }),
      });
      setMessage("Notificaciones activadas en este dispositivo.");
      await load();
    } catch (reason) {
      setError(readableError(reason));
    } finally {
      setWorking(false);
    }
  }

  async function disablePush() {
    setWorking(true);
    setError(null);
    setMessage(null);
    try {
      const registration = await navigator.serviceWorker.getRegistration("/");
      const subscription = await registration?.pushManager.getSubscription();
      if (subscription) {
        await hmsJson("/api/hms/push/subscriptions/deactivate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ endpoint: subscription.endpoint }),
        });
        await subscription.unsubscribe();
      }
      setMessage("Notificaciones desactivadas en este dispositivo.");
      await load();
    } catch (reason) {
      setError(readableError(reason));
    } finally {
      setWorking(false);
    }
  }

  async function testPush() {
    setWorking(true);
    setError(null);
    setMessage(null);
    try {
      const result = await hmsJson<{ delivery?: { sent?: number } }>("/api/hms/push/test", { method: "POST" });
      const sent = Number(result.delivery?.sent || 0);
      setMessage(sent > 0 ? `Prueba enviada a ${sent} dispositivo(s).` : "La prueba quedó en el centro de avisos; no hay un dispositivo push activo.");
      await load();
    } catch (reason) {
      setError(readableError(reason));
    } finally {
      setWorking(false);
    }
  }

  async function markRead(id: string) {
    await hmsJson(`/api/hms/push/notifications/${id}/read`, { method: "PATCH" });
    await load();
  }

  return (
    <div className="hms-push-backdrop" role="dialog" aria-modal="true">
      <section className="hms-push-panel">
        <header>
          <div><span>AVISOS POR DISPOSITIVO</span><h2>Notificaciones push</h2><p>HMS avisa por favoritos, reglas y correos que requieren atención.</p></div>
          <button type="button" onClick={onClose} aria-label="Cerrar"><X size={22} /></button>
        </header>

        {loading ? <div className="hms-push-loading"><LoaderCircle className="app-spin" size={30} /> Consultando dispositivos...</div> : null}
        {error ? <div className="hms-push-error">{error}</div> : null}
        {message ? <div className="hms-push-success"><CheckCircle2 size={18} /> {message}</div> : null}

        {!loading ? (
          <>
            <section className="hms-push-status">
              <div><MonitorSmartphone size={25} /><span>Dispositivos activos</span><strong>{status?.devices ?? 0}</strong></div>
              <div><BellRing size={25} /><span>Avisos sin leer</span><strong>{status?.unread ?? 0}</strong></div>
              <div><ShieldCheck size={25} /><span>Servidor push</span><strong>{status?.configured && status?.sender_available ? "Listo" : "Pendiente"}</strong></div>
            </section>

            <div className="hms-push-actions">
              <button type="button" disabled={working || !supported} onClick={() => void enablePush()}><Smartphone size={19} /> Activar en este dispositivo</button>
              <button type="button" disabled={working || !(status?.devices)} onClick={() => void testPush()}><Send size={19} /> Enviar prueba</button>
              <button type="button" className="secondary" disabled={working} onClick={() => void disablePush()}><Bell size={19} /> Desactivar aquí</button>
            </div>

            {!supported ? <p className="hms-push-note">Este navegador no ofrece Push API. En iPhone/iPad se requiere instalar HMS en la pantalla de inicio y usar una versión compatible.</p> : null}

            <section className="hms-push-feed">
              <h3>Centro de avisos</h3>
              {notifications.length === 0 ? <p>No hay avisos todavía.</p> : notifications.map((item) => (
                <button key={item.id} type="button" className={item.read_at ? "is-read" : ""} onClick={() => void markRead(item.id)}>
                  <Bell size={18} />
                  <span><strong>{item.title}</strong><small>{item.body}</small></span>
                  <time>{new Intl.DateTimeFormat("es-MX", { dateStyle: "short", timeStyle: "short" }).format(new Date(item.created_at))}</time>
                </button>
              ))}
            </section>
          </>
        ) : null}
      </section>
    </div>
  );
}
