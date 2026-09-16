type VerificationUser = {
  email?: string;
  app_metadata?: Record<string, unknown>;
};

export function isMailboxEmailVerified(user: VerificationUser | null | undefined): boolean {
  const proof = user?.app_metadata?.mailbox_email_verification_v1;
  if (!user?.email || !proof || typeof proof !== "object") return false;
  const record = proof as Record<string, unknown>;
  return record.method === "email_link" && typeof record.verified_at === "number"
    && record.verified_at > 0 && record.email === user.email.trim().toLowerCase();
}
