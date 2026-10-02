"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
  type PointerEvent as ReactPointerEvent,
  type ReactNode,
} from "react";

import {
  NEXTO_POS_KEY,
  bubbleSide,
  clampPos,
  isDrag,
  nudge,
  parsePos,
  type DockPos,
  type DockSize,
} from "@/lib/nucleo/nextoDock";

type Props = {
  label: string;
  /** Short how-to (drag / arrows / Home), read by screen readers. */
  hint: string;
  bubble: ReactNode | null;
  robot: ReactNode;
  onActivate: () => void;
  /** Element under the robot after a drag or keyboard move (null = nothing to explain). */
  onExplain: (target: HTMLElement | null) => void;
};

const HELP_SELECTOR = "[data-help-key],[data-help]";

function viewport() {
  return { w: window.innerWidth, h: window.innerHeight };
}

/** Nearest element with help under (x, y), ignoring the robot and its bubble. */
export function helpTargetAt(x: number, y: number, dock: HTMLElement | null): HTMLElement | null {
  if (typeof document === "undefined" || !document.elementsFromPoint) return null;
  for (const element of document.elementsFromPoint(x, y)) {
    if (dock && dock.contains(element)) continue;
    const hit = (element as HTMLElement).closest?.<HTMLElement>(HELP_SELECTOR) ?? null;
    if (hit && !(dock && dock.contains(hit))) return hit;
    if (element.classList?.contains("nx")) break;
  }
  return null;
}

/**
 * Nexto, draggable with mouse/touch (pointer events) and movable with the
 * arrow keys while focused. The position is remembered in localStorage and
 * kept inside the viewport. Only the robot and its bubble take pointer events.
 */
