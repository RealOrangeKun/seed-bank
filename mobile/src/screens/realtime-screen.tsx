import { Ionicons } from "@expo/vector-icons";
import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { CameraView, useCameraPermissions } from "expo-camera";
import { useCallback, useEffect, useRef, useState } from "react";
import { Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { analyzeFrame, tallyBatch, waitForBatch } from "@/api/batches";
import { ApiError } from "@/api/client";
import { AppButton, H1, Muted } from "@/components/ui";
import { useI18n } from "@/i18n/i18n";
import type { RootStackParamList } from "@/navigation/types";
import { radius, spacing } from "@/theme/colors";
import { useTheme } from "@/theme/use-theme";

type Nav = NativeStackNavigationProp<RootStackParamList>;

interface LiveStats {
  frames: number; // frames analyzed this session
  total: number; // cumulative seeds detected
  good: number;
  bad: number;
}

const EMPTY: LiveStats = { frames: 0, total: 0, good: 0, bad: 0 };

/**
 * Realtime analysis: instead of capturing photos and selecting which to send,
 * this streams the live camera video frame-by-frame to the backend and shows
 * the running tally as results come back — the mobile counterpart of the
 * desktop app's webcam inference mode. Frames are processed sequentially (grab
 * one, await its result, grab the next) so we never flood the worker queue.
 */
export function RealtimeScreen() {
  const { palette } = useTheme();
  const { t } = useI18n();
  const navigation = useNavigation<Nav>();

  const cameraRef = useRef<CameraView>(null);
  const [permission, requestPermission] = useCameraPermissions();
  const [running, setRunning] = useState(false);
  const [stats, setStats] = useState<LiveStats>(EMPTY);
  const [frameGood, setFrameGood] = useState<number | null>(null);
  const [frameBad, setFrameBad] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Loop control: a ref the async loop reads each tick, plus an AbortController
  // so an in-flight poll unblocks immediately on stop/unmount.
  const runningRef = useRef(false);
  const abortRef = useRef<AbortController | null>(null);

  const stop = useCallback(() => {
    runningRef.current = false;
    abortRef.current?.abort();
    setRunning(false);
  }, []);

  // Stop the loop if the screen unmounts mid-stream.
  useEffect(() => () => stop(), [stop]);

  async function loop() {
    while (runningRef.current && cameraRef.current) {
      let shot;
      try {
        shot = await cameraRef.current.takePictureAsync({ quality: 0.5, skipProcessing: true });
      } catch {
        break; // camera went away (navigated off, backgrounded)
      }
      if (!shot || !runningRef.current) break;

      try {
        const batch = await analyzeFrame({ uri: shot.uri, width: shot.width, height: shot.height });
        const detail = await waitForBatch(batch.id, { signal: abortRef.current?.signal });
        if (!runningRef.current) break;
        const tally = tallyBatch(detail);
        setFrameGood(tally.good);
        setFrameBad(tally.bad);
        setStats((prev) => ({
          frames: prev.frames + 1,
          total: prev.total + tally.total,
          good: prev.good + tally.good,
          bad: prev.bad + tally.bad,
        }));
        setError(null);
      } catch (err) {
        if (err instanceof Error && err.name === "AbortError") break;
        setError(
          err instanceof ApiError && err.status === 0
            ? t("error.network")
            : t("realtime.frameError"),
        );
        // Brief backoff so a transient failure doesn't spin the loop hot.
        await new Promise((r) => setTimeout(r, 1200));
      }
    }
  }

  function start() {
    if (runningRef.current) return;
    setStats(EMPTY);
    setFrameGood(null);
    setFrameBad(null);
    setError(null);
    abortRef.current = new AbortController();
    runningRef.current = true;
    setRunning(true);
    void loop();
  }

  // ── Permission gate ────────────────────────────────────────────────────────
  if (!permission) {
    return <View style={{ flex: 1, backgroundColor: "#000" }} />;
  }
  if (!permission.granted) {
    return (
      <SafeAreaView
        style={{
          flex: 1,
          backgroundColor: palette.background,
          alignItems: "center",
          justifyContent: "center",
          padding: spacing.xl,
          gap: spacing.md,
        }}
      >
        <Ionicons name="videocam-outline" size={48} color={palette.primary} />
        <H1 style={{ textAlign: "center" }}>{t("camera.permTitle")}</H1>
        <Muted style={{ textAlign: "center" }}>{t("camera.permMessage")}</Muted>
        <AppButton
          label={t("camera.grant")}
          icon="camera"
          onPress={() => void requestPermission()}
          style={{ marginTop: spacing.md, alignSelf: "stretch" }}
        />
      </SafeAreaView>
    );
  }

  const goodRate =
    stats.good + stats.bad > 0 ? Math.round((stats.good / (stats.good + stats.bad)) * 100) : 0;

  return (
    <View style={{ flex: 1, backgroundColor: "#000" }}>
      <CameraView ref={cameraRef} style={{ flex: 1 }} facing="back" />

      {/* Live status pill */}
      <SafeAreaView edges={["top"]} style={{ position: "absolute", top: 0, left: 0, right: 0 }}>
        <View style={{ alignItems: "center", paddingTop: spacing.md }}>
          <View
            style={{
              flexDirection: "row",
              alignItems: "center",
              gap: 8,
              backgroundColor: "rgba(0,0,0,0.5)",
              paddingHorizontal: spacing.md,
              paddingVertical: 6,
              borderRadius: radius.pill,
            }}
          >
            <View
              style={{
                width: 9,
                height: 9,
                borderRadius: 5,
                backgroundColor: running ? palette.danger : palette.textMuted,
              }}
            />
            <Text style={{ color: "#fff", fontSize: 13 }}>
              {running ? t("realtime.live") : t("realtime.idle")}
            </Text>
          </View>
        </View>
      </SafeAreaView>

      {/* Latest-frame badge */}
      {running && (frameGood !== null || frameBad !== null) ? (
        <View
          pointerEvents="none"
          style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 160, alignItems: "center", justifyContent: "center" }}
        >
          <View
            style={{
              flexDirection: "row",
              gap: spacing.md,
              backgroundColor: "rgba(0,0,0,0.4)",
              paddingHorizontal: spacing.lg,
              paddingVertical: spacing.sm,
              borderRadius: radius.lg,
            }}
          >
            <Text style={{ color: palette.success, fontSize: 28, fontWeight: "800" }}>
              {frameGood ?? 0}
            </Text>
            <Text style={{ color: "#fff", fontSize: 28, fontWeight: "300" }}>/</Text>
            <Text style={{ color: palette.danger, fontSize: 28, fontWeight: "800" }}>
              {frameBad ?? 0}
            </Text>
          </View>
        </View>
      ) : null}

      {/* Bottom panel: cumulative stats + control */}
      <SafeAreaView edges={["bottom"]} style={{ position: "absolute", bottom: 0, left: 0, right: 0 }}>
        <View style={{ paddingHorizontal: spacing.md, gap: spacing.sm }}>
          <View
            style={{
              flexDirection: "row",
              backgroundColor: "rgba(0,0,0,0.55)",
              borderRadius: radius.lg,
              paddingVertical: spacing.md,
            }}
          >
            <Stat label={t("realtime.frames")} value={`${stats.frames}`} />
            <Stat label={t("result.seeds")} value={`${stats.total}`} />
            <Stat label={t("result.good")} value={`${stats.good}`} color={palette.success} />
            <Stat label={t("result.bad")} value={`${stats.bad}`} color={palette.danger} />
            <Stat label={t("result.goodRate")} value={`${goodRate}%`} color={palette.primary} />
          </View>

          {error ? <Text style={{ color: "#ff8a80", fontSize: 13 }}>{error}</Text> : null}

          <View style={{ flexDirection: "row", gap: spacing.sm, paddingBottom: spacing.md }}>
            <View style={{ flex: 1 }}>
              <AppButton
                label={running ? t("realtime.stop") : t("realtime.start")}
                icon={running ? "stop" : "play"}
                variant={running ? "outline" : "primary"}
                onPress={running ? stop : start}
              />
            </View>
            {!running && stats.frames > 0 ? (
              <View style={{ flex: 1 }}>
                <AppButton
                  label={t("result.viewHistory")}
                  icon="time-outline"
                  variant="outline"
                  onPress={() => navigation.navigate("Tabs", { screen: "History" })}
                />
              </View>
            ) : null}
          </View>
        </View>
      </SafeAreaView>
    </View>
  );
}

function Stat({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <View style={{ flex: 1, alignItems: "center" }}>
      <Text style={{ color: color ?? "#fff", fontSize: 18, fontWeight: "700" }}>{value}</Text>
      <Text style={{ color: "rgba(255,255,255,0.7)", fontSize: 10, marginTop: 2 }}>{label}</Text>
    </View>
  );
}
