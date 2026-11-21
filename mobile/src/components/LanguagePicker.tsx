import { Pressable, StyleSheet, Text, View } from "react-native";
import { useSession } from "../session";
import { useTheme } from "../theme";

const LANGS = [["auto", "Auto"], ["english", "English"], ["bangla", "বাংলা"], ["banglish", "Banglish"]];
/** English / বাংলা / Banglish switch. "Auto" answers in whatever style you use. */
export function LanguagePicker() {
  const t = useTheme();
  const { language, setLanguage } = useSession();
  return (
    <View style={[styles.seg, { backgroundColor: t.dark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.06)" }]}>
      {LANGS.map(([key, label]) => (
        <Pressable key={key} onPress={() => setLanguage(key)} style={[styles.segBtn, language === key && { backgroundColor: t.fill }]}
          accessibilityRole="button" accessibilityState={{ selected: language === key }}>
          <Text style={{ color: t.ink, fontWeight: language === key ? "700" : "500", fontSize: 14 }}>{label}</Text>
        </Pressable>
      ))}
    </View>
  );
}


const styles = StyleSheet.create({
  seg: { flexDirection: "row", borderRadius: 999, padding: 3, alignSelf: "flex-start" },
  segBtn: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 999 },
});
