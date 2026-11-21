import * as SecureStore from "expo-secure-store";
import { demoDashboard, demoReply } from "./demo";

/** Talks to your Mr. Bob server. The address and login token are kept in the phone's secure storage. */

let server = "";
let token = "";

export class AuthError extends Error {}

export async function loadSession(): Promise<boolean> {
  server = (await SecureStore.getItemAsync("server")) || "";
  token = (await SecureStore.getItemAsync("token")) || "";
  return Boolean(server && token);
}

export const DEMO = "demo";
export const isDemo = () => server === DEMO;

export async function startDemo() {
  server = DEMO;
  token = DEMO;
  await SecureStore.setItemAsync("server", server);
  await SecureStore.setItemAsync("token", token);
}

export function serverUrl() {
  return server;
}

export function absolute(path: string) {
  return path.startsWith("http") ? path : server + path;
}

export async function login(address: string, password: string) {
  let base = address.trim().replace(/\/+$/, "");
  if (!/^https?:\/\//.test(base)) base = "https://" + base;
  const res = await fetch(base + "/api/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  }).catch(() => {
    throw new Error("Can't reach that address. Check it and your internet.");
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok || !body.token) throw new Error(body.detail || "Wrong password");
  server = base;
  token = body.token;
  await SecureStore.setItemAsync("server", server);
  await SecureStore.setItemAsync("token", token);
}

export async function logout() {
  token = "";
  await SecureStore.deleteItemAsync("token");
}

export async function api<T = any>(path: string, init: RequestInit = {}): Promise<T> {
  if (isDemo()) return demoApi(path, init) as T;
  const headers: Record<string, string> = { Authorization: `Bearer ${token}`, ...(init.headers as any) };
  if (init.body && typeof init.body === "string") headers["Content-Type"] = "application/json";
  const res = await fetch(server + "/api" + path, { ...init, headers });
  if (res.status === 401) throw new AuthError("Please log in again");
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail || `Error ${res.status}`);
  return body as T;
}

export const get = <T = any>(path: string) => api<T>(path);
export const post = <T = any>(path: string, body: unknown = {}) =>
  api<T>(path, { method: "POST", body: JSON.stringify(body) });

export type Reply = { heard?: string; reply: string; audio_url?: string | null };

export function chat(text: string, language: string, speak = false) {
  return post<Reply>("/chat", { text, language, speak });
}

export function sendVoice(uri: string, seconds: number, language: string) {
  if (isDemo()) return Promise.resolve({ heard: "(demo) Ajke amar schedule ki?", ...demoReply("schedule") });
  const form = new FormData();
  const ext = uri.split(".").pop() || "m4a";
  form.append("audio", { uri, name: `voice.${ext}`, type: ext === "webm" ? "audio/webm" : "audio/m4a" } as any);
  form.append("seconds", seconds.toFixed(1));
  form.append("language", language);
  return api<Reply>("/voice", { method: "POST", body: form });
}

/* ---------- shapes of the data the server sends ---------- */
export type Dashboard = {
  owner: string;
  now: { day: string; date: number; time: string };
  weather: { city: string; temp_c: number; condition: string; aqi: number | null; aqi_label: string; rain_at: string | null } | null;
  events: { title: string; time: string; where: string }[];
  reminders: { id: number; text: string; when: string; done: boolean }[];
  alerts: { id: number; source: string; title: string; sender: string; detail: string; level: string; when: string }[];
  suggestions: { id: number; text: string; feedback: string | null }[];
  connections: { name: string; label: string; detail: string; enabled: boolean }[];
  google: { ready: boolean; connected: boolean };
  telegram: { ready: boolean; chat_set: boolean };
  whatsapp: { alerts: boolean; chat: boolean };
  bkash: {
    in: number; out: number; balance: number | null; count: number;
    recent: { label: string; direction: "in" | "out"; amount: number; party: string; when: string }[];
  };
  activity: { time: string; text: string }[];
  cost: { items: { label: string; bdt: number; color: string }[]; total: number; budget: number; left: number };
  language: string;
  brain: { claude: boolean; backup: boolean };
};

export type ChatMessage = { role: "user" | "assistant"; text: string; channel?: string };

export const taka = (x: number | null | undefined) =>
  x == null ? "—" : "৳" + Number(x).toLocaleString("en-US", { maximumFractionDigits: 2 });

/* ---------- demo mode: answers from sample data, no server needed ---------- */
async function demoApi(path: string, init: RequestInit): Promise<unknown> {
  await new Promise(r => setTimeout(r, 350));
  const body = typeof init.body === "string" ? JSON.parse(init.body) : {};
  if (path === "/dashboard") return demoDashboard;
  if (path === "/messages") return [];
  if (path === "/chat") return demoReply(body.text || "");
  if (path === "/briefing/morning")
    return { text: "Good morning! Ajke 24 degree, sondhay brishti hote pare. 3:00 PM e TechNest interview, 2:15 PM er moddhe ber hoye jeo. DESCO bill 25 tarikh e due." };
  const rem = path.match(/^\/reminders\/(\d+)$/);
  if (rem) {
    const r = demoDashboard.reminders.find(x => x.id === Number(rem[1]));
    if (r) r.done = body.done;
  }
  const fb = path.match(/^\/suggestions\/(\d+)\/feedback$/);
  if (fb) {
    const s = demoDashboard.suggestions.find(x => x.id === Number(fb[1]));
    if (s) s.feedback = body.value;
  }
  const conn = path.match(/^\/connections\/(\w+)$/);
  if (conn) {
    const c = demoDashboard.connections.find(x => x.name === conn[1]);
    if (c) c.enabled = body.enabled;
  }
  return { ok: true };
}
