import { useState } from "react";
import { ActivityIndicator, Image, KeyboardAvoidingView, Platform, StyleSheet, Text, TextInput, View } from "react-native";
import { login } from "../src/api";
import { Glass, Muted, Pill } from "../src/components/Glass";
import { Wallpaper } from "../src/components/Wallpaper";
import { useSession } from "../src/session";
import { brand, useTheme } from "../src/theme";

export default function Login() {
  const t = useTheme();
  const { setSignedIn } = useSession();
  const [address, setAddress] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    if (!address || !password) return setError("Enter your Mr. Bob address and password");
    setBusy(true);
    setError("");
    try {
      await login(address, password);
      setSignedIn(true);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const input = [styles.input, { color: t.ink, backgroundColor: t.fill, borderColor: t.rim }];
  return (
    <View style={{ flex: 1, backgroundColor: t.bg }}>
      <Wallpaper />
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={styles.center}>
        <Glass style={{ width: "100%", maxWidth: 380 }} padding={26}>
          <View style={{ alignItems: "center", gap: 6 }}>
            <Image source={require("../assets/bob-face.jpg")} style={styles.face} />
            <Text style={[styles.title, { color: t.ink }]}>Mr. Bob</Text>
            <Muted>A Project Aethrix Work</Muted>
          </View>
          <View style={{ gap: 12, marginTop: 22 }}>
            <TextInput
              style={input}
              placeholder="bob.yourdomain.com"
              placeholderTextColor={t.mute}
              autoCapitalize="none"
              autoCorrect={false}
              keyboardType="url"
              value={address}
              onChangeText={setAddress}
              accessibilityLabel="Server address"
            />
            <TextInput
              style={input}
              placeholder="Password"
              placeholderTextColor={t.mute}
              secureTextEntry
              value={password}
              onChangeText={setPassword}
              onSubmitEditing={submit}
              accessibilityLabel="Password"
            />
            {error ? <Text style={{ color: brand.red, textAlign: "center" }}>{error}</Text> : null}
            {busy ? <ActivityIndicator color={brand.red} style={{ height: 54 }} /> : <Pill label="Unlock" primary onPress={submit} />}
          </View>
        </Glass>
      </KeyboardAvoidingView>
    </View>
  );
}

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: "center", justifyContent: "center", padding: 22 },
  face: { width: 84, height: 84, borderRadius: 42, borderWidth: 3, borderColor: "rgba(255,255,255,0.85)" },
  title: { fontSize: 32, fontWeight: "700", letterSpacing: -0.8, marginTop: 6 },
  input: { minHeight: 52, borderRadius: 26, paddingHorizontal: 20, fontSize: 16, borderWidth: 1 },
});