export function NextoDock({ label, hint, bubble, robot, onActivate, onExplain }: Props) {
  const dockRef = useRef<HTMLDivElement>(null);
  const botRef = useRef<HTMLButtonElement>(null);
  const [placement, setPlacement] = useState<{ pos: DockPos; side: { h: "left" | "right"; v: "up" | "down" } } | null>(null);
  const pos = placement?.pos ?? null;
  const [dragging, setDragging] = useState(false);
  const drag = useRef<{ id: number; sx: number; sy: number; ox: number; oy: number; moved: boolean } | null>(null);
  const suppressClick = useRef(false);
  const keyTimer = useRef<number | null>(null);
  const liveTimer = useRef<number>(0);

  const size = useCallback((): DockSize => {
    const rect = botRef.current?.getBoundingClientRect();
    return { w: rect?.width || 96, h: rect?.height || 112 };
  }, []);

  /** Moves the robot (null = default corner) and picks the bubble side. */
  const setPos = useCallback((next: DockPos | null) => {
    if (!next) {
      setPlacement(null);
      return;
    }
    const box = size();
    const clamped = clampPos(next, box, viewport());
    setPlacement({ pos: clamped, side: bubbleSide(clamped, box, viewport()) });
  }, [size]);

  // Restore the saved position (client only) and keep it on screen on resize.
  const posRef = useRef<DockPos | null>(null);
  useEffect(() => {
    posRef.current = placement?.pos ?? null;
  }, [placement]);
  useEffect(() => {
    const frame = window.requestAnimationFrame(() => {
      let saved: DockPos | null = null;
      try {
        saved = parsePos(window.localStorage.getItem(NEXTO_POS_KEY));
      } catch {
        saved = null;
      }
      if (saved) setPos(saved);
    });
    function onResize() {
      if (posRef.current) setPos(posRef.current);
    }
    window.addEventListener("resize", onResize);
    return () => {
      window.cancelAnimationFrame(frame);
      window.removeEventListener("resize", onResize);
    };
  }, [setPos]);

  useEffect(() => () => {
    if (keyTimer.current !== null) window.clearTimeout(keyTimer.current);
  }, []);

  const save = (next: DockPos | null) => {
    try {
      if (next) window.localStorage.setItem(NEXTO_POS_KEY, JSON.stringify(next));
      else window.localStorage.removeItem(NEXTO_POS_KEY);
    } catch {
      /* private mode: position just isn't remembered */
    }
  };

  const explainHere = (next: DockPos) => {
    const box = size();
    onExplain(helpTargetAt(next.x + box.w / 2, next.y + box.h / 2, dockRef.current));
  };

  function currentPos(): DockPos {
    if (pos) return pos;
    const rect = botRef.current?.getBoundingClientRect();
    return { x: rect?.left ?? window.innerWidth - 120, y: rect?.top ?? window.innerHeight - 140 };
  }

  function onPointerDown(event: ReactPointerEvent<HTMLButtonElement>) {
    if (event.button !== 0 && event.pointerType === "mouse") return;
    const start = currentPos();
    drag.current = { id: event.pointerId, sx: event.clientX, sy: event.clientY, ox: start.x, oy: start.y, moved: false };
    // Capture right away so fast drags keep reaching the robot.
    try {
      event.currentTarget.setPointerCapture(event.pointerId);
    } catch {
      /* capture is optional */
    }
  }

  function onPointerMove(event: ReactPointerEvent<HTMLButtonElement>) {
    const state = drag.current;
    if (!state || state.id !== event.pointerId) return;
    const dx = event.clientX - state.sx;
    const dy = event.clientY - state.sy;
    if (!state.moved) {
      if (!isDrag(dx, dy)) return;
      state.moved = true;
      setDragging(true);
    }
    event.preventDefault();
    const next = clampPos({ x: state.ox + dx, y: state.oy + dy }, size(), viewport());
    setPos(next);
    // Live explanation while dragging, at most every 300 ms.
    const now = Date.now();
    if (now - liveTimer.current > 300) {
      liveTimer.current = now;
      explainHere(next);
    }
  }

  function endDrag(event: ReactPointerEvent<HTMLButtonElement>, cancelled: boolean) {
    const state = drag.current;
    if (!state || state.id !== event.pointerId) return;
    drag.current = null;
    if (!state.moved) return;
    setDragging(false);
    suppressClick.current = true;
    // Touch drags may not emit a click; never swallow the next real tap.
    window.setTimeout(() => {
      suppressClick.current = false;
    }, 250);
    const next = clampPos({ x: state.ox + event.clientX - state.sx, y: state.oy + event.clientY - state.sy }, size(), viewport());
    setPos(next);
    save(next);
    if (!cancelled) explainHere(next);
  }

  function onKeyDown(event: ReactKeyboardEvent<HTMLButtonElement>) {
    if (event.key === "Home") {
      event.preventDefault();
      setPos(null);
      save(null);
      return;
    }
    const moved = nudge(currentPos(), event.key, event.shiftKey);
    if (!moved) return;
    event.preventDefault();
    const next = clampPos(moved, size(), viewport());
    setPos(next);
    save(next);
    if (keyTimer.current !== null) window.clearTimeout(keyTimer.current);
    keyTimer.current = window.setTimeout(() => {
      keyTimer.current = null;
      explainHere(next);
    }, 350);
  }

  const side = placement?.side ?? null;
  const className = [
    "bot-dock",
    pos ? "is-placed" : "",
    dragging ? "is-dragging" : "",
    side ? `b-${side.h} b-${side.v}` : "",
  ].filter(Boolean).join(" ");

  return (
    <div ref={dockRef} className={className} style={pos ? { left: pos.x, top: pos.y, right: "auto", bottom: "auto" } : undefined}>
      {bubble}
      <button
        ref={botRef}
        type="button"
        className="bot"
        data-help-key="robot"
        aria-label={label}
        aria-describedby="nexto-drag-hint"
        title={hint}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={(event) => endDrag(event, false)}
        onPointerCancel={(event) => endDrag(event, true)}
        onKeyDown={onKeyDown}
        onClick={() => {
          if (suppressClick.current) {
            suppressClick.current = false;
            return;
          }
          onActivate();
        }}
      >
        {robot}
      </button>
      <span id="nexto-drag-hint" className="sr-only">{hint}</span>
    </div>
  );
}
