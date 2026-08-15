"use client";

/**
 * The opening illustration: two robots working through a specification alongside
 * the person who wrote it.
 *
 * Drawn as inline SVG rather than pulled from a 3D component library — the scene
 * is decorative, so it should not cost a WebGL runtime on first paint. Everything
 * moves through the CSS keyframes in globals.css, which means the whole thing
 * stops dead under prefers-reduced-motion without any JavaScript branch.
 *
 * The scene is `aria-hidden`: it carries no information that isn't already in the
 * heading beside it, so announcing it would only add noise for screen readers.
 */

/** One robot. `side` mirrors the gesturing arm so both robots reach inward. */
function Robot({
  x,
  y,
  side,
  hue,
  delay,
}: {
  x: number;
  y: number;
  side: "left" | "right";
  hue: string;
  delay: number;
}) {
  const inward = side === "left" ? 1 : -1;

  return (
    <g transform={`translate(${x} ${y})`}>
      <g className="sg-float" style={{ "--sg-delay": `${delay}s` } as React.CSSProperties}>
        {/* Antenna, with a beacon that pulses on its own cycle */}
        <line x1="55" y1="8" x2="55" y2="-10" stroke={hue} strokeWidth="2.5" strokeLinecap="round" />
        <circle
          className="sg-beacon"
          style={{ "--sg-delay": `${delay}s` } as React.CSSProperties}
          cx="55"
          cy="-14"
          r="4.5"
          fill={hue}
        />

        {/* Head */}
        <rect x="24" y="8" width="62" height="46" rx="15" fill="#182031" stroke={hue} strokeWidth="2" />
        {/* Visor */}
        <rect x="33" y="20" width="44" height="21" rx="10" fill="#0a0d15" />
        {/* Eyes */}
        <g
          className="sg-blink"
          style={{ "--sg-delay": `${delay + 0.4}s`, transformOrigin: `55px 30px` } as React.CSSProperties}
        >
          <circle cx="46" cy="30" r="4.6" fill={hue} />
          <circle cx="64" cy="30" r="4.6" fill={hue} />
        </g>

        {/* Neck */}
        <rect x="49" y="54" width="12" height="7" fill="#182031" stroke={hue} strokeWidth="1.5" />

        {/* Torso */}
        <rect x="17" y="61" width="76" height="58" rx="17" fill="#141b2a" stroke={hue} strokeWidth="2" />

        {/* Chest reactor: a steady core inside an expanding ring */}
        <circle cx="55" cy="88" r="10" fill="none" stroke={hue} strokeWidth="1.6" opacity="0.45" />
        <circle
          className="sg-ripple"
          style={{ "--sg-delay": `${delay}s`, transformOrigin: "55px 88px" } as React.CSSProperties}
          cx="55"
          cy="88"
          r="10"
          fill="none"
          stroke={hue}
          strokeWidth="1.6"
        />
        <circle cx="55" cy="88" r="4.5" fill={hue} />

        {/* Outer arm rests; inner arm gestures toward the document */}
        <path
          d={`M ${side === "left" ? 17 : 93} 74 q ${inward * -14} 16 ${inward * -10} 30`}
          fill="none"
          stroke={hue}
          strokeWidth="5"
          strokeLinecap="round"
          opacity="0.75"
        />
        <g
          className="sg-wave"
          style={
            {
              "--sg-delay": `${delay + 0.2}s`,
              transformOrigin: `${side === "left" ? 93 : 17}px 74px`,
            } as React.CSSProperties
          }
        >
          <path
            d={`M ${side === "left" ? 93 : 17} 74 q ${inward * 20} 6 ${inward * 30} -12`}
            fill="none"
            stroke={hue}
            strokeWidth="5"
            strokeLinecap="round"
          />
          <circle cx={side === "left" ? 125 : -15} cy="62" r="5" fill={hue} />
        </g>

        {/* Hover pad — these robots float, so no legs */}
        <ellipse cx="55" cy="130" rx="30" ry="6" fill={hue} opacity="0.18" />
        <ellipse cx="55" cy="130" rx="16" ry="3" fill={hue} opacity="0.35" />
      </g>
    </g>
  );
}

