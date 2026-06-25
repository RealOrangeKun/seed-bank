import { Ionicons } from "@expo/vector-icons";
import { useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { ApiError } from "@/api/client";
import { useAuth } from "@/auth/auth-context";
import { AppButton, H1, Muted, TextField } from "@/components/ui";
import { useI18n } from "@/i18n/i18n";
import { LanguageToggle } from "@/i18n/language-toggle";
import { spacing } from "@/theme/colors";
import { useTheme } from "@/theme/use-theme";

export function LoginScreen() {
  const { palette } = useTheme();
  const { t } = useI18n();
  const { signIn } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit() {
    if (!email.trim() || !password) {
      setError(t("auth.fillFields"));
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await signIn(email.trim(), password);
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 0
          ? t("error.network")
          : t("auth.failed"),
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: palette.background }}>
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <ScrollView
          contentContainerStyle={{ flexGrow: 1, justifyContent: "center", padding: spacing.xl }}
          keyboardShouldPersistTaps="handled"
        >
          <View style={{ alignItems: "center", marginBottom: spacing.xl }}>
            <View
              style={{
                width: 64,
                height: 64,
                borderRadius: 20,
                backgroundColor: `${palette.primary}22`,
                alignItems: "center",
                justifyContent: "center",
                marginBottom: spacing.md,
              }}
            >
              <Ionicons name="leaf" size={32} color={palette.primary} />
            </View>
            <H1>{t("common.appName")}</H1>
            <Muted style={{ marginTop: 4 }}>{t("common.tagline")}</Muted>
          </View>

          <View style={{ gap: spacing.md }}>
            <View style={{ marginBottom: spacing.xs }}>
              <Text style={{ color: palette.text, fontSize: 18, fontWeight: "700" }}>
                {t("auth.title")}
              </Text>
              <Muted>{t("auth.subtitle")}</Muted>
            </View>

            <TextField
              label={t("auth.email")}
              value={email}
              onChangeText={setEmail}
              autoCapitalize="none"
              keyboardType="email-address"
              autoComplete="email"
              placeholder={t("auth.emailPlaceholder")}
            />
            <TextField
              label={t("auth.password")}
              value={password}
              onChangeText={setPassword}
              secureTextEntry
              autoComplete="password"
            />

            {error ? (
              <Text style={{ color: palette.danger, fontSize: 13 }}>{error}</Text>
            ) : null}

            <AppButton
              label={t("auth.signIn")}
              onPress={onSubmit}
              loading={submitting}
              style={{ marginTop: spacing.sm }}
            />
            <Muted style={{ textAlign: "center", fontSize: 12 }}>
              {t("auth.serverHint")}
            </Muted>
          </View>

          <View style={{ alignItems: "center", marginTop: spacing.xl }}>
            <LanguageToggle />
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
