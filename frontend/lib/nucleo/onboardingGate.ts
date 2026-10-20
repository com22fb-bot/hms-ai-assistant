/**
 * Orden del primer uso: primero el paso de notificaciones, después la
 * importación inicial. Antes, page.tsx abría la importación en cuanto el
 * backend decía needs_initial_import y tapaba el paso de notificaciones
 * (que NucleoApp abría en paralelo).
 */
export type PushOnboardingState = "pending" | "open" | "done";

/** Tiempo máximo esperando a saber si hay paso de notificaciones. */
export const ONBOARDING_DECISION_TIMEOUT_MS = 4000;

export function canOpenInitialImport(
  wantsImport: boolean,
  onboarding: PushOnboardingState,
): boolean {
  return wantsImport && onboarding === "done";
}
