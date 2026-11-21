import { Ionicons } from "@expo/vector-icons";
import { BlurView } from "expo-blur";
import { Tabs, useRouter } from "expo-router";
import { StyleSheet, View } from "react-native";
import { Orb } from "../../src/components/Orb";
import { Wallpaper } from "../../src/components/Wallpaper";
import { brand, useTheme } from "../../src/theme";

const ICONS: Record<string, keyof typeof Ionicons.glyphMap> = { index: "home", chat: "chatbubble-ellipses", settings: "settings" };

export default function TabsLayout() {
  const t = useTheme();
  const router = useRouter();
  return (
    <View style={{ flex: 1, backgroundColor: t.bg }}>
      <Wallpaper />
      <Tabs
        screenOptions={({ route }) => ({
          headerShown: false,
          sceneStyle: { backgroundColor: "transparent" },
          tabBarActiveTintColor: brand.red,
          tabBarInactiveTintColor: t.mute,
          tabBarStyle: styles.bar,
          tabBarItemStyle: { borderRadius: 999 },
          tabBarLabelStyle: { fontSize: 11, fontWeight: "600" },
          tabBarBackground: () => (
            <View style={[StyleSheet.absoluteFill, styles.barBg, { borderColor: t.rim }]}>
              <BlurView intensity={60} tint={t.glassTint} experimentalBlurMethod="dimezisBlurView" style={StyleSheet.absoluteFill} />
              <View style={[StyleSheet.absoluteFill, { backgroundColor: t.glassFill }]} />
            </View>
          ),
          tabBarIcon: ({ color, focused }) => (
            <Ionicons name={(focused ? ICONS[route.name] : `${String(ICONS[route.name])}-outline`) as any} size={22} color={color} />
          ),
        })}
      >
        <Tabs.Screen name="index" options={{ title: "Home" }} />
        <Tabs.Screen name="chat" options={{ title: "Chat" }} />
        <Tabs.Screen name="settings" options={{ title: "Settings" }} />
      </Tabs>
      {/* the Siri-style button floats beside the tab bar */}
      <View style={styles.orbWrap} pointerEvents="box-none">
        <Orb size={62} onPress={() => router.push("/voice")} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {
    position: "absolute", left: 16, right: 92, bottom: 22, height: 66, paddingBottom: 8, paddingTop: 8,
    borderRadius: 999, borderTopWidth: 0, backgroundColor: "transparent", elevation: 0,
  },
  barBg: { borderRadius: 999, overflow: "hidden", borderWidth: 1 },
  orbWrap: { position: "absolute", right: 18, bottom: 24 },
});
