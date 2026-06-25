import { Ionicons } from "@expo/vector-icons";
import { Pressable, View } from "react-native";

import type { BatchOut } from "@/api/types";
import { useI18n } from "@/i18n/i18n";
import { formatDateTime } from "@/i18n/locale";
import { spacing } from "@/theme/colors";
import { useTheme } from "@/theme/use-theme";

import { Card, Muted, StatusPill } from "./ui";

/** A single scan row: timestamp, photo count, status — used by Home and History. */
export function BatchRow({ batch, onPress }: { batch: BatchOut; onPress: () => void }) {
  const { palette } = useTheme();
  const { t, tn } = useI18n();

  return (
    <Pressable onPress={onPress}>
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
            {formatDateTime(batch.submitted_at)}
          </Muted>
          <Muted style={{ fontSize: 13 }}>{tn("photos", batch.image_count)}</Muted>
        </View>
        <StatusPill status={batch.status} label={t(`status.${batch.status}`)} />
        <Ionicons name="chevron-forward" size={18} color={palette.textMuted} />
      </Card>
    </Pressable>
  );
}
