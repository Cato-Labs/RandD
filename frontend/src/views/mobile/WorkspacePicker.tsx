import { ChevronRightIcon, LogOutIcon } from "lucide-react";
import { useAuth } from "@/auth/AuthProvider";
import { Logo } from "@/components/mobile/Logo";
import { Eyebrow, WorkspaceCrest } from "@/components/mobile/bits";
import { workspacesFor, type FieldUser } from "@/lib/tenancy";

/**
 * Multi-tenancy entry point: choose which workspace (management company /
 * owner group) to work inside. A field user can belong to several; the
 * selection becomes the active tenant for the rest of the session.
 */
export function WorkspacePicker({ user }: { user: FieldUser }) {
  const { selectWorkspace, signOut } = useAuth();
  const workspaces = workspacesFor(user);
  const firstName = user.name.split(" ")[0];

  return (
    <div className="on-forest field-app bg-forest-950 text-sage-200">
      <div className="field-scroll px-7 pb-10 pt-14">
        <div className="mb-8 flex items-center gap-3">
          <Logo size={36} />
          <span className="font-display text-lg tracking-tight text-cream">Vantage</span>
        </div>
        <Eyebrow className="text-gold-300">Signed in as {firstName}</Eyebrow>
        <h1 className="mt-3 font-display text-[clamp(1.9rem,8vw,2.4rem)] leading-[1.06] tracking-tight text-cream">
          Choose a workspace.
        </h1>
        <p className="muted mt-2 max-w-xs text-[0.95rem] leading-relaxed text-sage-300">
          You have access to {workspaces.length} portfolios. Vantage tailors the
          day to whichever you pick.
        </p>

        <ul className="mt-8 flex flex-col gap-3">
          {workspaces.map((ws, i) => (
            <li key={ws.id}>
              <button
                className="rise-in flex w-full items-center gap-4 rounded-3xl border border-forest-700 bg-forest-900 p-4 text-left transition-colors hover:border-forest-600 hover:bg-forest-850"
                onClick={() => selectWorkspace(ws.id)}
                style={{ animationDelay: `${i * 70}ms` }}
                type="button"
              >
                <WorkspaceCrest workspace={ws} size={52} />
                <span className="min-w-0 flex-1">
                  <span className="block truncate font-display text-lg text-cream">
                    {ws.name}
                  </span>
                  <span className="mt-0.5 block truncate text-sm text-sage-300">
                    {ws.kind} · {ws.region}
                  </span>
                  <span className="mt-2 flex items-center gap-2">
                    <span className="eyebrow rounded-full bg-forest-800 px-2.5 py-1 text-sage-200">
                      {ws.role}
                    </span>
                    <span className="text-xs text-sage-400">{ws.units} units</span>
                  </span>
                </span>
                <ChevronRightIcon className="size-5 shrink-0 text-sage-400" />
              </button>
            </li>
          ))}
        </ul>

        <button
          className="mx-auto mt-8 flex items-center gap-2 text-sm text-sage-300 underline-offset-4 hover:underline"
          onClick={signOut}
          type="button"
        >
          <LogOutIcon className="size-4" />
          Sign out
        </button>
      </div>
    </div>
  );
}
