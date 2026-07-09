import { useEffect, useState } from "react";
import {
  CalendarCheckIcon,
  CheckIcon,
  ClipboardIcon,
  InfoIcon,
  KeyRoundIcon,
  LockIcon,
  MapPinIcon,
  NavigationIcon,
  SparklesIcon,
  WifiIcon,
} from "lucide-react";
import { Chip, Eyebrow, PropertyTone } from "@/components/mobile/bits";
import { cn } from "@/lib/utils";
import {
  countCheckpoints,
  fetchProperty,
  formatArrival,
  toneFor,
  type ChecklistSection,
  type Cluster,
  type PropertyDetail,
  type Task,
} from "@/lib/tenancy";

const TODAY = new Date().toLocaleDateString("en-US", {
  weekday: "short",
  month: "short",
  day: "numeric",
});

/** Google Maps turn-by-turn to a real property address. */
function mapsUrl(query: string) {
  return `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(
    query
  )}&travelmode=driving`;
}

function openNavigation(task: { address: string; name: string }) {
  const q = task.address || task.name;
  window.open(mapsUrl(q), "_blank", "noopener,noreferrer");
}

export function MyDay({
  cluster,
  tasks,
  checklist,
  onStartQC,
  onOpenChat,
}: {
  cluster: Cluster | null;
  tasks: Task[] | null;
  checklist: ChecklistSection[];
  onStartQC: (task: Task) => void;
  onOpenChat: () => void;
}) {
  const active = tasks && tasks.length > 0 ? tasks[0] : null;
  const [detail, setDetail] = useState<PropertyDetail | null>(null);

  useEffect(() => {
    setDetail(null);
    if (active) fetchProperty(active.propertyId).then(setDetail);
  }, [active?.propertyId]);

  const checkpoints = countCheckpoints(checklist);

  if (tasks === null) return <LoadingDay cluster={cluster} />;
  if (!active) return <EmptyDay cluster={cluster} />;

  const later = tasks.slice(1);
  const arrival = formatArrival(active.arrivalDate);

  return (
    <div className="bg-cream">
      {/* ── Forest header ─────────────────────────────────────────────────── */}
      <header className="on-forest relative bg-forest-950 px-6 pb-16 pt-12 text-sage-200">
        <div className="flex items-center justify-between gap-3">
          <div className="flex min-w-0 flex-1 items-center gap-2.5">
            <span className="grid size-8 shrink-0 place-items-center rounded-xl bg-forest-800 text-gold-300">
              <MapPinIcon className="size-4" />
            </span>
            <span className="truncate text-sm font-medium text-sage-200">
              {cluster?.name ?? active.cluster}
            </span>
          </div>
          <span className="eyebrow shrink-0 whitespace-nowrap text-sage-400">{TODAY}</span>
        </div>

        <div className="mt-7">
          <span className="inline-flex items-center gap-2 rounded-full bg-gold px-3.5 py-1.5">
            <span className="size-1.5 rounded-full bg-[#231a06]" />
            <span className="eyebrow text-[#231a06]">
              {active.stage.name ? `${active.stage.name} · ` : ""}Stop 1 of {tasks.length}
            </span>
          </span>
          <h1 className="mt-4 font-display text-[clamp(2rem,8.5vw,2.7rem)] leading-[1.02] tracking-tight text-cream">
            {active.name}
          </h1>
          {active.address && (
            <p className="mt-2 flex items-center gap-1.5 text-sage-300">
              <MapPinIcon className="size-4 shrink-0" />
              <span className="truncate">
                {active.address}
                {active.unitCode ? ` · ${active.unitCode}` : ""}
              </span>
            </p>
          )}
        </div>
      </header>

      {/* ── Cream operational content ─────────────────────────────────────── */}
      <div className="relative -mt-8 rounded-t-[2rem] bg-cream px-5 pb-8 pt-6">
        <DoorCode detail={detail} />

        <div className="mt-4 grid grid-cols-2 gap-3">
          <MetaCard
            icon={<SparklesIcon className="size-4" />}
            label="Cleaned by"
            value={active.cleanedBy || "Unassigned"}
          />
          <MetaCard
            icon={<CalendarCheckIcon className="size-4" />}
            label="Guest arrives"
            value={arrival ?? "Not scheduled"}
          />
        </div>

        <Wifi detail={detail} />

        {detail?.standingInstructions ? (
          <section className="mt-4 rounded-2xl border border-gold-line bg-gold-soft p-4">
            <div className="flex items-center gap-2 text-[#7a5c17]">
              <InfoIcon className="size-4" />
              <Eyebrow>Standing instructions</Eyebrow>
            </div>
            <p className="mt-2 font-display text-[1.05rem] italic leading-snug text-[#5f4713]">
              {detail.standingInstructions}
            </p>
          </section>
        ) : null}

        <section className="mt-6">
          <p className="text-center text-sm text-ink-soft">
            {checkpoints > 0
              ? `Vantage is ready — ${checkpoints} checkpoints across ${checklist.length} sections.`
              : "Vantage is ready for the walkthrough."}
          </p>
          <button
            className="mt-3 flex h-14 w-full items-center justify-center gap-2.5 rounded-2xl bg-forest-950 text-base font-semibold text-cream transition-colors hover:bg-forest-900"
            onClick={() => onStartQC(active)}
            type="button"
          >
            <CalendarCheckIcon className="size-5" />
            Start QC
          </button>
          <div className="mt-2.5 grid grid-cols-2 gap-2.5">
            <button
              className="flex h-12 items-center justify-center gap-2 rounded-2xl border border-sand bg-white text-[0.95rem] font-medium text-forest-900 transition-colors hover:bg-cream-100 disabled:opacity-50"
              disabled={!active.address}
              onClick={() => openNavigation(active)}
              type="button"
            >
              <NavigationIcon className="size-4 text-moss" />
              Navigate
            </button>
            <button
              className="flex h-12 items-center justify-center gap-2 rounded-2xl border border-sand bg-white text-[0.95rem] font-medium text-forest-900 transition-colors hover:bg-cream-100"
              onClick={onOpenChat}
              type="button"
            >
              <SparklesIcon className="size-4 text-moss" />
              Ask Vantage
            </button>
          </div>
        </section>

        {later.length > 0 && (
          <section className="mt-9">
            <Eyebrow className="text-ink-soft">Rest of the board</Eyebrow>
            <ul className="mt-3 flex flex-col gap-3">
              {later.map((task, i) => (
                <li
                  key={task.taskId}
                  className="flex items-center gap-1 rounded-2xl border border-sand bg-white pr-2 transition-colors hover:bg-cream-100"
                >
                  <button
                    className="flex min-w-0 flex-1 items-center gap-3 rounded-2xl p-3 text-left"
                    onClick={() => onStartQC(task)}
                    type="button"
                  >
                    <PropertyTone
                      tone={toneFor(task.unitCode)}
                      className="grid size-14 shrink-0 place-items-center rounded-xl"
                    >
                      <span className="relative font-display text-lg text-white/90">
                        {task.unitCode}
                      </span>
                    </PropertyTone>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate font-display text-lg leading-tight text-ink">
                        {task.name}
                      </span>
                      <span className="mt-0.5 block truncate text-sm text-ink-soft">
                        {task.cluster}
                        {formatArrival(task.arrivalDate)
                          ? ` · ${formatArrival(task.arrivalDate)}`
                          : ""}
                      </span>
                    </span>
                    <Chip tone="neutral">{task.stage.name ?? `Stop ${i + 2}`}</Chip>
                  </button>
                  {task.address && (
                    <button
                      aria-label={`Navigate to ${task.name}`}
                      className="grid size-9 shrink-0 place-items-center rounded-xl border border-sand text-moss transition-colors hover:bg-cream-100"
                      onClick={() => openNavigation(task)}
                      type="button"
                    >
                      <NavigationIcon className="size-4" />
                    </button>
                  )}
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>
    </div>
  );
}

function DoorCode({ detail }: { detail: PropertyDetail | null }) {
  const [copied, setCopied] = useState(false);
  const code = detail?.doorCode ?? null;
  const locked = detail?.doorCodeLocked ?? false;

  return (
    <section className="rounded-2xl border border-sand bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-ink-soft">
          <KeyRoundIcon className="size-4" />
          <Eyebrow>Door code</Eyebrow>
        </div>
        {code && (
          <CopyButton
            copied={copied}
            onCopy={() => {
              void navigator.clipboard?.writeText(code);
              setCopied(true);
              setTimeout(() => setCopied(false), 1600);
            }}
          />
        )}
      </div>
      {code ? (
        <div className="mt-2 flex gap-[clamp(0.5rem,4vw,1rem)] font-display text-[clamp(2.4rem,12vw,3.25rem)] leading-none tracking-[0.1em] text-ink">
          {code.split("").map((d, i) => (
            <span key={i}>{d}</span>
          ))}
        </div>
      ) : locked ? (
        <div className="mt-2 flex items-center gap-3">
          <span className="font-display text-[clamp(2.4rem,12vw,3.25rem)] leading-none tracking-[0.2em] text-ink/80">
            ••••
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-cream-100 px-2.5 py-1 text-xs text-ink-soft">
            <LockIcon className="size-3" />
            Encrypted — reveal on site
          </span>
        </div>
      ) : (
        <p className="mt-3 text-sm text-ink-soft">No door code on file.</p>
      )}
    </section>
  );
}

function Wifi({ detail }: { detail: PropertyDetail | null }) {
  const [copied, setCopied] = useState(false);
  if (!detail?.wifiSsid) return null;
  const pass = detail.wifiPassword;
  return (
    <section className="mt-4 rounded-2xl border border-sand bg-white p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-ink-soft">
          <WifiIcon className="size-4" />
          <Eyebrow>Wi-Fi</Eyebrow>
        </div>
        {pass && (
          <CopyButton
            copied={copied}
            onCopy={() => {
              void navigator.clipboard?.writeText(pass);
              setCopied(true);
              setTimeout(() => setCopied(false), 1600);
            }}
          />
        )}
      </div>
      <p className="mt-1.5 text-[1.05rem] text-ink">
        <span className="font-medium">{detail.wifiSsid}</span>
        {pass ? (
          <span className="text-ink-soft"> · {pass}</span>
        ) : detail.wifiPasswordLocked ? (
          <span className="text-ink-soft"> · ••••</span>
        ) : null}
      </p>
    </section>
  );
}

function MetaCard({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <section className="rounded-2xl border border-sand bg-white p-4">
      <div className="flex items-center gap-2 text-ink-soft">
        {icon}
        <Eyebrow>{label}</Eyebrow>
      </div>
      <p className="mt-1.5 text-[1.05rem] font-medium leading-tight text-ink">{value}</p>
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

function LoadingDay({ cluster }: { cluster: Cluster | null }) {
  return (
    <div className="bg-cream">
      <header className="on-forest bg-forest-950 px-6 pb-16 pt-12">
        <span className="text-sm text-sage-300">{cluster?.name ?? "Loading…"}</span>
        <div className="mt-8 h-10 w-2/3 animate-pulse rounded-lg bg-forest-800" />
      </header>
      <div className="-mt-8 rounded-t-[2rem] bg-cream px-5 pt-6">
        {[0, 1, 2].map((i) => (
          <div key={i} className="mb-4 h-28 animate-pulse rounded-2xl border border-sand bg-white" />
        ))}
      </div>
    </div>
  );
}

function EmptyDay({ cluster }: { cluster: Cluster | null }) {
  return (
    <div className="bg-cream">
      <header className="on-forest bg-forest-950 px-6 pb-16 pt-12 text-sage-200">
        <span className="text-sm text-sage-300">{cluster?.name ?? "Field area"}</span>
        <h1 className="mt-6 font-display text-[clamp(2rem,8vw,2.6rem)] leading-tight tracking-tight text-cream">
          Nothing on the board.
        </h1>
      </header>
      <div className="-mt-8 rounded-t-[2rem] bg-cream px-5 pb-8 pt-8">
        <p className="text-center text-ink-soft">
          There are no turnover tasks for this cluster right now.
        </p>
      </div>
    </div>
  );
}
