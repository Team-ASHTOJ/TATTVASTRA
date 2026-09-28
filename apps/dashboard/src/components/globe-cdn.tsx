"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type PointerEvent as ReactPointerEvent,
} from "react";
import createGlobe from "./cobe";

interface CdnMarker {
  id: string;
  location: [number, number];
  region: string;
}

interface CdnArc {
  id: string;
  from: [number, number];
  to: [number, number];
}

interface GlobeCdnProps {
  markers?: CdnMarker[];
  arcs?: CdnArc[];
  className?: string;
  speed?: number;
}

const defaultMarkers: CdnMarker[] = [
  { id: "mesh-iad", location: [38.95, -77.45], region: "IAD" },
  { id: "mesh-sfo", location: [37.62, -122.38], region: "SFO" },
  { id: "mesh-cdg", location: [49.01, 2.55], region: "CDG" },
  { id: "mesh-hnd", location: [35.55, 139.78], region: "HND" },
  { id: "mesh-syd", location: [-33.95, 151.18], region: "SYD" },
  { id: "mesh-gru", location: [-23.43, -46.47], region: "GRU" },
  { id: "mesh-sin", location: [1.36, 103.99], region: "SIN" },
  { id: "mesh-bom", location: [19.09, 72.87], region: "BOM" },
];

const defaultArcs: CdnArc[] = [
  { id: "mesh-1", from: [38.95, -77.45], to: [49.01, 2.55] },
  { id: "mesh-2", from: [37.62, -122.38], to: [35.55, 139.78] },
  { id: "mesh-3", from: [49.01, 2.55], to: [1.36, 103.99] },
  { id: "mesh-4", from: [38.95, -77.45], to: [-23.43, -46.47] },
  { id: "mesh-5", from: [35.55, 139.78], to: [-33.95, 151.18] },
  { id: "mesh-6", from: [49.01, 2.55], to: [19.09, 72.87] },
];

const seedActivity = [42, 38, 29, 18, 16, 13];

/*
  Particle (map dot) treatment.

  cobe's map shader paints every dot as the sphere's `baseColor` scaled by that
  sample's intensity, while the ocean floor sits at a flat 10% of the same
  colour. That makes baseColor the one lever that lifts the particles without
  repainting the globe body: at dot intensity it resolves to a muted antique
  gold, and at ocean intensity it is a near-black warm graphite rather than a
  gold sphere.

  The gold is deliberately desaturated — roughly hsl(38 30% 48%) at full dot
  intensity — so it reads as champagne/antique metal, not saturated yellow.
  `mapBaseBrightness` floors the sample value, which is what makes the dot
  field itself visible instead of only the continents.
*/
type Rgb = [number, number, number];

const DOT_GOLD_IDLE: Rgb = [0.38, 0.315, 0.2];
const DOT_GOLD_HOVER: Rgb = [0.43, 0.357, 0.228];
const MAP_BRIGHTNESS_IDLE = 1.7;
const MAP_BRIGHTNESS_HOVER = 1.9;
/* The floor only affects sample values the map texture leaves at zero, i.e. the
   ocean. Continent dots are driven by the texture and are unaffected by it, so
   this is the knob that decides how much the open water sparkles — kept low so
   the gold reads as landmasses rather than a gold-plated sphere. */
const MAP_BASE_IDLE = 0.13;
const MAP_BASE_HOVER = 0.17;

/* Long enough to read as a glow rather than a switch, short enough to feel
   immediate. The value is eased with a smoothstep before it drives the shader. */
const GLOW_MS = 200;

function lerp(a: number, b: number, t: number) {
  return a + (b - a) * t;
}

function lerpRgb(from: Rgb, to: Rgb, t: number): Rgb {
  return [lerp(from[0], to[0], t), lerp(from[1], to[1], t), lerp(from[2], to[2], t)];
}

function smoothstep(t: number) {
  const c = t < 0 ? 0 : t > 1 ? 1 : t;
  return c * c * (3 - 2 * c);
}

