import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

test("the HMS proxy forwards PUT", () => {
  const source = readFileSync(
    new URL("../../app/api/hms/[...path]/route.ts", import.meta.url),
    "utf8",
  );
  for (const method of ["GET", "POST", "PUT", "PATCH", "DELETE"]) {
    assert.match(source, new RegExp(`export async function ${method}\\b`));
  }
});
