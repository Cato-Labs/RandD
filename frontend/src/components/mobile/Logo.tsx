import { cn } from "@/lib/utils";

/**
 * Vantage brand logo — the circular crest: an arched portal holding a serif "V"
 * beneath a gold sparkle, two figures at a balustrade. Rebuilt as a scalable SVG
 * so it stays crisp from a 28px glyph to a full sign-in hero.
 *
 * `background` draws the forest roundel (the app-icon lockup); omit it to place
 * the line-art crest on an existing dark surface. Line work is cream; the
 * sparkle is brand gold.
 */
export function Logo({
  size = 96,
  className,
  background = true,
  detail = true,
  ink = "#f4ede3",
  gold = "#cf9f43",
  forest = "#16271f",
}: {
  size?: number;
  className?: string;
  background?: boolean;
  detail?: boolean;
  ink?: string;
  gold?: string;
  forest?: string;
}) {
  return (
    <svg
      aria-label="Vantage"
      className={cn(className)}
      fill="none"
      height={size}
      role="img"
      viewBox="0 0 200 200"
      width={size}
      xmlns="http://www.w3.org/2000/svg"
    >
      {background && <circle cx="100" cy="100" r="100" fill={forest} />}

      {/* Arched portal */}
      <path
        d="M56 158 V96 C56 62 76 44 100 44 C124 44 144 62 144 96 V158"
        stroke={ink}
        strokeWidth="3.4"
        strokeLinecap="round"
      />

      {/* Gold sparkle */}
      <path
        d="M100 52 L103.5 74 L125 78 L103.5 82 L100 104 L96.5 82 L75 78 L96.5 74 Z"
        fill={gold}
      />

      {/* Serif V — the heart of the crest */}
      <text
        x="100"
        y="139"
        fill={ink}
        fontFamily="'EB Garamond', Georgia, serif"
        fontSize="76"
        fontWeight="500"
        textAnchor="middle"
      >
        V
      </text>

      {detail && (
        <g stroke={ink} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" opacity="0.82">
          {/* Two figures flanking the V */}
          <g>
            <circle cx="74" cy="120" r="4.6" />
            <path d="M69.5 130 C69.5 124 78.5 124 78.5 130 L77.5 146 L70.5 146 Z" />
          </g>
          <g>
            <circle cx="126" cy="120" r="4.6" />
            <path d="M121.5 130 C121.5 124 130.5 124 130.5 130 L129.5 146 L122.5 146 Z" />
          </g>

          {/* Balustrade */}
          <path d="M60 150 H140" strokeWidth="2.4" />
          <path d="M68 152 V158 M84 152 V158 M100 152 V158 M116 152 V158 M132 152 V158" strokeWidth="3" />
          <path d="M58 159 H142" strokeWidth="2.4" />
        </g>
      )}
    </svg>
  );
}
