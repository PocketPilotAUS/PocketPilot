
import React from "react";
import { Pressable, StyleSheet, StyleProp, ViewStyle } from "react-native";
import { Text } from "../preferences/LocalizedNative";
import { LinearGradient } from "expo-linear-gradient";

import { useAppTheme } from "../theme/ThemeContext";

type Props = {
  title: string;
  onPress: () => void;
  variant?: "primary" | "secondary" | "danger";
  style?: StyleProp<ViewStyle>;
  disabled?: boolean;
};

export default function MetallicGlassButton({
  title,
  onPress,
  variant = "primary",
  style,
  disabled = false,
}: Props) {
  const { mode, colors } = useAppTheme();

  const gradientColors =
    variant === "danger"
      ? (["#A34F55", "#652C32"] as const)
      : mode === "dark"
        ? variant === "primary"
          ? (["#DCE0E7", "#A5ACB7", "#727B89"] as const)
          : (["#373B44", "#1B1D24", "#15171D"] as const)
        : variant === "primary"
          ? (["#737B88", "#454D59", "#303640"] as const)
          : (["#FFFFFF", "#ECEFF3", "#DDE1E7"] as const);

  const textColor =
    variant === "primary" || variant === "danger"
      ? variant === "danger"
        ? "#FFFFFF"
        : colors.primaryText
      : colors.text;

  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      style={({ pressed }) => [
        styles.container,
        {
          borderColor: colors.glassBorder,
          opacity: disabled ? 0.5 : pressed ? 0.8 : 1,
        },
        style,
      ]}
    >
      <LinearGradient
        colors={gradientColors}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={styles.gradient}
      >
        <Text style={[styles.text, { color: textColor }]}>
          {title}
        </Text>
      </LinearGradient>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  container: {
    borderRadius: 16,
    borderWidth: 1,
    overflow: "hidden",
    marginBottom: 12,
  },

  gradient: {
    minHeight: 54,
    paddingHorizontal: 20,
    paddingVertical: 15,
    alignItems: "center",
    justifyContent: "center",
  },

  text: {
    fontSize: 15,
    fontWeight: "600",
    letterSpacing: 0.3,
  },
});
