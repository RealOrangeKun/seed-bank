import { Ionicons } from "@expo/vector-icons";
import { Pressable, Text, View } from "react-native";

import { radius, spacing } from "@/theme/colors";
import { useTheme } from "@/theme/use-theme";

import { LOCALE_LABEL, LOCALES } from "./locale";
import { useI18n } from "./i18n";

/** Segmented English / العربية switch. Switching to Arabic restarts the app. */
export function LanguageToggle() {
  const { palette } = useTheme();
  const { locale, setLocale } = useI18n();

  return (
    <View
      style={{
        flexDirection: "row",
        alignItems: "center",
        gap: spacing.sm,
        backgroundColor: palette.surface,
        borderColor: palette.border,
        borderWidth: 1,
        borderRadius: radius.pill,
        padding: 4,
      }}
    >
      <Ionicons
        name="language"
        size={16}
        color={palette.textMuted}
        style={{ marginHorizontal: 4 }}
      />
      {LOCALES.map((loc) => {
        const active = loc === locale;
        return (
          <Pressable
            key={loc}
            onPress={() => void setLocale(loc)}
            accessibilityRole="button"
            style={{
              backgroundColor: active ? palette.primary : "transparent",
              borderRadius: radius.pill,
              paddingVertical: 6,
              paddingHorizontal: 14,
            }}
          >
            <Text
              style={{
                color: active ? palette.primaryText : palette.textMuted,
                fontWeight: "600",
                fontSize: 13,
              }}
            >
              {LOCALE_LABEL[loc]}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}
