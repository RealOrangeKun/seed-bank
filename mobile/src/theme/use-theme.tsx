import AsyncStorage from "@react-native-async-storage/async-storage";
import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { useColorScheme } from "react-native";

import { darkPalette, lightPalette, type Palette } from "./colors";

type ThemeMode = "system" | "light" | "dark";

const STORAGE_KEY = "seedbank.themeMode";
const MODES: ThemeMode[] = ["system", "light", "dark"];
const isMode = (value: unknown): value is ThemeMode =>
  typeof value === "string" && (MODES as string[]).includes(value);

interface ThemeValue {
  palette: Palette;
  isDark: boolean;
  mode: ThemeMode;
  setMode: (mode: ThemeMode) => void;
}

const ThemeContext = createContext<ThemeValue | null>(null);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const system = useColorScheme();
  const [mode, setModeState] = useState<ThemeMode>("system");

  // Hydrate the persisted preference once at startup.
  useEffect(() => {
    let active = true;
    void AsyncStorage.getItem(STORAGE_KEY).then((stored) => {
      if (active && isMode(stored)) setModeState(stored);
    });
    return () => {
      active = false;
    };
  }, []);

  const isDark = mode === "system" ? system === "dark" : mode === "dark";

  const value = useMemo<ThemeValue>(() => {
    const setMode = (next: ThemeMode) => {
      setModeState(next);
      void AsyncStorage.setItem(STORAGE_KEY, next);
    };
    return {
      palette: isDark ? darkPalette : lightPalette,
      isDark,
      mode,
      setMode,
    };
  }, [isDark, mode]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within <ThemeProvider>");
  return ctx;
}
