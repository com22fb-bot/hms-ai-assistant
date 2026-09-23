/**
 * Cold email-link verification.
 *
 * Outlook often opens Verificar in a tab that has no Donexto session.
 * The token_hash in that URL is the proof. The "Ya abrí el enlace" button
 * only finishes a proof already stored here, or refreshes a session that
 * another tab already verified.
 */

export type DonextoVerifyProof = {
  tokenHash: string;
  tokenType: string;
};

export type VerifyLinkErrorCode = "invalid" | "retry" | "sign_in_again";

export type ConfirmDonextoOutcome =
  | { kind: "session"; accessToken: string; refreshToken: string }
  | { kind: "verified_without_session" }
  | { kind: "invalid" }
  | { kind: "retry" };

export const DONEXTO_VERIFY_PROOF_KEY = "donexto_verify_proof";
export const DONEXTO_VERIFY_ERROR_KEY = "donexto_verify_link_error";

const TOKEN_HASH_MAX = 2048;

type KeyValueStore = {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
};

export function readDonextoVerifyProof(search: string): DonextoVerifyProof | null {
  const raw = search.startsWith("?") ? search.slice(1) : search;
  const params = new URLSearchParams(raw);
  if (params.get("donexto_verify") !== "1") {
    return null;
  }
  const tokenHash = (params.get("token_hash") || "").trim();
  if (!tokenHash || tokenHash.length > TOKEN_HASH_MAX) {
    return null;
  }
  const tokenType = (params.get("type") || "magiclink").trim() || "magiclink";
  return { tokenHash, tokenType };
}

export function parseStoredDonextoVerifyProof(raw: string | null): DonextoVerifyProof | null {
  if (!raw) {
    return null;
  }
  try {
    const parsed = JSON.parse(raw) as {
      tokenHash?: unknown;
      tokenType?: unknown;
    };
    const tokenHash = typeof parsed.tokenHash === "string" ? parsed.tokenHash.trim() : "";
    if (!tokenHash || tokenHash.length > TOKEN_HASH_MAX) {
      return null;
    }
    const tokenType = typeof parsed.tokenType === "string" && parsed.tokenType.trim()
      ? parsed.tokenType.trim()
      : "magiclink";
    return { tokenHash, tokenType };
  } catch {
    return null;
  }
}

export function rememberDonextoVerifyProof(
  store: KeyValueStore,
  proof: DonextoVerifyProof,
): void {
  store.setItem(
    DONEXTO_VERIFY_PROOF_KEY,
    JSON.stringify({
      tokenHash: proof.tokenHash,
      tokenType: proof.tokenType || "magiclink",
    }),
  );
}

export function loadDonextoVerifyProof(store: KeyValueStore): DonextoVerifyProof | null {
  return parseStoredDonextoVerifyProof(store.getItem(DONEXTO_VERIFY_PROOF_KEY));
}

export function forgetDonextoVerifyProof(store: KeyValueStore): void {
  store.removeItem(DONEXTO_VERIFY_PROOF_KEY);
}

export function confirmDonextoPath(proof: DonextoVerifyProof): string {
  const query = new URLSearchParams({
    donexto_verify: "1",
    token_hash: proof.tokenHash,
    type: proof.tokenType || "magiclink",
  });
  return `/identity/confirm-donexto?${query.toString()}`;
}

export function interpretConfirmDonextoResponse(
  status: number,
  payload: unknown,
): ConfirmDonextoOutcome {
  if (status === 403) {
    return { kind: "invalid" };
  }
  if (status < 200 || status >= 300) {
    return { kind: "retry" };
  }
  if (!payload || typeof payload !== "object") {
    return { kind: "retry" };
  }
  const body = payload as {
    donexto_verified?: unknown;
    access_token?: unknown;
    refresh_token?: unknown;
  };
  if (body.donexto_verified !== true) {
    return { kind: "retry" };
  }
  const accessToken = typeof body.access_token === "string" ? body.access_token.trim() : "";
  const refreshToken = typeof body.refresh_token === "string" ? body.refresh_token.trim() : "";
  if (accessToken && refreshToken) {
    return { kind: "session", accessToken, refreshToken };
  }
  return { kind: "verified_without_session" };
}

export function stripDonextoVerifySearch(href: string): string {
  const url = new URL(href, "https://app.donexto.com");
  const hadProof = url.searchParams.has("donexto_verify") || url.searchParams.has("token_hash");
  url.searchParams.delete("donexto_verify");
  url.searchParams.delete("token_hash");
  if (hadProof) {
    url.searchParams.delete("type");
  }
  return `${url.pathname}${url.search}${url.hash}`;
}

let latchedVerifyLinkError: { code: VerifyLinkErrorCode; at: number } | null = null;
const VERIFY_ERROR_LATCH_MS = 10_000;

function asVerifyLinkErrorCode(value: string | null): VerifyLinkErrorCode | null {
  if (value === "invalid" || value === "retry" || value === "sign_in_again") {
    return value;
  }
  return null;
}

export function rememberVerifyLinkError(
  store: KeyValueStore,
  code: VerifyLinkErrorCode,
): void {
  store.setItem(DONEXTO_VERIFY_ERROR_KEY, code);
  latchedVerifyLinkError = { code, at: Date.now() };
}

export function acknowledgeVerifyLinkError(): void {
  latchedVerifyLinkError = null;
}

export function consumeVerifyLinkError(store: KeyValueStore): VerifyLinkErrorCode | null {
  const stored = asVerifyLinkErrorCode(store.getItem(DONEXTO_VERIFY_ERROR_KEY));
  if (stored) {
    latchedVerifyLinkError = { code: stored, at: Date.now() };
    store.removeItem(DONEXTO_VERIFY_ERROR_KEY);
  }
  if (
    latchedVerifyLinkError
    && Date.now() - latchedVerifyLinkError.at < VERIFY_ERROR_LATCH_MS
  ) {
    return latchedVerifyLinkError.code;
  }
  return null;
}

export function donextoVerifyFailure(code: VerifyLinkErrorCode | "unverified"): Error {
  const error = new Error(code);
  Object.assign(error, { donextoVerifyCode: code });
  return error;
}

export function verifyUiErrorCode(error: unknown): VerifyLinkErrorCode | "unverified" {
  const code = error && typeof error === "object" && "donextoVerifyCode" in error
    ? (error as { donextoVerifyCode?: unknown }).donextoVerifyCode
    : null;
  if (
    code === "invalid"
    || code === "retry"
    || code === "sign_in_again"
    || code === "unverified"
  ) {
    return code;
  }
  return "unverified";
}
