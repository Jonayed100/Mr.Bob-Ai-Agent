import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import { useEffect, useRef, useState } from "react";
import {
  FlatList, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { chat, ChatMessage, get } from "../../src/api";
import { brand, Glass, Muted, Pill } from "../../src/components/Glass";
import { LanguagePicker } from "../../src/components/LanguagePicker";
import { useSession } from "../../src/session";
import { useTheme } from "../../src/theme";

const IDEAS = ["Ajke amar schedule ki?", "আজকের আবহাওয়া কেমন?", "Any important email?", "bKash e koto taka ache?",
  "Remind me to call Ammu at 8 PM"];

export default function Chat() {
  const t = useTheme();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { language, refresh } = useSession();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const list = useRef<FlatList<ChatMessage>>(null);

  useEffect(() => {
    get<ChatMessage[]>("/messages").then(ms => setMessages(ms.length ? ms : [
      { role: "assistant", text: "Assalamu alaikum! Ami Mr. Bob. Ki jante chao?" },
    ])).catch(() => {});
  }, []);

  const send = async (value: string) => {
    const msg = value.trim();
    if (!msg || busy) return;
    setText("");
    setBusy(true);
    setMessages(m => [...m, { role: "user", text: msg }, { role: "assistant", text: "…" }]);
    try {
      const r = await chat(msg, language);
      setMessages(m => [...m.slice(0, -1), { role: "assistant", text: r.reply }]);
      refresh();
    } catch (e: any) {
      setMessages(m => [...m.slice(0, -1), { role: "assistant", text: "Sorry, something went wrong: " + e.message }]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <View style={{ paddingTop: insets.top + 12, paddingHorizontal: 18, gap: 12 }}>
        <Text style={[styles.title, { color: t.ink }]}>Messages</Text>
        <LanguagePicker />
      </View>
      <FlatList
        ref={list}
        data={messages}
        keyExtractor={(_, i) => String(i)}
        contentContainerStyle={{ padding: 18, gap: 6 }}
        onContentSizeChange={() => list.current?.scrollToEnd({ animated: true })}
        renderItem={({ item }) => (
          <View style={[styles.msg, item.role === "user"
            ? { alignSelf: "flex-end", backgroundColor: brand.red, borderBottomRightRadius: 6 }
            : { alignSelf: "flex-start", backgroundColor: t.fill, borderBottomLeftRadius: 6, borderWidth: 1, borderColor: t.rim }]}>
            <Text style={{ color: item.role === "user" ? "#fff" : t.ink, fontSize: 16, lineHeight: 22 }}>{item.text}</Text>
          </View>
        )}
      />
      <View style={{ paddingHorizontal: 14, paddingBottom: 104, gap: 10 }}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8 }}>
          {IDEAS.map(i => <Pill key={i} small label={i} onPress={() => send(i)} />)}
        </ScrollView>
        <Glass radius={30} padding={6}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
            <Pressable onPress={() => router.push("/voice")} style={styles.iconBtn} accessibilityLabel="Talk instead">
              <Ionicons name="mic" size={22} color={brand.red} />
            </Pressable>
            <TextInput
              style={[styles.input, { color: t.ink }]}
              placeholder="Message Mr. Bob"
              placeholderTextColor={t.mute}
              value={text}
              onChangeText={setText}
              onSubmitEditing={() => send(text)}
              returnKeyType="send"
              multiline={false}
            />
            <Pressable onPress={() => send(text)} disabled={busy || !text.trim()} accessibilityLabel="Send"
              style={[styles.sendBtn, { opacity: busy || !text.trim() ? 0.5 : 1 }]}>
              <Ionicons name="arrow-up" size={20} color="#fff" />
            </Pressable>
          </View>
        </Glass>
        {busy ? <Muted style={{ textAlign: "center" }}>Mr. Bob is thinking…</Muted> : null}
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  title: { fontSize: 34, fontWeight: "700", letterSpacing: -1 },
  msg: { maxWidth: "80%", paddingHorizontal: 15, paddingVertical: 9, borderRadius: 21 },
  input: { flex: 1, fontSize: 16, minHeight: 44, paddingHorizontal: 6 },
  iconBtn: { width: 44, height: 44, borderRadius: 22, alignItems: "center", justifyContent: "center" },
  sendBtn: { width: 44, height: 44, borderRadius: 22, backgroundColor: brand.red, alignItems: "center", justifyContent: "center" },
});
