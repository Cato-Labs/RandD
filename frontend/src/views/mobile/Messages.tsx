import { useState } from "react";
import { ArrowLeftIcon, ArrowUpIcon } from "lucide-react";
import { Eyebrow } from "@/components/mobile/bits";
import { THREADS, type MessageThread, type ThreadMessage } from "@/lib/tenancy";
import { cn } from "@/lib/utils";

export function Messages() {
  const [openId, setOpenId] = useState<string | null>(null);
  const open = THREADS.find((t) => t.id === openId) ?? null;

  if (open) {
    return <ThreadView thread={open} onBack={() => setOpenId(null)} />;
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col bg-cream">
      <header className="on-forest bg-forest-950 px-6 pb-6 pt-12 text-sage-200">
        <Eyebrow className="text-gold-300">Boulder Bay Collection</Eyebrow>
        <h1 className="mt-2 font-display text-[2.1rem] tracking-tight text-cream">
          Messages
        </h1>
      </header>
      <div className="field-scroll px-4 py-4">
        <ul className="flex flex-col gap-2">
          {THREADS.map((t) => (
            <li key={t.id}>
              <button
                className="flex w-full items-center gap-3 rounded-2xl border border-sand bg-white p-3 text-left transition-colors hover:bg-cream-100"
                onClick={() => setOpenId(t.id)}
                type="button"
              >
                <span className="grid size-12 shrink-0 place-items-center rounded-2xl bg-forest-900 font-display text-base text-cream">
                  {t.initials}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="flex items-baseline justify-between gap-2">
                    <span className="truncate font-medium text-ink">{t.title}</span>
                    <span className="shrink-0 text-xs text-ink-soft">{t.lastAt}</span>
                  </span>
                  <span className="mt-0.5 flex items-center gap-2">
                    <span className="min-w-0 flex-1 truncate text-sm text-ink-soft">
                      {t.messages.at(-1)?.body}
                    </span>
                    {t.unread > 0 && (
                      <span className="grid size-5 shrink-0 place-items-center rounded-full bg-gold text-[11px] font-bold text-[#231a06]">
                        {t.unread}
                      </span>
                    )}
                  </span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function ThreadView({
  thread,
  onBack,
}: {
  thread: MessageThread;
  onBack: () => void;
}) {
  const [draft, setDraft] = useState("");
  const [extra, setExtra] = useState<ThreadMessage[]>([]);
  const all = [...thread.messages, ...extra];

  function send() {
    const body = draft.trim();
    if (!body) return;
    setExtra((prev) => [
      ...prev,
      { id: `local-${prev.length}`, author: "You", role: "me", body, at: "Now" },
    ]);
    setDraft("");
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col bg-cream">
      <header className="flex items-center gap-3 border-b border-sand bg-white px-3 pb-3 pt-12">
        <button
          aria-label="Back to messages"
          className="grid size-9 place-items-center rounded-xl text-ink-soft hover:bg-cream-100"
          onClick={onBack}
          type="button"
        >
          <ArrowLeftIcon className="size-5" />
        </button>
        <span className="grid size-9 place-items-center rounded-xl bg-forest-900 font-display text-sm text-cream">
          {thread.initials}
        </span>
        <div className="min-w-0">
          <p className="truncate font-medium text-ink">{thread.title}</p>
          <p className="truncate text-xs text-ink-soft">{thread.subtitle}</p>
        </div>
      </header>

      <div className="field-scroll flex flex-col gap-3 px-4 py-4">
        {all.map((m) => (
          <div
            className={cn("flex", m.role === "me" ? "justify-end" : "justify-start")}
            key={m.id}
          >
            <div className="max-w-[80%]">
              <div
                className={cn(
                  "rounded-2xl px-3.5 py-2.5 text-[0.95rem] leading-relaxed",
                  m.role === "me"
                    ? "bg-forest-900 text-cream"
                    : "border border-sand bg-white text-ink"
                )}
              >
                {m.body}
              </div>
              <p
                className={cn(
                  "mt-1 text-[0.7rem] text-ink-soft",
                  m.role === "me" ? "text-right" : "text-left"
                )}
              >
                {m.at}
              </p>
            </div>
          </div>
        ))}
      </div>

      <div className="flex items-center gap-2 border-t border-sand bg-white px-3 py-2 pb-[max(0.5rem,env(safe-area-inset-bottom))]">
        <input
          className="min-w-0 flex-1 rounded-full border border-sand bg-cream px-4 py-2.5 text-[0.95rem] text-ink placeholder:text-ink-soft/70 focus:outline-none"
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Message…"
          value={draft}
        />
        <button
          aria-label="Send"
          className="grid size-10 shrink-0 place-items-center rounded-full bg-moss text-white transition-colors hover:bg-moss-300 disabled:opacity-40"
          disabled={!draft.trim()}
          onClick={send}
          type="button"
        >
          <ArrowUpIcon className="size-5" strokeWidth={2.4} />
        </button>
      </div>
    </div>
  );
}
