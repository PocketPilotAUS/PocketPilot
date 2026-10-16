import { StyleSheet } from "react-native";
import type { DashboardPalette } from "./DashboardStyles";
import { createLoginStyles } from "./LoginStyles";

export const createRegisterStyles = (palette: DashboardPalette) => {
  const login = createLoginStyles(palette);

  return StyleSheet.create({
    ...login,
    passwordContainer: {
      ...login.passwordContainer,
      marginBottom: 20,
    },
    confirmPasswordInput: {
      ...login.input,
      marginBottom: 0,
    },
    loginRow: login.registerRow,
    loginPrompt: login.registerPrompt,
    loginLink: login.registerLink,
  });
};
