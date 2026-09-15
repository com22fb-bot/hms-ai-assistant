import assert from "node:assert/strict";
import { test } from "node:test";
import { isMailboxEmailVerified } from "./mailboxVerification.ts";

test("Microsoft and the legacy verification flag cannot unlock the dashboard", () => {
  assert.equal(isMailboxEmailVerified({email: "a@outlook.com", app_metadata: {
    provider: "azure", donexto_verified: true,
  }}), false);
});

test("only explicit proof for the current mailbox unlocks the dashboard", () => {
  const app_metadata = {mailbox_email_verification_v1: {
    email: "a@outlook.com", method: "email_link", verified_at: 100,
  }};
  assert.equal(isMailboxEmailVerified({email: "a@outlook.com", app_metadata}), true);
  assert.equal(isMailboxEmailVerified({email: "b@outlook.com", app_metadata}), false);
  assert.equal(isMailboxEmailVerified(null), false);
});
