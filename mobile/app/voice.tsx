import { BlurView } from "expo-blur";
import {
  AudioModule, AudioPlayer, createAudioPlayer, RecordingPresets, setAudioModeAsync, useAudioRecorder,
} from "expo-audio";
import * as Haptics from "expo-haptics";
import { LinearGradient } from "expo-linear-gradient";
import { useRouter } from "expo-router";
import { useEffect, useRef, useState } from "react";
import {
  Animated, Easing, KeyboardAvoidingView, Platform, StyleSheet, Text, TextInput, useWindowDimensions, View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { absolute, chat, Reply, sendVoice } from "../src/api";
import { BobCard, BobState } from "../src/components/BobCard";
import { Pill } from "../src/components/Glass";
import { Orb } from "../src/components/Orb";
import { Wallpaper } from "../src/components/Wallpaper";
import { useSession } from "../src/session";
import { useTheme } from "../src/theme";

const STATE_TEXT: Record<BobState, string> = {
  idle: "Tap the orb and speak",
  listening: "Listening… tap when you're done",
  thinking: "Thinking…",
  speaking: "Mr. Bob is speaking",
};
const MAX_SECONDS = 20;

/** The Siri-style screen: glowing edges, Mr. Bob in the middle, tap to talk. */
export default function Voice() {
  const t = useTheme();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { width } = useWindowDimensions();
  const { language, refresh } = useSession();
  const recorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
  const [state, setStateRaw] = useState<BobState>("idle");
  const stateRef = useRef<BobState>("idle");
  const [heard, setHeard] = useState("");
  const [reply, setReply] = useState("");
  const [typed, setTyped] = useState("");
  const startedAt = useRef(0);
  const limit = useRef<ReturnType<typeof setTimeout> | null>(null);
  const player = useRef<AudioPlayer | null>(null);

  const setState = (s: BobState) => {
    stateRef.current = s;
    setStateRaw(s);
  };

  const stopPlayer = () => {
    try {
      player.current?.pause();
      player.current?.remove();
    } catch {}
    player.current = null;
  };

  const speak = async (r: Reply) => {
    setReply(r.reply);
    refresh();
    if (!r.audio_url) return setState("idle");
    await setAudioModeAsync({ allowsRecording: false, playsInSilentMode: true }).catch(() => {});
    stopPlayer();
    const p = createAudioPlayer({ uri: absolute(r.audio_url) });
    player.current = p;
    setState("speaking");
    p.addListener("playbackStatusUpdate", status => {
      if (status.didJustFinish) {
        setState("idle");
        stopPlayer();
      }
    });
    p.play();
  };

  const listen = async () => {
    stopPlayer();
    const perm = await AudioModule.requestRecordingPermissionsAsync();
    if (!perm.granted) {
      setReply("Please allow the microphone in your phone settings, or type below.");
      return;
    }
    await setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true });
    await recorder.prepareToRecordAsync();
    recorder.record();
    startedAt.current = Date.now();
    setHeard("");
    setReply("");
    setState("listening");
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {});
    limit.current = setTimeout(finish, MAX_SECONDS * 1000);
  };

  const finish = async () => {
    if (stateRef.current !== "listening") return;
    if (limit.current) clearTimeout(limit.current);
    setState("thinking");
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium).catch(() => {});
    try {
      await recorder.stop();
      const seconds = (Date.now() - startedAt.current) / 1000;
      if (!recorder.uri || seconds < 0.6) return setState("idle");
      const r = await sendVoice(recorder.uri, seconds, language);
      setHeard(r.heard || "");
      await speak(r);
    } catch (e: any) {
      setReply("Sorry: " + e.message);
      setState("idle");
    }
  };

  const sendTyped = async () => {
    const msg = typed.trim();
    if (!msg || stateRef.current === "thinking") return;
    setTyped("");
    setHeard(msg);
    setReply("");
    setState("thinking");
    try {
      await speak(await chat(msg, language, true));
    } catch (e: any) {
      setReply("Sorry: " + e.message);
      setState("idle");
    }
  };

  useEffect(() => {
    listen().catch(() => setState("idle"));
    return () => {
      if (limit.current) clearTimeout(limit.current);
      stopPlayer();
      if (stateRef.current === "listening") recorder.stop().catch(() => {});
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <View style={{ flex: 1, backgroundColor: t.bg }}>
      <Wallpaper />
      <BlurView intensity={30} tint={t.glassTint} style={StyleSheet.absoluteFill} />
      <GlowEdges state={state} />
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined}
        style={{ flex: 1, paddingTop: insets.top + 8, paddingBottom: insets.bottom + 16, paddingHorizontal: 20 }}>
        <View style={styles.top}>
          <Text style={{ color: t.ink, fontWeight: "700", fontSize: 17 }}>Mr. Bob</Text>
          <Pill small label="Done" onPress={() => router.back()} />
        </View>

        <View style={{ flex: 1, alignItems: "center", justifyContent: "center" }}>
          <BobCard state={state} width={Math.min(width - 60, 420)} />
        </View>

        <Text style={[styles.state, { color: t.mute }]}>{STATE_TEXT[state]}</Text>
        {heard ? <Text style={[styles.heard, { color: t.ink }]}>{heard}</Text> : null}
        {reply ? (
          <View style={[styles.reply, { backgroundColor: t.fill, borderColor: t.rim }]}>
            <Text style={{ color: t.ink, fontSize: 17, lineHeight: 24, textAlign: "center" }}>{reply}</Text>
          </View>
        ) : null}

        <View style={{ alignItems: "center", marginVertical: 14 }}>
          <Orb size={82} active={state === "listening"} label={state === "listening" ? "Stop and send" : "Speak"}
            onPress={() => (stateRef.current === "listening" ? finish() : stateRef.current === "idle" || stateRef.current === "speaking" ? listen() : null)} />
        </View>
        <TextInput
          style={[styles.input, { color: t.ink, backgroundColor: t.fill, borderColor: t.rim }]}
          placeholder="Or type to Mr. Bob"
          placeholderTextColor={t.mute}
          value={typed}
          onChangeText={setTyped}
          onSubmitEditing={sendTyped}
          returnKeyType="send"
        />
      </KeyboardAvoidingView>
    </View>
  );
}

