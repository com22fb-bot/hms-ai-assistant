import { readdir, readFile } from "node:fs/promises";
import path from "node:path";

/** Public Worker bindings. nodejs_compat exposes these as process.env at runtime. */
export const PUBLIC_WORKER_ENV_KEYS = [
  "NEXT_PUBLIC_SUPABASE_URL",
  "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY",
  "NEXT_PUBLIC_API_BASE_URL",
];

/**
 * Insert or replace string vars inside the wrangler.jsonc `vars` object.
 * Keeps comments and the rest of the file intact.
 */
export function upsertWranglerVars(source, entries) {
  let next = source;
  if (!/"vars"\s*:/.test(next)) {
    throw new Error("wrangler.jsonc no tiene un bloque vars.");
  }
  for (const [name, value] of Object.entries(entries)) {
    if (typeof value !== "string" || value.length === 0) {
      throw new Error(`Falta ${name} para el deploy del Worker.`);
    }
    const encoded = JSON.stringify(value);
    const existing = new RegExp(
      `("${name}"\\s*:\\s*)"(?:\\\\.|[^"\\\\])*"`,
    );
    if (existing.test(next)) {
      next = next.replace(existing, `$1${encoded}`);
      continue;
    }
    next = next.replace(
      /"vars"\s*:\s*\{/,
      (match) => `${match}\n\t\t"${name}": ${encoded},`,
    );
  }
  return next;
}

export function publicWorkerEnvFromProcess(env = process.env) {
  const apiBase = env.NEXT_PUBLIC_API_BASE_URL?.trim() || "/api/hms";
  return {
    NEXT_PUBLIC_SUPABASE_URL: env.NEXT_PUBLIC_SUPABASE_URL?.trim() ?? "",
    NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY:
      env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY?.trim() ?? "",
    NEXT_PUBLIC_API_BASE_URL: apiBase,
  };
}

const DYNAMIC_ENV_ACCESS =
  /\.env\.NEXT_PUBLIC_SUPABASE_(?:URL|PUBLISHABLE_KEY)/;

/**
 * The OpenNext client bundle must contain the Supabase host as a literal.
 * A leftover `process.env.NEXT_PUBLIC_SUPABASE_*` read crashes the Worker:
 * nodejs_compat uses the Worker env, which does not include those keys unless
 * they were copied into wrangler vars at deploy time — and the browser has
 * neither.
 */
export async function findUninlinedPublicEnv(directories, supabaseUrl) {
  const problems = [];
  let sawHost = false;
  const host = supabaseUrl.replace(/^https?:\/\//, "").replace(/\/$/, "");
  for (const directory of directories) {
    let names;
    try {
      names = await readdir(directory);
    } catch {
      problems.push(`No existe el directorio de chunks: ${directory}`);
      continue;
    }
    for (const name of names) {
      if (!name.endsWith(".js")) continue;
      const filePath = path.join(directory, name);
      const source = await readFile(filePath, "utf8");
      if (DYNAMIC_ENV_ACCESS.test(source)) {
        problems.push(
          `${filePath} sigue leyendo process.env.NEXT_PUBLIC_SUPABASE_* en runtime.`,
        );
      }
      if (host && source.includes(host)) {
        sawHost = true;
      }
    }
  }
  if (!sawHost) {
    problems.push(
      "Ningún chunk trae el host de NEXT_PUBLIC_SUPABASE_URL inlineado.",
    );
  }
  return problems;
}
