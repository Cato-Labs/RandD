import { useEffect, useState } from "react";
import { ChevronRightIcon, LogOutIcon, MapPinIcon } from "lucide-react";
import { useAuth } from "@/auth/AuthProvider";
import { Logo } from "@/components/mobile/Logo";
import { Eyebrow } from "@/components/mobile/bits";
import { fetchClusters, type Cluster } from "@/lib/tenancy";

/**
 * Multi-tenancy entry point: choose which field area (cluster) to work inside.
 * Clusters and their unit counts are real, fetched from `/api/field/clusters`.
 */
export function WorkspacePicker({ email }: { email: string }) {
  const { selectCluster, signOut } = useAuth();
  const [clusters, setClusters] = useState<Cluster[] | null>(null);

  useEffect(() => {
    fetchClusters().then(setClusters);
  }, []);

  return (
    <div className="on-forest field-app bg-forest-950 text-sage-200">
      <div className="field-scroll px-7 pb-10 pt-14">
        <div className="mb-8 flex items-center gap-3">
          <Logo size={36} />
          <span className="font-display text-lg tracking-tight text-cream">Vantage</span>
        </div>
        <Eyebrow className="text-gold-300">Signed in as {email}</Eyebrow>
        <h1 className="mt-3 font-display text-[clamp(1.9rem,8vw,2.4rem)] leading-[1.06] tracking-tight text-cream">
          Choose a field area.
        </h1>
        <p className="muted mt-2 max-w-xs text-[0.95rem] leading-relaxed text-sage-300">
          Vantage scopes today to the cluster you pick.
        </p>

        {clusters === null ? (
          <ul className="mt-8 flex flex-col gap-3">
            {[0, 1, 2, 3].map((i) => (
              <li
                key={i}
                className="h-[76px] animate-pulse rounded-3xl border border-forest-800 bg-forest-900"
              />
            ))}
          </ul>
        ) : clusters.length === 0 ? (
          <div className="mt-10 rounded-3xl border border-forest-800 bg-forest-900 p-6 text-center">
            <p className="text-sage-200">No field areas are available.</p>
            <p className="muted mt-1 text-sm text-sage-300">
              The backend returned no clusters — check that the API is running.
            </p>
          </div>
        ) : (
          <ul className="mt-8 flex flex-col gap-3">
            {clusters.map((c, i) => (
              <li key={c.id}>
                <button
                  className="rise-in flex w-full items-center gap-4 rounded-3xl border border-forest-700 bg-forest-900 p-4 text-left transition-colors hover:border-forest-600 hover:bg-forest-850"
                  onClick={() => selectCluster(c.id)}
                  style={{ animationDelay: `${i * 60}ms` }}
                  type="button"
                >
                  <span className="grid size-12 shrink-0 place-items-center rounded-2xl bg-forest-800 text-gold-300">
                    <MapPinIcon className="size-5" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-display text-lg text-cream">
                      {c.name}
                    </span>
                    <span className="mt-0.5 block text-sm text-sage-300">
                      {c.units} {c.units === 1 ? "property" : "properties"}
                    </span>
                  </span>
                  <ChevronRightIcon className="size-5 shrink-0 text-sage-400" />
                </button>
              </li>
            ))}
          </ul>
        )}

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
