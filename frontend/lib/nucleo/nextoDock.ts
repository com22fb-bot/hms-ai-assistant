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

/** After the user closes the bubble (X / Esc) or stops typing, hover-help waits this long. */
export const HELP_COOLDOWN_MS = 4000;
/** Pixels around the robot that count as "approaching" it. */
export const APPROACH_PX = 56;

export type BubbleGate = {
  /** X was pressed: stay closed until the robot itself is hovered or dragged. */
  muted: boolean;
  /** Timestamp until which hover-help stays quiet (cooldown). */
  quietUntil: number;
  /** The user is typing in an input/textarea/select/contenteditable. */
  typing: boolean;
  /** When X was last pressed (0 = never). */
  closedAt: number;
};

export const OPEN_GATE: BubbleGate = { muted: false, quietUntil: 0, typing: false, closedAt: 0 };

/** Hover/focus help on page elements may open the bubble. */
export function canAutoHelp(gate: BubbleGate, now: number): boolean {
  return !gate.muted && !gate.typing && now >= gate.quietUntil;
}

export function gateAfterClose(gate: BubbleGate, now: number): BubbleGate {
  return { ...gate, muted: true, closedAt: now, quietUntil: Math.max(gate.quietUntil, now + HELP_COOLDOWN_MS) };
}

export function gateAfterTyping(gate: BubbleGate, typing: boolean, now: number): BubbleGate {
  return typing ? { ...gate, typing: true } : { ...gate, typing: false, quietUntil: Math.max(gate.quietUntil, now + HELP_COOLDOWN_MS) };
}

/**
 * Hovering/approaching the robot (or dragging it) un-mutes the guide. A short
 * grace period right after closing avoids reopening just because the pointer
 * passed over the robot on its way out.
 */
export function gateAfterRobot(gate: BubbleGate, now: number, closeGraceMs = 900): { gate: BubbleGate; reopen: boolean } {
  if (gate.typing) return { gate, reopen: false };
  if (gate.muted && now - gate.closedAt < closeGraceMs) return { gate, reopen: false };
  return { gate: { ...gate, muted: false, quietUntil: 0 }, reopen: gate.muted };
}

/** True for elements where the user types (the bubble must stay out of the way). */
export function isTypingTarget(element: { tagName?: string; isContentEditable?: boolean; getAttribute?: (name: string) => string | null; type?: string } | null | undefined): boolean {
  if (!element) return false;
  if (element.isContentEditable) return true;
  const tag = String(element.tagName || "").toUpperCase();
  if (tag === "TEXTAREA" || tag === "SELECT") return true;
  if (tag !== "INPUT") return element.getAttribute?.("role") === "textbox";
  const type = String(element.type || element.getAttribute?.("type") || "text").toLowerCase();
  return !["button", "submit", "reset", "checkbox", "radio", "range", "color", "file", "image"].includes(type);
}

/** Distance from a point to a rectangle (0 when inside). */
export function distanceToRect(x: number, y: number, rect: { left: number; top: number; right: number; bottom: number }): number {
  const dx = Math.max(rect.left - x, 0, x - rect.right);
  const dy = Math.max(rect.top - y, 0, y - rect.bottom);
  return Math.hypot(dx, dy);
}
