import assert from "node:assert/strict";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";

import {
  findUninlinedPublicEnv,
  publicWorkerEnvFromProcess,
  upsertWranglerVars,
} from "./workerPublicEnv.mjs";

const sample = `{
	"vars": {
		// proxy
		"HMS_INTERNAL_API_BASE_URL": "https://api.example"
	}
}
`;

test("upsertWranglerVars adds public keys without dropping comments", () => {
  const next = upsertWranglerVars(sample, {
    NEXT_PUBLIC_SUPABASE_URL: "https://abc.supabase.co",
    NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY: "sb_publishable_test",
    NEXT_PUBLIC_API_BASE_URL: "/api/hms",
  });
  assert.match(next, /proxy/);
  assert.match(next, /HMS_INTERNAL_API_BASE_URL/);
  assert.match(next, /"NEXT_PUBLIC_SUPABASE_URL": "https:\/\/abc\.supabase\.co"/);
  assert.match(next, /"NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY": "sb_publishable_test"/);
  const replaced = upsertWranglerVars(next, {
    NEXT_PUBLIC_SUPABASE_URL: "https://other.supabase.co",
  });
  assert.match(replaced, /https:\/\/other\.supabase\.co/);
  assert.equal(replaced.match(/NEXT_PUBLIC_SUPABASE_URL/g)?.length, 1);
});

test("publicWorkerEnvFromProcess defaults the API base", () => {
  const env = publicWorkerEnvFromProcess({
    NEXT_PUBLIC_SUPABASE_URL: " https://abc.supabase.co ",
    NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY: "sb_publishable_test",
  });
  assert.equal(env.NEXT_PUBLIC_SUPABASE_URL, "https://abc.supabase.co");
  assert.equal(env.NEXT_PUBLIC_API_BASE_URL, "/api/hms");
});

test("findUninlinedPublicEnv rejects runtime env reads", async () => {
  const dir = await mkdtemp(path.join(tmpdir(), "donexto-env-"));
  try {
    await writeFile(
      path.join(dir, "app.js"),
      'let u=b.default.env.NEXT_PUBLIC_SUPABASE_URL;throw Error("Faltan")',
    );
    const problems = await findUninlinedPublicEnv(
      [dir],
      "https://abc.supabase.co",
    );
    assert.ok(problems.some((problem) => problem.includes("runtime")));
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
});

test("findUninlinedPublicEnv accepts an inlined host", async () => {
  const dir = await mkdtemp(path.join(tmpdir(), "donexto-env-"));
  try {
    await writeFile(
      path.join(dir, "app.js"),
      'createClient("https://abc.supabase.co","sb_publishable_test")',
    );
    const problems = await findUninlinedPublicEnv(
      [dir],
      "https://abc.supabase.co",
    );
    assert.deepEqual(problems, []);
    const raw = await readFile(path.join(dir, "app.js"), "utf8");
    assert.match(raw, /abc\.supabase\.co/);
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
});
