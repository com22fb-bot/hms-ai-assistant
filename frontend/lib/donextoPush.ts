import { hmsJson } from "@/lib/hmsApi";

const ONBOARD_KEY = "donexto_push_onboarded";

export function donextoPushSupported(): boolean {
  return (
    typeof window !== "undefined" &&
    "serviceWorker" in navigator &&
    "PushManager" in window &&
    "Notification" in window
  );
}

export function deviceLabel(): string {
  const ua = navigator.userAgent;
  if (/Android/i.test(ua)) {
    const match = ua.match(/Android\s([\d.]+)/i);
    return match ? `Android ${match[1]}` : "Android";
  }
  if (/iPhone|iPad|iPod/i.test(ua)) {
    return "iPhone o iPad";
  }
  if (/Windows/i.test(ua)) {
    return "PC Windows";
  }
  if (/Mac/i.test(ua)) {
    return "Mac";
  }
  return "Navegador web";
}

function urlBase64ToUint8Array(value: string): Uint8Array {
  const padding = "=".repeat((4 - (value.length % 4)) % 4);
  const base64 = (value + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = window.atob(base64);
  return Uint8Array.from([...raw].map((char) => char.charCodeAt(0)));
}

function onboardStorageKey(profileId: string): string {
  return `${ONBOARD_KEY}:${profileId}`;
}

export function wasPushOnboarded(profileId: string): boolean {
  try {
    return localStorage.getItem(onboardStorageKey(profileId)) === "1";
  } catch {
    return false;
  }
}

export function markPushOnboarded(profileId: string) {
  try {
    localStorage.setItem(onboardStorageKey(profileId), "1");
  } catch {
    // ignore
  }
}

export async function currentPushEndpoint(): Promise<string | null> {
  const registration = await navigator.serviceWorker.getRegistration("/");
  const subscription = await registration?.pushManager.getSubscription();
  return subscription?.endpoint ?? null;
}

export function openOsNotificationSettings() {
  const ua = navigator.userAgent;
  if (/Windows/i.test(ua)) {
    window.open("ms-settings:notifications", "_self");
    return;
  }
  if (/Android/i.test(ua)) {
    window.open("https://support.google.com/chrome/answer/3220216", "_blank");
    return;
  }
  window.open(
    "https://support.apple.com/es-mx/guide/iphone/iph0c0d3b7c6/ios",
    "_blank",
  );
}

export type EnablePushResult = {
  permission: NotificationPermission | "unsupported";
  subscribed: boolean;
  tested: boolean;
  device: string;
};

export async function enableThisDeviceAndTest(): Promise<EnablePushResult> {
  if (!donextoPushSupported()) {
    return {
      permission: "unsupported",
      subscribed: false,
      tested: false,
      device: deviceLabel(),
    };
  }

  const permission = await Notification.requestPermission();
  if (permission !== "granted") {
    return {
      permission,
      subscribed: false,
      tested: false,
      device: deviceLabel(),
    };
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
    throw new Error("El servidor push todavía no tiene llaves VAPID.");
  }

  const previous = await registration.pushManager.getSubscription();
  if (previous) {
    await previous.unsubscribe().catch(() => undefined);
  }

  const subscription = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(keyData.public_key)
      .buffer as ArrayBuffer,
  });
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

  let tested = false;
  try {
    const result = await hmsJson<{
      delivery?: { sent?: number };
    }>("/api/hms/push/test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ endpoint: serialized.endpoint }),
    });
    tested = Number(result.delivery?.sent || 0) > 0;
  } catch {
    tested = false;
  }

  return {
    permission: "granted",
    subscribed: true,
    tested,
    device: deviceLabel(),
  };
}

export async function sendTestToThisDevice(): Promise<{ sent: number; failed: number }> {
  const endpoint = await currentPushEndpoint();
  if (!endpoint) {
    throw new Error("Este dispositivo aún no tiene avisos autorizados.");
  }
  const result = await hmsJson<{
    delivery?: { sent?: number; failed?: number };
  }>("/api/hms/push/test", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ endpoint }),
  });
  return {
    sent: Number(result.delivery?.sent || 0),
    failed: Number(result.delivery?.failed || 0),
  };
}

export async function disableThisDevice(): Promise<void> {
  const registration = await navigator.serviceWorker.getRegistration("/");
  const subscription = await registration?.pushManager.getSubscription();
  if (!subscription) {
    return;
  }
  await hmsJson("/api/hms/push/subscriptions/deactivate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ endpoint: subscription.endpoint }),
  });
  await subscription.unsubscribe();
}
