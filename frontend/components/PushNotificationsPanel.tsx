"use client";

import {
  Bell,
  BellRing,
  CheckCircle2,
  LoaderCircle,
  MonitorSmartphone,
  Send,
  Settings,
  ShieldCheck,
  Smartphone,
  X,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { hmsJson } from "@/lib/hmsApi";
import {
  currentPushEndpoint,
  deviceLabel,
  disableThisDevice,
  donextoPushSupported,
  enableThisDeviceAndTest,
  openOsNotificationSettings,
  sendTestToThisDevice,
} from "@/lib/donextoPush";

type PushSubscriptionRow = {
  id: string;
  device_label: string | null;
  is_active: boolean;
  last_success_at: string | null;
  last_error: string | null;
  endpoint?: string;
};

type PushStatus = {
  status: string;
  configured: boolean;
  public_key: string;
  sender_available: boolean;
  devices: number;
  unread: number;
  subscriptions: PushSubscriptionRow[];
};

type HmsNotification = {
  id: string;
  title: string;
  body: string;
  notification_type: string;
  created_at: string;
  read_at: string | null;
};

function readableError(reason: unknown): string {
  return reason instanceof Error
    ? reason.message
    : "No fue posible configurar las notificaciones.";
}

export function PushNotificationsPanel({ onClose }: { onClose: () => void }) {
  const [status, setStatus] = useState<PushStatus | null>(null);
  const [notifications, setNotifications] = useState<HmsNotification[]>([]);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [localEndpoint, setLocalEndpoint] = useState<string | null>(null);

  const supported = donextoPushSupported();
  const permission =
    typeof Notification === "undefined" ? "unsupported" : Notification.permission;

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [statusData, notificationData, endpoint] = await Promise.all([
        hmsJson<PushStatus>("/api/hms/push/status", { cache: "no-store" }),
        hmsJson<{ notifications: HmsNotification[] }>(
          "/api/hms/push/notifications?limit=30",
          { cache: "no-store" },
        ),
        supported ? currentPushEndpoint() : Promise.resolve(null),
      ]);
      setStatus(statusData);
      setNotifications(notificationData.notifications);
      setLocalEndpoint(endpoint);
    } catch (reason) {
      setError(readableError(reason));
    } finally {
      setLoading(false);
    }
  }, [supported]);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  async function retryOsPermission() {
    setWorking(true);
    setError(null);
    setMessage(null);
    try {
      if (permission === "denied") {
        openOsNotificationSettings();
        setMessage(
          "Abre Ajustes del sistema, permite notificaciones a Donexto y vuelve aquí.",
        );
        return;
      }
      const result = await enableThisDeviceAndTest();
      if (result.permission === "denied") {
        openOsNotificationSettings();
        setMessage(
          "Este dispositivo bloqueó avisos. Actívalos en Ajustes y recarga Donexto.",
        );
        return;
      }
      setLocalEndpoint(await currentPushEndpoint());
      setMessage(
        result.tested
          ? `Listo en ${result.device}. Te enviamos un mensaje de prueba.`
          : `Avisos autorizados en ${result.device}.`,
      );
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
      const delivery = await sendTestToThisDevice();
      if (delivery.sent > 0) {
        setMessage(`Prueba enviada a ${deviceLabel()}.`);
      } else if (delivery.failed > 0) {
        setMessage(
          "El envío de prueba falló. Revisa permisos de notificaciones del sistema.",
        );
      } else {
        setMessage("Este dispositivo aún no tiene avisos autorizados.");
      }
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
      await disableThisDevice();
      setLocalEndpoint(null);
      setMessage("Avisos desactivados en este dispositivo.");
      await load();
    } catch (reason) {
      setError(readableError(reason));
    } finally {
      setWorking(false);
    }
  }

  async function markRead(id: string) {
    await hmsJson(`/api/hms/push/notifications/${id}/read`, {
      method: "PATCH",
    });
    await load();
  }

  const activeDevices = (status?.subscriptions || []).filter(
    (row) => row.is_active,
  );

  return (
    <div className="hms-push-backdrop" role="dialog" aria-modal="true">
      <section className="hms-push-panel">
        <header>
          <div>
            <span>CAPA DE ATENCIÓN</span>
            <h2>Avisos</h2>
            <p>
              Aquí lees lo que Donexto te avisó. El permiso de este Windows,
              celular o tablet se pide solo, como al instalar una app.
            </p>
          </div>
          <button type="button" onClick={onClose} aria-label="Cerrar">
            <X size={22} />
          </button>
        </header>

        {loading ? (
          <div className="hms-push-loading">
            <LoaderCircle className="app-spin" size={30} /> Cargando avisos…
          </div>
        ) : null}
        {error ? <div className="hms-push-error">{error}</div> : null}
        {message ? (
          <div className="hms-push-success">
            <CheckCircle2 size={18} /> {message}
          </div>
        ) : null}

        {!loading ? (
          <>
            <section className="hms-push-status">
              <div>
                <BellRing size={25} />
                <span>Sin leer</span>
                <strong>{status?.unread ?? 0}</strong>
              </div>
              <div>
                <MonitorSmartphone size={25} />
                <span>Equipos con aviso</span>
                <strong>{status?.devices ?? 0}</strong>
              </div>
              <div>
                <ShieldCheck size={25} />
                <span>Este dispositivo</span>
                <strong>
                  {localEndpoint
                    ? "Autorizado"
                    : permission === "denied"
                      ? "Bloqueado"
                      : "Pendiente"}
                </strong>
              </div>
            </section>

            <section className="hms-push-feed">
              <h3>Lo que te avisamos</h3>
              {notifications.length === 0 ? (
                <p>Todavía no hay avisos N1. Cuando algo te necesite, llega aquí y al dispositivo.</p>
              ) : (
                notifications.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    className={item.read_at ? "is-read" : ""}
                    onClick={() => void markRead(item.id)}
                  >
                    <Bell size={18} />
                    <span>
                      <strong>{item.title}</strong>
                      <small>{item.body}</small>
                    </span>
                    <time>
                      {new Intl.DateTimeFormat("es-MX", {
                        dateStyle: "short",
                        timeStyle: "short",
                      }).format(new Date(item.created_at))}
                    </time>
                  </button>
                ))
              )}
            </section>

            {activeDevices.length > 0 ? (
              <section className="hms-push-devices">
                <h3>Dónde te avisamos</h3>
                <ul>
                  {activeDevices.map((device) => {
                    const isThis =
                      Boolean(localEndpoint) &&
                      Boolean(device.endpoint) &&
                      device.endpoint === localEndpoint;
                    return (
                      <li key={device.id} className={isThis ? "is-current" : ""}>
                        <Smartphone size={18} />
                        <span>
                          <strong>
                            {device.device_label || "Dispositivo"}
                            {isThis ? " · este equipo" : ""}
                          </strong>
                          <small>
                            {device.last_error
                              ? `Error: ${device.last_error}`
                              : device.last_success_at
                                ? `Último envío OK: ${new Intl.DateTimeFormat("es-MX", {
                                    dateStyle: "short",
                                    timeStyle: "short",
                                  }).format(new Date(device.last_success_at))}`
                                : "Sin envíos aún"}
                          </small>
                        </span>
                      </li>
                    );
                  })}
                </ul>
              </section>
            ) : null}

            <div className="hms-push-actions">
              {permission === "denied" || !localEndpoint ? (
                <button
                  type="button"
                  disabled={working || !supported}
                  onClick={() => void retryOsPermission()}
                >
                  <Settings size={19} /> Abrir ajustes de notificaciones
                </button>
              ) : (
                <button
                  type="button"
                  disabled={working || !supported}
                  onClick={() => void testPush()}
                >
                  <Send size={19} /> Enviar prueba a este equipo
                </button>
              )}
              {localEndpoint ? (
                <button
                  type="button"
                  className="secondary"
                  disabled={working}
                  onClick={() => void disablePush()}
                >
                  <Bell size={19} /> Silenciar este equipo
                </button>
              ) : null}
            </div>

            {!supported ? (
              <p className="hms-push-note">
                En iPhone o iPad: Safari → Compartir → Añadir a pantalla de inicio.
                Luego Donexto pide el permiso del sistema solo.
              </p>
            ) : null}
          </>
        ) : null}
      </section>
    </div>
  );
}
