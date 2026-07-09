/**
 * Field-app data layer — every value comes from the live backend, which reads
 * the shared STRQC sqlite database. Nothing here is synthesized:
 *   - clusters, the task board (day plan), property detail, notifications, and
 *     inspectors are fetched from `/api/field/*` and `/api/inspectors`;
 *   - secrets (door code / Wi-Fi password) arrive decrypted or flagged locked.
 */

export type Cluster = {
  id: number;
  name: string;
  units: number;
};

export type Stage = { key: string | null; name: string | null };

/** One real turnover task = one stop on the field board. */
export type Task = {
  taskId: number;
  propertyId: number;
  unitCode: string;
  name: string;
  address: string;
  cluster: string;
  arrivalDate: string | null;
  cleanedBy: string;
  qcAssignee: string;
  stage: Stage;
};

export type PropertyDetail = {
  id: number;
  unitCode: string;
  name: string;
  address: string;
  cluster: string;
  qcAssignee: string;
  wifiSsid: string;
  standingInstructions: string;
  doorCode: string | null;
  doorCodeLocked: boolean;
  wifiPassword: string | null;
  wifiPasswordLocked: boolean;
};

export type ChecklistSection = { name: string; items: string[] };

export type Inspector = { id: number; name: string };

export type Notification = { event: string; description: string; role: string };

async function getJSON<T>(url: string, key: string, fallback: T): Promise<T> {
  try {
    const res = await fetch(url);
    if (!res.ok) return fallback;
    const data = (await res.json()) as Record<string, unknown>;
    const value = data[key];
    return (value ?? fallback) as T;
  } catch {
    return fallback;
  }
}

export const fetchClusters = () =>
  getJSON<Cluster[]>("/api/field/clusters", "clusters", []);

export const fetchDay = (clusterId?: number) =>
  getJSON<Task[]>(
    `/api/field/day${clusterId != null ? `?cluster=${clusterId}` : ""}`,
    "tasks",
    []
  );

export const fetchChecklist = () =>
  getJSON<ChecklistSection[]>("/api/field/checklist", "sections", []);

export const fetchInspectors = () =>
  getJSON<Inspector[]>("/api/inspectors", "inspectors", []);

export const fetchNotifications = () =>
  getJSON<Notification[]>("/api/field/notifications", "notifications", []);

export async function fetchProperty(id: number): Promise<PropertyDetail | null> {
  try {
    const res = await fetch(`/api/field/property/${id}`);
    if (!res.ok) return null;
    const data = (await res.json()) as PropertyDetail;
    return data && typeof data.id === "number" ? data : null;
  } catch {
    return null;
  }
}

/** Total checkpoints across all sections — the real count for readiness copy. */
export const countCheckpoints = (sections: ChecklistSection[]) =>
  sections.reduce((n, s) => n + s.items.length, 0);

/** Format a real ISO arrival date for display, or null when absent. */
export function formatArrival(date: string | null): string | null {
  if (!date) return null;
  const d = new Date(`${date}T00:00:00`);
  if (Number.isNaN(d.getTime())) return date;
  return d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
}

/** A stable editorial duotone per property, derived from its unit code (not
 *  random, not stored data — purely presentational, like an avatar color). */
export function toneFor(unitCode: string): [string, string] {
  let h = 0;
  for (const ch of unitCode) h = (h * 31 + ch.charCodeAt(0)) % 360;
  const base = 150 + (h % 80); // greens → teals → blues, on-brand
  return [`hsl(${base} 34% 32%)`, `hsl(${base} 40% 12%)`];
}
