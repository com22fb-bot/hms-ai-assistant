/**
 * "Traer correo nuevo": starts an incremental guided import
 * (`POST /gmail/import/start {mode:"incremental"}`) and follows
 * `/gmail/import/status` until that job ends. Pure logic: the fetchers and
 * the clock are injected so it can be tested without a browser.
 *
 * The legacy `/gmail/sync-jobs` endpoint is blocked in production while
 * HMS_DATA_MUTATIONS_ENABLED=false (HTTP 423), which is why the button used
 * to do nothing. The guided import is the sanctioned read-only path.
 */

export type ImportJobRow = {
  id?: string | null;
  status?: string | null;
  messages_inserted?: number | null;
  messages_found?: number | null;
  created_cases?: number | null;
  last_error?: string | null;
};

export type ImportStatusPayload = {
  phase?: string | null;
  initial_import_complete?: boolean;
  needs_initial_import?: boolean;
  active?: ImportJobRow | null;
  latest?: ImportJobRow | null;
  failure?: { reason?: string | null; reconnect_required?: boolean; message?: string | null } | null;
  progress?: { downloaded?: number | null; found?: number | null } | null;
};

export type MailRefreshResult =
  | { ok: true; inserted: number; createdCases: number }
  | { ok: false; reason: "auth" | "failed" | "timeout" | "initial"; message: string };

export type MailRefreshDeps = {
  start: () => Promise<{ job?: ImportJobRow | null }>;
  status: () => Promise<ImportStatusPayload>;
  sleep: (ms: number) => Promise<void>;
  now: () => number;
  onProgress?: (downloaded: number) => void;
  pollMs?: number;
  timeoutMs?: number;
};

const AUTH_HINTS = ["invalid_grant", "expired or revoked", "revoked", "unauthorized", "reconnect", "vuelve a conectar", "authenticationfailed"];

/** True when an error text means the mailbox permission must be renewed. */
export function isAuthError(text: string | null | undefined): boolean {
  const value = String(text || "").toLowerCase();
  return AUTH_HINTS.some((hint) => value.includes(hint));
}

/**
 * Result of the incremental job, or null while an import is still running
 * (ours, or one the backend reused instead of starting a duplicate).
 */
export function jobOutcome(payload: ImportStatusPayload): MailRefreshResult | null {
  if (payload.active) return null;
  const latest = payload.latest ?? null;
  const row = latest ?? {};
  if (row.status === "completed") {
    return { ok: true, inserted: Math.max(0, Number(row.messages_inserted ?? 0)), createdCases: Math.max(0, Number(row.created_cases ?? 0)) };
  }
  if (row.status === "failed" || row.status === "cancelled") {
    const auth = Boolean(payload.failure?.reconnect_required) || isAuthError(row.last_error);
    return {
      ok: false,
      reason: auth ? "auth" : "failed",
      message: payload.failure?.message || row.last_error || "",
    };
  }
  if (row.status === "queued" || row.status === "running" || row.status === "interrupted") return null;
  return { ok: true, inserted: 0, createdCases: 0 };
}

export async function refreshMailbox(deps: MailRefreshDeps): Promise<MailRefreshResult> {
  const pollMs = deps.pollMs ?? 1500;
  const timeoutMs = deps.timeoutMs ?? 240_000;
  const before = await deps.status();
  if (before.initial_import_complete === false || before.needs_initial_import) {
    return { ok: false, reason: "initial", message: "" };
  }
  await deps.start();
  const deadline = deps.now() + timeoutMs;
  for (;;) {
    await deps.sleep(pollMs);
    const payload = await deps.status();
    const downloaded = Number(payload.progress?.downloaded ?? payload.active?.messages_inserted ?? 0);
    deps.onProgress?.(Number.isFinite(downloaded) ? downloaded : 0);
    const outcome = jobOutcome(payload);
    if (outcome) return outcome;
    if (deps.now() >= deadline) return { ok: false, reason: "timeout", message: "" };
  }
}
