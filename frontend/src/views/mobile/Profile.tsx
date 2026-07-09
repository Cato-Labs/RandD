import { useEffect, useState } from "react";
import { LogOutIcon, MapPinIcon, RepeatIcon, UsersIcon } from "lucide-react";
import { useAuth } from "@/auth/AuthProvider";
import { Eyebrow } from "@/components/mobile/bits";
import { fetchInspectors, type Cluster, type Inspector } from "@/lib/tenancy";

/**
 * Profile — the signed-in account, the active field area, and the real QC team
 * (inspectors from `/api/inspectors`). Switching areas returns to the picker.
 */
export function Profile({ cluster }: { cluster: Cluster | null }) {
  const { email, signOut, clearCluster } = useAuth();
  const [inspectors, setInspectors] = useState<Inspector[] | null>(null);

  useEffect(() => {
    fetchInspectors().then(setInspectors);
  }, []);

  const initials = (email ?? "?").slice(0, 2).toUpperCase();

  return (
    <div className="flex min-h-0 flex-1 flex-col bg-cream">
      <header className="on-forest bg-forest-950 px-6 pb-8 pt-12 text-sage-200">
        <div className="flex items-center gap-4">
          <span className="grid size-16 shrink-0 place-items-center rounded-3xl bg-forest-800 font-display text-2xl text-cream">
            {initials}
          </span>
          <div className="min-w-0">
            <h1 className="truncate font-display text-2xl tracking-tight text-cream">
              {email ?? "Field access"}
            </h1>
            <p className="mt-1 flex items-center gap-1.5 text-sm text-sage-300">
              <MapPinIcon className="size-3.5" />
              {cluster?.name ?? "No area selected"}
            </p>
          </div>
        </div>
      </header>

      <div className="field-scroll px-5 py-5">
        {/* Active area + switch (multi-tenancy control) */}
        <Eyebrow className="text-ink-soft">Field area</Eyebrow>
        <button
          className="mt-3 flex w-full items-center gap-3 rounded-2xl border border-sand bg-white p-4 text-left transition-colors hover:bg-cream-100"
          onClick={clearCluster}
          type="button"
        >
          <span className="grid size-11 shrink-0 place-items-center rounded-2xl bg-forest-900 text-gold-300">
            <MapPinIcon className="size-5" />
          </span>
          <span className="min-w-0 flex-1">
            <span className="block truncate font-display text-base text-ink">
              {cluster?.name ?? "Choose a field area"}
            </span>
            <span className="block text-sm text-ink-soft">
              {cluster ? `${cluster.units} properties` : "Not selected"}
            </span>
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-cream-100 px-3 py-1.5 text-xs font-medium text-forest-900">
            <RepeatIcon className="size-3.5" />
            Switch
          </span>
        </button>

        {/* Real QC team */}
        <Eyebrow className="mt-7 text-ink-soft">QC team</Eyebrow>
        <div className="mt-3 overflow-hidden rounded-2xl border border-sand bg-white">
          {inspectors === null ? (
            <div className="p-4">
              {[0, 1].map((i) => (
                <div key={i} className="mb-2 h-6 animate-pulse rounded bg-cream-100 last:mb-0" />
              ))}
            </div>
          ) : inspectors.length === 0 ? (
            <div className="flex items-center gap-3 px-4 py-4 text-ink-soft">
              <UsersIcon className="size-4" />
              <span className="text-sm">No inspectors on file.</span>
            </div>
          ) : (
            inspectors.map((ins, i) => (
              <div
                key={ins.id}
                className={i > 0 ? "flex items-center gap-3 border-t border-sand px-4 py-3.5" : "flex items-center gap-3 px-4 py-3.5"}
              >
                <span className="grid size-9 shrink-0 place-items-center rounded-full bg-cream-100 font-display text-sm text-ink">
                  {ins.name.slice(0, 2).toUpperCase()}
                </span>
                <span className="flex-1 text-[0.95rem] text-ink">{ins.name}</span>
                <span className="text-xs text-ink-soft">QC</span>
              </div>
            ))
          )}
        </div>

        <button
          className="mt-7 flex w-full items-center justify-center gap-2 rounded-2xl border border-sand bg-white py-3.5 text-[0.95rem] font-medium text-destructive transition-colors hover:bg-cream-100"
          onClick={signOut}
          type="button"
        >
          <LogOutIcon className="size-4" />
          Sign out
        </button>
        <p className="mt-4 text-center text-xs text-ink-soft/70">Vantage · Field QC</p>
      </div>
    </div>
  );
}
