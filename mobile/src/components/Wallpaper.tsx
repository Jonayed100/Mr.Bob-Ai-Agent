import { BlurView } from "expo-blur";
import { LinearGradient } from "expo-linear-gradient";
import { useEffect, useRef } from "react";
import { Animated, Easing, StyleSheet, useWindowDimensions, View } from "react-native";
import { useTheme } from "../theme";

/** Slowly drifting colour blobs under heavy blur: the "water" behind the glass. */
const BLOBS = [
  { color: "#FF4D63", size: 0.95, x: -0.25, y: -0.1, dx: 0.35, dy: 0.25, ms: 22000 },
  { color: "#FFB27A", size: 0.8, x: 0.45, y: 0.05, dx: -0.4, dy: 0.2, ms: 26000 },
  { color: "#7CC4FF", size: 0.9, x: 0.1, y: 0.45, dx: 0.3, dy: -0.3, ms: 30000 },
  { color: "#FF7AA8", size: 0.75, x: 0.5, y: 0.7, dx: -0.35, dy: -0.25, ms: 24000 },
];

function Blob({ b, w, h, opacity }: { b: (typeof BLOBS)[number]; w: number; h: number; opacity: number }) {
  const t = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(t, { toValue: 1, duration: b.ms, easing: Easing.inOut(Easing.sin), useNativeDriver: true }),
        Animated.timing(t, { toValue: 0, duration: b.ms, easing: Easing.inOut(Easing.sin), useNativeDriver: true }),
      ])
    );
    loop.start();
    return () => loop.stop();
  }, [t, b.ms]);
  const size = Math.max(w, h) * b.size;
  return (
    <Animated.View
      style={{
        position: "absolute",
        width: size,
        height: size,
        borderRadius: size / 2,
        backgroundColor: b.color,
        opacity,
        left: b.x * w,
        top: b.y * h,
        transform: [
          { translateX: t.interpolate({ inputRange: [0, 1], outputRange: [0, b.dx * w] }) },
          { translateY: t.interpolate({ inputRange: [0, 1], outputRange: [0, b.dy * h] }) },
          { scale: t.interpolate({ inputRange: [0, 1], outputRange: [1, 1.18] }) },
        ],
      }}
    />
  );
}

export function Wallpaper() {
  const { width, height } = useWindowDimensions();
  const theme = useTheme();
  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="none">
      <LinearGradient colors={[theme.bg, theme.bg]} style={StyleSheet.absoluteFill} />
      {BLOBS.map((b, i) => (
        <Blob key={i} b={b} w={width} h={height} opacity={theme.dark ? 0.42 : 0.7} />
      ))}
      <BlurView
        intensity={100}
        tint={theme.glassTint}
        experimentalBlurMethod="dimezisBlurView"
        style={StyleSheet.absoluteFill}
      />
    </View>
  );
}