/** The person the robots are working with: mid-hand-off of their spec document. */
function Person({ x, y }: { x: number; y: number }) {
  const skin = "#f0b088";
  const cloth = "#4b8eff";

  return (
    <g transform={`translate(${x} ${y})`}>
      <g className="sg-float-soft" style={{ "--sg-delay": "0.6s" } as React.CSSProperties}>
        {/* Head and hair */}
        <circle cx="0" cy="-52" r="15" fill={skin} />
        <path d="M -15 -56 q 3 -16 15 -16 q 12 0 15 16 q -8 -7 -15 -6 q -8 -1 -15 6 Z" fill="#2a2f3d" />

        {/* Torso */}
        <path d="M -16 -36 q 16 -6 32 0 l 6 44 q -22 7 -44 0 Z" fill={cloth} />

        {/* Legs */}
        <path d="M -10 8 l -3 34" stroke="#2a2f3d" strokeWidth="9" strokeLinecap="round" />
        <path d="M 10 8 l 3 34" stroke="#2a2f3d" strokeWidth="9" strokeLinecap="round" />

        {/* Both arms raised, holding the document up to the robots */}
        <path d="M -16 -32 q -16 -12 -20 -30" stroke={skin} strokeWidth="8" strokeLinecap="round" fill="none" />
        <path d="M 16 -32 q 16 -12 20 -30" stroke={skin} strokeWidth="8" strokeLinecap="round" fill="none" />
      </g>
    </g>
  );
}

/** The document under inspection, with a scan line sweeping it and findings landing. */
function Document({ x, y }: { x: number; y: number }) {
  const lines = [0, 1, 2, 3, 4, 5];

  return (
    <g transform={`translate(${x} ${y})`}>
      <g className="sg-float" style={{ "--sg-delay": "0.3s" } as React.CSSProperties}>
        {/* Sheet */}
        <rect x="-46" y="-58" width="92" height="118" rx="7" fill="#111726" stroke="#334155" strokeWidth="2" />

        {/* Folded corner */}
        <path d="M 30 -58 l 16 16 l -16 0 Z" fill="#1c2537" />

        {/* Text lines, drawn on one after another */}
        {lines.map((i) => (
          <rect
            key={i}
            className="sg-draw"
            style={
              {
                "--sg-delay": `${0.9 + i * 0.09}s`,
                strokeDasharray: 70,
                strokeDashoffset: 70,
              } as React.CSSProperties
            }
            x="-33"
            y={-36 + i * 15}
            width={i % 3 === 2 ? 40 : 66}
            height="5"
            rx="2.5"
            fill="none"
            stroke="#475569"
            strokeWidth="5"
          />
        ))}

        {/* Scanner sweep */}
        <g clipPath="url(#sg-doc-clip)">
          <rect
            className="sg-scan"
            x="-46"
            y="-58"
            width="92"
            height="3"
            fill="#4b8eff"
            style={{ filter: "drop-shadow(0 0 6px #4b8eff)" }}
          />
        </g>
      </g>
    </g>
  );
}

/** A finding the robots surfaced, popping in beside the document. */
function Finding({
  x,
  y,
  color,
  delay,
  label,
}: {
  x: number;
  y: number;
  color: string;
  delay: number;
  label: string;
}) {
  // The positioning `transform` attribute and the animated CSS `transform` must
  // live on different elements: a CSS transform overrides the presentation
  // attribute outright rather than composing with it, so sharing one element
  // would drop the translate the moment the animation started.
  // Sized from the label rather than fixed: JetBrains Mono advances ~0.6em, so
  // at 11px each character is ~6.7px wide, plus room for the dot and padding.
  const w = 38 + label.length * 6.7;

  return (
    <g transform={`translate(${x} ${y})`}>
      <g
        className="sg-pop"
        style={
          {
            "--sg-delay": `${delay}s`,
            transformBox: "fill-box",
            transformOrigin: "center",
          } as React.CSSProperties
        }
      >
        <g className="sg-float-soft" style={{ "--sg-delay": `${delay}s` } as React.CSSProperties}>
          <rect x={-w / 2} y="-13" width={w} height="26" rx="13" fill="#141b2a" stroke={color} strokeWidth="1.5" />
          <circle cx={-w / 2 + 14} cy="0" r="4.5" fill={color} />
          <text
            x={-w / 2 + 24}
            y="4"
            fill={color}
            fontSize="11"
            fontFamily="var(--font-jetbrains), monospace"
            letterSpacing="0.5"
          >
            {label}
          </text>
        </g>
      </g>
    </g>
  );
}

