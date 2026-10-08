import React from "react";
import { View, StyleSheet, ViewStyle, StyleProp } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { BlurView } from "expo-blur";

import { useAppTheme } from "../theme/ThemeContext";

type Props = {
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
  glass?: boolean;
};

export default function MetallicGlassCard({
  children,
  style,
  glass = true,
}: Props) {
  const { mode, colors } = useAppTheme();

  const gradientColors =
    mode === "dark"
      ? (["#33363D", "#1B1D23", "#101115"] as const)
      : (["#FFFFFF", "#E9EBEF", "#DDE1E7"] as const);

  return (
    <View
      style={[
        styles.outer,
        {
          borderColor: colors.glassBorder,
          shadowColor: mode === "dark" ? "#000000" : "#8B929E",
        },
        style,
      ]}
    >
      <LinearGradient
        colors={gradientColors}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={StyleSheet.absoluteFill}
      />

      {glass && (
        <BlurView
          intensity={mode === "dark" ? 15 : 10}
          tint={mode}
          style={StyleSheet.absoluteFill}
          pointerEvents="none"
        />
      )}

      <View
        pointerEvents="none"
        style={[
          styles.highlight,
          {
            borderTopColor:
              mode === "dark"
                ? "rgba(255,255,255,0.22)"
                : "rgba(255,255,255,0.95)",
          },
        ]}
      />

      <View style={styles.content}>{children}</View>
    </View>
  );
}

const styles = StyleSheet.create({
  outer: {
    borderRadius: 22,
    borderWidth: 1,
    overflow: "hidden",
    marginBottom: 18,
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.18,
    shadowRadius: 20,
    elevation: 5,
  },

  highlight: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    borderTopWidth: 1,
    borderRadius: 22,
  },

  content: {
    padding: 22,
  },
});
