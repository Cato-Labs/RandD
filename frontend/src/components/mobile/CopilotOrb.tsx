import { cn } from "@/lib/utils";
import type { PersonaState } from "@/lib/live-types";

/**
 * The Vantage co-pilot orb — a glossy green sphere inside soft concentric
 * halo rings. Pure CSS (see index.css .copilot-orb) so it never blocks the
 * main thread the way the WebGL Rive persona does. Rings animate only when
 * the agent is actively listening/speaking/thinking.
 */
export function CopilotOrb({
  state,
  size = 168,
  className,
}: {
  state: PersonaState;
  size?: number;
  className?: string;
}) {
  const live = state === "listening" || state === "speaking" || state === "thinking";
  return (
    <div
      aria-label={`Vantage ${state}`}
      className={cn("copilot-orb", className)}
      role="img"
      style={{ ["--orb-size" as string]: `${size}px` }}
      data-state={state}
    >
      <div className="copilot-orb__halo" />
      <div className={cn("copilot-orb__ring r3", live && "pulse d")} />
      <div className={cn("copilot-orb__ring r2", live && "pulse")} />
      <div className="copilot-orb__ring" />
      <div className="copilot-orb__ball" />
    </div>
  );
}
