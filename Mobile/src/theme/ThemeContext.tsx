
import React, {
  createContext,
  useContext,
  useMemo,
  useState,
} from "react";

import {
  darkColors,
  lightColors,
  AppColors,
  ThemeMode,
} from "./colors";

type ThemeContextType = {
  mode: ThemeMode;
  colors: AppColors;
  toggleTheme: () => void;
  setTheme: (mode: ThemeMode) => void;
};

const ThemeContext = createContext<ThemeContextType | undefined>(
  undefined
);

export function ThemeProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [mode, setMode] = useState<ThemeMode>("dark");

  const toggleTheme = () => {
    setMode((current) => (current === "dark" ? "light" : "dark"));
  };

  const value = useMemo(
    () => ({
      mode,
      colors: mode === "dark" ? darkColors : lightColors,
      toggleTheme,
      setTheme: setMode,
    }),
    [mode]
  );

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useAppTheme() {
  const context = useContext(ThemeContext);

  if (!context) {
    throw new Error(
      "useAppTheme must be used inside ThemeProvider"
    );
  }

  return context;
}
