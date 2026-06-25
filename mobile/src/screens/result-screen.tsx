import { Ionicons } from "@expo/vector-icons";
import { useQuery } from "@tanstack/react-query";
import { useNavigation, useRoute, type RouteProp } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useLayoutEffect } from "react";
import { ScrollView, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { getBatch, isTerminal, tallyBatch } from "@/api/batches";
import { AppButton, Card, H1, Loader, Muted, StatusPill } from "@/components/ui";
import { useI18n } from "@/i18n/i18n";
import { formatDateTime } from "@/i18n/locale";
import type { RootStackParamList } from "@/navigation/types";
import { radius, spacing } from "@/theme/colors";
import { useTheme } from "@/theme/use-theme";

type Nav = NativeStackNavigationProp<RootStackParamList>;
type Route = RouteProp<RootStackParamList, "Result">;

function Metric({ label, value, color }: { label: string; value: string; color?: string }) {
  const { palette } = useTheme();
  return (
    <View
      style={{
        flex: 1,
        backgroundColor: palette.surface,
        borderRadius: radius.md,
        padding: spacing.md,
        alignItems: "center",
      }}
    >
      <Text style={{ fontSize: 22, fontWeight: "700", color: color ?? palette.text }}>
        {value}
      </Text>
      <Muted style={{ fontSize: 12, marginTop: 2, textAlign: "center" }}>{label}</Muted>
    </View>
  );
}

export function ResultScreen() {
  const { palette } = useTheme();
  const { t } = useI18n();
  const navigation = useNavigation<Nav>();
  const { params } = useRoute<Route>();

  useLayoutEffect(() => {
    navigation.setOptions({ title: t("result.title") });
  }, [navigation, t]);

  const query = useQuery({
    queryKey: ["batch", params.batchId],
    queryFn: () => getBatch(params.batchId),
    refetchInterval: (q) =>
      q.state.data && isTerminal(q.state.data.status) ? false : 2000,
  });

  const batch = query.data;
  const terminal = batch ? isTerminal(batch.status) : false;
  const failed = batch?.status === "failed";
  const tally = batch && terminal && !failed ? tallyBatch(batch) : null;

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: palette.background }} edges={["bottom"]}>
      <ScrollView contentContainerStyle={{ padding: spacing.lg, gap: spacing.lg }}>
        {!batch ? (
          <Loader label={t("common.loading")} />
        ) : !terminal ? (
          <Card style={{ alignItems: "center", gap: spacing.md, paddingVertical: spacing.xl }}>
            <Loader />
            <H1 style={{ textAlign: "center" }}>{t("result.analyzingTitle")}</H1>
            <Muted style={{ textAlign: "center" }}>{t("result.analyzingHint")}</Muted>
            <StatusPill status={batch.status} label={t(`status.${batch.status}`)} />
          </Card>
        ) : failed ? (
          <Card style={{ alignItems: "center", gap: spacing.md, paddingVertical: spacing.xl }}>
            <Ionicons name="alert-circle-outline" size={48} color={palette.danger} />
            <H1 style={{ textAlign: "center" }}>{t("result.failedTitle")}</H1>
            <Muted style={{ textAlign: "center" }}>
              {batch.error_message ?? t("result.failedHint")}
            </Muted>
          </Card>
        ) : tally ? (
          <>
            <Card style={{ alignItems: "center", gap: spacing.sm }}>
              <StatusPill status={batch.status} label={t(`status.${batch.status}`)} />
              <Text style={{ fontSize: 56, fontWeight: "800", color: palette.primary }}>
                {Math.round(tally.goodRate * 100)}%
              </Text>
              <Muted style={{ textTransform: "uppercase", letterSpacing: 1, fontSize: 12 }}>
                {t("result.goodRate")}
              </Muted>
              {/* Good / bad proportion bar */}
              <View
                style={{
                  flexDirection: "row",
                  height: 12,
                  width: "100%",
                  borderRadius: radius.pill,
                  overflow: "hidden",
                  backgroundColor: palette.surface,
                  marginTop: spacing.sm,
                }}
              >
                <View
                  style={{
                    flex: tally.total ? tally.good : 0,
                    backgroundColor: palette.success,
                  }}
                />
                <View
                  style={{
                    flex: tally.total ? tally.bad : 0,
                    backgroundColor: palette.danger,
                  }}
                />
                <View style={{ flex: tally.total ? tally.total - tally.good - tally.bad : 1 }} />
              </View>
            </Card>

            <View style={{ flexDirection: "row", gap: spacing.sm }}>
              <Metric label={t("result.seeds")} value={`${tally.total}`} />
              <Metric
                label={t("result.good")}
                value={`${tally.good}`}
                color={palette.success}
              />
              <Metric label={t("result.bad")} value={`${tally.bad}`} color={palette.danger} />
            </View>
            <View style={{ flexDirection: "row", gap: spacing.sm }}>
              <Metric
                label={t("result.meanConfidence")}
                value={`${(tally.meanConfidence * 100).toFixed(0)}%`}
              />
              <Metric label={t("result.captured")} value={formatDateTime(batch.submitted_at)} />
            </View>
          </>
        ) : null}

        <View style={{ gap: spacing.sm, marginTop: spacing.sm }}>
          <AppButton
            label={t("result.newScan")}
            icon="camera"
            onPress={() => navigation.goBack()}
          />
          <AppButton
            label={t("result.viewHistory")}
            variant="outline"
            icon="time-outline"
            onPress={() => navigation.navigate("Tabs", { screen: "History" })}
          />
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
