# Mr. Bob — phone app

The Android and iPhone app for Mr. Bob, built with React Native and Expo. It connects to your own Mr. Bob server (the `backend/` in this repo), so the server must be running first.

**What it has**
- **Home:** Mr. Bob's photo in a floating glass card (tap him for hearts), today's weather and calendar, reminders you can tick off, important alerts, suggestions with Useful / Not useful, and bKash this month.
- **Voice:** a Siri-style screen with glowing edges. Mr. Bob starts listening as soon as it opens; tap the orb when you finish talking and he answers out loud. You can also type there.
- **Chat:** messages in English, বাংলা or Banglish, with quick ideas to tap.
- **Settings:** switch each connection on or off, account status, monthly cost, activity log, send a briefing, log out.
- **Push notifications:** important emails, reminders, rain warnings and briefings arrive like any other app notification.
- **Look:** iOS 26-style Liquid Glass over a slowly moving colour background, in light and dark mode. All times are 12-hour.

---

## Step 1. Try it on your phone today (Expo Go, free)

You need **Node.js 20 or newer** on your computer, and the **Expo Go** app on your phone (Play Store or App Store).

```bash
cd mobile
npm install
npx expo install expo@latest --fix     # matches the app to the newest Expo Go
npx expo start
```

What to expect:
1. A QR code appears in the terminal.
2. **Android:** open Expo Go and scan it. **iPhone:** scan it with the Camera app.
3. The Mr. Bob login screen opens. Either:
   - tap **Try demo (no server needed)** to look around with sample data, or
   - type your server address (for example `bob.yourdomain.com`) and your dashboard password.
4. You're in. Pull down on Home to refresh. (To leave the demo: Settings → Log out.)

> Testing before the server is online? Run the backend on your computer and use its local address, for example `http://192.168.0.105:8000`. The phone and computer must be on the same Wi-Fi.

Push notifications don't work inside Expo Go. Everything else does. For notifications, do Step 2.

---

## Step 2. Make a real installable app (Android APK, free)

This gives you a proper Mr. Bob icon on your phone, with push notifications.

```bash
npm install -g eas-cli
eas login              # free Expo account (expo.dev)
eas init               # links the app to your account and fills in the project id
eas build -p android --profile preview
```

What to expect:
- The build runs on Expo's servers (about 10–20 minutes; the free plan includes a number of builds each month).
- When it finishes you get a link. Open it on your Android phone, download the `.apk`, and install it (allow "install unknown apps" if asked).
- Open Mr. Bob, log in, then **Settings → Notifications on this phone → Turn on**.

## Step 3 (optional). Put it in the stores

- **Google Play:** one-time $25 developer account. Run `eas build -p android --profile production`, then `eas submit -p android`.
- **iPhone:** needs an Apple Developer account ($99/year) to install outside Expo Go. Run `eas build -p ios`, then `eas submit -p ios`.

---

## How it fits together

```
Phone app ──HTTPS──► Mr. Bob server (/api/...)
   │                     │
   │  login token        ├─ answers chat and voice (Claude + speech)
   │  in secure storage  ├─ sends replies as short-lived audio links
   │                     └─ sends push notifications through Expo's free push service
```

```
mobile/
├─ app/                 screens (Expo Router)
│  ├─ login.tsx         server address + password
│  ├─ voice.tsx         Siri-style voice screen
│  └─ (tabs)/           Home, Chat, Settings
├─ src/
│  ├─ api.ts            talks to the server
│  ├─ session.tsx       login state and live dashboard data
│  ├─ push.ts           push notification sign-up
│  ├─ theme.ts          colours for light and dark mode
│  └─ components/       Glass panels, Mr. Bob's card, the orb, wallpaper
└─ assets/              Mr. Bob's photo, icon and splash screen
```

## Troubleshooting

| Problem | Fix |
|---|---|
| "Can't reach that address" | Open the address in your phone's browser. If the dashboard loads there, check spelling in the app. |
| Expo Go says the project needs a newer/older SDK | Run `npx expo install expo@latest --fix` again, then `npx expo start -c`. |
| No sound from Mr. Bob on iPhone | Turn the ring/silent switch off and raise the volume. |
| Mic doesn't work | Phone Settings → Mr. Bob (or Expo Go) → allow Microphone. |
| No notifications | They need the installed app from Step 2, not Expo Go. Then Settings → Turn on. |

---

Mr. Bob · A Project Aethrix Work · Made by Jonayed Hossain
