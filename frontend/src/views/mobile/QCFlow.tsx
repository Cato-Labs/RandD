import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowLeftIcon,
  CheckIcon,
  MicIcon,
  RefreshCwIcon,
  SquareIcon,
  XIcon,
} from "lucide-react";
import { CopilotOrb } from "@/components/mobile/CopilotOrb";
import { Eyebrow, PropertyTone } from "@/components/mobile/bits";
import type { LiveAgent } from "@/hooks/use-live-agent";
import type { QcCheckpoint, QcSection, Stop } from "@/lib/tenancy";
import { cn } from "@/lib/utils";

type FlatStep = { section: QcSection; checkpoint: QcCheckpoint; index: number; total: number };

/** The pending approval, whether it came from a live agent handoff or the
 *  offline conductor that stands in for the agent when no session is live. */
type Approval = { source: "agent" | "local"; message: string; note: boolean };

/**
 * Agent-driven field QC. Vantage guides the walkthrough and TAKES each photo
 * itself (control_camera / take_photo run in the browser); the inspector simply
 * holds the phone on what Vantage asks for. Every shot is signed off through the
 * agent's `handoff_to_user` approval — never a manual shutter.
 *
 * When no live session is connected, an offline conductor reproduces the same
 * capture → handoff → approve loop so the experience is fully demonstrable.
 */
