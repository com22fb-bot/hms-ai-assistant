export type DevicePlatform =
  | "ios"
  | "android"
  | "macos"
  | "windows"
  | "linux"
  | "desktop";

export type DeviceProfile = {
  platform: DevicePlatform;
  ios: boolean;
  android: boolean;
  safari: boolean;
  standalone: boolean;
  pushSupported: boolean;
  notificationPermission: NotificationPermission | "unsupported";
  label: string;
};

export function detectDevice(userAgent?: string): DeviceProfile {
  const ua =
    userAgent ??
    (typeof navigator === "undefined" ? "" : navigator.userAgent);
  const touchMac =
    typeof navigator !== "undefined" &&
    navigator.platform === "MacIntel" &&
    navigator.maxTouchPoints > 1;
  const ios = /iPad|iPhone|iPod/i.test(ua) || touchMac;
  const android = /Android/i.test(ua);
  const safari =
    /Safari/i.test(ua) && !/CriOS|FxiOS|EdgiOS|OPiOS|Chrome|Chromium/i.test(ua);
  const standalone =
    typeof window !== "undefined" &&
    (window.matchMedia("(display-mode: standalone)").matches ||
      Boolean((navigator as Navigator & { standalone?: boolean }).standalone));
  const pushSupported =
    typeof window !== "undefined" &&
    "serviceWorker" in navigator &&
    "PushManager" in window &&
    "Notification" in window &&
    (!ios || standalone);

  let platform: DevicePlatform = "desktop";
  if (ios) platform = "ios";
  else if (android) platform = "android";
  else if (/Mac OS X|Macintosh/i.test(ua)) platform = "macos";
  else if (/Windows/i.test(ua)) platform = "windows";
  else if (/Linux/i.test(ua)) platform = "linux";

  const permission: DeviceProfile["notificationPermission"] =
    typeof Notification === "undefined" ? "unsupported" : Notification.permission;

  const label = deviceLabel(ua, platform);
  return {
    platform,
    ios,
    android,
    safari: ios ? safari || !/CriOS|FxiOS|EdgiOS/.test(ua) : safari,
    standalone,
    pushSupported,
    notificationPermission: permission,
    label,
  };
}

export function deviceLabel(ua: string, platform: DevicePlatform): string {
  if (platform === "ios") return /iPad/i.test(ua) ? "iPad" : "iPhone";
  if (platform === "android") {
    const version = ua.match(/Android\s([\d.]+)/i);
    return version ? `Android ${version[1]}` : "Android";
  }
  if (platform === "windows") return "Windows";
  if (platform === "macos") return "Mac";
  if (platform === "linux") return "Linux";
  return "Navegador";
}

export function browserName(ua: string): string {
  if (/Edg\//i.test(ua)) return "Edge";
  if (/Chrome|CriOS/i.test(ua)) return "Chrome";
  if (/Firefox|FxiOS/i.test(ua)) return "Firefox";
  if (/Safari/i.test(ua)) return "Safari";
  return "Navegador";
}
