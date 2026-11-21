import * as Haptics from "expo-haptics";
import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";
import { Animated, Easing, Image, Pressable, StyleSheet, Text, View } from "react-native";
import { useTheme } from "../theme";

export type BobState = "idle" | "listening" | "thinking" | "speaking";
export type BobCardHandle = { hop: (hearts?: number) => void };

const LINES = ["Meow! Ami Mr. Bob.", "Hehe, sursuri lage!", "Ki khobor, Jonayed?", "Purr… always here for you.",
  "Shh… roder moddhe ghumacchilam."];

/** Mr. Bob's photo in a floating glass frame that reacts to what he's doing. */
export const BobCard = forwardRef<BobCardHandle, { state?: BobState; width: number; onTap?: (line: string) => void }>(
  function BobCard({ state = "idle", width, onTap }, ref) {
    const t = useTheme();
    const float = useRef(new Animated.Value(0)).current;
    const pulse = useRef(new Animated.Value(0)).current;
    const hop = useRef(new Animated.Value(0)).current;
    const [hearts, setHearts] = useState<number[]>([]);

    useEffect(() => {
      const loop = Animated.loop(Animated.sequence([
        Animated.timing(float, { toValue: 1, duration: 2500, easing: Easing.inOut(Easing.sin), useNativeDriver: true }),
        Animated.timing(float, { toValue: 0, duration: 2500, easing: Easing.inOut(Easing.sin), useNativeDriver: true }),
      ]));
      loop.start();
      return () => loop.stop();
    }, [float]);

    useEffect(() => {
      pulse.stopAnimation();
      pulse.setValue(0);
      if (state === "idle") return;
      const speed = state === "speaking" ? 230 : state === "listening" ? 500 : 800;
      const loop = Animated.loop(Animated.sequence([
        Animated.timing(pulse, { toValue: 1, duration: speed, easing: Easing.inOut(Easing.quad), useNativeDriver: true }),
        Animated.timing(pulse, { toValue: 0, duration: speed, easing: Easing.inOut(Easing.quad), useNativeDriver: true }),
      ]));
      loop.start();
      return () => loop.stop();
    }, [state, pulse]);

    const doHop = (n = 0) => {
      hop.setValue(0);
      Animated.spring(hop, { toValue: 1, useNativeDriver: true, speed: 14, bounciness: 14 }).start(() => hop.setValue(0));
      if (n) setHearts(h => [...h, ...Array.from({ length: n }, () => Math.random())]);
    };
    useImperativeHandle(ref, () => ({ hop: doHop }));

    const height = width * 0.75;
    const amount = state === "speaking" ? 0.03 : state === "listening" ? 0.045 : 0.015;
    const scale = pulse.interpolate({ inputRange: [0, 1], outputRange: [1, 1 + amount] });
    const rotate = state === "thinking" ? pulse.interpolate({ inputRange: [0, 1], outputRange: ["-2deg", "2deg"] }) : "0deg";
    const translateY = Animated.add(
      float.interpolate({ inputRange: [0, 1], outputRange: [0, -8] }),
      hop.interpolate({ inputRange: [0, 0.4, 1], outputRange: [0, -26, 0] })
    );

    return (
      <View style={{ width, height: height + 30, alignItems: "center", justifyContent: "center" }}>
        <Animated.View
          pointerEvents="none"
          style={[styles.glow, { width: width * 0.8, height: width * 0.8, borderRadius: width,
            opacity: state === "idle" ? 0.35 : pulse.interpolate({ inputRange: [0, 1], outputRange: [0.5, 0.9] }),
            transform: [{ scale: state === "idle" ? 1 : 1.2 }] }]}
        />
        <Pressable
          onPress={() => {
            Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {});
            doHop(3);
            onTap?.(LINES[Math.floor(Math.random() * LINES.length)]);
          }}
          accessibilityRole="imagebutton"
          accessibilityLabel="Mr. Bob, a white and brown tabby cat napping in the sun. Tap to say hi."
        >
          <Animated.View style={[styles.frame, { width, height, borderColor: t.rim, backgroundColor: t.fill,
            transform: [{ perspective: 800 }, { translateY }, { scale }, { rotate }, { rotateX: "4deg" }] }]}>
            <Image source={require("../../assets/bob.jpg")} style={styles.photo} resizeMode="cover" />
          </Animated.View>
        </Pressable>
        {hearts.map((seed, i) => (
          <Heart key={`${seed}-${i}`} seed={seed} onDone={() => setHearts(h => h.filter(x => x !== seed))} />
        ))}
      </View>
    );
  }
);

function Heart({ seed, onDone }: { seed: number; onDone: () => void }) {
  const v = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    Animated.timing(v, { toValue: 1, duration: 1500, delay: seed * 250, easing: Easing.out(Easing.quad), useNativeDriver: true })
      .start(onDone);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <Animated.Text
      pointerEvents="none"
      style={[styles.heart, { left: `${35 + seed * 30}%`,
        opacity: v.interpolate({ inputRange: [0, 0.2, 1], outputRange: [0, 1, 0] }),
        transform: [{ translateY: v.interpolate({ inputRange: [0, 1], outputRange: [0, -170] }) },
          { scale: v.interpolate({ inputRange: [0, 1], outputRange: [0.8, 1.5] }) }] }]}
    >
      ♥
    </Animated.Text>
  );
}

const styles = StyleSheet.create({
  glow: { position: "absolute", backgroundColor: "rgba(255,110,135,0.45)" },
  frame: {
    borderRadius: 32, padding: 7, borderWidth: 1,
    shadowColor: "#501428", shadowOpacity: 0.25, shadowRadius: 24, shadowOffset: { width: 0, height: 14 }, elevation: 8,
  },
  photo: { width: "100%", height: "100%", borderRadius: 26 },
  heart: { position: "absolute", bottom: "40%", fontSize: 30, color: "#FF3D64" },
});

export const Speech = ({ text }: { text: string }) => {
  const t = useTheme();
  return (
    <View style={{ alignSelf: "center", maxWidth: "88%", paddingHorizontal: 16, paddingVertical: 10, borderRadius: 22,
      backgroundColor: t.fill, borderWidth: 1, borderColor: t.rim, marginBottom: 6 }}>
      <Text style={{ color: t.ink, fontSize: 15, textAlign: "center" }} numberOfLines={3}>{text}</Text>
    </View>
  );
};
