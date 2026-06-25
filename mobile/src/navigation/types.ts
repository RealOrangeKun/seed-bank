import type { NavigatorScreenParams } from "@react-navigation/native";

export type TabsParamList = {
  Home: undefined;
  Capture: undefined;
  History: undefined;
  Settings: undefined;
};

export type RootStackParamList = {
  Splash: undefined;
  Login: undefined;
  Tabs: NavigatorScreenParams<TabsParamList>;
  Result: { batchId: string };
};
