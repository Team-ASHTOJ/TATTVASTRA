"use client";

import { useEffect, useRef } from "react";

/*
  Site-wide Particle Drift background.

  Three things drift behind the interface: monospace characters rising slowly,
  faint proximity links between them, and sparse vertical light shafts. A few
  characters brighten to a steel-blue highlight now and then, and the cursor
  pulls a soft local cluster toward it.

  It is ambience, not decoration — it has to be legible as *something* when you
  look at empty page space, while never competing with the UI in front of it.
  The layer is fixed, pointer-events:none and aria-hidden, so it can never
  affect layout, scrolling or hit-testing. Under prefers-reduced-motion it
  paints one static frame and never starts the loop.
*/

/* Technical-looking ASCII: digits, brackets and operators read as instrumentation. */
const GLYPHS = "01<>/\\|=+*#%@$&{}[]()ABCDEFXZabcdefxk0123456789:;._-";

const GLYPH_INK = "125, 150, 165";
const HIGHLIGHT_INK = "95, 155, 185";
const LINK_INK = "115, 145, 165";
const BEAM_INK = "75, 135, 165";

const LINK_DISTANCE = 132;
const MOUSE_RADIUS = 150;
const FRAME_MS = 1000 / 30;

type Glyph = {
  x: number;
  y: number;
  vx: number;
  vy: number;
  char: string;
  alpha: number;
  highlight: number;
  nextMutation: number;
};

type Beam = {
  x: number;
  y: number;
  w: number;
  h: number;
  vx: number;
  vy: number;
  alpha: number;
  phase: number;
};

type Field = {
  glyphs: Glyph[];
  beams: Beam[];
  fontSize: number;
};

function rgba(ink: string, alpha: number) {
  return `rgba(${ink}, ${alpha.toFixed(4)})`;
}

function pickChar() {
  return GLYPHS[(Math.random() * GLYPHS.length) | 0] ?? "0";
}

/* Node and beam counts scale down on narrow viewports to keep the layer cheap
   and to avoid crowding a small screen. */
function counts(width: number) {
  if (width < 760) return { glyphs: 24, beams: 5, fontSize: 10 };
  if (width < 1280) return { glyphs: 38, beams: 8, fontSize: 10 };
  return { glyphs: 50, beams: 11, fontSize: 11 };
}