export function QCFlow({
  agent,
  stop,
  onExit,
}: {
  agent: LiveAgent;
  stop: Stop;
  onExit: () => void;
}) {
  const steps = useMemo<FlatStep[]>(() => {
    const flat: { section: QcSection; checkpoint: QcCheckpoint }[] = [];
    for (const section of stop.sections) {
      for (const checkpoint of section.checkpoints) flat.push({ section, checkpoint });
    }
    return flat.map((s, index) => ({ ...s, index, total: flat.length }));
  }, [stop]);

  const [started, setStarted] = useState(false);
  const [stepIdx, setStepIdx] = useState(0);
  const [captured, setCaptured] = useState<string | null>(null);
  const [localApproval, setLocalApproval] = useState<Approval | null>(null);
  const [note, setNote] = useState("");
  const [reshootOpen, setReshootOpen] = useState(false);
  const [done, setDone] = useState(false);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);

  const step = steps[Math.min(stepIdx, steps.length - 1)];
  const connected = agent.status === "connected";

  // A live agent handoff always wins; otherwise the offline conductor's prompt.
  const approval: Approval | null = agent.handoff
    ? { source: "agent", message: agent.handoff.message, note: true }
    : localApproval;

  const clearTimers = useCallback(() => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
  }, []);

  // Camera on for the whole walkthrough so the agent can frame + snap.
  useEffect(() => {
    if (started) void agent.startCamera();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [started]);

  // Release camera + pending timers only when the flow unmounts, so the
  // offline conductor's scheduled handoff survives the `started` transition.
  useEffect(() => {
    return () => {
      clearTimers();
      agent.stopCamera();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Offline conductor: stand in for the agent — "capture" the current
  // checkpoint, then raise a handoff for approval, mirroring the live loop.
  const conduct = useCallback(
    (idx: number) => {
      if (connected) return; // the real agent drives capture + handoff
      clearTimers();
      setCaptured(null);
      timers.current.push(
        setTimeout(() => {
          const frame = agent.getLatestFrame();
          setCaptured(frame ? `data:image/jpeg;base64,${frame}` : null);
          const cp = steps[idx]?.checkpoint;
          setLocalApproval({
            source: "local",
            message: `I framed the ${cp?.label.toLowerCase() ?? "checkpoint"}. Approve to log it, or tell me what to change.`,
            note: true,
          });
        }, 1400)
      );
    },
    [agent, clearTimers, connected, steps]
  );

  function begin() {
    setStarted(true);
    if (connected) {
      // Hand the walkthrough to the agent: it captures and hands off per shot.
      agent.submit({
        text: `Start the QC walkthrough for ${stop.propertyName} (${stop.unitCode}). Guide me section by section, take each checkpoint photo yourself with the camera, and hand off to me to approve every shot before moving on.`,
        files: [],
      });
    } else {
      conduct(0);
    }
  }

  function approve() {
    if (approval?.source === "agent") {
      agent.respondHandoff("Approved — that shot looks good. Log it and continue to the next checkpoint.");
      setCaptured(null);
      return;
    }
    // Offline: advance the conductor.
    setLocalApproval(null);
    setCaptured(null);
    if (stepIdx + 1 >= steps.length) {
      setDone(true);
    } else {
      const next = stepIdx + 1;
      setStepIdx(next);
      conduct(next);
    }
  }

  function reshoot() {
    const detail = note.trim() || "Please get closer and show the edge more clearly.";
    if (approval?.source === "agent") {
      agent.respondHandoff(`Re-shoot this one. ${detail}`);
    } else {
      conduct(stepIdx); // re-frame the same checkpoint
    }
    setNote("");
    setReshootOpen(false);
    setCaptured(null);
  }

  if (done) return <Complete stop={stop} onExit={onExit} />;

  return (
    <div className="on-forest flex min-h-0 flex-1 flex-col bg-forest-950 text-sage-200">
      <QCHeader step={step} started={started} onExit={onExit} />

      {!started ? (
        <Intro stop={stop} steps={steps} onBegin={begin} />
      ) : (
        <Walkthrough
          agent={agent}
          step={step}
          captured={captured}
          tone={stop.tone}
          approval={approval}
          reshootOpen={reshootOpen}
          note={note}
          setNote={setNote}
          onOpenReshoot={() => setReshootOpen(true)}
          onCloseReshoot={() => setReshootOpen(false)}
          onApprove={approve}
          onReshoot={reshoot}
        />
      )}
    </div>
  );
}

function QCHeader({
  step,
  started,
  onExit,
}: {
  step: FlatStep;
  started: boolean;
  onExit: () => void;
}) {
  const pct = started ? (step.index / step.total) * 100 : 0;
  return (
    <header className="px-5 pt-[max(1.25rem,env(safe-area-inset-top))]">
      <div className="flex items-center justify-between gap-2">
        <button
          aria-label="Close QC"
          className="grid size-9 shrink-0 place-items-center rounded-xl bg-forest-800 text-sage-300"
          onClick={onExit}
          type="button"
        >
          <XIcon className="size-4" />
        </button>
        <Eyebrow className="truncate text-sage-400">
          {started ? step.section.name : "Quality walkthrough"}
        </Eyebrow>
        <span className="grid h-9 min-w-9 shrink-0 place-items-center rounded-xl bg-forest-800 px-2 text-sm font-medium text-sage-200">
          {started ? `${step.index + 1}/${step.total}` : step.total}
        </span>
      </div>
      <div className="mt-3 h-1 overflow-hidden rounded-full bg-forest-800">
        <div
          className="h-full rounded-full bg-gold transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
    </header>
  );
}

function Intro({
  stop,
  steps,
  onBegin,
}: {
  stop: Stop;
  steps: FlatStep[];
  onBegin: () => void;
}) {
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="field-scroll px-6 pt-6">
        <CopilotOrb state="idle" size={128} className="mx-auto" />
        <h1 className="mt-6 text-center font-display text-[clamp(1.7rem,7vw,2.2rem)] leading-tight tracking-tight text-cream">
          Vantage will walk {stop.propertyName} with you
        </h1>
        <p className="muted mx-auto mt-2 max-w-sm text-center text-sm leading-relaxed text-sage-300">
          Hold your phone on what Vantage points out. It frames and captures each
          shot — you just approve, or ask for a re-shoot. {steps.length} checkpoints
          across {stop.sections.length} sections.
        </p>

        <ul className="mt-7 flex flex-col gap-1.5">
          {stop.sections.map((section, i) => (
            <li
              className="flex items-center gap-3 rounded-2xl border border-forest-800 bg-forest-900 px-4 py-3"
              key={section.id}
            >
              <span className="grid size-7 shrink-0 place-items-center rounded-full bg-forest-800 text-xs font-semibold text-gold-300">
                {i + 1}
              </span>
              <span className="min-w-0 flex-1 truncate text-sm text-sage-200">
                {section.name}
              </span>
              <span className="text-xs text-sage-400">{section.checkpoints.length}</span>
            </li>
          ))}
        </ul>
      </div>
      <div className="px-5 pb-[max(1rem,env(safe-area-inset-bottom))] pt-3">
        <button
          className="flex h-14 w-full items-center justify-center gap-2 rounded-2xl bg-gold text-base font-semibold text-[#231a06] transition-colors hover:bg-gold-300"
          onClick={onBegin}
          type="button"
        >
          Begin walkthrough with Vantage
        </button>
      </div>
    </div>
  );
}

function Walkthrough({
  agent,
  step,
  captured,
  tone,
  approval,
  reshootOpen,
  note,
  setNote,
  onOpenReshoot,
  onCloseReshoot,
  onApprove,
  onReshoot,
}: {
  agent: LiveAgent;
  step: FlatStep;
  captured: string | null;
  tone: [string, string];
  approval: Approval | null;
  reshootOpen: boolean;
  note: string;
  setNote: (v: string) => void;
  onOpenReshoot: () => void;
  onCloseReshoot: () => void;
  onApprove: () => void;
  onReshoot: () => void;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  useEffect(() => {
    const v = videoRef.current;
    if (!v) return;
    v.srcObject = agent.cameraStream;
    if (agent.cameraStream) void v.play().catch(() => {});
  }, [agent.cameraStream]);

  const capturing = !approval;

  return (
    <div className="relative flex min-h-0 flex-1 flex-col">
      {/* Guidance */}
      <div className="px-5 pt-5">
        <Eyebrow className="text-gold-300">{step.section.name}</Eyebrow>
        <h1 className="mt-1.5 font-display text-[clamp(1.4rem,6vw,1.9rem)] leading-tight tracking-tight text-cream">
          {step.checkpoint.label}
        </h1>
        {step.checkpoint.hint && (
          <p className="muted mt-1 text-sm text-sage-300">{step.checkpoint.hint}</p>
        )}
      </div>

      {/* Viewfinder / captured frame */}
      <div className="relative mx-5 mt-4 min-h-0 flex-1 overflow-hidden rounded-3xl border border-forest-700 bg-forest-900">
        {captured ? (
          <img alt="Captured checkpoint" className="h-full w-full object-cover" src={captured} />
        ) : agent.cameraActive ? (
          <video className="h-full w-full object-cover" muted playsInline ref={videoRef} />
        ) : (
          <PropertyTone tone={tone} className="h-full w-full" />
        )}

        {/* Framing guides */}
        <div className="pointer-events-none absolute inset-4 rounded-2xl border border-white/12" />

        {/* Live capture status — the agent is taking the shot, not the human */}
        {capturing && (
          <div className="absolute inset-x-0 bottom-0 flex items-center gap-3 bg-gradient-to-t from-forest-950/90 to-transparent px-4 pb-4 pt-10">
            <CopilotOrb state={agent.micActive ? "listening" : "thinking"} size={40} />
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-cream">
                Vantage is framing the shot…
              </p>
              <p className="truncate text-xs text-sage-300">
                Hold steady on the {step.checkpoint.label.toLowerCase()}.
              </p>
            </div>
            <button
              aria-label={agent.micActive ? "Stop talking" : "Talk to Vantage"}
              className={cn(
                "ml-auto grid size-10 shrink-0 place-items-center rounded-full border border-forest-700 transition-colors",
                agent.micActive ? "bg-gold text-[#231a06]" : "text-sage-200 hover:bg-forest-800"
              )}
              onClick={() => (agent.micActive ? void agent.stopMic() : void agent.startMic())}
              type="button"
            >
              {agent.micActive ? <SquareIcon className="size-4" /> : <MicIcon className="size-5" />}
            </button>
          </div>
        )}
      </div>

      {/* Bottom rail while capturing */}
      {capturing && (
        <p className="px-5 py-4 text-center text-xs text-sage-400">
          Vantage captures each checkpoint and asks you to approve.
        </p>
      )}

      {/* Approval sheet — the agent's handoff_to_user, surfaced for sign-off */}
      {approval && (
        <ApprovalSheet
          approval={approval}
          reshootOpen={reshootOpen}
          note={note}
          setNote={setNote}
          onOpenReshoot={onOpenReshoot}
          onCloseReshoot={onCloseReshoot}
          onApprove={onApprove}
          onReshoot={onReshoot}
          agent={agent}
        />
      )}
    </div>
  );
}

function ApprovalSheet({
  approval,
  reshootOpen,
  note,
  setNote,
  onOpenReshoot,
  onCloseReshoot,
  onApprove,
  onReshoot,
  agent,
}: {
  approval: Approval;
  reshootOpen: boolean;
  note: string;
  setNote: (v: string) => void;
  onOpenReshoot: () => void;
  onCloseReshoot: () => void;
  onApprove: () => void;
  onReshoot: () => void;
  agent: LiveAgent;
}) {
  return (
    <div className="absolute inset-x-0 bottom-0 z-20">
      <div className="rounded-t-[1.75rem] border-t border-forest-700 bg-forest-900/95 px-5 pb-[max(1rem,env(safe-area-inset-bottom))] pt-5 shadow-[0_-20px_40px_-20px_rgba(0,0,0,0.7)] backdrop-blur-md">
        <div className="mx-auto mb-3 h-1 w-10 rounded-full bg-forest-700" />
        {!reshootOpen ? (
          <>
            <div className="flex items-start gap-3">
              <span className="mt-0.5 grid size-8 shrink-0 place-items-center rounded-full bg-forest-800">
                <span className="size-3 rounded-full bg-moss-300" />
              </span>
              <div className="min-w-0">
                <h2 className="font-display text-xl leading-tight text-cream">Looking good?</h2>
                <p className="muted mt-1 text-sm leading-relaxed text-sage-300">
                  {approval.message}
                </p>
                <p className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-forest-800 px-2.5 py-1 text-[0.68rem] font-semibold uppercase tracking-wider text-sage-300">
                  Vantage · needs your approval
                </p>
              </div>
            </div>
            <div className="mt-4 flex gap-3">
              <button
                className="flex-1 rounded-2xl border border-forest-700 py-3.5 text-base font-medium text-sage-200 transition-colors hover:bg-forest-800"
                onClick={onOpenReshoot}
                type="button"
              >
                Re-shoot
              </button>
              <button
                className="flex flex-[1.3] items-center justify-center gap-2 rounded-2xl bg-moss py-3.5 text-base font-semibold text-white transition-colors hover:bg-moss-300"
                onClick={onApprove}
                type="button"
              >
                <CheckIcon className="size-5" />
                Approve
              </button>
            </div>
          </>
        ) : (
          <>
            <div className="flex items-center gap-2">
              <span className="size-2.5 rounded-full bg-moss-300" />
              <h2 className="font-display text-lg leading-tight text-cream">
                Tell Vantage what to change
              </h2>
            </div>
            <p className="muted mt-1 text-sm text-sage-300">
              Speak, or type a quick note — Vantage will re-shoot together with you.
            </p>
            <textarea
              autoFocus
              className="mt-3 min-h-24 w-full rounded-2xl border border-forest-700 bg-forest-950 p-4 text-[0.95rem] leading-relaxed text-cream placeholder:text-sage-400 focus:outline-none"
              onChange={(e) => setNote(e.target.value)}
              placeholder="Get closer and show the edge of the range more clearly…"
              value={note}
            />
            <div className="mt-3 flex gap-3">
              <button
                className="flex flex-1 items-center justify-center gap-2 rounded-2xl border border-forest-700 py-3.5 text-base font-medium text-sage-200 transition-colors hover:bg-forest-800"
                onClick={onCloseReshoot}
                type="button"
              >
                <ArrowLeftIcon className="size-4" />
                Back
              </button>
              <button
                className="flex flex-1 items-center justify-center gap-2 rounded-2xl bg-forest-700 py-3.5 text-base font-semibold text-cream transition-colors hover:bg-forest-600"
                onClick={onReshoot}
                type="button"
              >
                <RefreshCwIcon className="size-4" />
                Re-shoot
              </button>
            </div>
            <button
              aria-label={agent.micActive ? "Stop talking" : "Speak the change"}
              className="mx-auto mt-3 flex items-center gap-2 text-sm text-sage-300 underline-offset-4 hover:underline"
              onClick={() => (agent.micActive ? void agent.stopMic() : void agent.startMic())}
              type="button"
            >
              <MicIcon className="size-4" />
              {agent.micActive ? "Listening… tap to stop" : "Or tell Vantage out loud"}
            </button>
          </>
        )}
      </div>
    </div>
  );
}

function Complete({ stop, onExit }: { stop: Stop; onExit: () => void }) {
  const total = stop.sections.reduce((n, s) => n + s.checkpoints.length, 0);
  return (
    <div className="on-forest flex min-h-0 flex-1 flex-col items-center justify-center bg-forest-950 px-8 text-center text-sage-200">
      <CopilotOrb state="speaking" size={140} />
      <span className="mt-8 inline-flex items-center gap-2 rounded-full bg-[#e2efe6] px-3.5 py-1.5">
        <CheckIcon className="size-4 text-[#245c3a]" />
        <span className="eyebrow text-[#245c3a]">Walkthrough complete</span>
      </span>
      <h1 className="mt-4 font-display text-[clamp(1.8rem,8vw,2.3rem)] leading-tight tracking-tight text-cream">
        {stop.propertyName} is guest-ready.
      </h1>
      <p className="muted mt-2 max-w-xs text-sm leading-relaxed text-sage-300">
        {total} checkpoints captured and approved across {stop.sections.length}{" "}
        sections. Vantage compiled the readiness report — sign off to send it to
        Dispatch.
      </p>
      <button
        className="mt-8 h-14 w-full max-w-sm rounded-2xl bg-gold text-base font-semibold text-[#231a06] transition-colors hover:bg-gold-300"
        onClick={onExit}
        type="button"
      >
        Sign off & submit report
      </button>
      <button
        className="mt-3 text-sm text-sage-300 underline-offset-4 hover:underline"
        onClick={onExit}
        type="button"
      >
        Back to My Day
      </button>
    </div>
  );
}
