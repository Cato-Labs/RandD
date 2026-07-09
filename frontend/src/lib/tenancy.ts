/**
 * Tenancy + field-day data model for the Vantage experience.
 *
 * Multi-tenancy is modeled here as a set of Workspaces (management companies /
 * owner groups) a field user belongs to. The auth layer selects an active
 * workspace, and every screen reads its data through this module.
 *
 * The backend on this branch exposes read-only property/inspector lookups
 * (`/api/properties`, `/api/inspectors`) and the live agent socket, but no
 * auth or day-plan endpoints yet. So identity, workspaces, and the day plan
 * are seeded here behind small typed accessors — each is a drop-in seam for a
 * real endpoint later (see `fetchProperties`, which already reads live data).
 */

export type Workspace = {
  id: string;
  name: string;
  kind: string;
  region: string;
  units: number;
  role: string;
  /** Two-letter monogram shown on the workspace crest. */
  initials: string;
  /** Editorial hue used for the workspace crest gradient. */
  hue: number;
};

export type FieldUser = {
  id: string;
  name: string;
  email: string;
  title: string;
  initials: string;
  workspaceIds: string[];
};

export type StopStatus = "arrived" | "en-route" | "upcoming" | "complete";

export type QcCheckpoint = {
  id: string;
  label: string;
  hint?: string;
};

export type QcSection = {
  id: string;
  name: string;
  checkpoints: QcCheckpoint[];
};

export type Stop = {
  id: string;
  order: number;
  status: StopStatus;
  propertyName: string;
  unitCode: string;
  street: string;
  cluster: string;
  doorCode: string;
  cleanedBy: string;
  cleanedAt: string;
  guestArrives: string;
  wifiName: string;
  wifiPass: string;
  careNote?: string;
  /** Duotone gradient stops for the property "photo" (kept asset-free). */
  tone: [string, string];
  sections: QcSection[];
};

export type PropertyOption = {
  id: number | string;
  unitCode: string;
  name: string;
  address: string;
  cluster: string;
  qcAssignee: string;
};

export type ThreadMessage = {
  id: string;
  author: string;
  role: "them" | "me" | "system";
  body: string;
  at: string;
};

export type MessageThread = {
  id: string;
  title: string;
  subtitle: string;
  initials: string;
  unread: number;
  lastAt: string;
  messages: ThreadMessage[];
};

// ── Seed data ────────────────────────────────────────────────────────────────

export const USER: FieldUser = {
  id: "u_maribel",
  name: "Maribel Ortiz",
  email: "maribel@boulderbay.co",
  title: "QC Specialist",
  initials: "MO",
  workspaceIds: ["ws_boulderbay", "ws_summit", "ws_coastline"],
};

export const WORKSPACES: Workspace[] = [
  {
    id: "ws_boulderbay",
    name: "Boulder Bay Collection",
    kind: "Lakefront portfolio",
    region: "Big Bear Lake, CA",
    units: 96,
    role: "Quality Control",
    initials: "BB",
    hue: 158,
  },
  {
    id: "ws_summit",
    name: "Summit House Residences",
    kind: "Alpine rentals",
    region: "Mammoth Lakes, CA",
    units: 41,
    role: "Lead Inspector",
    initials: "SH",
    hue: 210,
  },
  {
    id: "ws_coastline",
    name: "Coastline & Co.",
    kind: "Coastal estates",
    region: "Mendocino, CA",
    units: 28,
    role: "QC Specialist",
    initials: "CC",
    hue: 32,
  },
];

const SECTIONS_STANDARD: QcSection[] = [
  {
    id: "sec_arrival",
    name: "Arrival & Entry",
    checkpoints: [
      { id: "cp_door", label: "Door hardware & lock", hint: "Deadbolt throws cleanly; keypad lit" },
      { id: "cp_entry", label: "Entry floor & mat", hint: "No debris, mat squared" },
    ],
  },
  {
    id: "sec_living",
    name: "Living Room",
    checkpoints: [
      { id: "cp_stage", label: "Staging & pillows", hint: "Cushions plumped, throws folded" },
      { id: "cp_surfaces", label: "Surfaces dusted" },
    ],
  },
  {
    id: "sec_kitchen",
    name: "Kitchen",
    checkpoints: [
      { id: "cp_counters", label: "Counters & sink", hint: "Streak-free, dry" },
      { id: "cp_appliances", label: "Appliances wiped" },
    ],
  },
  {
    id: "sec_primary",
    name: "Primary Bedroom",
    checkpoints: [
      { id: "cp_bed", label: "Bed dressed to standard", hint: "Hospital corners, even drop" },
      { id: "cp_nightstand", label: "Nightstands staged" },
    ],
  },
  {
    id: "sec_bath",
    name: "Bathrooms",
    checkpoints: [
      { id: "cp_towels", label: "Towel presentation" },
      { id: "cp_amenities", label: "Amenities restocked" },
    ],
  },
  {
    id: "sec_exterior",
    name: "Deck & Exterior",
    checkpoints: [
      { id: "cp_deck", label: "Deck swept & staged" },
      { id: "cp_range", label: "Grill / range clean", hint: "Show the edge of the range clearly" },
    ],
  },
  {
    id: "sec_dock",
    name: "Dock & Waterfront",
    checkpoints: [
      { id: "cp_paddles", label: "Kayak paddles staged", hint: "Leave staged by the dock" },
      { id: "cp_railing", label: "Railings wiped" },
    ],
  },
  {
    id: "sec_final",
    name: "Final Walkthrough",
    checkpoints: [
      { id: "cp_scent", label: "Scent & air" },
      { id: "cp_lights", label: "Welcome lights set" },
    ],
  },
];

