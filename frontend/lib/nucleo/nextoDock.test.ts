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

test("nexto: X keeps the bubble closed until the robot itself is approached", async () => {
  const { OPEN_GATE, canAutoHelp, gateAfterClose, gateAfterRobot, HELP_COOLDOWN_MS } = await import("./nextoDock.ts");
  const closed = gateAfterClose(OPEN_GATE, 10_000);
  assert.equal(canAutoHelp(closed, 10_100), false);
  // Long after the cooldown, hovering other elements still doesn't reopen it (muted).
  assert.equal(canAutoHelp(closed, 10_000 + HELP_COOLDOWN_MS * 10), false);
  // Passing over the robot right after closing doesn't reopen it…
  assert.equal(gateAfterRobot(closed, 10_300).reopen, false);
  // …but hovering/approaching it later does, and hover-help works again.
  const back = gateAfterRobot(closed, 12_000);
  assert.equal(back.reopen, true);
  assert.equal(canAutoHelp(back.gate, 12_001), true);
});

test("nexto: typing hides the guide and a short cooldown follows", async () => {
  const { OPEN_GATE, canAutoHelp, gateAfterTyping, gateAfterRobot, HELP_COOLDOWN_MS } = await import("./nextoDock.ts");
  const typing = gateAfterTyping(OPEN_GATE, true, 1_000);
  assert.equal(canAutoHelp(typing, 5_000), false);
  assert.equal(gateAfterRobot(typing, 5_000).reopen, false);
  const stopped = gateAfterTyping(typing, false, 6_000);
  assert.equal(canAutoHelp(stopped, 6_000 + HELP_COOLDOWN_MS - 1), false);
  assert.equal(canAutoHelp(stopped, 6_000 + HELP_COOLDOWN_MS), true);
});

test("nexto: typing targets and proximity", async () => {
  const { isTypingTarget, distanceToRect } = await import("./nextoDock.ts");
  assert.equal(isTypingTarget({ tagName: "INPUT", type: "text" }), true);
  assert.equal(isTypingTarget({ tagName: "INPUT", type: "search" }), true);
  assert.equal(isTypingTarget({ tagName: "INPUT", type: "checkbox" }), false);
  assert.equal(isTypingTarget({ tagName: "TEXTAREA" }), true);
  assert.equal(isTypingTarget({ tagName: "DIV", isContentEditable: true }), true);
  assert.equal(isTypingTarget({ tagName: "BUTTON" }), false);
  assert.equal(isTypingTarget(null), false);
  const rect = { left: 100, top: 100, right: 196, bottom: 212 };
  assert.equal(distanceToRect(150, 150, rect), 0);
  assert.equal(distanceToRect(60, 150, rect), 40);
});
