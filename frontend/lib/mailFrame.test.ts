import assert from "node:assert/strict";
import test from "node:test";

import { INITIAL_MAIL_FRAME, MAIL_FRAME_MAX, nextMailFrameHeight, withoutViewportUnits, type MailFrameState } from "./mailFrame.ts";

const W = 800;
const VIEW = 600;

function run(samples: Array<(height: number) => number>, start: MailFrameState = INITIAL_MAIL_FRAME) {
  let state = start;
  for (const content of samples) {
    state = nextMailFrameHeight(state, { content: content(state.height), overflow: Math.max(state.height, 0), width: W, viewport: VIEW });
  }
  return state;
}

test("fits content once and stays stable", () => {
  const state = run(Array.from({ length: 10 }, () => () => 1234.4));
  assert.equal(state.height, 1235);
  assert.equal(state.fallback, false);
});

test("content that grows with the frame (100vh) stops at a capped fallback", () => {
  // Every measurement is "frame height + 300": a classic feedback loop.
  const state = run(Array.from({ length: 50 }, () => (height: number) => height + 300));
  assert.equal(state.fallback, true);
  assert.ok(state.height <= MAIL_FRAME_MAX);
  assert.equal(state.height, VIEW);
  // Further samples at the same width do not move it again.
  assert.equal(run([(h) => h + 300], state).height, VIEW);
});

test("legitimate growth (images loading) is followed, not treated as a loop", () => {
  const heights = [400, 650, 700, 1100, 1180];
  const state = run(heights.map((value) => () => value));
  assert.equal(state.height, 1180);
  assert.equal(state.fallback, false);
});

test("absurdly tall content falls back instead of creating a giant frame", () => {
  const state = run([() => MAIL_FRAME_MAX + 5000]);
  assert.equal(state.fallback, true);
  assert.equal(state.height, VIEW);
});

test("under-reported content uses scrollHeight so nothing is clipped", () => {
  let state = nextMailFrameHeight(INITIAL_MAIL_FRAME, { content: 500, overflow: 320, width: W, viewport: VIEW });
  assert.equal(state.height, 500);
  state = nextMailFrameHeight(state, { content: 500, overflow: 760, width: W, viewport: VIEW });
  assert.equal(state.height, 760);
});

test("a new width re-measures even after a fallback", () => {
  const looped = run(Array.from({ length: 10 }, () => (height: number) => height + 300));
  assert.equal(looped.fallback, true);
  const resized = nextMailFrameHeight(looped, { content: 900, overflow: 900, width: 500, viewport: VIEW });
  assert.equal(resized.fallback, false);
  assert.equal(resized.height, 900);
});

test("viewport units in email CSS are neutralised", () => {
  assert.equal(withoutViewportUnits("min-height:100vh;height: 50.5dvh"), "min-height:auto;height: auto");
  assert.equal(withoutViewportUnits("width:100%;padding:12px"), "width:100%;padding:12px");
  assert.equal(withoutViewportUnits("height:calc(100vh - 20px)"), "height:calc(auto - 20px)");
});