export function RobotScene({ className = "" }: { className?: string }) {
  // Rising particles. Positions are fixed rather than random so the server and
  // client render identical markup and React does not report a hydration mismatch.
  const sparks = [
    [70, 300, 0], [140, 340, 1.4], [230, 320, 2.6], [300, 350, 0.7],
    [420, 330, 3.2], [500, 310, 1.9], [575, 345, 2.2], [650, 325, 0.4],
    [110, 250, 3.8], [610, 265, 4.3],
  ] as const;

  return (
    <svg
      viewBox="0 0 720 400"
      className={className}
      role="presentation"
      aria-hidden="true"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <clipPath id="sg-doc-clip">
          <rect x="-46" y="-58" width="92" height="118" rx="7" />
        </clipPath>
        <radialGradient id="sg-glow-a" cx="50%" cy="50%">
          <stop offset="0%" stopColor="#4b8eff" stopOpacity="0.30" />
          <stop offset="100%" stopColor="#4b8eff" stopOpacity="0" />
        </radialGradient>
        <radialGradient id="sg-glow-b" cx="50%" cy="50%">
          <stop offset="0%" stopColor="#7ee2b8" stopOpacity="0.22" />
          <stop offset="100%" stopColor="#7ee2b8" stopOpacity="0" />
        </radialGradient>
        <linearGradient id="sg-floor" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#4b8eff" stopOpacity="0" />
          <stop offset="50%" stopColor="#4b8eff" stopOpacity="0.5" />
          <stop offset="100%" stopColor="#4b8eff" stopOpacity="0" />
        </linearGradient>
        <pattern id="sg-grid" width="36" height="36" patternUnits="userSpaceOnUse">
          <path d="M 36 0 L 0 0 0 36" fill="none" stroke="#1c2331" strokeWidth="1" />
        </pattern>
        {/* Without this the grid ends on a hard rectangular edge and reads as a
            box pasted onto the page rather than as depth behind the scene. */}
        <radialGradient id="sg-grid-fade" cx="50%" cy="50%">
          <stop offset="35%" stopColor="#fff" stopOpacity="0.55" />
          <stop offset="100%" stopColor="#fff" stopOpacity="0" />
        </radialGradient>
        <mask id="sg-grid-mask">
          <rect width="720" height="400" fill="url(#sg-grid-fade)" />
        </mask>
      </defs>

      {/* Backdrop: grid, then two drifting glows */}
      <rect width="720" height="400" fill="url(#sg-grid)" mask="url(#sg-grid-mask)" />
      <ellipse className="sg-drift" cx="200" cy="180" rx="180" ry="150" fill="url(#sg-glow-a)" />
      <ellipse
        className="sg-drift"
        style={{ "--sg-delay": "-6s" } as React.CSSProperties}
        cx="530"
        cy="200"
        rx="170"
        ry="150"
        fill="url(#sg-glow-b)"
      />

      {/* Rising motes */}
      {sparks.map(([cx, cy, delay], i) => (
        <circle
          key={i}
          className="sg-spark"
          style={{ "--sg-delay": `${delay}s` } as React.CSSProperties}
          cx={cx}
          cy={cy}
          r={i % 3 === 0 ? 2.4 : 1.6}
          fill={i % 2 === 0 ? "#4b8eff" : "#7ee2b8"}
        />
      ))}

      {/* Floor */}
      <rect x="60" y="352" width="600" height="2" fill="url(#sg-floor)" />

      {/* Wires carrying data from each robot to the document */}
      <g stroke="#4b8eff" strokeWidth="1.5" opacity="0.28" fill="none">
        <path d="M 200 200 C 250 190 280 165 305 150" />
        <path d="M 520 200 C 470 190 440 165 415 150" />
      </g>
      {[0, 0.6, 1.2].map((delay, i) => (
        <circle
          key={`l${i}`}
          className="sg-travel"
          style={{ "--sg-delay": `${delay}s`, "--sg-dx": "105px", "--sg-dy": "-50px" } as React.CSSProperties}
          cx="200"
          cy="200"
          r="3"
          fill="#4b8eff"
        />
      ))}
      {[0.3, 0.9, 1.5].map((delay, i) => (
        <circle
          key={`r${i}`}
          className="sg-travel"
          style={{ "--sg-delay": `${delay}s`, "--sg-dx": "-105px", "--sg-dy": "-50px" } as React.CSSProperties}
          cx="520"
          cy="200"
          r="3"
          fill="#7ee2b8"
        />
      ))}

      {/* Cast */}
      <g className="sg-slide-left" style={{ "--sg-delay": "0.15s" } as React.CSSProperties}>
        <Robot x={90} y={150} side="left" hue="#4b8eff" delay={0} />
      </g>
      <g className="sg-slide-right" style={{ "--sg-delay": "0.3s" } as React.CSSProperties}>
        <Robot x={475} y={150} side="right" hue="#7ee2b8" delay={0.8} />
      </g>
      <g className="sg-rise" style={{ "--sg-delay": "0.55s" } as React.CSSProperties}>
        <Person x={360} y={300} />
      </g>
      <g className="sg-rise" style={{ "--sg-delay": "0.75s" } as React.CSSProperties}>
        <Document x={360} y={150} />
      </g>

      {/* What the robots found */}
      <Finding x={175} y={78} color="#ffa657" delay={1.9} label="AMBIGUOUS" />
      <Finding x={548} y={74} color="#ff8a80" delay={2.15} label="SEC GAP" />
      <Finding x={150} y={312} color="#7ee2b8" delay={2.4} label="TESTABLE" />
      <Finding x={575} y={308} color="#ffd479" delay={2.65} label="CONFLICT" />
    </svg>
  );
}
