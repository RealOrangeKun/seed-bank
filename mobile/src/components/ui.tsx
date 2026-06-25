import { Ionicons } from "@expo/vector-icons";
import {
  ActivityIndicator,
  Pressable,
  type StyleProp,
  StyleSheet,
  Text,
  TextInput,
  type TextInputProps,
  type TextStyle,
  View,
  type ViewStyle,
} from "react-native";

import { radius, spacing } from "@/theme/colors";
import { useTheme } from "@/theme/use-theme";

export function Loader({ label }: { label?: string }) {
  const { palette } = useTheme();
  return (
    <View style={styles.center}>
      <ActivityIndicator color={palette.primary} size="large" />
      {label ? (
        <Text style={{ marginTop: spacing.md, color: palette.textMuted }}>{label}</Text>
      ) : null}
    </View>
  );
}

export function Card({
  children,
  style,
}: {
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
}) {
  const { palette } = useTheme();
  return (
    <View
      style={[
        {
          backgroundColor: palette.card,
          borderColor: palette.border,
          borderWidth: StyleSheet.hairlineWidth,
          borderRadius: radius.lg,
          padding: spacing.lg,
        },
        style,
      ]}
    >
      {children}
    </View>
  );
}

type ButtonVariant = "primary" | "outline" | "ghost" | "danger";

export function AppButton({
  label,
  onPress,
  variant = "primary",
  icon,
  loading,
  disabled,
  style,
}: {
  label: string;
  onPress: () => void;
  variant?: ButtonVariant;
  icon?: keyof typeof Ionicons.glyphMap;
  loading?: boolean;
  disabled?: boolean;
  style?: StyleProp<ViewStyle>;
}) {
  const { palette } = useTheme();
  const isDisabled = disabled || loading;

  const bg =
    variant === "primary"
      ? palette.primary
      : variant === "danger"
        ? palette.danger
        : "transparent";
  const fg =
    variant === "primary" || variant === "danger"
      ? palette.primaryText
      : variant === "outline"
        ? palette.text
        : palette.primary;
  const border = variant === "outline" ? palette.border : "transparent";

  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      disabled={isDisabled}
      style={({ pressed }) => [
        {
          flexDirection: "row",
          alignItems: "center",
          justifyContent: "center",
          gap: spacing.sm,
          backgroundColor: bg,
          borderColor: border,
          borderWidth: variant === "outline" ? StyleSheet.hairlineWidth : 0,
          borderRadius: radius.md,
          paddingVertical: 14,
          paddingHorizontal: spacing.lg,
          opacity: isDisabled ? 0.5 : pressed ? 0.85 : 1,
        },
        style,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={fg} />
      ) : icon ? (
        <Ionicons name={icon} size={18} color={fg} />
      ) : null}
      <Text style={{ color: fg, fontSize: 16, fontWeight: "600" }}>{label}</Text>
    </Pressable>
  );
}

export function TextField({
  label,
  style,
  ...props
}: TextInputProps & { label?: string }) {
  const { palette } = useTheme();
  return (
    <View style={{ gap: spacing.xs }}>
      {label ? (
        <Text style={{ color: palette.textMuted, fontSize: 13, fontWeight: "500" }}>
          {label}
        </Text>
      ) : null}
      <TextInput
        placeholderTextColor={palette.textMuted}
        style={[
          {
            backgroundColor: palette.card,
            borderColor: palette.border,
            borderWidth: StyleSheet.hairlineWidth,
            borderRadius: radius.md,
            paddingHorizontal: spacing.md,
            paddingVertical: 12,
            color: palette.text,
            fontSize: 16,
            textAlign: "left",
          },
          style,
        ]}
        {...props}
      />
    </View>
  );
}

const STATUS_COLOR: Record<string, "success" | "danger" | "warning" | "muted"> = {
  succeeded: "success",
  partial: "warning",
  running: "warning",
  pending: "muted",
  failed: "danger",
};

export function StatusPill({ status, label }: { status: string; label: string }) {
  const { palette } = useTheme();
  const tone = STATUS_COLOR[status] ?? "muted";
  const color =
    tone === "success"
      ? palette.success
      : tone === "danger"
        ? palette.danger
        : tone === "warning"
          ? palette.warning
          : palette.textMuted;
  return (
    <View
      style={{
        alignSelf: "flex-start",
        flexDirection: "row",
        alignItems: "center",
        gap: 6,
        backgroundColor: `${color}22`,
        borderRadius: radius.pill,
        paddingHorizontal: 10,
        paddingVertical: 4,
      }}
    >
      <View style={{ width: 7, height: 7, borderRadius: 4, backgroundColor: color }} />
      <Text style={{ color, fontSize: 12, fontWeight: "600" }}>{label}</Text>
    </View>
  );
}

export function H1({ children, style }: { children: React.ReactNode; style?: StyleProp<TextStyle> }) {
  const { palette } = useTheme();
  return (
    <Text style={[{ color: palette.text, fontSize: 24, fontWeight: "700" }, style]}>
      {children}
    </Text>
  );
}

export function Muted({
  children,
  style,
}: {
  children: React.ReactNode;
  style?: StyleProp<TextStyle>;
}) {
  const { palette } = useTheme();
  return <Text style={[{ color: palette.textMuted, fontSize: 14 }, style]}>{children}</Text>;
}

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: "center", justifyContent: "center", padding: spacing.xl },
});
