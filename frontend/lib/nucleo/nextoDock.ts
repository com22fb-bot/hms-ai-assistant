/**
 * Pure helpers for the draggable Nexto robot: position parsing, clamping to
 * the viewport, keyboard nudges and where the speech bubble should open.
 */

export type DockPos = { x: number; y: number };
export type DockSize = { w: number; h: number };
export type Viewport = { w: number; h: number };

export const NEXTO_POS_KEY = "donexto.nexto.pos";
export const DOCK_MARGIN = 8;
export const DRAG_THRESHOLD = 6;

/** Keeps the robot fully on screen (with a small margin). */
export function clampPos(pos: DockPos, size: DockSize, view: Viewport, margin = DOCK_MARGIN): DockPos {
  const maxX = Math.max(margin, view.w - size.w - margin);
  const maxY = Math.max(margin, view.h - size.h - margin);
  return {
    x: Math.round(Math.min(Math.max(pos.x, margin), maxX)),
    y: Math.round(Math.min(Math.max(pos.y, margin), maxY)),
  };
}

/** Reads a stored position; anything malformed means "default corner". */
export function parsePos(raw: string | null | undefined): DockPos | null {
  if (!raw) return null;
  try {
    const value = JSON.parse(raw) as { x?: unknown; y?: unknown };
    if (typeof value?.x !== "number" || typeof value?.y !== "number") return null;
    if (!Number.isFinite(value.x) || !Number.isFinite(value.y)) return null;
    return { x: value.x, y: value.y };
  } catch {
    return null;
  }
}

/** Arrow keys move 24px (96px with Shift). Returns null for other keys. */
export function nudge(pos: DockPos, key: string, shift: boolean): DockPos | null {
  const step = shift ? 96 : 24;
  if (key === "ArrowLeft") return { x: pos.x - step, y: pos.y };
  if (key === "ArrowRight") return { x: pos.x + step, y: pos.y };
  if (key === "ArrowUp") return { x: pos.x, y: pos.y - step };
  if (key === "ArrowDown") return { x: pos.x, y: pos.y + step };
  return null;
}

/** Bubble opens toward the roomier side, above unless the robot is near the top. */
export function bubbleSide(pos: DockPos, size: DockSize, view: Viewport, bubbleH = 220): { h: "left" | "right"; v: "up" | "down" } {
  const centerX = pos.x + size.w / 2;
  return {
    h: centerX > view.w / 2 ? "left" : "right",
    v: pos.y + size.h < bubbleH ? "down" : "up",
  };
}

/** True once the pointer moved far enough to count as a drag (not a tap). */
export function isDrag(dx: number, dy: number, threshold = DRAG_THRESHOLD): boolean {
  return Math.hypot(dx, dy) >= threshold;
}
