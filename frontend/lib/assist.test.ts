import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { describe, it } from "node:test";
import { fileURLToPath } from "node:url";

import {
  ASSIST_MAX_TURNS,
  ASSIST_SESSION_KEY,
  ctaFromPayload,
  errorMessage,
  historyForRequest,
  langFromSearch,
  linkTokenFromSearch,
  loadSession,
  onlyDigits,
  saveSession,
  sessionFromVerified,
  stripLinkToken,
  welcomeMessage,
} from "./assist.ts";

function memoryStorage() {
  const data = new Map<string, string>();
  return {
    getItem: (key: string) => data.get(key) ?? null,
    setItem: (key: string, value: string) => void data.set(key, value),
    removeItem: (key: string) => void data.delete(key),
    data,
  };
}

const here = dirname(fileURLToPath(import.meta.url));

describe("asistencia helpers", () => {
  it("reads the signed link token and strips it from the URL", () => {
    assert.equal(linkTokenFromSearch("?t=abcdefghij.sig"), "abcdefghij.sig");
    assert.equal(linkTokenFromSearch("?t=short"), null);
    assert.equal(linkTokenFromSearch(""), null);
    assert.equal(
      stripLinkToken("https://app.donexto.com/asistencia?t=abc.def&lang=es#x"),
      "/asistencia?lang=es#x",
    );
  });

  it("builds a session only from a verified payload", () => {
    const now = 1_000_000;
    const session = sessionFromVerified(
      { status: "verified", session: "tok.sig", email: "an•••@x.com", expires_in: 86400 },
      now,
    );
    assert.deepEqual(session, { token: "tok.sig", email: "an•••@x.com", expiresAt: now + (86400 - 60) * 1000 });
    assert.equal(sessionFromVerified({ status: "sent", session: "x" }, now), null);
    assert.equal(sessionFromVerified(null, now), null);
  });

  it("stores sessions and drops expired or corrupt ones", () => {
    const storage = memoryStorage();
    saveSession(storage, { token: "t.s", email: "a@x.com", expiresAt: 2000 });
    assert.equal(loadSession(storage, 1000)?.token, "t.s");
    assert.equal(loadSession(storage, 3000), null);
    assert.equal(storage.data.has(ASSIST_SESSION_KEY), false);
    storage.setItem(ASSIST_SESSION_KEY, "{not json");
    assert.equal(loadSession(storage, 0), null);
  });

  it("trims history to the backend limits", () => {
    const turns = Array.from({ length: 20 }, (_, i) => ({
      role: (i % 2 ? "assistant" : "user") as "user" | "assistant",
      content: i === 19 ? "  hola   mundo  " : `m${i}`,
    }));
    turns.push({ role: "user", content: "   " });
    const out = historyForRequest(turns);
    assert.equal(out.length, ASSIST_MAX_TURNS);
    assert.equal(out.at(-1)?.content, "hola mundo");
    assert.equal(historyForRequest([{ role: "user", content: "x".repeat(5000) }])[0].content.length, 1000);
  });

  it("reads the visitor language from the link, default Spanish", () => {
    assert.equal(langFromSearch("?t=a.b&lang=en"), "en");
    assert.equal(langFromSearch("?lang=pt-BR"), "pt");
    assert.equal(langFromSearch("?lang=<script>"), "sc");
    assert.equal(langFromSearch("?lang=x"), "es");
    assert.equal(langFromSearch(""), "es");
  });

  it("keeps only 6 digits of a pasted code", () => {
    assert.equal(onlyDigits(" 12-34 56 78"), "123456");
  });

  it("accepts CTAs only to donexto.com", () => {
    assert.equal(ctaFromPayload({ cta: { url: "https://evil.example/", label: "x" } }), null);
    assert.deepEqual(ctaFromPayload({ cta: { url: "https://app.donexto.com/", label: "Crear", detail: "Plan" } }), {
      label: "Crear",
      detail: "Plan",
      url: "https://app.donexto.com/",
    });
  });

  it("surfaces backend error messages", () => {
    assert.equal(errorMessage({ detail: { message: "Ese código no coincide." } }, "x"), "Ese código no coincide.");
    assert.equal(errorMessage({}, "fallback"), "fallback");
  });

  it("welcome mentions the verified email", () => {
    assert.match(welcomeMessage("an•••@x.com"), /Verificamos tu correo \(an•••@x\.com\)/);
  });

  it("page calls the public assist endpoints, not the mailbox or Gmail flow", () => {
    const source = readFileSync(join(here, "../app/asistencia/AssistChat.tsx"), "utf8");
    for (const path of ["/public/assist/start", "/public/assist/verify", "/public/assist/redeem", "/public/assist/chat"]) {
      assert.ok(source.includes(path), path);
    }
    assert.ok(!source.includes("gmail.readonly"));
    assert.ok(!source.includes("/auth/google"));
  });

  it("admin tab label uses correct Spanish (Quejas e ideas)", () => {
    const admin = readFileSync(join(here, "../app/admin/page.tsx"), "utf8");
    assert.ok(admin.includes('"Quejas e ideas"'));
    assert.ok(!admin.includes('"Quejas y ideas"'));
  });
});
