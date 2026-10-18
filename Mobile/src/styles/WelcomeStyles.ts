import { StyleSheet } from "react-native";
import type { DashboardPalette } from "./DashboardStyles";
import { createLoginStyles } from "./LoginStyles";

export const createWelcomeStyles = (palette: DashboardPalette, logoSize = 176) => {
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
      width: logoSize,
      height: logoSize,
      flexShrink: 0,
      overflow: "visible",
      marginBottom: 20,
    },
    logoImage: {
      // Override both intrinsic asset dimensions; aspectRatio alone retains its height.
      width: logoSize,
      height: logoSize,
      aspectRatio: 1,
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
      marginBottom: 28,
    },
    welcomeButtonContainer: {
      width: "70%",
      alignSelf: "center",
    },
    button: {
      ...login.submitButton,
      flex: 0,
      minHeight: 48,
      paddingVertical: 12,
    },
    pressed: login.pressed,
  });
};
