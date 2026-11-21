import { createContext, ReactNode, useCallback, useContext, useEffect, useRef, useState } from "react";
import { AppState } from "react-native";
import { AuthError, Dashboard, get, loadSession } from "./api";

type Session = {
  ready: boolean;
  signedIn: boolean;
  setSignedIn: (v: boolean) => void;
  data: Dashboard | null;
  error: string;
  refresh: () => Promise<void>;
  language: string;
  setLanguage: (l: string) => void;
};

const Ctx = createContext<Session | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [signedIn, setSignedIn] = useState(false);
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState("");
  const [language, setLanguage] = useState("auto");
  const busy = useRef(false);

  useEffect(() => {
    loadSession().then(ok => {
      setSignedIn(ok);
      setReady(true);
    });
  }, []);

  const refresh = useCallback(async () => {
    if (busy.current) return;
    busy.current = true;
    try {
      const d = await get<Dashboard>("/dashboard");
      setData(d);
      setError("");
      if (d.language) setLanguage(d.language);
    } catch (e) {
      if (e instanceof AuthError) setSignedIn(false);
      else setError("Can't reach Mr. Bob right now");
    } finally {
      busy.current = false;
    }
  }, []);

  // refresh on login, every 30 seconds, and whenever the app comes back to the front
  useEffect(() => {
    if (!signedIn) return;
    refresh();
    const timer = setInterval(refresh, 30000);
    const sub = AppState.addEventListener("change", s => s === "active" && refresh());
    return () => {
      clearInterval(timer);
      sub.remove();
    };
  }, [signedIn, refresh]);

  return (
    <Ctx.Provider value={{ ready, signedIn, setSignedIn, data, error, refresh, language, setLanguage }}>
      {children}
    </Ctx.Provider>
  );
}

export function useSession() {
  const s = useContext(Ctx);
  if (!s) throw new Error("useSession must be inside SessionProvider");
  return s;
}
