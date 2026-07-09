import { useEffect, useRef, useState } from "react";
import {
  ArrowUpIcon,
  MicIcon,
  SettingsIcon,
  SquareIcon,
  WrenchIcon,
} from "lucide-react";
import { CopilotOrb } from "@/components/mobile/CopilotOrb";
import type { LiveAgent } from "@/hooks/use-live-agent";
import type { LiveMessage } from "@/lib/live-types";
import { cn } from "@/lib/utils";

const PROMPTS = [
  "What needs attention at Lakefront Bay View?",
  "Summarize today's route for me.",
  "Walk me through the dock section.",
];

export function CoPilot({ agent }: { agent: LiveAgent }) {
  const [text, setText] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const hasMessages = agent.messages.length > 0;

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [agent.messages]);

  function send(value: string) {
    const t = value.trim();
    if (!t) return;
    agent.submit({ text: t, files: [] });
    setText("");
  }

  const listening = agent.micActive;
  const connected = agent.status === "connected";

  return (
    <div className="on-forest flex min-h-0 flex-1 flex-col bg-forest-950 text-sage-200">
      {/* Header */}
      <header className="flex items-center justify-between px-5 pb-3 pt-5">
        <div className="flex items-center gap-2">
          <span
            className={cn(
              "size-2 rounded-full",
              connected ? "bg-moss-300" : agent.status === "connecting" ? "bg-gold-300" : "bg-sage-400"
            )}
          />
          <span className="font-display text-lg tracking-tight text-cream">
            Vantage Co-Pilot
          </span>
        </div>
        <button
          aria-label="Voice & session settings"
          className="grid size-9 place-items-center rounded-xl bg-forest-800 text-sage-300"
          onClick={() => (connected ? agent.disconnect() : agent.connect())}
          type="button"
        >
          <SettingsIcon className="size-4" />
        </button>
      </header>

      {/* Messages / empty hero */}
      <div ref={scrollRef} className="field-scroll px-5">
        {!hasMessages ? (
          <div className="flex h-full flex-col items-center justify-center py-8 text-center">
            <CopilotOrb state={agent.personaState} size={190} />
            <h2 className="mt-8 font-display text-2xl tracking-tight text-cream">
              {listening ? "Vantage is listening…" : "How can I help on this stop?"}
            </h2>
            <p className="muted mt-2 max-w-xs text-sm leading-relaxed text-sage-300">
              {listening
                ? "Speak clearly — I'll capture what you say."
                : "Ask about the property, the checklist, or start a section by voice."}
            </p>
            <div className="mt-7 flex w-full flex-col gap-2">
              {PROMPTS.map((p) => (
                <button
                  className="rounded-2xl border border-forest-700 bg-forest-900 px-4 py-3 text-left text-sm text-sage-200 transition-colors hover:border-forest-600 hover:bg-forest-850"
                  key={p}
                  onClick={() => send(p)}
                  type="button"
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-4 py-4">
            {agent.messages.map((m) => (
              <MessageBubble key={m.id} message={m} />
            ))}
            {(agent.chatStatus === "submitted" || agent.chatStatus === "streaming") && (
              <div className="flex items-center gap-2 text-sage-400">
                <CopilotOrb state="thinking" size={28} />
                <span className="text-sm">Vantage is thinking…</span>
              </div>
            )}
          </div>
        )}
      </div>

      {agent.error && (
        <p className="mx-5 mb-2 rounded-xl bg-[#3a1c1c] px-3 py-2 text-xs text-[#f0b3b0]">
          {agent.error}
        </p>
      )}

      {/* Input bar */}
      <div className="flex items-end gap-2 px-4 pb-[max(0.75rem,env(safe-area-inset-bottom))] pt-2">
        <div className="flex flex-1 items-center gap-2 rounded-full border border-forest-700 bg-forest-900 py-1.5 pl-4 pr-1.5">
          <input
            className="min-w-0 flex-1 bg-transparent py-1.5 text-[0.95rem] text-cream placeholder:text-sage-400 focus:outline-none"
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send(text);
              }
            }}
            placeholder="Type a message…"
            value={text}
          />
          <button
            aria-label={listening ? "Stop listening" : "Speak to Vantage"}
            className={cn(
              "grid size-9 shrink-0 place-items-center rounded-full transition-colors",
              listening ? "bg-gold text-[#231a06]" : "text-sage-300 hover:text-cream"
            )}
            onClick={() => (listening ? void agent.stopMic() : void agent.startMic())}
            type="button"
          >
            {listening ? <SquareIcon className="size-4" /> : <MicIcon className="size-5" />}
          </button>
        </div>
        {/* Send — moss green, replacing the palette-clashing bright yellow. */}
        <button
          aria-label="Send message"
          className="grid size-11 shrink-0 place-items-center rounded-full bg-moss text-white transition-colors hover:bg-moss-300 disabled:opacity-40"
          disabled={!text.trim()}
          onClick={() => send(text)}
          type="button"
        >
          <ArrowUpIcon className="size-5" strokeWidth={2.4} />
        </button>
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: LiveMessage }) {
  const mine = message.role === "user";
  const textParts = message.parts.filter((p) => p.type === "text") as {
    type: "text";
    text: string;
  }[];
  const fileParts = message.parts.filter((p) => p.type === "file") as {
    type: "file";
    url: string;
    mediaType: string;
  }[];
  const toolParts = message.parts.filter((p) => p.type.startsWith("tool-")) as {
    toolName: string;
  }[];
  const body = textParts.map((p) => p.text).join("");

  return (
    <div className={cn("flex", mine ? "justify-end" : "justify-start")}>
      <div className={cn("flex max-w-[85%] gap-2", mine && "flex-row-reverse")}>
        {!mine && (
          <span className="mt-1 grid size-6 shrink-0 place-items-center rounded-full bg-forest-800">
            <span className="size-2.5 rounded-full bg-moss-300" />
          </span>
        )}
        <div className="flex flex-col gap-2">
          {fileParts.map((f, i) => (
            <img
              alt="attachment"
              className="max-h-56 rounded-2xl border border-forest-700 object-cover"
              key={i}
              src={f.url}
            />
          ))}
          {toolParts.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {toolParts.map((t, i) => (
                <span
                  className="inline-flex items-center gap-1 rounded-full bg-forest-800 px-2.5 py-1 text-[0.68rem] text-sage-300"
                  key={i}
                >
                  <WrenchIcon className="size-3" />
                  {t.toolName}
                </span>
              ))}
            </div>
          )}
          {body && (
            <div
              className={cn(
                "rounded-2xl px-4 py-2.5 text-[0.95rem] leading-relaxed",
                mine
                  ? "bg-forest-700 text-cream"
                  : "border border-forest-700 bg-forest-900 text-sage-200"
              )}
            >
              {body}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