export const TODAY_STOPS: Stop[] = [
  {
    id: "stop_lbv",
    order: 1,
    status: "arrived",
    propertyName: "Lakefront Bay View",
    unitCode: "LBV",
    street: "701 Cove Dr",
    cluster: "Boulder Bay",
    doorCode: "4725",
    cleanedBy: "Maribel",
    cleanedAt: "8:10 AM",
    guestArrives: "Today · 4:00 PM",
    wifiName: "LBV-Guest",
    wifiPass: "cove701lake",
    careNote:
      "Owner keeps the kayak paddles in the garage — leave them staged by the dock for this stay.",
    tone: ["#2f6d52", "#0f2a1f"],
    sections: SECTIONS_STANDARD,
  },
  {
    id: "stop_pinecrest",
    order: 2,
    status: "upcoming",
    propertyName: "Pinecrest Hideaway",
    unitCode: "PCH",
    street: "22 Tamarack Way",
    cluster: "Moonridge",
    doorCode: "8801",
    cleanedBy: "Devon",
    cleanedAt: "9:35 AM",
    guestArrives: "Today · 5:30 PM",
    wifiName: "Pinecrest",
    wifiPass: "tallpines22",
    careNote: "Thermostat is smart — leave it on Away/Eco, guest app controls it.",
    tone: ["#3a5f7a", "#12232f"],
    sections: SECTIONS_STANDARD.slice(0, 6),
  },
  {
    id: "stop_goldenaspen",
    order: 3,
    status: "upcoming",
    propertyName: "Golden Aspen Lodge",
    unitCode: "GAL",
    street: "5 Ridgeline Ct",
    cluster: "Sugarloaf",
    doorCode: "3390",
    cleanedBy: "Priya",
    cleanedAt: "11:00 AM",
    guestArrives: "Tomorrow · 3:00 PM",
    wifiName: "AspenLodge",
    wifiPass: "goldleaf5",
    careNote: "Firewood restock is on the porch — do not bring indoors until guest check-in.",
    tone: ["#7a5a2f", "#2b1e10"],
    sections: SECTIONS_STANDARD.slice(0, 5),
  },
];

export const THREADS: MessageThread[] = [
  {
    id: "th_dispatch",
    title: "Dispatch · Boulder Bay",
    subtitle: "Route + priorities for today",
    initials: "DP",
    unread: 1,
    lastAt: "8:02 AM",
    messages: [
      {
        id: "m1",
        author: "Dispatch",
        role: "them",
        body: "Morning Maribel — 3 stops today. Lakefront Bay View is priority, guest arrives 4 PM sharp.",
        at: "7:58 AM",
      },
      {
        id: "m2",
        author: "You",
        role: "me",
        body: "On it. Heading to LBV now.",
        at: "8:00 AM",
      },
      {
        id: "m3",
        author: "Dispatch",
        role: "them",
        body: "Owner flagged the kayak paddles — Vantage has the care note. Thanks!",
        at: "8:02 AM",
      },
    ],
  },
  {
    id: "th_devon",
    title: "Devon Reyes",
    subtitle: "Turnover crew",
    initials: "DR",
    unread: 0,
    lastAt: "Yesterday",
    messages: [
      {
        id: "m1",
        author: "Devon",
        role: "them",
        body: "Left the extra linens in the LBV hall closet, top shelf.",
        at: "Yesterday · 6:40 PM",
      },
      {
        id: "m2",
        author: "You",
        role: "me",
        body: "Perfect, thank you!",
        at: "Yesterday · 6:44 PM",
      },
    ],
  },
  {
    id: "th_owner",
    title: "Owner · L. Tran",
    subtitle: "Lakefront Bay View",
    initials: "LT",
    unread: 0,
    lastAt: "Mon",
    messages: [
      {
        id: "m1",
        author: "L. Tran",
        role: "them",
        body: "Please make sure the dock area looks pristine for this group — they kayak every morning.",
        at: "Mon · 9:10 AM",
      },
    ],
  },
];

// ── Live-backend integration ─────────────────────────────────────────────────

/** Active homes for the searchable property picker (live `/api/properties`). */
export async function fetchProperties(): Promise<PropertyOption[]> {
  try {
    const res = await fetch("/api/properties");
    if (!res.ok) return [];
    const data = (await res.json()) as { properties: PropertyOption[] };
    return Array.isArray(data.properties) ? data.properties : [];
  } catch {
    return [];
  }
}

export function workspacesFor(user: FieldUser): Workspace[] {
  return WORKSPACES.filter((ws) => user.workspaceIds.includes(ws.id));
}

export function getWorkspace(id: string | null | undefined): Workspace | undefined {
  return WORKSPACES.find((ws) => ws.id === id);
}
