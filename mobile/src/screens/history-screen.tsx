import { Ionicons } from "@expo/vector-icons";
import { useQuery } from "@tanstack/react-query";
import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { FlatList, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { listBatches } from "@/api/batches";
import type { BatchOut } from "@/api/types";
import { BatchRow } from "@/components/batch-row";
import { AppButton, H1, Loader, Muted } from "@/components/ui";
import { useI18n } from "@/i18n/i18n";
import type { RootStackParamList } from "@/navigation/types";
import { spacing } from "@/theme/colors";
import { useTheme } from "@/theme/use-theme";

type Nav = NativeStackNavigationProp<RootStackParamList>;

export function HistoryScreen() {
  const { palette } = useTheme();
  const { t } = useI18n();
  const navigation = useNavigation<Nav>();

  const query = useQuery({
    queryKey: ["batches"],
    queryFn: () => listBatches(1, 30),
  });

  const rows = query.data?.data ?? [];

  function renderItem({ item }: { item: BatchOut }) {
    return (
      <BatchRow
        batch={item}
        onPress={() => navigation.navigate("Result", { batchId: item.id })}
      />
    );
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: palette.background }} edges={["top"]}>
      <View style={{ paddingHorizontal: spacing.lg, paddingTop: spacing.md }}>
        <H1>{t("history.title")}</H1>
      </View>
      {query.isPending ? (
        <Loader label={t("common.loading")} />
      ) : query.isError ? (
        <View style={{ flex: 1, alignItems: "center", justifyContent: "center", gap: spacing.md, padding: spacing.xl }}>
          <Ionicons name="cloud-offline-outline" size={40} color={palette.danger} />
          <H1 style={{ fontSize: 18, textAlign: "center" }}>{t("history.loadError")}</H1>
          <AppButton
            label={t("common.retry")}
            icon="refresh"
            variant="outline"
            onPress={() => void query.refetch()}
          />
        </View>
      ) : (
        <FlatList
          data={rows}
          keyExtractor={(b) => b.id}
          renderItem={renderItem}
          onRefresh={() => void query.refetch()}
          refreshing={query.isRefetching}
          contentContainerStyle={{ padding: spacing.lg, gap: spacing.md, flexGrow: 1 }}
          ListEmptyComponent={
            <View style={{ alignItems: "center", justifyContent: "center", flex: 1, gap: spacing.md, paddingTop: spacing.xxl }}>
              <Ionicons name="images-outline" size={40} color={palette.textMuted} />
              <H1 style={{ fontSize: 18 }}>{t("history.empty")}</H1>
              <Muted style={{ textAlign: "center" }}>{t("history.emptyHint")}</Muted>
              <AppButton
                label={t("camera.analyzeNow")}
                icon="camera"
                onPress={() => navigation.navigate("Tabs", { screen: "Capture" })}
                style={{ marginTop: spacing.sm }}
              />
            </View>
          }
        />
      )}
    </SafeAreaView>
  );
}
