"use client";

import { API_BASE } from "@/components/api";

import {
  createContext,
  useContext,
  useState,
  useEffect,
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

// Single source of truth; see components/api.ts. A local copy here meant
// sign-in ignored NEXT_PUBLIC_API_BASE and always hit port 8000.

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [userId, setUserId] = useState<number | null>(null);
  const [role, setRole] = useState<string | null>(null);
  const [email, setEmail] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [dialog, setDialog] = useState({ open: false, title: '', message: '', type: 'info' as 'info' | 'success' | 'error' | 'warning' });

  useEffect(() => {
    const t = localStorage.getItem("access_token");
    const uid = localStorage.getItem("user_id");
    const r = localStorage.getItem("careerLens_role");
    const e = localStorage.getItem("user_email");
    if (t) {
      setToken(t);
      if (uid) setUserId(parseInt(uid, 10));
      if (r) setRole(r);
      if (e) setEmail(e);
    }
    setLoading(false);
  }, []);

  const login = async (email: string, password: string) => {
    setLoading(true);
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

      setToken(data.access_token);
      setUserId(data.user_id);
      setRole(data.role);
      setEmail(data.email);

      setDialog({ open: true, title: 'Success', message: "Login successful!", type: 'success' });

      if (data.role === "employer") {
        router.push("/employer/dashboard");
      } else if (data.role === "admin") {
        router.push("/admin/dashboard");
      } else {
        router.push("/dashboard");
      }
    } catch (err) {
      setDialog({ open: true, title: 'Error', message: "Network error. Please try again.", type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user_id");
    localStorage.removeItem("careerLens_role");
    localStorage.removeItem("user_email");
    setToken(null);
    setUserId(null);
    setRole(null);
    setEmail(null);
    router.push("/login");
  };

  return (
    <AuthContext.Provider
      value={{
        token,
        userId,
        role,
        email,
        loading,
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