export function AtmosphereField() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const element = canvasRef.current;
    if (!element) return;

    // Explicitly typed so the closures below keep the non-null narrowing.
    const canvas: HTMLCanvasElement = element;

    const context = canvas.getContext("2d");
    if (!context) return;

    const ctx: CanvasRenderingContext2D = context;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");

    let width = 0;
    let height = 0;
    let field: Field = { glyphs: [], beams: [], fontSize: 11 };
    let raf = 0;
    let lastPaint = 0;
    let elapsed = 0;
    let pointerX: number | null = null;
    let pointerY: number | null = null;

    function seed() {
      const shape = counts(width);
      field = {
        fontSize: shape.fontSize,
        glyphs: Array.from({ length: shape.glyphs }, () => ({
          x: Math.random() * width,
          y: Math.random() * height,
          // Roughly 5-14px per second: slow enough to read as drift, not motion.
          vx: (Math.random() - 0.5) * 0.05,
          vy: -(0.08 + Math.random() * 0.16),
          char: pickChar(),
          alpha: 0.21 + Math.random() * 0.09,
          highlight: 0,
          nextMutation: Math.random() * 3000,
        })),
        beams: Array.from({ length: shape.beams }, () => {
          const h = 130 + Math.random() * 190;
          return {
            x: Math.random() * width,
            y: Math.random() * height,
            w: h * (0.5 + Math.random() * 0.5),
            h,
            vx: 0.04 + Math.random() * 0.07,
            vy: -(0.05 + Math.random() * 0.09),
            alpha: 0.105 + Math.random() * 0.065,
            phase: Math.random() * Math.PI * 2,
          };
        }),
      };
    }

    function paint() {
      ctx.clearRect(0, 0, width, height);

      /* Vertical signal streaks. A full-height gradient column reads as a stage
         curtain, so each beam is an elongated radial glow: drawing a circle
         under a horizontal squash gives an ellipse whose falloff is soft in
         both axes, and it drifts rather than standing still. */
      for (const beam of field.beams) {
        const shimmer = 0.78 + 0.22 * Math.sin(elapsed * 0.00019 + beam.phase);
        const peak = beam.alpha * shimmer;
        ctx.save();
        ctx.translate(beam.x, beam.y);
        ctx.scale(beam.w / 2 / beam.h, 1);
        const gradient = ctx.createRadialGradient(0, 0, 0, 0, 0, beam.h);
        gradient.addColorStop(0, rgba(BEAM_INK, peak));
        gradient.addColorStop(0.42, rgba(BEAM_INK, peak * 0.4));
        gradient.addColorStop(1, rgba(BEAM_INK, 0));
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(0, 0, beam.h, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      }

      const { glyphs } = field;

      ctx.lineWidth = 1;
      for (let i = 0; i < glyphs.length; i += 1) {
        const a = glyphs[i];
        if (!a) continue;
        for (let j = i + 1; j < glyphs.length; j += 1) {
          const b = glyphs[j];
          if (!b) continue;
          const distance = Math.hypot(a.x - b.x, a.y - b.y);
          if (distance > LINK_DISTANCE) continue;
          ctx.strokeStyle = rgba(LINK_INK, (1 - distance / LINK_DISTANCE) * 0.115);
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.stroke();
        }
      }

      // Cursor cluster: a short-lived local web that keeps the field feeling live.
      if (pointerX !== null && pointerY !== null) {
        for (const g of glyphs) {
          const distance = Math.hypot(g.x - pointerX, g.y - pointerY);
          if (distance > MOUSE_RADIUS) continue;
          ctx.strokeStyle = rgba(HIGHLIGHT_INK, (1 - distance / MOUSE_RADIUS) * 0.085);
          ctx.beginPath();
          ctx.moveTo(g.x, g.y);
          ctx.lineTo(pointerX, pointerY);
          ctx.stroke();
        }
      }

      ctx.font = `${field.fontSize}px Consolas, "Cascadia Mono", ui-monospace, monospace`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";

      for (const g of glyphs) {
        const near =
          pointerX === null || pointerY === null
            ? 0
            : Math.max(0, 1 - Math.hypot(g.x - pointerX, g.y - pointerY) / MOUSE_RADIUS);

        // Highlights sweep the resting alpha up toward the bright tier.
        const lit = Math.min(1, g.highlight + near * 0.5);
        const alpha = g.alpha + (0.4 - g.alpha) * lit;
        ctx.fillStyle = rgba(lit > 0.34 ? HIGHLIGHT_INK : GLYPH_INK, alpha);
        ctx.fillText(g.char, g.x, g.y);
      }
    }

    function advance(delta: number) {
      for (const g of field.glyphs) {
        g.x += g.vx * delta;
        g.y += g.vy * delta;

        if (g.y < -24) {
          g.y = height + 24;
          g.x = Math.random() * width;
        }
        if (g.x < -24) g.x = width + 24;
        else if (g.x > width + 24) g.x = -24;

        if (g.highlight > 0) g.highlight = Math.max(0, g.highlight - delta * 0.012);
        else if (Math.random() < 0.0011 * delta) g.highlight = 1;

        g.nextMutation -= delta * 16.667;
        if (g.nextMutation <= 0) {
          g.char = pickChar();
          g.nextMutation = 1400 + Math.random() * 2800;
        }
      }

      for (const beam of field.beams) {
        beam.x += beam.vx * delta;
        beam.y += beam.vy * delta;
        if (beam.x - beam.w / 2 > width) beam.x = -beam.w / 2;
        if (beam.y + beam.h < 0) {
          beam.y = height + beam.h;
          beam.x = Math.random() * width;
        }
      }
    }

    function frame(now: number) {
      raf = requestAnimationFrame(frame);
      if (now - lastPaint < FRAME_MS) return;
      const delta = lastPaint === 0 ? 1 : Math.min((now - lastPaint) / 16.667, 3);
      lastPaint = now;
      elapsed = now;
      advance(delta);
      paint();
    }

    function start() {
      if (raf || reduced.matches) return;
      lastPaint = 0;
      raf = requestAnimationFrame(frame);
    }

    function stop() {
      if (!raf) return;
      cancelAnimationFrame(raf);
      raf = 0;
    }

    function resize() {
      const ratio = Math.min(window.devicePixelRatio || 1, 1.5);
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = Math.round(width * ratio);
      canvas.height = Math.round(height * ratio);
      ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
      seed();
      paint();
    }

    let resizeTimer = 0;
    function onResize() {
      window.clearTimeout(resizeTimer);
      resizeTimer = window.setTimeout(resize, 180);
    }

    function onPointerMove(event: PointerEvent) {
      pointerX = event.clientX;
      pointerY = event.clientY;
    }

    function onPointerLeave() {
      pointerX = null;
      pointerY = null;
    }

    function onVisibilityChange() {
      if (document.hidden) stop();
      else start();
    }

    // Reduced-motion can be toggled while the page is open.
    function onMotionPreferenceChange() {
      stop();
      paint();
      start();
    }

    resize();
    start();

    window.addEventListener("resize", onResize);
    window.addEventListener("pointermove", onPointerMove, { passive: true });
    document.addEventListener("pointerleave", onPointerLeave);
    document.addEventListener("visibilitychange", onVisibilityChange);
    reduced.addEventListener("change", onMotionPreferenceChange);

    return () => {
      stop();
      window.clearTimeout(resizeTimer);
      window.removeEventListener("resize", onResize);
      window.removeEventListener("pointermove", onPointerMove);
      document.removeEventListener("pointerleave", onPointerLeave);
      document.removeEventListener("visibilitychange", onVisibilityChange);
      reduced.removeEventListener("change", onMotionPreferenceChange);
    };
  }, []);

  return (
    <div className="atmosphere-field" aria-hidden="true">
      <canvas ref={canvasRef} />
    </div>
  );
}
