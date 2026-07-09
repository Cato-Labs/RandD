/**
 * Auth + active-workspace context for the Vantage field app.
 *
 * The branch has no auth backend yet, so this holds session state client-side
 * (localStorage) behind a small API — `signIn`, `signOut`, `selectWorkspace`.
 * Swapping in real endpoints later means changing only the bodies here; every
 * screen consumes the context, never storage directly.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { USER, type FieldUser } from "@/lib/tenancy";

const STORAGE_KEY = "vantage.session.v1";

type Session = {
  user: FieldUser;
  workspaceId: string | null;
};

type AuthValue = {
  ready: boolean;
  user: FieldUser | null;
  workspaceId: string | null;
  signIn: (email: string) => Promise<FieldUser>;
  signOut: () => void;
  selectWorkspace: (id: string) => void;
};

const AuthContext = createContext<AuthValue | null>(null);

function load(): Session | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as Session) : null;
  } catch {
    return null;
  }
}

function save(session: Session | null) {
  try {
    if (session) localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
    else localStorage.removeItem(STORAGE_KEY);
  } catch {
    // storage unavailable (private mode) — session stays in memory for the tab
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setSession(load());
    setReady(true);
  }, []);

  const signIn = useCallback(async (email: string) => {
    // Demo identity resolution — carries the entered email onto the seeded
    // profile so the app feels personal. A real backend returns the user here.
    const trimmed = email.trim().toLowerCase();
    const user: FieldUser = trimmed ? { ...USER, email: trimmed } : USER;
    const next: Session = { user, workspaceId: null };
    setSession(next);
    save(next);
    return user;
  }, []);

  const signOut = useCallback(() => {
    setSession(null);
    save(null);
  }, []);

  const selectWorkspace = useCallback((id: string) => {
    setSession((prev) => {
      if (!prev) return prev;
      const next = { ...prev, workspaceId: id };
      save(next);
      return next;
    });
  }, []);

  const value = useMemo<AuthValue>(
    () => ({
      ready,
      user: session?.user ?? null,
      workspaceId: session?.workspaceId ?? null,
      signIn,
      signOut,
      selectWorkspace,
    }),
    [ready, session, signIn, signOut, selectWorkspace]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
  return ctx;
}
