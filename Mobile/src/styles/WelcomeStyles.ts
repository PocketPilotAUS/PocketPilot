import { StyleSheet } from "react-native";
import type { DashboardPalette } from "./DashboardStyles";
import { createLoginStyles } from "./LoginStyles";

export const createWelcomeStyles = (palette: DashboardPalette) => {
  const login = createLoginStyles(palette);

  return StyleSheet.create({
    screen: login.container,
    content: {
      flexGrow: 1,
      justifyContent: "center",
      alignItems: "center",
      paddingHorizontal: 18,
      paddingVertical: 32,
    },
    logo: {
      marginBottom: 24,
    },
    body: {
      alignItems: "center",
      width: "100%",
      maxWidth: 420,
    },
    title: {
      ...login.title,
      textAlign: "center",
    },
    subtitle: {
      color: palette.accent,
      fontSize: 15,
      fontWeight: "600",
      lineHeight: 22,
      textAlign: "center",
      marginBottom: 16,
    },
    description: {
      ...login.subtitle,
      textAlign: "center",
      marginBottom: 32,
    },
    welcomeButtonContainer: {
      width: "100%",
    },
    button: login.submitButton,
    pressed: login.pressed,
  });
};
