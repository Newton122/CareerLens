"use client";

import {
  API_BASE,
  AUTH_CHANGED_EVENT,
  SESSION_EXPIRED_EVENT,
  SESSION_KEYS,
  clearStoredSession,
  notifySessionChanged,
} from "@/components/api";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  useSyncExternalStore,
  ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import MessageDialog from "@/components/MessageDialog";

interface AuthContextType {
  token: string | null;
  userId: number | null;
  role: string | null;
  email: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}

// ─── The login session lives in localStorage ──────────────────────────────
//
// localStorage is an "external store": React doesn't own it, and it doesn't
// exist on the server, where these pages are first rendered. The tool React
// provides for reading such a store is useSyncExternalStore. It renders the
// server value (signed out) during hydration, then switches to the browser's
// value with no mismatch warning -- which reading localStorage in an effect
// and copying it into state did only by rendering twice.

function subscribe(onChange: () => void) {
  window.addEventListener("storage", onChange);
  window.addEventListener(AUTH_CHANGED_EVENT, onChange);
  return () => {
    window.removeEventListener("storage", onChange);
    window.removeEventListener(AUTH_CHANGED_EVENT, onChange);
  };
}

// A single string so React can compare snapshots cheaply (it must return an
// identical value while nothing has changed).
function readSession(): string {
  return JSON.stringify(SESSION_KEYS.map((key) => localStorage.getItem(key)));
}

const SIGNED_OUT = JSON.stringify(SESSION_KEYS.map(() => null));

const noSubscription = () => () => {};

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const session = useSyncExternalStore(subscribe, readSession, () => SIGNED_OUT);
  // False on the server and during hydration, true once in the browser:
  // until then we cannot know whether someone is signed in.
  const hydrated = useSyncExternalStore(noSubscription, () => true, () => false);
  const [signingIn, setSigningIn] = useState(false);
  const [dialog, setDialog] = useState({ open: false, title: '', message: '', type: 'info' as 'info' | 'success' | 'error' | 'warning' });

  const [token, storedUserId, role, email] = JSON.parse(session) as (string | null)[];
  const userId = token && storedUserId ? parseInt(storedUserId, 10) : null;

  // Say why someone was signed out, when api.ts reports a dead session. A
  // subscription: state is set in the event callback, not in the effect.
  useEffect(() => {
    const onExpired = () =>
      setDialog({ open: true, title: "Signed out", message: "Your session has ended. Please sign in again.", type: "info" });
    window.addEventListener(SESSION_EXPIRED_EVENT, onExpired);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onExpired);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setSigningIn(true);
    try {
      const response = await fetch(`${API_BASE}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        setDialog({ open: true, title: 'Error', message: data.detail || "Login failed. Please try again.", type: 'error' });
        return;
      }

      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("user_id", String(data.user_id));
      localStorage.setItem("careerLens_role", data.role);
      localStorage.setItem("user_email", data.email);
      notifySessionChanged();

      setDialog({ open: true, title: 'Success', message: "Login successful!", type: 'success' });

      if (data.role === "employer") {
        router.push("/employer/dashboard");
      } else if (data.role === "admin") {
        router.push("/admin/dashboard");
      } else {
        router.push("/dashboard");
      }
    } catch {
      setDialog({ open: true, title: 'Error', message: "Network error. Please try again.", type: 'error' });
    } finally {
      setSigningIn(false);
    }
  }, [router]);

  const logout = useCallback(() => {
    clearStoredSession();
    router.push("/login");
  }, [router]);

  return (
    <AuthContext.Provider
      value={{
        token,
        userId,
        role: token ? role : null,
        email: token ? email : null,
        loading: !hydrated || signingIn,
        login,
        logout,
        isAuthenticated: !!token,
      }}
    >
      {children}
      <MessageDialog
        open={dialog.open}
        onClose={() => setDialog({ ...dialog, open: false })}
        title={dialog.title}
        message={dialog.message}
        type={dialog.type}
      />
    </AuthContext.Provider>
  );
}
