import { createContext, useContext, useMemo, useState } from "react";
import { useColorScheme } from "react-native";

import { darkPalette, lightPalette, type Palette } from "./colors";

type ThemeMode = "system" | "light" | "dark";

interface ThemeValue {
  palette: Palette;
  isDark: boolean;
  mode: ThemeMode;
  setMode: (mode: ThemeMode) => void;
}

const ThemeContext = createContext<ThemeValue | null>(null);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const system = useColorScheme();
  const [mode, setMode] = useState<ThemeMode>("system");

  const isDark = mode === "system" ? system === "dark" : mode === "dark";

  const value = useMemo<ThemeValue>(
    () => ({
      palette: isDark ? darkPalette : lightPalette,
      isDark,
      mode,
      setMode,
    }),
    [isDark, mode],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within <ThemeProvider>");
  return ctx;
}
