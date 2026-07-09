/**
 * Auth + active-cluster context for the Vantage field app.
 *
 * There is no auth backend on this branch, so the session (the signed-in email
 * and the selected cluster/workspace) is held client-side. Everything the app
 * then shows is fetched live from the real backend — the session only decides
 * *who* is looking and *which cluster* they're scoped to.
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

const STORAGE_KEY = "vantage.session.v2";

type Session = {
  email: string;
  clusterId: number | null;
};

type AuthValue = {
  ready: boolean;
  email: string | null;
  clusterId: number | null;
  signIn: (email: string) => Promise<void>;
  signOut: () => void;
  selectCluster: (id: number) => void;
  clearCluster: () => void;
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
    const next: Session = { email: email.trim().toLowerCase(), clusterId: null };
    setSession(next);
    save(next);
  }, []);

  const signOut = useCallback(() => {
    setSession(null);
    save(null);
  }, []);

  const selectCluster = useCallback((id: number) => {
    setSession((prev) => {
      const next = { email: prev?.email ?? "", clusterId: id };
      save(next);
      return next;
    });
  }, []);

  const clearCluster = useCallback(() => {
    setSession((prev) => {
      if (!prev) return prev;
      const next = { ...prev, clusterId: null };
      save(next);
      return next;
    });
  }, []);

  const value = useMemo<AuthValue>(
    () => ({
      ready,
      email: session?.email ?? null,
      clusterId: session?.clusterId ?? null,
      signIn,
      signOut,
      selectCluster,
      clearCluster,
    }),
    [ready, session, signIn, signOut, selectCluster, clearCluster]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
  return ctx;
}
