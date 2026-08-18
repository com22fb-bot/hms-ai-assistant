"use client";

import { useEffect, useRef, useState } from "react";

import {
  donextoPushSupported,
  enableThisDeviceAndTest,
  markPushOnboarded,
  wasPushOnboarded,
} from "@/lib/donextoPush";

export type PushOnboardNotice = {
  kind: "ok" | "denied" | "error";
  text: string;
} | null;

/**
 * Como instalar una app en el celular: al entrar a Donexto en este
 * dispositivo, el SO pide permiso de notificaciones y se envía un aviso de prueba.
 * Avisos no es el interruptor de dispositivos.
 */
export function useDonextoPushOnboarding(options: {
  ready: boolean;
  profileId: string;
}): PushOnboardNotice {
  const { ready, profileId } = options;
  const started = useRef(false);
  const [notice, setNotice] = useState<PushOnboardNotice>(null);

  useEffect(() => {
    if (!ready || !profileId || started.current) {
      return;
    }
    if (!donextoPushSupported()) {
      return;
    }
    if (wasPushOnboarded(profileId) && Notification.permission === "granted") {
      return;
    }
    started.current = true;

    const timer = window.setTimeout(() => {
      void (async () => {
        try {
          const result = await enableThisDeviceAndTest();
          markPushOnboarded(profileId);
          if (result.permission === "granted" && result.subscribed) {
            setNotice({
              kind: "ok",
              text: result.tested
                ? `Avisos listos en ${result.device}. Te enviamos un mensaje de prueba.`
                : `Avisos autorizados en ${result.device}.`,
            });
            return;
          }
          if (result.permission === "denied") {
            setNotice({
              kind: "denied",
              text:
                "Windows o este celular bloqueó los avisos. Ábrelos en Ajustes del sistema para recibir N1.",
            });
          }
        } catch (reason) {
          setNotice({
            kind: "error",
            text:
              reason instanceof Error
                ? reason.message
                : "No fue posible activar avisos en este dispositivo.",
          });
        }
      })();
    }, 1600);

    return () => window.clearTimeout(timer);
  }, [ready, profileId]);

  return notice;
}
