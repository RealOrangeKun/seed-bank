import { Ionicons } from "@expo/vector-icons";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { createNativeStackNavigator } from "@react-navigation/native-stack";

import { useAuth } from "@/auth/auth-context";
import { Loader } from "@/components/ui";
import { useI18n } from "@/i18n/i18n";
import { CameraScreen } from "@/screens/camera-screen";
import { HistoryScreen } from "@/screens/history-screen";
import { HomeScreen } from "@/screens/home-screen";
import { LoginScreen } from "@/screens/login-screen";
import { RealtimeScreen } from "@/screens/realtime-screen";
import { ResultScreen } from "@/screens/result-screen";
import { SettingsScreen } from "@/screens/settings-screen";
import { useTheme } from "@/theme/use-theme";

import type { RootStackParamList, TabsParamList } from "./types";

const Tab = createBottomTabNavigator<TabsParamList>();
const Stack = createNativeStackNavigator<RootStackParamList>();

const TAB_ICONS: Record<keyof TabsParamList, keyof typeof Ionicons.glyphMap> = {
  Home: "home",
  Capture: "camera",
  Realtime: "videocam",
  History: "time",
  Settings: "settings",
};

function MainTabs() {
  const { palette } = useTheme();
  const { t } = useI18n();

  const labels: Record<keyof TabsParamList, string> = {
    Home: t("tab.home"),
    Capture: t("tab.capture"),
    Realtime: t("tab.realtime"),
    History: t("tab.history"),
    Settings: t("tab.settings"),
  };

  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarActiveTintColor: palette.primary,
        tabBarInactiveTintColor: palette.textMuted,
        tabBarStyle: {
          backgroundColor: palette.card,
          borderTopColor: palette.border,
        },
        tabBarLabel: labels[route.name],
        tabBarIcon: ({ color, size }) => (
          <Ionicons name={TAB_ICONS[route.name]} size={size} color={color} />
        ),
      })}
    >
      <Tab.Screen name="Home" component={HomeScreen} />
      <Tab.Screen name="Capture" component={CameraScreen} />
      <Tab.Screen name="Realtime" component={RealtimeScreen} />
      <Tab.Screen name="History" component={HistoryScreen} />
      <Tab.Screen name="Settings" component={SettingsScreen} />
    </Tab.Navigator>
  );
}

export function RootNavigator() {
  const { palette } = useTheme();
  const { status } = useAuth();

  return (
    <Stack.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: palette.card },
        headerTintColor: palette.text,
        headerShadowVisible: false,
        contentStyle: { backgroundColor: palette.background },
      }}
    >
      {status === "loading" ? (
        <Stack.Screen name="Splash" component={SplashScreen} options={{ headerShown: false }} />
      ) : status === "unauthenticated" ? (
        <Stack.Screen name="Login" component={LoginScreen} options={{ headerShown: false }} />
      ) : (
        <>
          <Stack.Screen name="Tabs" component={MainTabs} options={{ headerShown: false }} />
          <Stack.Screen name="Result" component={ResultScreen} options={{ title: "" }} />
        </>
      )}
    </Stack.Navigator>
  );
}

function SplashScreen() {
  return <Loader />;
}
