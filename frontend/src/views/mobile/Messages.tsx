import { AlertTriangleIcon, BellIcon } from "lucide-react";
import { Eyebrow } from "@/components/mobile/bits";
import type { Cluster, Notification, Task } from "@/lib/tenancy";

/**
 * Alerts feed — the workspace's real notification triggers (from
 * `/api/field/notifications`), plus a live count of the board. No invented
 * conversations; everything shown is configured backend data.
 */
export function Messages({
  cluster,
  notifications,
  tasks,
}: {
  cluster: Cluster | null;
  notifications: Notification[] | null;
  tasks: Task[] | null;
}) {
  return (
    <div className="flex min-h-0 flex-1 flex-col bg-cream">
      <header className="on-forest bg-forest-950 px-6 pb-6 pt-12 text-sage-200">
        <Eyebrow className="text-gold-300">{cluster?.name ?? "Field area"}</Eyebrow>
        <h1 className="mt-2 font-display text-[clamp(1.8rem,7vw,2.1rem)] tracking-tight text-cream">
          Alerts
        </h1>
        <p className="mt-1 text-sm text-sage-300">
          {tasks == null
            ? "Loading the board…"
            : `${tasks.length} ${tasks.length === 1 ? "task" : "tasks"} on the board`}
        </p>
      </header>

      <div className="field-scroll px-4 py-4">
        {notifications === null ? (
          <ul className="flex flex-col gap-2">
            {[0, 1, 2].map((i) => (
              <li key={i} className="h-20 animate-pulse rounded-2xl border border-sand bg-white" />
            ))}
          </ul>
        ) : notifications.length === 0 ? (
          <div className="mt-10 flex flex-col items-center text-center">
            <span className="grid size-12 place-items-center rounded-2xl bg-cream-100 text-ink-soft">
              <BellIcon className="size-5" />
            </span>
            <p className="mt-3 font-medium text-ink">You're all caught up</p>
            <p className="mt-1 text-sm text-ink-soft">No alerts configured for this area.</p>
          </div>
        ) : (
          <ul className="flex flex-col gap-2">
            {notifications.map((n) => (
              <li
                key={n.event}
                className="flex items-start gap-3 rounded-2xl border border-sand bg-white p-3.5"
              >
                <span className="mt-0.5 grid size-9 shrink-0 place-items-center rounded-xl bg-gold-soft text-[#7a5c17]">
                  <AlertTriangleIcon className="size-4" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-[0.95rem] font-medium text-ink">
                    {titleize(n.event)}
                  </p>
                  <p className="mt-0.5 text-sm leading-snug text-ink-soft">{n.description}</p>
                  {n.role && (
                    <span className="mt-2 inline-block rounded-full bg-cream-100 px-2.5 py-0.5 text-[0.68rem] font-semibold uppercase tracking-wider text-ink-soft">
                      {n.role}
                    </span>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function titleize(eventKey: string) {
  return eventKey
    .toLowerCase()
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}
