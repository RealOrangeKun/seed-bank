/**
 * Agricultural-green palette, mirroring the web app's design tokens so the two
 * clients feel like one product. Light is a warm off-white field; dark is a
 * soil-night palette. Resolved to concrete hex/hsl values (no CSS variables on
 * native).
 */
export interface Palette {
  background: string;
  surface: string;
  card: string;
  border: string;
  text: string;
  textMuted: string;
  primary: string;
  primaryText: string;
  success: string;
  danger: string;
  warning: string;
  overlay: string;
}

export const lightPalette: Palette = {
  background: "hsl(80, 30%, 98%)",
  surface: "hsl(90, 28%, 96%)",
  card: "#ffffff",
  border: "hsl(110, 16%, 86%)",
  text: "hsl(150, 25%, 12%)",
  textMuted: "hsl(150, 10%, 40%)",
  primary: "hsl(142, 60%, 30%)",
  primaryText: "hsl(140, 50%, 97%)",
  success: "hsl(142, 60%, 32%)",
  danger: "hsl(0, 72%, 45%)",
  warning: "hsl(38, 92%, 45%)",
  overlay: "rgba(0,0,0,0.5)",
};

export const darkPalette: Palette = {
  background: "hsl(160, 18%, 9%)",
  surface: "hsl(158, 16%, 12%)",
  card: "hsl(156, 15%, 14%)",
  border: "hsl(150, 10%, 26%)",
  text: "hsl(96, 14%, 93%)",
  textMuted: "hsl(140, 9%, 68%)",
  primary: "hsl(142, 62%, 48%)",
  primaryText: "hsl(152, 45%, 7%)",
  success: "hsl(142, 58%, 47%)",
  danger: "hsl(4, 70%, 55%)",
  warning: "hsl(38, 88%, 56%)",
  overlay: "rgba(0,0,0,0.6)",
};

export const radius = { sm: 8, md: 12, lg: 16, pill: 999 } as const;
export const spacing = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 } as const;
