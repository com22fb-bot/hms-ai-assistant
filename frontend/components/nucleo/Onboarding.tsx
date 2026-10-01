"use client";

import { Bell, X } from "lucide-react";

import type { NxKey } from "@/lib/nucleo/copy";
import type { DeviceProfile } from "@/lib/nucleo/platform";

import { Nexto } from "@/components/nucleo/Nexto";

type T = (key: NxKey, vars?: Record<string, string | number>) => string;

export function Onboarding({
  t,
  device,
  platformLabel,
  busy,
  message,
  onEnable,
  onSkip,
  onClose,
}: {
  t: T;
  device: DeviceProfile;
  platformLabel: string;
  busy: boolean;
  message: string | null;
  onEnable: () => void;
  onSkip: () => void;
  onClose: () => void;
}) {
  const steps =
    device.platform === "ios"
      ? `${t("iosInstallTitle")}\n${t("iosInstallSteps")}\n\n${t("iosSettingsSteps")}`
      : device.platform === "android"
        ? t("androidSteps")
        : t("desktopSteps");

  return (
    <div className="onboard" role="dialog" aria-modal="true" aria-labelledby="onboard-title">
      <section className="card onboard-card">
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
          <Nexto pose="explaining" className="bot" label="Nexto" />
          <button type="button" className="icon-btn" aria-label={t("close")} onClick={onClose}>
            <X className="i" />
          </button>
        </div>
        <p className="eyebrow">{t("onboardKicker")}</p>
        <h2 id="onboard-title">{t("onboardTitle")}</h2>
        <p>{t("onboardBody")}</p>
        <p>
          <b>{t("onboardingPlatform", { platform: platformLabel })}</b>
          {" · "}
          {device.standalone ? t("installed") : t("notInstalled")}
        </p>
        <div className="steps">{steps}</div>
        {message ? <p className="error-line" role="status">{message}</p> : null}
        <div className="onboard-actions">
          <button type="button" className="btn primary" disabled={busy} onClick={onEnable}>
            <Bell className="i" />
            {busy ? t("testing") : t("allowAndTest")}
          </button>
          <button type="button" className="btn" onClick={onSkip}>
            {t("skip")}
          </button>
        </div>
      </section>
    </div>
  );
}
