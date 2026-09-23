import { spawnSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  findUninlinedPublicEnv,
  publicWorkerEnvFromProcess,
  upsertWranglerVars,
} from "./workerPublicEnv.mjs";

const frontendRoot = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const wranglerPath = path.join(frontendRoot, "wrangler.jsonc");

function run(command, args) {
  const result = spawnSync(command, args, {
    cwd: frontendRoot,
    stdio: "inherit",
    env: process.env,
  });
  return result.status ?? 1;
}

const original = readFileSync(wranglerPath, "utf8");
const publicEnv = publicWorkerEnvFromProcess();
const patched = upsertWranglerVars(original, publicEnv);
writeFileSync(wranglerPath, patched);

let exitCode = 0;
try {
  exitCode = run("npx", ["opennextjs-cloudflare", "build"]);
  if (exitCode === 0) {
    const problems = await findUninlinedPublicEnv(
      [
        path.join(frontendRoot, ".open-next/assets/_next/static/chunks"),
        path.join(
          frontendRoot,
          ".open-next/server-functions/default/.next/server/chunks/ssr",
        ),
      ],
      publicEnv.NEXT_PUBLIC_SUPABASE_URL,
    );
    if (problems.length > 0) {
      console.error(
        "El build de OpenNext no inlineó NEXT_PUBLIC_SUPABASE_*. No se despliega, para no repetir el HTTP 500.",
      );
      for (const problem of problems) {
        console.error(`- ${problem}`);
      }
      exitCode = 1;
    } else {
      // --keep-vars retains dashboard vars that are not in wrangler.jsonc.
      // The public Supabase keys are in that file only for this deploy.
      exitCode = run("npx", [
        "opennextjs-cloudflare",
        "deploy",
        "--",
        "--keep-vars",
      ]);
    }
  }
} finally {
  writeFileSync(wranglerPath, original);
}

process.exit(exitCode);
