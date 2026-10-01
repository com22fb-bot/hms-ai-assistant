import type { AppLanguage } from "@/lib/i18n/languages";
import { localeForLanguage } from "@/lib/i18n/languages";

import { ALERT_PHRASE } from "@/lib/nucleo/copy";

export function speakText(
  text: string,
  language: AppLanguage,
  rate = 1,
): void {
  if (typeof window === "undefined" || !window.speechSynthesis || !text.trim()) {
    return;
  }
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = localeForLanguage(language);
  utterance.rate = rate;
  window.speechSynthesis.speak(utterance);
}

export function stopSpeaking(): void {
  if (typeof window === "undefined" || !window.speechSynthesis) return;
  window.speechSynthesis.cancel();
}

export async function playAlertTone(
  language: AppLanguage,
  volume: number,
): Promise<void> {
  if (typeof window === "undefined") return;
  const audio = new Audio(`/sounds/alert-${language}.mp3`);
  audio.volume = Math.min(1, Math.max(0, volume));
  try {
    await audio.play();
  } catch {
    speakText(ALERT_PHRASE[language], language, 1);
  }
}

export function vibrateDevice(pattern: number[]): void {
  if (typeof navigator !== "undefined" && typeof navigator.vibrate === "function") {
    navigator.vibrate(pattern);
  }
}
