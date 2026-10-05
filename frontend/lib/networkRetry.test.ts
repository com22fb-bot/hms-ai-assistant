import assert from "node:assert/strict";
import test from "node:test";

import {
  NETWORK_ERROR_MESSAGE,
  NetworkUnavailableError,
  fetchWithNetworkRetry,
  isNetworkFailure,
  isRetryableMethod,
  shouldSurfacePollError,
} from "./networkRetry.ts";

const firefox = () => new TypeError("NetworkError when attempting to fetch resource.");
const ok = () => new Response("{}", { status: 200 });

test("network failures are recognised across browsers, aborts and HTTP errors are not", () => {
  assert.equal(isNetworkFailure(firefox()), true);
  assert.equal(isNetworkFailure(new TypeError("Failed to fetch")), true);
  assert.equal(isNetworkFailure(new TypeError("Load failed")), true);
  assert.equal(isNetworkFailure(new TypeError("The network connection was lost.")), true);
  assert.equal(isNetworkFailure(new DOMException("The operation was aborted.", "AbortError")), false);
  assert.equal(isNetworkFailure(new Error("HTTP 500")), false);
  assert.equal(isNetworkFailure(new TypeError("x is not a function")), false);
});

test("only reads are retried", () => {
  assert.equal(isRetryableMethod(undefined), true);
  assert.equal(isRetryableMethod("get"), true);
  assert.equal(isRetryableMethod("POST"), false);
  assert.equal(isRetryableMethod("PUT"), false);
});

test("a dropped GET (Firefox NetworkError) is retried quietly and succeeds", async () => {
  let calls = 0;
  const waits: number[] = [];
  const response = await fetchWithNetworkRetry(async () => {
    calls += 1;
    if (calls < 3) throw firefox();
    return ok();
  }, { sleep: async (ms) => { waits.push(ms); } });
  assert.equal(response.status, 200);
  assert.equal(calls, 3);
  assert.deepEqual(waits, [700, 2000]);
});

test("after the retries a plain-language error replaces the raw browser text", async () => {
  let calls = 0;
  await assert.rejects(
    fetchWithNetworkRetry(async () => { calls += 1; throw firefox(); }, { sleep: async () => {} }),
    (error: unknown) => error instanceof NetworkUnavailableError && error.message === NETWORK_ERROR_MESSAGE && !/NetworkError/.test(error.message),
  );
  assert.equal(calls, 3);
});

test("a POST is never re-sent (could start a second import)", async () => {
  let calls = 0;
  await assert.rejects(
    fetchWithNetworkRetry(async () => { calls += 1; throw firefox(); }, { method: "POST", sleep: async () => {} }),
    NetworkUnavailableError,
  );
  assert.equal(calls, 1);
});

test("non-network errors pass through untouched", async () => {
  const boom = new Error("boom");
  await assert.rejects(fetchWithNetworkRetry(async () => { throw boom; }, { sleep: async () => {} }), (error) => error === boom);
});

test("pollers only surface an error after three failures in a row", () => {
  assert.equal(shouldSurfacePollError(1), false);
  assert.equal(shouldSurfacePollError(2), false);
  assert.equal(shouldSurfacePollError(3), true);
});
