import { useState } from "react";
import {
  SparklesIcon,
  SunIcon,
  UserIcon,
  MessageCircleIcon,
} from "lucide-react";
import { useLiveAgent } from "@/hooks/use-live-agent";
import { getWorkspace, TODAY_STOPS, type Stop, type Workspace } from "@/lib/tenancy";
import { cn } from "@/lib/utils";
import { MyDay } from "@/views/mobile/MyDay";
import { Messages } from "@/views/mobile/Messages";
import { CoPilot } from "@/views/mobile/CoPilot";
import { Profile } from "@/views/mobile/Profile";
import { QCFlow } from "@/views/mobile/QCFlow";

type Tab = "day" | "messages" | "chat" | "profile";

const TABS: { id: Tab; label: string; icon: typeof SunIcon }[] = [
  { id: "day", label: "My Day", icon: SunIcon },
  { id: "messages", label: "Messages", icon: MessageCircleIcon },
  { id: "chat", label: "AI Chat", icon: SparklesIcon },
  { id: "profile", label: "Profile", icon: UserIcon },
];

export function AppShell({ workspaceId }: { workspaceId: string }) {
  const agent = useLiveAgent();
  const workspace = getWorkspace(workspaceId) as Workspace;
  const [tab, setTab] = useState<Tab>("day");
  const [qcStop, setQcStop] = useState<Stop | null>(null);

  // Unread count drives the Messages badge.
  const unread = 1;

  // The AI Chat tab is the only full-forest screen; the rest are cream, so the
  // nav goes light there to avoid an all-green interface ("too much green").
  const dark = tab === "chat";

  return (
    <div className="field-app">
      {qcStop ? (
        <QCFlow agent={agent} stop={qcStop} onExit={() => setQcStop(null)} />
      ) : (
        <>
          {/* Each screen owns its own scrolling so the co-pilot can pin its
              input bar while the itinerary scrolls freely — no nested bars. */}
          <div className="flex min-h-0 flex-1 flex-col">
            {tab === "day" && (
              <div className="field-scroll">
                <MyDay
                  workspace={workspace}
                  stops={TODAY_STOPS}
                  onStartQC={(stop) => setQcStop(stop)}
                  onOpenChat={() => setTab("chat")}
                />
              </div>
            )}
            {tab === "messages" && <Messages />}
            {tab === "chat" && <CoPilot agent={agent} />}
            {tab === "profile" && <Profile workspace={workspace} />}
          </div>

          {/* Adaptive nav: forest on the immersive AI Chat, a light sage-gray
              gradient on the cream screens so the app never reads as all-green. */}
          <nav
            aria-label="Primary"
            className={cn(
              "relative z-30 flex items-stretch justify-around gap-1 border-t px-3 pb-[max(0.5rem,env(safe-area-inset-bottom))] pt-2 transition-colors",
              dark
                ? "on-forest border-forest-800 bg-forest-950 text-sage-400"
                : "border-[#c3ccc2] bg-gradient-to-b from-[#eef1ec] to-[#d4ddd4] text-[#6b746d]"
            )}
          >
            {TABS.map(({ id, label, icon: Icon }) => {
              const active = tab === id;
              const feature = id === "chat";
              return (
                <button
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "relative flex min-w-0 flex-1 flex-col items-center gap-1 rounded-2xl px-1 py-1.5 transition-colors",
                    active
                      ? dark
                        ? "text-gold-300"
                        : "text-forest-900"
                      : dark
                        ? "hover:text-sage-200"
                        : "hover:text-ink"
                  )}
                  key={id}
                  onClick={() => setTab(id)}
                  type="button"
                >
                  <span
                    className={cn(
                      "grid size-9 place-items-center rounded-xl transition-all",
                      feature && active && "bg-gold text-[#231a06]",
                      feature && !active && (dark ? "bg-forest-800 text-sage-300" : "bg-black/[0.06] text-forest-800"),
                      !feature && active && (dark ? "bg-forest-800" : "bg-black/[0.06]")
                    )}
                  >
                    <Icon className="size-5" strokeWidth={active ? 2.2 : 1.8} />
                    {id === "messages" && unread > 0 && (
                      <span className="absolute -right-0.5 -top-0.5 grid size-4 place-items-center rounded-full bg-gold text-[10px] font-bold text-[#231a06]">
                        {unread}
                      </span>
                    )}
                  </span>
                  <span className="text-[0.68rem] font-medium tracking-wide">
                    {label}
                  </span>
                </button>
              );
            })}
          </nav>
        </>
      )}
    </div>
  );
}
