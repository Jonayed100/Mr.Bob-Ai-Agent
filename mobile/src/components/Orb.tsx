import * as Haptics from "expo-haptics";
import { LinearGradient } from "expo-linear-gradient";
import { useEffect, useRef } from "react";
import { Animated, Easing, Pressable, View } from "react-native";

/** The swirling Siri-style button. Spins faster while listening. */
export function Orb({ size = 62, onPress, active = false, label = "Talk to Mr. Bob" }: {
  size?: number; onPress?: () => void; active?: boolean; label?: string;
}) {
  const spin = useRef(new Animated.Value(0)).current;
  const press = useRef(new Animated.Value(1)).current;
  useEffect(() => {
    spin.setValue(0);
    const loop = Animated.loop(Animated.timing(spin, { toValue: 1, duration: active ? 1400 : 7000, easing: Easing.linear, useNativeDriver: true }));
    loop.start();
    return () => loop.stop();
  }, [active, spin]);
  const rotate = spin.interpolate({ inputRange: [0, 1], outputRange: ["0deg", "360deg"] });
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      onPressIn={() => Animated.spring(press, { toValue: 0.9, useNativeDriver: true }).start()}
      onPressOut={() => Animated.spring(press, { toValue: 1, useNativeDriver: true, bounciness: 14 }).start()}
      onPress={() => {
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium).catch(() => {});
        onPress?.();
      }}
    >
      <Animated.View style={{ width: size, height: size, borderRadius: size / 2, transform: [{ scale: press }],
        shadowColor: "#E0142F", shadowOpacity: 0.45, shadowRadius: 16, shadowOffset: { width: 0, height: 8 }, elevation: 10 }}>
        <Animated.View style={{ width: size, height: size, borderRadius: size / 2, overflow: "hidden", transform: [{ rotate }] }}>
          <LinearGradient colors={["#FF2D55", "#FF9500", "#FF6B81", "#7CC4FF", "#E0142F"]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={{ flex: 1 }} />
        </Animated.View>
        <View pointerEvents="none" style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0, borderRadius: size / 2, borderWidth: 2, borderColor: "rgba(255,255,255,0.65)" }} />
      </Animated.View>
    </Pressable>
  );
}
