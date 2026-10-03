/**
 * Transient network failures ("NetworkError when attempting to fetch resource."
 * in Firefox, "Failed to fetch" in Chrome, "Load failed" in Safari).
 *
 * They happen on phones when the tab is frozen in the background, the screen
 * locks, or the connection switches between Wi-Fi and mobile data while a
 * request is in flight. The request never reaches Donexto, so the server
 * cannot report anything. Idempotent reads are retried quietly; if the
 * network is really gone the user gets a plain message instead of the
 * browser's raw text.
 */

export const NETWORK_ERROR_MESSAGE =
  "Se perdió la conexión con Donexto por un momento. Revisa tu internet; lo volvemos a intentar solo.";

const NETWORK_PATTERN =
  /failed to fetch|networkerror|network error|load failed|network request failed|network connection was lost|internet connection appears to be offline|err_network|err_internet_disconnected/i;

export class NetworkUnavailableError extends Error {
  readonly cause: unknown;

  constructor(cause: unknown) {
    super(NETWORK_ERROR_MESSAGE);
    this.name = "NetworkUnavailableError";
    this.cause = cause;
  }
}

/** True for the browser's "request never completed" TypeError (not aborts, not HTTP errors). */
export function isNetworkFailure(error: unknown): boolean {
  if (!(error instanceof TypeError)) return false;
  return NETWORK_PATTERN.test(error.message);
}

/** Only reads are safe to send twice; a POST might start a second import. */
export function isRetryableMethod(method: string | undefined): boolean {
  const value = (method || "GET").toUpperCase();
  return value === "GET" || value === "HEAD" || value === "OPTIONS";
}

export const DEFAULT_RETRY_DELAYS_MS = [700, 2000];

export async function fetchWithNetworkRetry(
  doFetch: () => Promise<Response>,
  options: {
    method?: string;
    delays?: number[];
    sleep?: (ms: number) => Promise<void>;
  } = {},
): Promise<Response> {
  const delays = isRetryableMethod(options.method) ? options.delays ?? DEFAULT_RETRY_DELAYS_MS : [];
  const sleep = options.sleep ?? ((ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms)));
  let attempt = 0;
  for (;;) {
    try {
      return await doFetch();
    } catch (error) {
      if (!isNetworkFailure(error)) throw error;
      if (attempt >= delays.length) throw new NetworkUnavailableError(error);
      await sleep(delays[attempt]);
      attempt += 1;
    }
  }
}

/**
 * Background pollers (import progress, sync progress) should not flash an
 * error for one dropped request: only after `threshold` failures in a row.
 */
export function shouldSurfacePollError(consecutiveFailures: number, threshold = 3): boolean {
  return consecutiveFailures >= threshold;
}