/** Siri's glowing border: four soft gradient edges that breathe with Mr. Bob's state. */
function GlowEdges({ state }: { state: BobState }) {
  const v = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    const ms = state === "speaking" ? 450 : state === "listening" ? 800 : state === "thinking" ? 1200 : 2400;
    const loop = Animated.loop(Animated.sequence([
      Animated.timing(v, { toValue: 1, duration: ms, easing: Easing.inOut(Easing.sin), useNativeDriver: true }),
      Animated.timing(v, { toValue: 0, duration: ms, easing: Easing.inOut(Easing.sin), useNativeDriver: true }),
    ]));
    loop.start();
    return () => loop.stop();
  }, [state, v]);
  const size = state === "idle" ? 26 : state === "thinking" ? 40 : 64;
  const opacity = v.interpolate({ inputRange: [0, 1], outputRange: state === "idle" ? [0.35, 0.55] : [0.6, 1] });
  const edge = (colors: [string, string], style: object, start: { x: number; y: number }, end: { x: number; y: number }) => (
    <LinearGradient colors={colors} start={start} end={end} style={[{ position: "absolute" }, style]} />
  );
  return (
    <Animated.View pointerEvents="none" style={[StyleSheet.absoluteFill, { opacity }]}>
      {edge(["rgba(255,45,85,0.9)", "rgba(255,45,85,0)"], { top: 0, left: 0, right: 0, height: size }, { x: 0, y: 0 }, { x: 0, y: 1 })}
      {edge(["rgba(255,149,0,0.85)", "rgba(255,149,0,0)"], { bottom: 0, left: 0, right: 0, height: size }, { x: 0, y: 1 }, { x: 0, y: 0 })}
      {edge(["rgba(255,107,129,0.85)", "rgba(255,107,129,0)"], { top: 0, bottom: 0, left: 0, width: size }, { x: 0, y: 0 }, { x: 1, y: 0 })}
      {edge(["rgba(124,196,255,0.8)", "rgba(124,196,255,0)"], { top: 0, bottom: 0, right: 0, width: size }, { x: 1, y: 0 }, { x: 0, y: 0 })}
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  top: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  state: { textAlign: "center", fontSize: 15 },
  heard: { textAlign: "center", fontSize: 24, fontWeight: "600", letterSpacing: -0.5, marginTop: 6 },
  reply: { marginTop: 12, borderRadius: 24, borderWidth: 1, paddingHorizontal: 18, paddingVertical: 12 },
  input: { minHeight: 50, borderRadius: 25, borderWidth: 1, paddingHorizontal: 20, fontSize: 16 },
});
