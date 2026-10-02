import assert from "node:assert/strict";
import test from "node:test";

import { bubbleSide, clampPos, isDrag, nudge, parsePos } from "./nextoDock.ts";

const size = { w: 96, h: 112 };
const view = { w: 1366, h: 768 };

test("nexto: positions are clamped inside the viewport", () => {
  assert.deepEqual(clampPos({ x: -50, y: -10 }, size, view), { x: 8, y: 8 });
  assert.deepEqual(clampPos({ x: 5000, y: 5000 }, size, view), { x: 1366 - 96 - 8, y: 768 - 112 - 8 });
  assert.deepEqual(clampPos({ x: 400.4, y: 300.6 }, size, view), { x: 400, y: 301 });
  // Tiny viewport: never negative.
  assert.deepEqual(clampPos({ x: 50, y: 50 }, size, { w: 60, h: 60 }), { x: 8, y: 8 });
});

test("nexto: stored position parsing is defensive", () => {
  assert.deepEqual(parsePos('{"x":10,"y":20}'), { x: 10, y: 20 });
  assert.equal(parsePos(null), null);
  assert.equal(parsePos("nope"), null);
  assert.equal(parsePos('{"x":"1","y":2}'), null);
  assert.equal(parsePos('{"x":null,"y":2}'), null);
});

test("nexto: keyboard nudges", () => {
  assert.deepEqual(nudge({ x: 100, y: 100 }, "ArrowLeft", false), { x: 76, y: 100 });
  assert.deepEqual(nudge({ x: 100, y: 100 }, "ArrowDown", true), { x: 100, y: 196 });
  assert.equal(nudge({ x: 100, y: 100 }, "Enter", false), null);
});

test("nexto: bubble opens toward the free side", () => {
  assert.deepEqual(bubbleSide({ x: 1200, y: 600 }, size, view), { h: "left", v: "up" });
  assert.deepEqual(bubbleSide({ x: 40, y: 20 }, size, view), { h: "right", v: "down" });
});

test("nexto: a tap is not a drag", () => {
  assert.equal(isDrag(2, 3), false);
  assert.equal(isDrag(5, 5), true);
});
