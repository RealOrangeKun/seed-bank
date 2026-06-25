import { Ionicons } from "@expo/vector-icons";
import { useQuery } from "@tanstack/react-query";
import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { FlatList, Pressable, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { listBatches } from "@/api/batches";
import type { BatchOut } from "@/api/types";
import { Card, H1, Loader, Muted, StatusPill } from "@/components/ui";
import { useI18n } from "@/i18n/i18n";
import { formatDateTime } from "@/i18n/locale";
import type { RootStackParamList } from "@/navigation/types";
import { spacing } from "@/theme/colors";
import { useTheme } from "@/theme/use-theme";

type Nav = NativeStackNavigationProp<RootStackParamList>;

export function HistoryScreen() {
  const { palette } = useTheme();
  const { t, tn } = useI18n();
  const navigation = useNavigation<Nav>();

  const query = useQuery({
    queryKey: ["batches"],
    queryFn: () => listBatches(1, 30),
  });

  const rows = query.data?.data ?? [];

  function renderItem({ item }: { item: BatchOut }) {
    return (
      <Pressable onPress={() => navigation.navigate("Result", { batchId: item.id })}>
        <Card style={{ flexDirection: "row", alignItems: "center", gap: spacing.md }}>
          <View
            style={{
              width: 44,
              height: 44,
              borderRadius: 12,
              backgroundColor: `${palette.primary}22`,
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Ionicons name="leaf-outline" size={22} color={palette.primary} />
          </View>
          <View style={{ flex: 1, gap: 4 }}>
            <Muted style={{ color: palette.text, fontWeight: "600", fontSize: 15 }}>
              {formatDateTime(item.submitted_at)}
            </Muted>
            <Muted style={{ fontSize: 13 }}>{tn("photos", item.image_count)}</Muted>
          </View>
          <StatusPill status={item.status} label={t(`status.${item.status}`)} />
          <Ionicons name="chevron-forward" size={18} color={palette.textMuted} />
        </Card>
      </Pressable>
    );
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: palette.background }} edges={["top"]}>
      <View style={{ paddingHorizontal: spacing.lg, paddingTop: spacing.md }}>
        <H1>{t("history.title")}</H1>
      </View>
      {query.isPending ? (
        <Loader label={t("common.loading")} />
      ) : (
        <FlatList
          data={rows}
          keyExtractor={(b) => b.id}
          renderItem={renderItem}
          onRefresh={() => void query.refetch()}
          refreshing={query.isRefetching}
          contentContainerStyle={{ padding: spacing.lg, gap: spacing.md, flexGrow: 1 }}
          ListEmptyComponent={
            <View style={{ alignItems: "center", justifyContent: "center", flex: 1, gap: spacing.sm, paddingTop: spacing.xxl }}>
              <Ionicons name="images-outline" size={40} color={palette.textMuted} />
              <H1 style={{ fontSize: 18 }}>{t("history.empty")}</H1>
              <Muted style={{ textAlign: "center" }}>{t("history.emptyHint")}</Muted>
            </View>
          }
        />
      )}
    </SafeAreaView>
  );
}
