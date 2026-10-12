
import React, {
  createContext,
  useContext,
  useMemo,
  useState,
  useEffect,
  useRef,
} from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";

import {
  darkColors,
  lightColors,
  AppColors,
  ThemeMode,
} from "./colors";

type ThemeContextType = {
  mode: ThemeMode;
  colors: AppColors;
  setTheme: (mode: ThemeMode) => Promise<void>;
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
  const userChanged = useRef(false);
  useEffect(() => {
    let active = true;
    AsyncStorage.getItem("@pocketpilot_theme").then(saved => {
      if (active && !userChanged.current && (saved === "dark" || saved === "light")) setMode(saved);
    }).catch(() => {});
    return () => { active = false; };
  }, []);
  const setTheme = async (next: ThemeMode) => {
    userChanged.current = true;
    await AsyncStorage.setItem("@pocketpilot_theme", next);
    setMode(next);
  };

  const value = useMemo(
    () => ({
      mode,
      colors: mode === "dark" ? darkColors : lightColors,
      setTheme,
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
