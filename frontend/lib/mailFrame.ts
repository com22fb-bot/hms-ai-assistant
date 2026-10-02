/**
 * Sizing rule for the read-only email iframe in the reading view.
 *
 * The iframe is sized to its content so the reading pane keeps exactly one
 * scroll area. The content box is measured (never the iframe viewport), but
 * an email can still size itself from the viewport (e.g. `100vh`), which
 * would make every resize trigger a bigger one. This pure function detects
 * that feedback and caps absurd heights; in both cases it falls back to a
 * capped frame that scrolls by itself, so the email is never clipped.
 */

/** Above this height the email is shown in a capped, scrollable frame. */
export const MAIL_FRAME_MAX = 30000;
/** Consecutive growths equal to our own previous resize = feedback loop. */
export const MAIL_FRAME_LOOP = 3;

export type MailFrameState = {
  height: number;
  width: number;
  /** Last change we applied to the frame height. */
  delta: number;
  /** Consecutive samples whose growth mirrored our previous resize. */
  streak: number;
  fallback: boolean;
};

export const INITIAL_MAIL_FRAME: MailFrameState = { height: 0, width: 0, delta: 0, streak: 0, fallback: false };

export type MailFrameSample = {
  /** Height of the content wrapper plus body padding. */
  content: number;
  /** documentElement.scrollHeight, used only when the wrapper under-reports. */
  overflow: number;
  /** Current iframe width; a new width resets the guard. */
  width: number;
  /** Visible height of the reading pane, used for the fallback frame. */
  viewport: number;
};

export function nextMailFrameHeight(prev: MailFrameState, sample: MailFrameSample): MailFrameState {
  const sameWidth = sample.width === prev.width;
  if (prev.fallback && sameWidth) return prev;
  const base = sameWidth ? prev : { ...INITIAL_MAIL_FRAME, height: prev.height, width: sample.width };
  let target = Math.ceil(sample.content);
  // Something (e.g. absolutely positioned content) sticks out of the box.
  if (sample.overflow > base.height + 2 && sample.overflow > target + 2) target = Math.ceil(sample.overflow);
  if (!Number.isFinite(target) || target <= 0) return { ...base, width: sample.width };
  if (Math.abs(target - base.height) <= 1) return { ...base, width: sample.width, streak: 0 };
  const delta = target - base.height;
  const mirrors = base.delta > 2 && delta > 2 && Math.abs(delta - base.delta) <= 2;
  const streak = mirrors ? base.streak + 1 : 0;
  if (target > MAIL_FRAME_MAX || streak >= MAIL_FRAME_LOOP) {
    const height = Math.max(320, Math.min(MAIL_FRAME_MAX, Math.round(sample.viewport)));
    return { height, width: sample.width, delta: height - base.height, streak, fallback: true };
  }
  return { height: target, width: sample.width, delta, streak, fallback: false };
}

/**
 * Viewport units inside the email iframe follow the iframe height, which the
 * reader sets from the content: `100vh` → `auto` breaks that loop. Results
 * that become invalid (e.g. `calc(auto - 2px)`) are simply dropped by CSS.
 */
export function withoutViewportUnits(css: string): string {
  return css.replace(/-?\d*\.?\d+\s*(?:vh|dvh|svh|lvh|vmin|vmax)\b/gi, "auto");
}
