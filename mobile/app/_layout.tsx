import { Stack, useRouter, useSegments } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { useEffect } from "react";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { registerForPush } from "../src/push";
import { SessionProvider, useSession } from "../src/session";

function Gate() {
  const { ready, signedIn } = useSession();
  const segments = useSegments();
  const router = useRouter();

  // send people to the login screen until they're signed in
  useEffect(() => {
    if (!ready) return;
    const onLogin = segments[0] === "login";
    if (!signedIn && !onLogin) router.replace("/login");
    if (signedIn && onLogin) router.replace("/");
  }, [ready, signedIn, segments, router]);

  useEffect(() => {
    if (signedIn) registerForPush();
  }, [signedIn]);

  return (
    <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: "transparent" } }}>
      <Stack.Screen name="(tabs)" />
      <Stack.Screen name="login" options={{ animation: "fade" }} />
      <Stack.Screen name="voice" options={{ presentation: "fullScreenModal", animation: "fade" }} />
    </Stack>
  );
}

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <SessionProvider>
        <StatusBar style="auto" />
        <Gate />
      </SessionProvider>
    </SafeAreaProvider>
  );
}
