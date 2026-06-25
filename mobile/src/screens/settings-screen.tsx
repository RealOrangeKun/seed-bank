import Constants from "expo-constants";
import { useState } from "react";
import { Pressable, ScrollView, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { getApiBaseUrl, setApiBaseUrl } from "@/api/config";
import { useAuth } from "@/auth/auth-context";
import { AppButton, Card, H1, Muted, TextField } from "@/components/ui";
import { useI18n } from "@/i18n/i18n";
import { LanguageToggle } from "@/i18n/language-toggle";
import { radius, spacing } from "@/theme/colors";
import { useTheme } from "@/theme/use-theme";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  const { palette } = useTheme();
  return (
    <View style={{ gap: spacing.sm }}>
      <Text
        style={{
          color: palette.textMuted,
          fontSize: 12,
          fontWeight: "700",
          textTransform: "uppercase",
          letterSpacing: 1,
        }}
      >
        {title}
      </Text>
      {children}
    </View>
  );
}

export function SettingsScreen() {
  const { palette, mode, setMode } = useTheme();
  const { t } = useI18n();
  const { user, signOut } = useAuth();
  const [server, setServer] = useState(getApiBaseUrl());

  const themeOptions = [
    { key: "system" as const, label: t("settings.themeSystem") },
    { key: "light" as const, label: t("settings.themeLight") },
    { key: "dark" as const, label: t("settings.themeDark") },
  ];

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: palette.background }} edges={["top"]}>
      <ScrollView contentContainerStyle={{ padding: spacing.lg, gap: spacing.xl }}>
        <H1>{t("settings.title")}</H1>

        <Section title={t("settings.language")}>
          <LanguageToggle />
        </Section>

        <Section title={t("settings.appearance")}>
          <View
            style={{
              flexDirection: "row",
              backgroundColor: palette.surface,
              borderColor: palette.border,
              borderWidth: 1,
              borderRadius: radius.md,
              padding: 4,
              gap: 4,
            }}
          >
            {themeOptions.map((opt) => {
              const active = mode === opt.key;
              return (
                <Pressable
                  key={opt.key}
                  onPress={() => setMode(opt.key)}
                  style={{
                    flex: 1,
                    alignItems: "center",
                    paddingVertical: 10,
                    borderRadius: radius.sm,
                    backgroundColor: active ? palette.primary : "transparent",
                  }}
                >
                  <Text
                    style={{
                      color: active ? palette.primaryText : palette.textMuted,
                      fontWeight: "600",
                    }}
                  >
                    {opt.label}
                  </Text>
                </Pressable>
              );
            })}
          </View>
        </Section>

        <Section title={t("settings.server")}>
          <TextField
            value={server}
            onChangeText={setServer}
            autoCapitalize="none"
            keyboardType="url"
            placeholder="http://192.168.1.10:8000"
          />
          <AppButton
            label={t("common.ok")}
            variant="outline"
            onPress={() => void setApiBaseUrl(server)}
          />
        </Section>

        <Section title={t("settings.account")}>
          <Card style={{ gap: spacing.md }}>
            <View>
              <Muted style={{ fontSize: 12 }}>{t("settings.signedInAs")}</Muted>
              <Text style={{ color: palette.text, fontSize: 15, fontWeight: "600" }}>
                {user?.email ?? "—"}
              </Text>
            </View>
            <AppButton
              label={t("settings.signOut")}
              variant="danger"
              icon="log-out-outline"
              onPress={() => void signOut()}
            />
          </Card>
        </Section>

        <Section title={t("settings.about")}>
          <Muted>
            {t("settings.version")}: {Constants.expoConfig?.version ?? "0.1.0"}
          </Muted>
        </Section>
      </ScrollView>
    </SafeAreaView>
  );
}
