export type PrefsSyncAction = "hold" | "apply-server" | "upload";

/** What to do when the preferences GET settles. */
export function prefsAfterLoad(input: {
  dirty: boolean;
  hasServer: boolean;
}): PrefsSyncAction {
  if (input.dirty) return "upload";
  if (input.hasServer) return "apply-server";
  return "hold";
}

/** What to do when the user edits preferences. */
export function prefsAfterEdit(input: { hydrated: boolean }): PrefsSyncAction {
  return input.hydrated ? "upload" : "hold";
}
