import {
  BellIcon,
  CheckIcon,
  ChevronRightIcon,
  LogOutIcon,
  ShieldCheckIcon,
  AudioLinesIcon,
} from "lucide-react";
import { useAuth } from "@/auth/AuthProvider";
import { Eyebrow, WorkspaceCrest } from "@/components/mobile/bits";
import { workspacesFor, type Workspace } from "@/lib/tenancy";
import { cn } from "@/lib/utils";

export function Profile({ workspace }: { workspace: Workspace }) {
  const { user, workspaceId, selectWorkspace, signOut } = useAuth();
  if (!user) return null;
  const workspaces = workspacesFor(user);

  return (
    <div className="flex min-h-0 flex-1 flex-col bg-cream">
      <header className="on-forest bg-forest-950 px-6 pb-8 pt-12 text-sage-200">
        <div className="flex items-center gap-4">
          <span className="grid size-16 shrink-0 place-items-center rounded-3xl bg-forest-800 font-display text-2xl text-cream">
            {user.initials}
          </span>
          <div className="min-w-0">
            <h1 className="truncate font-display text-2xl tracking-tight text-cream">
              {user.name}
            </h1>
            <p className="truncate text-sm text-sage-300">{user.email}</p>
            <span className="mt-1.5 inline-block rounded-full bg-forest-800 px-2.5 py-0.5 text-xs font-medium text-gold-300">
              {workspace.role}
            </span>
          </div>
        </div>
      </header>

      <div className="field-scroll px-5 py-5">
        {/* Workspace switcher — the multi-tenancy control. */}
        <Eyebrow className="text-ink-soft">Workspaces</Eyebrow>
        <ul className="mt-3 flex flex-col gap-2">
          {workspaces.map((ws) => {
            const active = ws.id === workspaceId;
            return (
              <li key={ws.id}>
                <button
                  className={cn(
                    "flex w-full items-center gap-3 rounded-2xl border p-3 text-left transition-colors",
                    active
                      ? "border-forest-600 bg-white ring-1 ring-forest-900/10"
                      : "border-sand bg-white hover:bg-cream-100"
                  )}
                  onClick={() => selectWorkspace(ws.id)}
                  type="button"
                >
                  <WorkspaceCrest workspace={ws} size={44} />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-display text-base text-ink">
                      {ws.name}
                    </span>
                    <span className="block truncate text-sm text-ink-soft">
                      {ws.region} · {ws.units} units
                    </span>
                  </span>
                  {active ? (
                    <span className="grid size-6 place-items-center rounded-full bg-moss text-white">
                      <CheckIcon className="size-4" />
                    </span>
                  ) : (
                    <ChevronRightIcon className="size-5 text-ink-soft" />
                  )}
                </button>
              </li>
            );
          })}
        </ul>

        {/* Preferences */}
        <Eyebrow className="mt-7 text-ink-soft">Preferences</Eyebrow>
        <div className="mt-3 overflow-hidden rounded-2xl border border-sand bg-white">
          <Row icon={<AudioLinesIcon className="size-4" />} label="Vantage voice" value="Kore" />
          <Row icon={<BellIcon className="size-4" />} label="Notifications" value="On" divide />
          <Row
            icon={<ShieldCheckIcon className="size-4" />}
            label="Door codes"
            value="Face ID"
            divide
          />
        </div>

        <button
          className="mt-7 flex w-full items-center justify-center gap-2 rounded-2xl border border-sand bg-white py-3.5 text-[0.95rem] font-medium text-destructive transition-colors hover:bg-cream-100"
          onClick={signOut}
          type="button"
        >
          <LogOutIcon className="size-4" />
          Sign out
        </button>
        <p className="mt-4 text-center text-xs text-ink-soft/70">Vantage · Field QC · v0.1</p>
      </div>
    </div>
  );
}

function Row({
  icon,
  label,
  value,
  divide,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  divide?: boolean;
}) {
  return (
    <div
      className={cn(
        "flex items-center gap-3 px-4 py-3.5",
        divide && "border-t border-sand"
      )}
    >
      <span className="grid size-8 place-items-center rounded-lg bg-cream-100 text-ink-soft">
        {icon}
      </span>
      <span className="flex-1 text-[0.95rem] text-ink">{label}</span>
      <span className="text-sm text-ink-soft">{value}</span>
      <ChevronRightIcon className="size-4 text-ink-soft/60" />
    </div>
  );
}
