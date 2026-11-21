import { BlurView } from "expo-blur";
import * as Haptics from "expo-haptics";
import { LinearGradient } from "expo-linear-gradient";
import { ReactNode, useRef } from "react";
import { Animated, Pressable, StyleProp, StyleSheet, Text, TextStyle, View, ViewStyle } from "react-native";
import { brand, useTheme } from "../theme";

/** A Liquid Glass panel: blur, a light rim and a soft shine on top. */
export function Glass({ children, style, radius = 28, padding = 18 }: {
  children?: ReactNode; style?: StyleProp<ViewStyle>; radius?: number; padding?: number;
}) {
  const t = useTheme();
  return (
    <View style={[{ borderRadius: radius, overflow: "hidden", borderWidth: 1, borderColor: t.rim }, shadow, style]}>
      <BlurView intensity={45} tint={t.glassTint} experimentalBlurMethod="dimezisBlurView" style={StyleSheet.absoluteFill} />
      <View style={[StyleSheet.absoluteFill, { backgroundColor: t.glassFill }]} />
      <LinearGradient
        colors={[t.dark ? "rgba(255,255,255,0.12)" : "rgba(255,255,255,0.55)", "rgba(255,255,255,0)"]}
        start={{ x: 0, y: 0 }}
        end={{ x: 0.6, y: 0.5 }}
        style={StyleSheet.absoluteFill}
        pointerEvents="none"
      />
      <View style={{ padding }}>{children}</View>
    </View>
  );
}

/** A springy glass button. */
export function Pill({ label, onPress, icon, primary, small, style, disabled }: {
  label: string; onPress?: () => void; icon?: ReactNode; primary?: boolean; small?: boolean;
  style?: StyleProp<ViewStyle>; disabled?: boolean;
}) {
  const t = useTheme();
  const scale = useRef(new Animated.Value(1)).current;
  const to = (v: number) => Animated.spring(scale, { toValue: v, useNativeDriver: true, speed: 40, bounciness: 12 }).start();
  return (
    <Animated.View style={[{ transform: [{ scale }], opacity: disabled ? 0.5 : 1 }, style]}>
      <Pressable
        disabled={disabled}
        onPressIn={() => to(0.94)}
        onPressOut={() => to(1)}
        onPress={() => {
          Haptics.selectionAsync().catch(() => {});
          onPress?.();
        }}
        accessibilityRole="button"
        accessibilityLabel={label}
      >
        {primary ? (
          <LinearGradient
            colors={["#FF3B55", "#D80F2B"]}
            style={[styles.pill, small && styles.small, { borderColor: "rgba(255,255,255,0.4)" }]}
          >
            {icon}
            <Text style={[styles.pillText, small && styles.smallText, { color: "#fff" }]}>{label}</Text>
          </LinearGradient>
        ) : (
          <View style={[styles.pill, small && styles.small, { backgroundColor: t.fill, borderColor: t.rim }]}>
            {icon}
            <Text style={[styles.pillText, small && styles.smallText, { color: t.ink }]}>{label}</Text>
          </View>
        )}
      </Pressable>
    </Animated.View>
  );
}

export function H2({ children, style }: { children: ReactNode; style?: StyleProp<TextStyle> }) {
  const t = useTheme();
  return <Text style={[{ fontSize: 26, fontWeight: "700", letterSpacing: -0.6, color: t.ink, marginBottom: 12, marginTop: 26 }, style]}>{children}</Text>;
}

export function Muted({ children, style }: { children: ReactNode; style?: StyleProp<TextStyle> }) {
  const t = useTheme();
  return <Text style={[{ color: t.mute, fontSize: 14 }, style]}>{children}</Text>;
}

export function AppIcon({ letter, color }: { letter: string; color: string }) {
  return (
    <View style={{ width: 34, height: 34, borderRadius: 10, backgroundColor: color, alignItems: "center", justifyContent: "center" }}>
      <Text style={{ color: "#fff", fontWeight: "700", fontSize: 14 }}>{letter}</Text>
    </View>
  );
}

export function Row({ children, last }: { children: ReactNode; last?: boolean }) {
  const t = useTheme();
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: 12, paddingVertical: 11,
      borderBottomWidth: last ? 0 : StyleSheet.hairlineWidth, borderBottomColor: t.line }}>
      {children}
    </View>
  );
}

export const shadow: ViewStyle = {
  shadowColor: "#501428",
  shadowOpacity: 0.12,
  shadowRadius: 18,
  shadowOffset: { width: 0, height: 10 },
  elevation: 3,
};

const styles = StyleSheet.create({
  pill: {
    flexDirection: "row", alignItems: "center", gap: 10, minHeight: 54, paddingHorizontal: 22,
    borderRadius: 999, borderWidth: 1, justifyContent: "center",
  },
  small: { minHeight: 36, paddingHorizontal: 14 },
  pillText: { fontSize: 17, fontWeight: "600", letterSpacing: -0.2 },
  smallText: { fontSize: 14, fontWeight: "500" },
});

export { brand };
