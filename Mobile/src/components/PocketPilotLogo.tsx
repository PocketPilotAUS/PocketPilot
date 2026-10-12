
import React from "react";
import { StyleSheet } from "react-native";
import { View, Text } from "../preferences/LocalizedNative";
import { LinearGradient } from "expo-linear-gradient";

import { useAppTheme } from "../theme/ThemeContext";

export default function PocketPilotLogo() {
  const { mode } = useAppTheme();

  return (
    <View style={styles.outer}>
      <LinearGradient
        colors={
          mode === "dark"
            ? ["#F1F3F6", "#A6ADB8", "#565D69"]
            : ["#FFFFFF", "#BCC3CE", "#707987"]
        }
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={styles.metallicSurface}
      >
        <View style={styles.inner}>
          <Text style={styles.letter}>P</Text>
        </View>
      </LinearGradient>
    </View>
  );
}

const styles = StyleSheet.create({
  outer: {
    width: 104,
    height: 104,
    borderRadius: 30,
    overflow: "hidden",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.4)",
    shadowColor: "#000000",
    shadowOffset: { width: 0, height: 12 },
    shadowOpacity: 0.25,
    shadowRadius: 20,
    elevation: 8,
  },

  metallicSurface: {
    flex: 1,
    padding: 3,
  },

  inner: {
    flex: 1,
    borderRadius: 26,
    backgroundColor: "rgba(12,14,19,0.88)",
    justifyContent: "center",
    alignItems: "center",
  },

  letter: {
    color: "#E6E9EF",
    fontSize: 58,
    fontWeight: "800",
    letterSpacing: -3,
  },
});
