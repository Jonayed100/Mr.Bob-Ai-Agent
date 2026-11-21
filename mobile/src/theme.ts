import { useColorScheme } from "react-native";

export const brand = {
  red: "#E0142F",
  green: "#34C759",
  orange: "#FF9500",
  blue: "#0A84FF",
  pink: "#E2136E",
};

export function useTheme() {
  const dark = useColorScheme() === "dark";
  return {
    dark,
    bg: dark ? "#07050A" : "#F3EEF2",
    ink: dark ? "#F5F5F7" : "#1D1D1F",
    mute: dark ? "rgba(245,245,247,0.62)" : "rgba(29,29,31,0.6)",
    line: dark ? "rgba(255,255,255,0.10)" : "rgba(0,0,0,0.07)",
    glassTint: (dark ? "dark" : "light") as "dark" | "light",
    glassFill: dark ? "rgba(40,36,44,0.35)" : "rgba(255,255,255,0.38)",
    fill: dark ? "rgba(255,255,255,0.10)" : "rgba(255,255,255,0.65)",
    rim: dark ? "rgba(255,255,255,0.22)" : "rgba(255,255,255,0.85)",
  };
}

export type Theme = ReturnType<typeof useTheme>;