export function GlobeCdn({
  markers = defaultMarkers,
  arcs = defaultArcs,
  className = "",
  speed = 0.0018,
}: GlobeCdnProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const pointerInteracting = useRef<{ x: number; y: number } | null>(null);
  const dragOffset = useRef({ phi: 0, theta: 0 });
  const phiOffsetRef = useRef(0);
  const thetaOffsetRef = useRef(0);
  const isPausedRef = useRef(false);
  /* Kept in refs rather than state: the glow is animated per frame inside the
     existing rAF loop, and re-rendering React on every pointer enter would
     restart that loop's effect for no visual gain. */
  const isHoveredRef = useRef(false);
  const [activity, setActivity] = useState(() =>
    arcs.map((arc, index) => ({
      id: arc.id,
      value: seedActivity[index] ?? 10,
    })),
  );

  useEffect(() => {
    const reducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    if (reducedMotion) return;
    const interval = window.setInterval(() => {
      if (document.hidden) return;
      setActivity((items) =>
        items.map((item) => ({
          ...item,
          value: Math.max(5, item.value + Math.floor(Math.random() * 5) - 2),
        })),
      );
    }, 1000);
    return () => window.clearInterval(interval);
  }, []);

  const handlePointerDown = useCallback(
    (event: ReactPointerEvent<HTMLCanvasElement>) => {
      pointerInteracting.current = {
        x: event.clientX,
        y: event.clientY,
      };
      event.currentTarget.setPointerCapture(event.pointerId);
      event.currentTarget.style.cursor = "grabbing";
      isPausedRef.current = true;
    },
    [],
  );

  const handlePointerUp = useCallback(() => {
    if (pointerInteracting.current) {
      phiOffsetRef.current += dragOffset.current.phi;
      thetaOffsetRef.current += dragOffset.current.theta;
      dragOffset.current = { phi: 0, theta: 0 };
    }
    pointerInteracting.current = null;
    if (canvasRef.current) canvasRef.current.style.cursor = "grab";
    isPausedRef.current = false;
  }, []);

  /* The glow is driven by the render loop, so these only flip a flag. */
  const handlePointerEnter = useCallback(() => {
    isHoveredRef.current = true;
  }, []);

  const handlePointerLeave = useCallback(() => {
    isHoveredRef.current = false;
  }, []);

  useEffect(() => {
    const handlePointerMove = (event: PointerEvent) => {
      if (!pointerInteracting.current) return;
      dragOffset.current = {
        phi: (event.clientX - pointerInteracting.current.x) / 300,
        theta: (event.clientY - pointerInteracting.current.y) / 1000,
      };
    };
    window.addEventListener("pointermove", handlePointerMove, {
      passive: true,
    });
    window.addEventListener("pointerup", handlePointerUp, { passive: true });
    window.addEventListener("pointercancel", handlePointerUp, {
      passive: true,
    });
    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
      window.removeEventListener("pointercancel", handlePointerUp);
    };
  }, [handlePointerUp]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    let globe: ReturnType<typeof createGlobe> | null = null;
    let animationId = 0;
    let revealId = 0;
    let phi = 0;
    let currentSize = 0;
    const reducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;

    /* 0 = resting gold, 1 = fully lit. Eased toward the pointer state each frame
       over GLOW_MS, then smoothstepped so the ramp has no hard start or stop. */
    let glow = 0;
    let lastFrame = 0;

    const render = (time?: number) => {
      if (!globe) return;
      const now = typeof time === "number" ? time : performance.now();
      const delta = lastFrame === 0 ? 0 : Math.min(now - lastFrame, 100);
      lastFrame = now;

      if (!isPausedRef.current && !document.hidden && !reducedMotion) {
        phi += speed;
      }

      const target = isHoveredRef.current ? 1 : 0;
      if (glow !== target) {
        const step = delta / GLOW_MS;
        glow =
          glow < target
            ? Math.min(target, glow + step)
            : Math.max(target, glow - step);
      }
      const lit = smoothstep(glow);

      globe.update({
        phi: phi + phiOffsetRef.current + dragOffset.current.phi,
        theta: 0.2 + thetaOffsetRef.current + dragOffset.current.theta,
        baseColor: lerpRgb(DOT_GOLD_IDLE, DOT_GOLD_HOVER, lit),
        mapBrightness: lerp(MAP_BRIGHTNESS_IDLE, MAP_BRIGHTNESS_HOVER, lit),
        mapBaseBrightness: lerp(MAP_BASE_IDLE, MAP_BASE_HOVER, lit),
      });
      animationId = requestAnimationFrame(render);
    };

    const initialize = (width: number) => {
      const size = Math.round(width);
      if (size <= 0) return;
      if (globe) {
        if (size !== currentSize) {
          currentSize = size;
          globe.update({ width: size, height: size });
        }
        return;
      }
      currentSize = size;
      globe = createGlobe(canvas, {
        devicePixelRatio: Math.min(window.devicePixelRatio || 1, 2),
        width: size,
        height: size,
        phi: 0,
        theta: 0.2,
        dark: 1,
        diffuse: 1.1,
        mapSamples: 16000,
        mapBrightness: MAP_BRIGHTNESS_IDLE,
        mapBaseBrightness: MAP_BASE_IDLE,
        baseColor: DOT_GOLD_IDLE,
        markerColor: [0.37, 0.63, 0.75],
        glowColor: [0.08, 0.14, 0.18],
        markerElevation: 0.018,
        markers: markers.map((marker) => ({
          location: marker.location,
          size: 0.014,
          id: marker.id,
        })),
        arcs: arcs.map((arc) => ({
          from: arc.from,
          to: arc.to,
          id: arc.id,
        })),
        arcColor: [0.33, 0.57, 0.69],
        arcWidth: 0.46,
        arcHeight: 0.2,
        opacity: 0.86,
      });
      render();
      revealId = window.setTimeout(() => {
        canvas.style.opacity = "1";
      });
    };

    const observer = new ResizeObserver((entries) => {
      const width = entries[0]?.contentRect.width ?? canvas.offsetWidth;
      initialize(width);
    });
    observer.observe(canvas);
    initialize(canvas.offsetWidth);

    return () => {
      observer.disconnect();
      window.clearTimeout(revealId);
      cancelAnimationFrame(animationId);
      globe?.destroy();
    };
  }, [arcs, markers, speed]);

  const pyramidFaceStyle = (index: number): CSSProperties => {
    const transforms = [
      "rotateY(0deg) translateZ(4px) rotateX(19.5deg)",
      "rotateY(120deg) translateZ(4px) rotateX(19.5deg)",
      "rotateY(240deg) translateZ(4px) rotateX(19.5deg)",
      "rotateX(-90deg) rotateZ(60deg) translateY(4px)",
    ];
    const colors = ["#294d5e", "#3e7188", "#72a5ba", "#1a3441"];
    return {
      position: "absolute",
      left: -0.5,
      top: 0,
      width: 0,
      height: 0,
      borderLeft: "6.5px solid transparent",
      borderRight: "6.5px solid transparent",
      borderBottom: `13px solid ${colors[index]}`,
      transformOrigin: "center bottom",
      transform: transforms[index],
    };
  };

  return (
    <div
      className={`tc-globe ${className}`}
      onPointerEnter={handlePointerEnter}
      onPointerLeave={handlePointerLeave}
    >
      <canvas
        ref={canvasRef}
        className="tc-globe-canvas"
        aria-label="Interactive decorative global endpoint mesh"
        onPointerDown={handlePointerDown}
      />
      {markers.map((marker) => (
        <div
          key={marker.id}
          className="tc-globe-node"
          style={
            {
              positionAnchor: `--cobe-${marker.id}`,
              opacity: `var(--cobe-visible-${marker.id}, 0)`,
              filter: `blur(calc((1 - var(--cobe-visible-${marker.id}, 0)) * 8px))`,
            } as CSSProperties
          }
        >
          <span className="tc-globe-pyramid" aria-hidden="true">
            {[0, 1, 2, 3].map((index) => (
              <span key={index} style={pyramidFaceStyle(index)} />
            ))}
          </span>
          <span className="tc-globe-region">{marker.region}</span>
        </div>
      ))}
      {activity.map((item) => (
        <div
          key={item.id}
          className="tc-globe-activity"
          title="Illustrative interface activity"
          style={
            {
              positionAnchor: `--cobe-arc-${item.id}`,
              opacity: `var(--cobe-visible-arc-${item.id}, 0)`,
              filter: `blur(calc((1 - var(--cobe-visible-arc-${item.id}, 0)) * 8px))`,
            } as CSSProperties
          }
        >
          {item.value} events/s
        </div>
      ))}
    </div>
  );
}
