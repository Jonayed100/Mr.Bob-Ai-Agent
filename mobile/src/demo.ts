import type { Dashboard, Reply } from "./api";

/** Sample data so the app can be tried without a server ("Try demo" on the login screen). */
export const demoDashboard: Dashboard = {
  owner: "Jonayed",
  now: { day: "SATURDAY", date: 21, time: "9:10 AM" },
  weather: { city: "Dhaka", temp_c: 24, condition: "Hazy", aqi: 168, aqi_label: "unhealthy", rain_at: "6:00 PM" },
  events: [
    { title: "Team stand-up", time: "10:30 AM", where: "Google Meet" },
    { title: "AI Engineer interview", time: "3:00 PM", where: "TechNest, Gulshan 2" },
    { title: "Gym", time: "8:00 PM", where: "Banani" },
  ],
  reminders: [
    { id: 1, text: "Pay DESCO bill", when: "25 Nov 10:00 AM", done: false },
    { id: 2, text: "Print interview CV", when: "Today 1:00 PM", done: true },
  ],
  alerts: [
    { id: 1, source: "gmail", title: "Interview confirmed for 3:00 PM today", sender: "TechNest HR", detail: "", level: "high", when: "Today 8:12 AM" },
    { id: 2, source: "gmail", title: "Electricity bill ৳1,240 due on 25 Nov", sender: "DESCO", detail: "", level: "high", when: "Today 7:40 AM" },
    { id: 3, source: "weather", title: "Rain likely around 6:00 PM", sender: "", detail: "Hazy, 24°C", level: "medium", when: "Today 9:00 AM" },
  ],
  suggestions: [
    { id: 1, text: "Leave for Gulshan by 2:15 PM. Airport Road gets slow in the afternoon and your interview is at 3:00 PM.", feedback: null },
    { id: 2, text: "Pay the DESCO bill today with bKash so you don't forget. It's due in 4 days.", feedback: null },
  ],
  connections: [
    { name: "gmail", label: "Gmail", detail: "Checks new mail regularly", enabled: true },
    { name: "calendar", label: "Google Calendar", detail: "Today and tomorrow", enabled: true },
    { name: "weather", label: "Weather", detail: "Rain and air quality", enabled: true },
    { name: "telegram", label: "Telegram", detail: "Alerts, briefings and chat", enabled: true },
    { name: "whatsapp", label: "WhatsApp", detail: "Alerts and chat", enabled: true },
    { name: "bkash", label: "bKash SMS", detail: "Tracks money in and out", enabled: true },
    { name: "app", label: "Phone app", detail: "Push notifications", enabled: true },
  ],
  google: { ready: true, connected: true },
  telegram: { ready: true, chat_set: true },
  whatsapp: { alerts: true, chat: true },
  bkash: {
    in: 1500, out: 2758.5, balance: 822, count: 4,
    recent: [
      { label: "Bill paid", direction: "out", amount: 1240, party: "DESCO Prepaid", when: "Today 11:20 AM" },
      { label: "Cash out", direction: "out", amount: 1000, party: "01912xxxxxx", when: "Today 10:40 AM" },
      { label: "Received", direction: "in", amount: 1500, party: "01712xxxxxx", when: "Today 10:15 AM" },
    ],
  },
  activity: [
    { time: "9:00 AM", text: "Warned you about rain" },
    { time: "8:15 AM", text: "Checked Gmail: 9 new, 6 skipped as low priority" },
    { time: "8:12 AM", text: "Flagged email as important: Interview confirmed" },
    { time: "7:00 AM", text: "Sent your morning briefing" },
  ],
  cost: {
    items: [
      { label: "Server (VPS)", bdt: 1300, color: "#1d1d1f" },
      { label: "AI brain (Claude)", bdt: 212, color: "#e0142f" },
      { label: "Speech-to-text", bdt: 96, color: "#ff9500" },
      { label: "Domain", bdt: 150, color: "#0a84ff" },
      { label: "VAT on USD services", bdt: 46, color: "#8e8e93" },
    ],
    total: 1804, budget: 2700, left: 896,
  },
  language: "auto",
  brain: { claude: true, backup: true },
};

export function demoReply(text: string): Reply {
  const s = text.toLowerCase();
  let reply = "Ami ekhon demo mode e achi. Schedule, weather, email, bKash ba reminder niye jiggesh koro.";
  if (/bkash|taka|টাকা|balance/.test(s)) reply = "Ei mashe bKash e 1,500 taka eseche, 2,758 taka khoroch hoyeche. Ekhon balance 822 taka.";
  else if (/schedule|meeting|kaj|শিডিউল|কাজ|ajke ki/.test(s)) reply = "Ajke 3 ta jinish: 10:30 AM e stand-up, 3:00 PM e TechNest interview Gulshan 2 te, ar 8:00 PM e gym. 2:15 PM er moddhe ber hoye jeo.";
  else if (/weather|rain|brishti|আবহাওয়া|বৃষ্টি/.test(s)) reply = "ঢাকায় এখন ২৪ ডিগ্রি, একটু কুয়াশা। সন্ধ্যা ৬টার পর হালকা বৃষ্টি হতে পারে, ছাতা নিয়ে যেও।";
  else if (/mail|email|মেইল/.test(s)) reply = "Two important emails: TechNest confirmed your interview at 3:00 PM, and your DESCO bill of 1,240 taka is due on 25 November.";
  else if (/remind|mone|মনে/.test(s)) reply = "Done! I'll remind you at 8:00 PM. Purr.";
  return { reply, audio_url: null };
}
