export const darkColors = {
  background: "#08090D",
  surface: "#17181E",
  surfaceElevated: "#22242B",

  primary: "#C8CDD5",
  primaryText: "#08090D",

  text: "#F5F5F7",
  textSecondary: "#A1A5AE",
  textMuted: "#717681",

  border: "#34363E",
  glassBorder: "rgba(255,255,255,0.15)",
  glassSurface: "rgba(255,255,255,0.07)",

  success: "#65C7A0",
  error: "#F08080",
  warning: "#E5BE78",

  overlay: "rgba(0,0,0,0.65)",
};

export const lightColors: typeof darkColors = {
  background: "#F5F6F8",
  surface: "#FFFFFF",
  surfaceElevated: "#E9EBEF",

  primary: "#505762",
  primaryText: "#FFFFFF",

  text: "#14161B",
  textSecondary: "#5D626C",
  textMuted: "#7B808A",

  border: "#DADDE3",
  glassBorder: "rgba(255,255,255,0.75)",
  glassSurface: "rgba(255,255,255,0.55)",

  success: "#218765",
  error: "#C44747",
  warning: "#A57520",

  overlay: "rgba(0,0,0,0.35)",
};

export type AppColors = typeof darkColors;
export type ThemeMode = "dark" | "light";