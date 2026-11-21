import Constants from "expo-constants";
import * as Device from "expo-device";
import * as Notifications from "expo-notifications";
import { Platform } from "react-native";
import { post } from "./api";

// show Mr. Bob's alerts even while the app is open
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

/**
 * Ask for permission and send this phone's push address to the server.
 * Push needs a real device and an app build (it does not work inside Expo Go on Android).
 */
export async function registerForPush(): Promise<string | null> {
  try {
    if (!Device.isDevice) return null;
    if (Platform.OS === "android") {
      await Notifications.setNotificationChannelAsync("default", {
        name: "Mr. Bob alerts",
        importance: Notifications.AndroidImportance.HIGH,
        lightColor: "#E0142F",
      });
    }
    let { status } = await Notifications.getPermissionsAsync();
    if (status !== "granted") status = (await Notifications.requestPermissionsAsync()).status;
    if (status !== "granted") return null;
    const projectId = Constants.expoConfig?.extra?.eas?.projectId || (Constants as any).easConfig?.projectId;
    if (!projectId) return null;
    const token = (await Notifications.getExpoPushTokenAsync({ projectId })).data;
    await post("/push/register", { token });
    return token;
  } catch {
    return null;
  }
}
