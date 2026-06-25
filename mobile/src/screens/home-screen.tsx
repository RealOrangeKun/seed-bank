import { Ionicons } from "@expo/vector-icons";
import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useQuery } from "@tanstack/react-query";
import { Pressable, ScrollView, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { listBatches } from "@/api/batches";
import { useAuth } from "@/auth/auth-context";
import { BatchRow } from "@/components/batch-row";
import { AppButton, Card, H1, Loader, Muted } from "@/components/ui";
import { useI18n } from "@/i18n/i18n";
import type { RootStackParamList } from "@/navigation/types";
import { radius, spacing } from "@/theme/colors";
import { useTheme } from "@/theme/use-theme";

type Nav = NativeStackNavigationProp<RootStackParamList>;

/** Friendly landing: greeting, a primary call-to-action, quick stats, recents. */
export function HomeScreen() {
  const { palette } = useTheme();
  const { t } = useI18n();
  const { user } = useAuth();
  const navigation = useNavigation<Nav>();

  const query = useQuery({
    queryKey: ["batches"],
    queryFn: () => listBatches(1, 30),
  });

  const rows = query.data?.data ?? [];
  const total = query.data?.meta?.total ?? rows.length;
  const photos = rows.reduce((sum, b) => sum + b.image_count, 0);
  const done = rows.filter((b) => b.status === "succeeded").length;
  const recent = rows.slice(0, 4);
  const name = user?.full_name?.trim() || user?.email?.split("@")[0] || "";

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: palette.background }} edges={["top"]}>
      <ScrollView contentContainerStyle={{ padding: spacing.lg, gap: spacing.lg }}>
        {/* Greeting */}
        <View style={{ gap: 2 }}>
          <Muted style={{ fontSize: 14 }}>{t("home.greeting")}</Muted>
          <H1>{name || t("common.appName")}</H1>
        </View>

        {/* Hero CTA */}
        <Card style={{ gap: spacing.md, backgroundColor: palette.primary, borderColor: palette.primary }}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: spacing.sm }}>
            <Ionicons name="leaf" size={22} color={palette.primaryText} />
            <Text style={{ color: palette.primaryText, fontSize: 18, fontWeight: "700", flex: 1 }}>
              {t("common.tagline")}
            </Text>
          </View>
          <AppButton
            label={t("camera.analyzeNow")}
            icon="camera"
            variant="outline"
            onPress={() => navigation.navigate("Tabs", { screen: "Capture" })}
            style={{ backgroundColor: palette.card, borderColor: palette.card }}
          />
        </Card>

        {/* Quick stats */}
        <View style={{ flexDirection: "row", gap: spacing.sm }}>
          <Stat label={t("home.statScans")} value={`${total}`} />
          <Stat label={t("home.statPhotos")} value={`${photos}`} />
          <Stat label={t("home.statDone")} value={`${done}`} color={palette.success} />
        </View>

        {/* Recent scans */}
        <View style={{ gap: spacing.sm }}>
          <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
            <Text style={{ color: palette.text, fontSize: 16, fontWeight: "700" }}>
              {t("home.recent")}
            </Text>
            {rows.length > 0 ? (
              <Pressable onPress={() => navigation.navigate("Tabs", { screen: "History" })}>
                <Text style={{ color: palette.primary, fontWeight: "600", fontSize: 13 }}>
                  {t("home.viewAll")}
                </Text>
              </Pressable>
            ) : null}
          </View>

          {query.isPending ? (
            <Loader />
          ) : recent.length === 0 ? (
            <Card style={{ alignItems: "center", gap: spacing.sm, paddingVertical: spacing.xl }}>
              <Ionicons name="images-outline" size={36} color={palette.textMuted} />
              <Muted style={{ textAlign: "center" }}>{t("home.emptyHint")}</Muted>
            </Card>
          ) : (
            <View style={{ gap: spacing.md }}>
              {recent.map((b) => (
                <BatchRow
                  key={b.id}
                  batch={b}
                  onPress={() => navigation.navigate("Result", { batchId: b.id })}
                />
              ))}
            </View>
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

function Stat({ label, value, color }: { label: string; value: string; color?: string }) {
  const { palette } = useTheme();
  return (
    <View
      style={{
        flex: 1,
        backgroundColor: palette.card,
        borderColor: palette.border,
        borderWidth: 1,
        borderRadius: radius.md,
        padding: spacing.md,
        alignItems: "center",
        gap: 2,
      }}
    >
      <Text style={{ fontSize: 22, fontWeight: "800", color: color ?? palette.text }}>{value}</Text>
      <Muted style={{ fontSize: 11, textAlign: "center" }}>{label}</Muted>
    </View>
  );
}
