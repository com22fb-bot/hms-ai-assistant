import { hmsJson } from "@/lib/hmsApi";

export type PushDevice = {
  id: string;
  endpoint?: string;
  device_label: string | null;
  user_agent: string | null;
  is_active: boolean;
  platform?: string | null;
  locale?: string | null;
  last_success_at?: string | null;
  last_error?: string | null;
};

export type PushStatus = {
  configured: boolean;
  public_key: string;
  sender_available?: boolean;
  devices: number;
  unread: number;
  subscriptions: PushDevice[];
};

export type AppNotification = {
  id: string;
  title: string;
  body: string;
  notification_type?: string;
  created_at: string;
  read_at: string | null;
};

function urlBase64ToUint8Array(value: string): Uint8Array {
  const padding = "=".repeat((4 - (value.length % 4)) % 4);
  const base64 = (value + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = window.atob(base64);
  return Uint8Array.from([...raw].map((char) => char.charCodeAt(0)));
}

export async function loadPushStatus(): Promise<{
  status: PushStatus;
  notifications: AppNotification[];
  endpoint: string | null;
}> {
  const [status, notificationData, endpoint] = await Promise.all([
    hmsJson<PushStatus>("/api/hms/push/status", { cache: "no-store" }),
    hmsJson<{ notifications: AppNotification[] }>(
      "/api/hms/push/notifications?limit=30",
      { cache: "no-store" },
    ),
    currentEndpoint(),
  ]);
  return {
    status,
    notifications: notificationData.notifications ?? [],
    endpoint,
  };
}

export async function currentEndpoint(): Promise<string | null> {
  if (!("serviceWorker" in navigator)) return null;
  const registration = await navigator.serviceWorker.getRegistration("/");
  const subscription = await registration?.pushManager.getSubscription();
  return subscription?.endpoint ?? null;
}

export async function enableWebPush(input: {
  deviceLabel: string;
  platform: string;
  locale: string;
}): Promise<{ endpoint: string; configured: boolean }> {
  if (!("serviceWorker" in navigator) || !("PushManager" in window) || !("Notification" in window)) {
    throw new Error("unsupported");
  }
  const permission = await Notification.requestPermission();
  if (permission !== "granted") {
    throw new Error(permission === "denied" ? "denied" : "dismissed");
  }
  const registration = await navigator.serviceWorker.register("/hms-sw.js", {
    scope: "/",
  });
  await navigator.serviceWorker.ready;
  const keyData = await hmsJson<{ configured: boolean; public_key: string }>(
    "/api/hms/push/vapid-public-key",
    { cache: "no-store" },
  );
  if (!keyData.configured || !keyData.public_key) {
    return { endpoint: "", configured: false };
  }
  const previous = await registration.pushManager.getSubscription();
  if (previous) {
    await previous.unsubscribe().catch(() => undefined);
  }
  const subscription = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(keyData.public_key) as BufferSource,
  });
  const json = subscription.toJSON();
  await hmsJson("/api/hms/push/subscriptions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      endpoint: subscription.endpoint,
      keys: {
        p256dh: json.keys?.p256dh,
        auth: json.keys?.auth,
      },
      device_label: input.deviceLabel,
      platform: input.platform,
      locale: input.locale,
    }),
  });
  return { endpoint: subscription.endpoint, configured: true };
}

export async function sendTestPush(input: {
  endpoint?: string | null;
  title: string;
  body: string;
  lang: string;
}): Promise<void> {
  await hmsJson("/api/hms/push/test", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      endpoint: input.endpoint || null,
      title: input.title,
      body: input.body,
      lang: input.lang,
    }),
  });
}

export async function deactivatePush(endpoint: string): Promise<void> {
  await hmsJson("/api/hms/push/subscriptions/deactivate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ endpoint }),
  });
}

export async function markPushRead(id: string): Promise<void> {
  await hmsJson(`/api/hms/push/notifications/${id}/read`, { method: "PATCH" });
}
