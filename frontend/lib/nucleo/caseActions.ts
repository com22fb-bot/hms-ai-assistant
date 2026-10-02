/**
 * Hecho / posponer / reabrir through the per-user endpoint
 * `POST /cases/{id}/user-action`. The generic `PATCH /cases/{id}` stays behind
 * the backend's data-mutation lock (HTTP 423 in production), so the UI must
 * never use it for these everyday actions.
 */

export type CaseAction = "done" | "reopen" | "snooze" | "unsnooze";

export type CaseActionErrorKey =
  | "caseErrLocked"
  | "caseErrSession"
  | "caseErrMissing"
  | "caseErrInvalid"
  | "caseErrNetwork"
  | "caseErrGeneric";

export type CaseActionResult =
  | { ok: true; status: string | null }
  | { ok: false; key: CaseActionErrorKey; status: number | null };

export type CaseActionSend = (url: string, init: RequestInit) => Promise<unknown>;

export function caseActionRequest(caseId: string, action: CaseAction, until?: Date | null): { url: string; init: RequestInit } {
  const body: { action: CaseAction; until?: string } = { action };
  if (action === "snooze" && until) body.until = until.toISOString();
  return {
    url: `/api/hms/cases/${encodeURIComponent(caseId)}/user-action`,
    init: { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) },
  };
}

/** Plain-language error for a failed action (never the raw server text). */
export function caseActionErrorKey(error: unknown): CaseActionErrorKey {
  const status = typeof (error as { status?: unknown })?.status === "number" ? (error as { status: number }).status : null;
  if (status === 423) return "caseErrLocked";
  if (status === 401 || status === 403) return "caseErrSession";
  if (status === 404 || status === 409) return "caseErrMissing";
  if (status === 400 || status === 422) return "caseErrInvalid";
  if (status === null && error instanceof TypeError) return "caseErrNetwork";
  return "caseErrGeneric";
}

export async function runCaseAction(send: CaseActionSend, caseId: string, action: CaseAction, until?: Date | null): Promise<CaseActionResult> {
  const { url, init } = caseActionRequest(caseId, action, until);
  try {
    const row = (await send(url, init)) as { status?: unknown } | null;
    return { ok: true, status: typeof row?.status === "string" ? row.status : null };
  } catch (error) {
    const status = typeof (error as { status?: unknown })?.status === "number" ? (error as { status: number }).status : null;
    return { ok: false, key: caseActionErrorKey(error), status };
  }
}

/** Snooze presets: 1 h, "mañana 9:00" (15) and 3 days (72). */
export function snoozeUntil(hours: number, now: Date = new Date()): Date {
  const until = new Date(now.getTime());
  if (hours === 15) {
    until.setDate(until.getDate() + 1);
    until.setHours(9, 0, 0, 0);
  } else {
    until.setTime(until.getTime() + hours * 36e5);
  }
  return until;
}

export function isClosedStatus(status: string | null | undefined): boolean {
  return status === "resolved" || status === "closed" || status === "archived";
}
