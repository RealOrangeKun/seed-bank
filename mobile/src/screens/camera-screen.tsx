import { Ionicons } from "@expo/vector-icons";
import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { CameraView, useCameraPermissions } from "expo-camera";
import * as ImagePicker from "expo-image-picker";
import { useRef, useState } from "react";
import { Image, Pressable, ScrollView, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { analyzePhotos, analyzeVideo } from "@/api/batches";
import { ApiError } from "@/api/client";
import type { CapturedPhoto } from "@/api/types";
import { AppButton, H1, Muted } from "@/components/ui";
import { useI18n } from "@/i18n/i18n";
import type { RootStackParamList } from "@/navigation/types";
import { radius, spacing } from "@/theme/colors";
import { useTheme } from "@/theme/use-theme";

type Nav = NativeStackNavigationProp<RootStackParamList>;

export function CameraScreen() {
  const { palette } = useTheme();
  const { t, tn } = useI18n();
  const navigation = useNavigation<Nav>();

  const cameraRef = useRef<CameraView>(null);
  const [permission, requestPermission] = useCameraPermissions();
  const [facing, setFacing] = useState<"back" | "front">("back");
  const [torch, setTorch] = useState(false);
  const [photos, setPhotos] = useState<CapturedPhoto[]>([]);
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadingVideo, setUploadingVideo] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
        <Ionicons name="camera-outline" size={48} color={palette.primary} />
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

  // ── Capture ────────────────────────────────────────────────────────────────
  async function capture() {
    if (busy || !cameraRef.current) return;
    setBusy(true);
    try {
      const shot = await cameraRef.current.takePictureAsync({ quality: 0.6 });
      if (shot) {
        setPhotos((prev) => [
          ...prev,
          { uri: shot.uri, width: shot.width, height: shot.height },
        ]);
      }
    } finally {
      setBusy(false);
    }
  }

  function removePhoto(uri: string) {
    setPhotos((prev) => prev.filter((p) => p.uri !== uri));
  }

  async function analyze() {
    if (photos.length === 0 || uploading) return;
    setUploading(true);
    setError(null);
    try {
      const batch = await analyzePhotos(photos);
      setPhotos([]);
      navigation.navigate("Result", { batchId: batch.id });
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 0
          ? t("error.network")
          : t("camera.uploadError"),
      );
    } finally {
      setUploading(false);
    }
  }

  // ── Pick a video from the library → upload (YOLO-only on the server) ─────────
  async function pickVideo() {
    if (uploadingVideo) return;
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ["videos"],
      quality: 1,
    });
    if (result.canceled || !result.assets[0]) return;
    const asset = result.assets[0];
    setUploadingVideo(true);
    setError(null);
    try {
      const batch = await analyzeVideo({
        uri: asset.uri,
        name: asset.fileName,
        type: asset.mimeType,
      });
      navigation.navigate("Result", { batchId: batch.id });
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 0
          ? t("error.network")
          : t("camera.uploadError"),
      );
    } finally {
      setUploadingVideo(false);
    }
  }

  return (
    <View style={{ flex: 1, backgroundColor: "#000" }}>
      <CameraView ref={cameraRef} style={{ flex: 1 }} facing={facing} enableTorch={torch} />

      {/* Top hint */}
      <SafeAreaView
        edges={["top"]}
        style={{ position: "absolute", top: 0, left: 0, right: 0, pointerEvents: "box-none" }}
      >
        <View style={{ alignItems: "center", paddingTop: spacing.md, gap: spacing.sm }}>
          <Text
            style={{
              color: "#fff",
              backgroundColor: "rgba(0,0,0,0.45)",
              paddingHorizontal: spacing.md,
              paddingVertical: 6,
              borderRadius: radius.pill,
              overflow: "hidden",
              fontSize: 13,
            }}
          >
            {t("camera.hint")}
          </Text>
          <Pressable
            onPress={pickVideo}
            disabled={uploadingVideo}
            accessibilityRole="button"
            accessibilityLabel={t("camera.uploadVideo")}
            style={{
              flexDirection: "row",
              alignItems: "center",
              gap: 6,
              backgroundColor: "rgba(0,0,0,0.55)",
              paddingHorizontal: spacing.md,
              paddingVertical: 6,
              borderRadius: radius.pill,
              opacity: uploadingVideo ? 0.7 : 1,
            }}
          >
            <Ionicons name="film-outline" size={16} color="#fff" />
            <Text style={{ color: "#fff", fontSize: 13, fontWeight: "600" }}>
              {uploadingVideo ? t("camera.uploadingVideo") : t("camera.uploadVideo")}
            </Text>
          </Pressable>
        </View>
      </SafeAreaView>

      {/* Center framing guide */}
      <View
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          alignItems: "center",
          justifyContent: "center",
          pointerEvents: "none",
        }}
      >
        <View
          style={{
            width: "72%",
            aspectRatio: 1,
            borderColor: "rgba(255,255,255,0.7)",
            borderWidth: 2,
            borderRadius: radius.lg,
          }}
        />
      </View>

      {/* Bottom controls */}
      <SafeAreaView
        edges={["bottom"]}
        style={{ position: "absolute", bottom: 0, left: 0, right: 0, pointerEvents: "box-none" }}
      >
        {photos.length > 0 ? (
          <View style={{ paddingHorizontal: spacing.md, gap: spacing.sm }}>
            <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
              <Text style={{ color: "#fff", fontSize: 13, fontWeight: "600" }}>
                {tn("photos", photos.length)}
              </Text>
              <Pressable onPress={() => setPhotos([])} accessibilityRole="button">
                <Text style={{ color: "#ff8a80", fontSize: 13, fontWeight: "600" }}>
                  {t("camera.clearAll")}
                </Text>
              </Pressable>
            </View>
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={{ gap: spacing.sm, paddingVertical: spacing.sm }}
            >
              {photos.map((p) => (
                <Pressable key={p.uri} onPress={() => removePhoto(p.uri)}>
                  <Image
                    source={{ uri: p.uri }}
                    style={{ width: 56, height: 56, borderRadius: radius.sm }}
                  />
                  <View
                    style={{
                      position: "absolute",
                      top: -6,
                      right: -6,
                      backgroundColor: palette.danger,
                      borderRadius: 999,
                      width: 18,
                      height: 18,
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    <Ionicons name="close" size={12} color="#fff" />
                  </View>
                </Pressable>
              ))}
            </ScrollView>
            {error ? (
              <Text style={{ color: "#ff8a80", fontSize: 13 }}>{error}</Text>
            ) : null}
            <AppButton
              label={uploading ? t("camera.uploading") : `${t("camera.analyzeNow")} · ${tn("photos", photos.length)}`}
              icon="sparkles"
              onPress={analyze}
              loading={uploading}
            />
          </View>
        ) : null}

        <View
          style={{
            flexDirection: "row",
            alignItems: "center",
            justifyContent: "space-between",
            paddingHorizontal: spacing.xl,
            paddingVertical: spacing.lg,
          }}
        >
          <ControlButton
            icon="camera-reverse-outline"
            onPress={() => setFacing((f) => (f === "back" ? "front" : "back"))}
            label={t("camera.flip")}
          />
          <Shutter busy={busy} onPress={capture} color={palette.primary} />
          <ControlButton
            icon={torch ? "flash" : "flash-off"}
            onPress={() => setTorch((v) => !v)}
            label={t("camera.torch")}
            active={torch}
          />
        </View>
      </SafeAreaView>
    </View>
  );
}

function ControlButton({
  icon,
  onPress,
  label,
  active,
}: {
  icon: keyof typeof Ionicons.glyphMap;
  onPress: () => void;
  label?: string;
  active?: boolean;
}) {
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ selected: active }}
      style={{
        width: 52,
        height: 52,
        borderRadius: 26,
        backgroundColor: active ? "rgba(255,255,255,0.9)" : "rgba(0,0,0,0.45)",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <Ionicons name={icon} size={24} color={active ? "#000" : "#fff"} />
    </Pressable>
  );
}

function Shutter({
  busy,
  onPress,
  color,
}: {
  busy: boolean;
  onPress: () => void;
  color: string;
}) {
  return (
    <Pressable
      onPress={onPress}
      disabled={busy}
      accessibilityRole="button"
      style={({ pressed }) => ({
        width: 78,
        height: 78,
        borderRadius: 39,
        borderWidth: 4,
        borderColor: "#fff",
        alignItems: "center",
        justifyContent: "center",
        opacity: pressed || busy ? 0.7 : 1,
      })}
    >
      <View style={{ width: 60, height: 60, borderRadius: 30, backgroundColor: color }} />
    </Pressable>
  );
}
