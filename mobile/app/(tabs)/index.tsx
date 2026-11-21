import { Ionicons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";
import { useRouter } from "expo-router";
import { useRef, useState } from "react";
import { Image, Pressable, RefreshControl, ScrollView, StyleSheet, Text, useWindowDimensions, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { api, post, taka } from "../../src/api";
import { BobCard, BobCardHandle, Speech } from "../../src/components/BobCard";
import { AppIcon, brand, Glass, H2, Muted, Pill, Row } from "../../src/components/Glass";
import { useSession } from "../../src/session";
import { useTheme } from "../../src/theme";

export default function Home() {
  const t = useTheme();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { width } = useWindowDimensions();
  const { data, error, refresh } = useSession();
  const [pulling, setPulling] = useState(false);
  const [line, setLine] = useState("");
  const bob = useRef<BobCardHandle>(null);

  const high = data?.alerts.find(a => a.level === "high");
  const bubble = line || (high ? `Heads up: ${high.title}` : data?.events[0] ? `Next up: ${data.events[0].title} at ${data.events[0].time}.` : "All calm today. Purr.");

  const toggleReminder = async (id: number, done: boolean) => {
    await api(`/reminders/${id}`, { method: "PATCH", body: JSON.stringify({ done: !done }) }).catch(() => {});
    refresh();
  };
  const rate = async (id: number, value: "up" | "down") => {
    await post(`/suggestions/${id}/feedback`, { value }).catch(() => {});
    refresh();
  };

  return (
    <ScrollView
      contentContainerStyle={{ paddingTop: insets.top + 12, paddingBottom: 130, paddingHorizontal: 18 }}
      refreshControl={<RefreshControl refreshing={pulling} tintColor={brand.red}
        onRefresh={async () => { setPulling(true); await refresh(); setPulling(false); }} />}
    >
      {/* header */}
      <View style={styles.header}>
        <Image source={require("../../assets/bob-face.jpg")} style={styles.avatar} />
        <View style={{ flex: 1 }}>
          <Text style={[styles.brand, { color: t.ink }]}>Mr. Bob</Text>
          <Muted style={{ fontSize: 12 }}>A Project Aethrix Work</Muted>
        </View>
        <View style={[styles.status, { backgroundColor: t.fill, borderColor: t.rim }]}>
          <View style={[styles.dot, { backgroundColor: error ? brand.orange : brand.green }]} />
          <Text style={{ color: t.mute, fontSize: 12 }}>{error ? "Offline" : "Online"}</Text>
        </View>
      </View>

      <Text style={[styles.hello, { color: t.ink }]}>Hi {data?.owner ?? "there"}, I'm Mr. Bob.</Text>
      <Muted style={{ fontSize: 16, marginBottom: 14 }}>I watch your mail, calendar, weather and bKash, and tell you what matters.</Muted>

      <Speech text={bubble} />
      <View style={{ alignItems: "center" }}>
        <BobCard ref={bob} width={Math.min(width - 36, 520)} onTap={setLine} />
      </View>
      <View style={{ flexDirection: "row", gap: 10, justifyContent: "center", marginTop: 4 }}>
        <Pill label="Talk to Mr. Bob" primary onPress={() => router.push("/voice")}
          icon={<Ionicons name="mic" size={20} color="#fff" />} />
        <Pill label="Type" onPress={() => router.push("/chat")} />
      </View>

      {!data ? (
        <Muted style={{ textAlign: "center", marginTop: 30 }}>{error || "Loading your day…"}</Muted>
      ) : (
        <>
          <H2>Today</H2>
          <View style={{ flexDirection: "row", gap: 12 }}>
            {/* weather */}
            <LinearGradient colors={["rgba(64,150,255,0.85)", "rgba(20,90,220,0.85)"]} style={[styles.weather]}>
              <Text style={styles.wxCity}>{data.weather?.city ?? "Weather"}</Text>
              <Text style={styles.wxTemp}>{data.weather ? `${data.weather.temp_c}°` : "--"}</Text>
              <Text style={styles.wxText}>{data.weather?.condition}</Text>
              {data.weather?.rain_at ? <Text style={styles.wxText}>Rain around {data.weather.rain_at}</Text> : null}
              {data.weather?.aqi != null ? <Text style={styles.wxText}>AQI {data.weather.aqi}</Text> : null}
            </LinearGradient>
            {/* date */}
            <Glass style={{ flex: 1 }} padding={16}>
              <Text style={{ color: brand.red, fontWeight: "700", fontSize: 12 }}>{data.now.day}</Text>
              <Text style={{ color: t.ink, fontSize: 42, fontWeight: "300", marginTop: -2 }}>{data.now.date}</Text>
              <Muted>{data.now.time}</Muted>
            </Glass>
          </View>

          <Glass style={{ marginTop: 12 }}>
            <Muted style={styles.cardTitle}>Calendar</Muted>
            {data.events.length ? data.events.map((e, i) => (
              <View key={i} style={styles.event}>
                <View style={styles.eventBar} />
                <View style={{ flex: 1 }}>
                  <Text style={[styles.bold, { color: t.ink }]}>{e.title}</Text>
                  <Muted>{e.time}{e.where ? ` · ${e.where}` : ""}</Muted>
                </View>
              </View>
            )) : <Muted>{data.google.connected ? "Nothing on your calendar today." : "Connect Google on the web dashboard."}</Muted>}
          </Glass>

          <Glass style={{ marginTop: 12 }}>
            <Muted style={styles.cardTitle}>Reminders</Muted>
            {data.reminders.length ? data.reminders.map((r, i) => (
              <Pressable key={r.id} onPress={() => toggleReminder(r.id, r.done)} accessibilityRole="checkbox" accessibilityState={{ checked: r.done }}>
                <Row last={i === data.reminders.length - 1}>
                  <Ionicons name={r.done ? "checkmark-circle" : "ellipse-outline"} size={24} color={brand.orange} />
                  <Text style={{ flex: 1, color: r.done ? t.mute : t.ink, textDecorationLine: r.done ? "line-through" : "none", fontSize: 16 }}>{r.text}</Text>
                  <Muted style={{ fontSize: 13 }}>{r.when}</Muted>
                </Row>
              </Pressable>
            )) : <Muted>No reminders. Ask me: “Remind me to call Ammu at 8 PM”.</Muted>}
          </Glass>

          <H2>Important</H2>
          <Glass padding={6} style={{ paddingHorizontal: 12 }}>
            {data.alerts.length ? data.alerts.map((a, i) => (
              <Row key={a.id} last={i === data.alerts.length - 1}>
                <AppIcon letter={a.source === "gmail" ? "M" : a.source === "calendar" ? "C" : "W"}
                  color={a.level === "high" ? brand.red : a.source === "weather" ? brand.blue : brand.orange} />
                <View style={{ flex: 1 }}>
                  <Text style={[styles.bold, { color: t.ink }]} numberOfLines={2}>{a.title}</Text>
                  <Muted>{a.sender || a.detail} · {a.when}</Muted>
                </View>
              </Row>
            )) : <View style={{ padding: 12 }}><Muted>Nothing important right now. Purr.</Muted></View>}
          </Glass>

          <H2>Mr. Bob suggests</H2>
          <View style={{ gap: 12 }}>
            {data.suggestions.length ? data.suggestions.map(s => (
              <Glass key={s.id} padding={16}>
                <Text style={{ color: t.ink, fontSize: 16, lineHeight: 22 }}>{s.text}</Text>
                <View style={{ flexDirection: "row", gap: 8, marginTop: 12 }}>
                  <Pill small label={s.feedback === "up" ? "✓ Useful" : "Useful"} onPress={() => rate(s.id, "up")} />
                  <Pill small label={s.feedback === "down" ? "✓ Not useful" : "Not useful"} onPress={() => rate(s.id, "down")} />
                </View>
              </Glass>
            )) : <Glass><Muted>No tips yet. They arrive a few times a day.</Muted></Glass>}
          </View>

          <H2>bKash this month</H2>
          <Glass>
            <View style={{ flexDirection: "row" }}>
              {[["Money in", data.bkash.in], ["Money out", data.bkash.out], ["Balance", data.bkash.balance]].map(([k, v]) => (
                <View key={k as string} style={{ flex: 1 }}>
                  <Muted style={{ fontSize: 12 }}>{k as string}</Muted>
                  <Text style={{ color: t.ink, fontSize: 21, fontWeight: "600" }} numberOfLines={1} adjustsFontSizeToFit>{taka(v as number)}</Text>
                </View>
              ))}
            </View>
            {data.bkash.recent.map((r, i) => (
              <Row key={i} last={i === data.bkash.recent.length - 1}>
                <AppIcon letter="৳" color={brand.pink} />
                <View style={{ flex: 1 }}>
                  <Text style={[styles.bold, { color: t.ink }]} numberOfLines={1}>{r.label}{r.party ? ` · ${r.party}` : ""}</Text>
                  <Muted>{r.when}</Muted>
                </View>
                <Text style={{ fontWeight: "600", color: r.direction === "in" ? brand.green : t.ink }}>
                  {r.direction === "in" ? "+" : "−"}{taka(r.amount)}
                </Text>
              </Row>
            ))}
            {!data.bkash.recent.length ? <Muted style={{ marginTop: 8 }}>No bKash messages yet.</Muted> : null}
          </Glass>
        </>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: "row", alignItems: "center", gap: 10, marginBottom: 18 },
  avatar: { width: 40, height: 40, borderRadius: 20, borderWidth: 2, borderColor: "rgba(255,255,255,0.9)" },
  brand: { fontSize: 17, fontWeight: "700" },
  status: { flexDirection: "row", alignItems: "center", gap: 6, paddingHorizontal: 10, paddingVertical: 5, borderRadius: 999, borderWidth: 1 },
  dot: { width: 8, height: 8, borderRadius: 4 },
  hello: { fontSize: 34, fontWeight: "700", letterSpacing: -1, lineHeight: 38, marginBottom: 6 },
  weather: { flex: 1.3, borderRadius: 28, padding: 16, borderWidth: 1, borderColor: "rgba(255,255,255,0.45)" },
  wxCity: { color: "rgba(255,255,255,0.85)", fontWeight: "600", fontSize: 13 },
  wxTemp: { color: "#fff", fontSize: 52, fontWeight: "300", letterSpacing: -2, marginVertical: -2 },
  wxText: { color: "#fff", fontSize: 13 },
  cardTitle: { fontWeight: "600", fontSize: 13, marginBottom: 6 },
  event: { flexDirection: "row", gap: 10, paddingVertical: 6 },
  eventBar: { width: 4, borderRadius: 2, backgroundColor: brand.red },
  bold: { fontWeight: "600", fontSize: 15 },
});
