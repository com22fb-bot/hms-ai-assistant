/**
 * Refresco periódico con espera creciente.
 * - Cada `baseMs` (90 s) mientras la pestaña está visible.
 * - Si la carga falla, duplica la espera hasta `maxMs` (5 min).
 * - Al volver a la pestaña tras más de `baseMs`, refresca de inmediato.
 */
export function pollWithBackoff(
  load: () => Promise<unknown>,
  { baseMs = 90_000, maxMs = 300_000 }: { baseMs?: number; maxMs?: number } = {},
): () => void {
  let stopped = false;
  let timer: number | null = null;
  let delay = baseMs;
  let lastRun = Date.now();

  const run = async () => {
    if (stopped) return;
    if (document.visibilityState !== "visible") {
      schedule();
      return;
    }
    lastRun = Date.now();
    try {
      const result = await load();
      delay = result === false ? Math.min(delay * 2, maxMs) : baseMs;
    } catch {
      delay = Math.min(delay * 2, maxMs);
    }
    schedule();
  };

  const schedule = () => {
    if (stopped) return;
    if (timer !== null) window.clearTimeout(timer);
    timer = window.setTimeout(() => void run(), delay);
  };

  const onVisible = () => {
    if (document.visibilityState === "visible" && Date.now() - lastRun >= baseMs) {
      void run();
    }
  };

  document.addEventListener("visibilitychange", onVisible);
  schedule();
  return () => {
    stopped = true;
    if (timer !== null) window.clearTimeout(timer);
    document.removeEventListener("visibilitychange", onVisible);
  };
}
