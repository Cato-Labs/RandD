import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/** Tracked small-caps metadata label. */
export function Eyebrow({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return <p className={cn("eyebrow", className)}>{children}</p>;
}

/**
 * Asset-free property "photo" — a layered duotone gradient with a faint
 * architectural horizon. Keeps the app self-contained (no external images)
 * while still giving each property a distinct, editorial hero.
 */
export function PropertyTone({
  tone,
  className,
  children,
}: {
  tone: [string, string];
  className?: string;
  children?: ReactNode;
}) {
  const [a, b] = tone;
  return (
    <div className={cn("relative overflow-hidden", className)}>
      <div
        className="absolute inset-0"
        style={{
          background: `linear-gradient(160deg, ${a} 0%, ${b} 78%)`,
        }}
      />
      <div
        className="absolute inset-0 opacity-60"
        style={{
          background:
            "radial-gradient(120% 80% at 20% 0%, rgba(255,255,255,0.22), transparent 55%)",
        }}
      />
      <div
        className="absolute inset-x-0 bottom-0 h-1/2 opacity-40"
        style={{
          background:
            "linear-gradient(to top, rgba(0,0,0,0.5), transparent), repeating-linear-gradient(90deg, transparent 0 46px, rgba(255,255,255,0.05) 46px 47px)",
        }}
      />
      {children}
    </div>
  );
}

/** Status chip with a soft, low-saturation tint (concierge, not "tax form"). */
export function Chip({
  children,
  tone = "neutral",
  className,
}: {
  children: ReactNode;
  tone?: "neutral" | "gold" | "moss" | "forest";
  className?: string;
}) {
  const tones: Record<string, string> = {
    neutral: "bg-cream-100 text-ink-soft",
    gold: "bg-gold-soft text-[#7a5c17]",
    moss: "bg-[#e2efe6] text-[#245c3a]",
    forest: "bg-forest-800 text-sage-200",
  };
  return (
    <span
      className={cn(
        "eyebrow inline-flex items-center gap-1.5 rounded-full px-3 py-1",
        tones[tone],
        className
      )}
    >
      {children}
    </span>
  );
}
