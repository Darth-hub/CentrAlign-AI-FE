// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import { createContext, useContext, useState, useEffect } from "react";
import type { ReactNode } from "react";
import type { AuthUser } from "./auth";
import { login as authLogin, logout as authLogout, getAuthUser, SESSION_INVALIDATED } from "./auth";

interface AuthContextType {
  user: AuthUser | null;
  loading: boolean;
  authError: string;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  authError: "",
  login: async () => {},
  logout: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState("");

  useEffect(() => {
    let active = true;
    let rejected = false;
    const invalidate = () => {
      rejected = true;
      setUser(null);
      setLoading(false);
      setAuthError("Your session could not be verified. Please sign in again.");
    };
    window.addEventListener(SESSION_INVALIDATED, invalidate);
    getAuthUser()
      .then(user => { if (active && !rejected) setUser(user); })
      .catch(() => { if (active) setUser(null); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; window.removeEventListener(SESSION_INVALIDATED, invalidate); };
  }, []);

  const login = async (username: string, password: string) => {
    const u = await authLogin(username, password);
    setUser(u);
  };

  const logout = async () => {
    await authLogout();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, authError, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components -- context hook co-located with its provider; splitting into a separate file is a larger refactor with no runtime benefit.
export const useAuth = () => useContext(AuthContext);
