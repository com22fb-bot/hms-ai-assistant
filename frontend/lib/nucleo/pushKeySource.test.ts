import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

function source(relativePath: string): string {
  return readFileSync(new URL(relativePath, import.meta.url), "utf8");
}

test("the browser asks the backend for the VAPID public key", () => {
  const files = [
    source("./pushClient.ts"),
    source("../../components/PushNotificationsPanel.tsx"),
  ];
  for (const file of files) {
    assert.match(file, /\/api\/hms\/push\/vapid-public-key/);
    assert.doesNotMatch(file, /NEXT_PUBLIC_[A-Z0-9_]*VAPID/);
    assert.doesNotMatch(file, /process\.env\.[A-Z0-9_]*VAPID/);
  }
});
