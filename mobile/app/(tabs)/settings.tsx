import * as Linking from "expo-linking";
import { Alert, ScrollView, StyleSheet, Switch, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { logout, post, serverUrl, taka } from "../../src/api";
import { AppIcon, brand, Glass, H2, Muted, Pill, Row } from "../../src/components/Glass";
import { registerForPush } from "../../src/push";
import { useSession } from "../../src/session";
import { useTheme } from "../../src/theme";

const COLORS: Record<string, string> = {
  gmail: brand.red, calendar: "#FF3B30", weather: brand.blue, telegram: "#2AABEE",
  whatsapp: "#25D366", bkash: brand.pink, app: "#1D1D1F",
};

export default function Settings() {
  const t = useTheme();
  const insets = useSafeAreaInsets();
  const { data, refresh, setSignedIn } = useSession();

  const toggle = async (name: string, enabled: boolean) => {
    await post(`/connections/${name}`, { enabled }).catch(() => {});
    refresh();
  };

  const briefing = async () => {
    const r = await post<{ text: string }>("/briefing/morning").catch(() => ({ text: "" }));
    Alert.alert(r.text ? "Briefing sent" : "Couldn't make the briefing", r.text || "Please try again in a minute.");
  };

  const signOut = () =>
    Alert.alert("Log out?", "You'll need the password to come back.", [
      { text: "Cancel", style: "cancel" },
      { text: "Log out", style: "destructive", onPress: async () => { await logout(); setSignedIn(false); } },
    ]);

  if (!data) return <View style={{ flex: 1 }} />;
  const c = data.cost;

  return (
    <ScrollView contentContainerStyle={{ paddingTop: insets.top + 12, paddingHorizontal: 18, paddingBottom: 130 }}>
      <Text style={[styles.title, { color: t.ink }]}>Settings</Text>

      <H2>Connections</H2>
      <Glass padding={4} style={{ paddingHorizontal: 14 }}>
        {data.connections.map((x, i) => (
          <Row key={x.name} last={i === data.connections.length - 1}>
            <AppIcon letter={x.label[0]} color={COLORS[x.name] ?? "#8E8E93"} />
            <View style={{ flex: 1 }}>
              <Text style={[styles.label, { color: t.ink }]}>{x.label}</Text>
              <Muted style={{ fontSize: 13 }}>{x.detail}</Muted>
            </View>
            <Switch value={x.enabled} onValueChange={v => toggle(x.name, v)} trackColor={{ true: brand.green }} />
          </Row>
        ))}
      </Glass>

      <H2>Accounts</H2>
      <Glass padding={4} style={{ paddingHorizontal: 14 }}>
        <Row>
          <AppIcon letter="G" color="#4285F4" />
          <View style={{ flex: 1 }}>
            <Text style={[styles.label, { color: t.ink }]}>Google</Text>
            <Muted style={{ fontSize: 13 }}>{data.google.connected ? "Gmail and Calendar connected" : "Connect it once on the web dashboard"}</Muted>
          </View>
          {!data.google.connected ? <Pill small label="Open" onPress={() => Linking.openURL(serverUrl() + "/#settings")} /> : null}
        </Row>
        <Row>
          <AppIcon letter="T" color="#2AABEE" />
          <View style={{ flex: 1 }}>
            <Text style={[styles.label, { color: t.ink }]}>Telegram</Text>
            <Muted style={{ fontSize: 13 }}>{data.telegram.chat_set ? "Linked to your account" : "Send /start to your bot and share your number"}</Muted>
          </View>
        </Row>
        <Row>
          <AppIcon letter="W" color="#25D366" />
          <View style={{ flex: 1 }}>
            <Text style={[styles.label, { color: t.ink }]}>WhatsApp</Text>
            <Muted style={{ fontSize: 13 }}>
              {[data.whatsapp.alerts && "Alerts on", data.whatsapp.chat && "Two-way chat on"].filter(Boolean).join(" · ") || "Not set up yet"}
            </Muted>
          </View>
        </Row>
        <Row last>
          <AppIcon letter="N" color="#1D1D1F" />
          <View style={{ flex: 1 }}>
            <Text style={[styles.label, { color: t.ink }]}>Notifications on this phone</Text>
            <Muted style={{ fontSize: 13 }}>Alerts and briefings as push notifications</Muted>
          </View>
          <Pill small label="Turn on" onPress={async () => {
            const tok = await registerForPush();
            Alert.alert(tok ? "Notifications are on" : "Couldn't turn them on",
              tok ? "Mr. Bob will now notify this phone." : "Allow notifications in phone settings. They need the installed app, not Expo Go.");
          }} />
        </Row>
      </Glass>

      <H2>Monthly cost</H2>
      <Glass>
        <Text style={{ color: t.ink, fontSize: 40, fontWeight: "600", letterSpacing: -1 }}>
          {taka(c.total)} <Text style={{ fontSize: 16, color: t.mute, fontWeight: "500" }}>this month</Text>
        </Text>
        <View style={[styles.stack, { backgroundColor: t.line }]}>
          {c.items.filter(i => i.bdt).map(i => (
            <View key={i.label} style={{ width: `${Math.min(100, (i.bdt / c.budget) * 100)}%`, backgroundColor: i.color }} />
          ))}
        </View>
        <Muted>{c.left >= 0 ? `${taka(c.left)} left of your ${taka(c.budget)} budget` : `${taka(-c.left)} over budget`}</Muted>
        <View style={{ marginTop: 10, gap: 6 }}>
          {c.items.map(i => (
            <View key={i.label} style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
              <View style={{ width: 10, height: 10, borderRadius: 3, backgroundColor: i.color }} />
              <Text style={{ flex: 1, color: t.ink, fontSize: 14 }}>{i.label}</Text>
              <Text style={{ color: t.ink, fontSize: 14, fontVariant: ["tabular-nums"] }}>{taka(i.bdt)}</Text>
            </View>
          ))}
        </View>
      </Glass>

      <H2>Activity</H2>
      <Glass padding={4} style={{ paddingHorizontal: 14 }}>
        {data.activity.slice(0, 15).map((a, i, all) => (
          <Row key={i} last={i === all.length - 1}>
            <Muted style={{ width: 72, fontSize: 13 }}>{a.time}</Muted>
            <Text style={{ flex: 1, color: t.ink, fontSize: 15 }}>{a.text}</Text>
          </Row>
        ))}
      </Glass>

      <View style={{ gap: 10, marginTop: 26 }}>
        <Pill label="Send morning briefing now" onPress={briefing} />
        <Pill label="Log out" onPress={signOut} />
        <Muted style={{ textAlign: "center", marginTop: 8 }}>Connected to {serverUrl().replace(/^https?:\/\//, "")}</Muted>
        <Muted style={{ textAlign: "center", fontSize: 12 }}>Mr. Bob · A Project Aethrix Work</Muted>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  title: { fontSize: 34, fontWeight: "700", letterSpacing: -1 },
  label: { fontSize: 16, fontWeight: "500" },
  stack: { flexDirection: "row", height: 12, borderRadius: 6, overflow: "hidden", marginVertical: 12 },
});
