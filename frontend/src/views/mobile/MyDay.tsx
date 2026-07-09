import { useState } from "react";
import {
  CalendarCheckIcon,
  CheckIcon,
  ClipboardIcon,
  InfoIcon,
  KeyRoundIcon,
  MapPinIcon,
  SparklesIcon,
  WifiIcon,
} from "lucide-react";
import { Chip, Eyebrow, PropertyTone, WorkspaceCrest } from "@/components/mobile/bits";
import { cn } from "@/lib/utils";
import type { Stop, Workspace } from "@/lib/tenancy";

const TODAY = new Date("2026-07-09T09:41:00").toLocaleDateString("en-US", {
  weekday: "short",
  month: "short",
  day: "numeric",
});

export function MyDay({
  workspace,
  stops,
  onStartQC,
  onOpenChat,
}: {
  workspace: Workspace;
  stops: Stop[];
  onStartQC: (stop: Stop) => void;
  onOpenChat: () => void;
}) {
  const active = stops.find((s) => s.status === "arrived") ?? stops[0];
  const later = stops.filter((s) => s.id !== active.id);
  const checkpoints = active.sections.reduce((n, s) => n + s.checkpoints.length, 0);

  return (
    <div className="bg-cream">
      {/* ── Forest arrival header ─────────────────────────────────────────── */}
      <header className="on-forest relative bg-forest-950 px-6 pb-16 pt-12 text-sage-200">
        <div className="flex items-center justify-between gap-3">
          <div className="flex min-w-0 flex-1 items-center gap-2.5">
            <WorkspaceCrest workspace={workspace} size={30} />
            <span className="truncate text-sm font-medium text-sage-200">
              {workspace.name}
            </span>
          </div>
          <span className="eyebrow shrink-0 whitespace-nowrap text-sage-400">
            {TODAY}
          </span>
        </div>

        <div className="mt-7">
          <span className="inline-flex items-center gap-2 rounded-full bg-gold px-3.5 py-1.5">
            <span className="size-1.5 rounded-full bg-[#231a06]" />
            <span className="eyebrow text-[#231a06]">
              You've arrived · Stop {active.order} of {stops.length}
            </span>
          </span>
          <h1 className="mt-4 font-display text-[clamp(2rem,8.5vw,2.7rem)] leading-[1.02] tracking-tight text-cream">
            {active.propertyName}
          </h1>
          <p className="mt-2 flex items-center gap-1.5 text-sage-300">
            <MapPinIcon className="size-4 shrink-0" />
            <span className="truncate">
              {active.street} · {active.cluster} · {active.unitCode}
            </span>
          </p>
        </div>
      </header>

      {/* ── Cream operational content, overlapping the header ─────────────── */}
      <div className="relative -mt-8 rounded-t-[2rem] bg-cream px-5 pb-8 pt-6">
        <DoorCode code={active.doorCode} />

        <div className="mt-4 grid grid-cols-2 gap-3">
          <MetaCard
            icon={<SparklesIcon className="size-4" />}
            label="Cleaned by"
            value={active.cleanedBy}
            sub={active.cleanedAt}
          />
          <MetaCard
            icon={<CalendarCheckIcon className="size-4" />}
            label="Guest arrives"
            value={active.guestArrives.split(" · ")[1] ?? active.guestArrives}
            sub={active.guestArrives.split(" · ")[0]}
          />
        </div>

        <Wifi name={active.wifiName} pass={active.wifiPass} />

        {active.careNote && (
          <section className="mt-4 rounded-2xl border border-gold-line bg-gold-soft p-4">
            <div className="flex items-center gap-2 text-[#7a5c17]">
              <InfoIcon className="size-4" />
              <Eyebrow>Care notes</Eyebrow>
            </div>
            <p className="mt-2 font-display text-[1.05rem] italic leading-snug text-[#5f4713]">
              {active.careNote}
            </p>
          </section>
        )}

        {/* Readiness + primary action */}
        <section className="mt-6">
          <p className="text-center text-sm text-ink-soft">
            Vantage is ready — {checkpoints} checkpoints across{" "}
            {active.sections.length} sections.
          </p>
          <button
            className="mt-3 flex h-14 w-full items-center justify-center gap-2.5 rounded-2xl bg-forest-950 text-base font-semibold text-cream transition-colors hover:bg-forest-900"
            onClick={() => onStartQC(active)}
            type="button"
          >
            <CalendarCheckIcon className="size-5" />
            Start QC
          </button>
          <button
            className="mt-2.5 flex h-12 w-full items-center justify-center gap-2 rounded-2xl border border-sand bg-white text-[0.95rem] font-medium text-forest-900 transition-colors hover:bg-cream-100"
            onClick={onOpenChat}
            type="button"
          >
            <SparklesIcon className="size-4 text-moss" />
            Ask Vantage a question
          </button>
        </section>

        {/* ── Later today itinerary ───────────────────────────────────────── */}
        {later.length > 0 && (
          <section className="mt-9">
            <Eyebrow className="text-ink-soft">Later today</Eyebrow>
            <ul className="mt-3 flex flex-col gap-3">
              {later.map((stop) => (
                <li key={stop.id}>
                  <button
                    className="flex w-full items-center gap-3 rounded-2xl border border-sand bg-white p-3 text-left transition-colors hover:bg-cream-100"
                    onClick={() => onStartQC(stop)}
                    type="button"
                  >
                    <PropertyTone
                      tone={stop.tone}
                      className="grid size-14 shrink-0 place-items-center rounded-xl"
                    >
                      <span className="relative font-display text-lg text-white/90">
                        {stop.unitCode}
                      </span>
                    </PropertyTone>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate font-display text-lg leading-tight text-ink">
                        {stop.propertyName}
                      </span>
                      <span className="mt-0.5 block truncate text-sm text-ink-soft">
                        {stop.street} · {stop.cluster}
                      </span>
                    </span>
                    <Chip tone="neutral">Stop {stop.order}</Chip>
                  </button>
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>
    </div>
  );
}

function DoorCode({ code }: { code: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <section className="rounded-2xl border border-sand bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-ink-soft">
          <KeyRoundIcon className="size-4" />
          <Eyebrow>Door code</Eyebrow>
        </div>
        <CopyButton
          copied={copied}
          onCopy={() => {
            void navigator.clipboard?.writeText(code);
            setCopied(true);
            setTimeout(() => setCopied(false), 1600);
          }}
        />
      </div>
      <div className="mt-2 flex gap-[clamp(0.5rem,4vw,1rem)] font-display text-[clamp(2.4rem,12vw,3.25rem)] leading-none tracking-[0.1em] text-ink">
        {code.split("").map((d, i) => (
          <span key={i}>{d}</span>
        ))}
      </div>
    </section>
  );
}

function Wifi({ name, pass }: { name: string; pass: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <section className="mt-4 rounded-2xl border border-sand bg-white p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-ink-soft">
          <WifiIcon className="size-4" />
          <Eyebrow>Wi-Fi</Eyebrow>
        </div>
        <CopyButton
          copied={copied}
          onCopy={() => {
            void navigator.clipboard?.writeText(pass);
            setCopied(true);
            setTimeout(() => setCopied(false), 1600);
          }}
        />
      </div>
      <p className="mt-1.5 text-[1.05rem] text-ink">
        <span className="font-medium">{name}</span>
        <span className="text-ink-soft"> · {pass}</span>
      </p>
    </section>
  );
}

function MetaCard({
  icon,
  label,
  value,
  sub,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <section className="rounded-2xl border border-sand bg-white p-4">
      <div className="flex items-center gap-2 text-ink-soft">
        {icon}
        <Eyebrow>{label}</Eyebrow>
      </div>
      <p className="mt-1.5 text-[1.05rem] font-medium leading-tight text-ink">
        {value}
      </p>
      {sub && <p className="text-sm text-ink-soft">{sub}</p>}
    </section>
  );
}

function CopyButton({ copied, onCopy }: { copied: boolean; onCopy: () => void }) {
  return (
    <button
      aria-label={copied ? "Copied" : "Copy"}
      className={cn(
        "grid size-8 place-items-center rounded-lg border border-sand text-ink-soft transition-colors hover:bg-cream-100",
        copied && "border-moss/40 text-moss"
      )}
      onClick={onCopy}
      type="button"
    >
      {copied ? <CheckIcon className="size-4" /> : <ClipboardIcon className="size-4" />}
    </button>
  );
}
