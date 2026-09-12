"use client";

/**
 * Motion helpers shared by the editing and interview screens.
 *
 * Two libraries, each doing what it is actually better at:
 *
 * - anime.js drives the 3D card flip and the staggered ledger rows. Its
 *   stagger and per-property easing are terser than hand-rolled keyframes,
 *   and it animates real `rotateY` on a `preserve-3d` subtree.
 * - GSAP drives the publish sequence, which is several overlapping tweens on
 *   different elements that must stay in step. A timeline expresses that; a
 *   chain of CSS transitions with matching delays does not survive editing.
 *
 * Everything here is a no-op when the visitor asks for reduced motion, and
 * every helper leaves the element at its final state rather than mid-tween --
 * an animation that never runs must not leave the UI half-built.
 */

import { animate, stagger } from "animejs";
import { gsap } from "gsap";

export function prefersReducedMotion(): boolean {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/**
 * Bring a group of form fields in with a slight depth offset.
 *
 * The translateZ is what separates this from a fade: fields arrive from
 * behind the card plane, which reads as the form assembling rather than
 * items appearing in a list.
 */
export function revealFields(targets: string | Element[], root?: Element) {
  if (prefersReducedMotion()) return;
  animate(targets, {
    opacity: [0, 1],
    translateY: [10, 0],
    translateZ: [-40, 0],
    duration: 460,
    delay: stagger(38, { start: 60 }),
    ease: "outCubic",
    ...(root ? {} : {}),
  });
}

/**
 * Flip the comparison card between its published and draft faces.
 *
 * A real rotation on a preserve-3d subtree rather than a crossfade: the two
 * faces are the same object seen from two sides, which is precisely the
 * relationship between a published posting and an unsaved edit of it.
 */
export function flipCard(el: Element, toDraft: boolean) {
  const deg = toDraft ? 180 : 0;
  if (prefersReducedMotion()) {
    (el as HTMLElement).style.transform = `rotateY(${deg}deg)`;
    return;
  }
  animate(el, {
    rotateY: deg,
    duration: 720,
    ease: "outExpo",
  });
}

/** A single ledger row arriving as a change is made. */
export function revealLedgerRow(el: Element) {
  if (prefersReducedMotion()) return;
  animate(el, {
    opacity: [0, 1],
    translateX: [-8, 0],
    duration: 300,
    ease: "outQuad",
  });
}

/**
 * The publish sequence: the ledger settles, the card returns to its
 * published face, and the badge acknowledges.
 *
 * Returns a promise so the caller can navigate only once the confirmation has
 * actually been seen, instead of guessing with a setTimeout.
 */
export function playPublishSequence(opts: {
  ledger: Element | null;
  card: Element | null;
  badge: Element | null;
}): Promise<void> {
  const { ledger, card, badge } = opts;

  if (prefersReducedMotion()) {
    if (card) (card as HTMLElement).style.transform = "rotateY(0deg)";
    return Promise.resolve();
  }

  return new Promise((resolve) => {
    const tl = gsap.timeline({ onComplete: () => resolve() });

    if (ledger) {
      tl.to(ledger, {
        opacity: 0,
        y: -6,
        duration: 0.28,
        ease: "power2.in",
      });
    }
    if (card) {
      tl.to(
        card,
        { rotateY: 0, duration: 0.6, ease: "expo.out" },
        ledger ? "-=0.1" : 0,
      );
    }
    if (badge) {
      tl.fromTo(
        badge,
        { scale: 0.9, opacity: 0 },
        { scale: 1, opacity: 1, duration: 0.34, ease: "back.out(2)" },
        "-=0.34",
      );
    }
    // A timeline with no targets completes immediately; resolve anyway.
    if (!ledger && !card && !badge) resolve();
  });
}

/**
 * Lift a card slightly toward the viewer on pointer focus.
 *
 * Used on interview cards, where the tilt tracks the pointer so the card
 * reads as a physical object -- appropriate for a screen whose job is to
 * make a scheduled meeting feel real rather than like a database row.
 */
export function attachTilt(el: HTMLElement, maxDeg = 5) {
  if (prefersReducedMotion()) return () => {};

  const onMove = (e: PointerEvent) => {
    const r = el.getBoundingClientRect();
    const px = (e.clientX - r.left) / r.width - 0.5;
    const py = (e.clientY - r.top) / r.height - 0.5;
    gsap.to(el, {
      rotateY: px * maxDeg * 2,
      rotateX: -py * maxDeg * 2,
      duration: 0.4,
      ease: "power2.out",
      transformPerspective: 900,
    });
  };
  const onLeave = () => {
    gsap.to(el, { rotateY: 0, rotateX: 0, duration: 0.6, ease: "elastic.out(1, 0.6)" });
  };

  el.addEventListener("pointermove", onMove);
  el.addEventListener("pointerleave", onLeave);
  return () => {
    el.removeEventListener("pointermove", onMove);
    el.removeEventListener("pointerleave", onLeave);
    gsap.killTweensOf(el);
  };
}
