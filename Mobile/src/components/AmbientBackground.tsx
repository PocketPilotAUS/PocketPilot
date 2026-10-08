
import React from "react";
import { View, StyleSheet } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import Svg, { Defs, RadialGradient, Stop, Rect } from "react-native-svg";

import { useAppTheme } from "../theme/ThemeContext";

export default function AmbientBackground() {
  const { mode } = useAppTheme();

  return (
    <View pointerEvents="none" style={styles.container}>
      <LinearGradient
        colors={
          mode === "dark"
            ? ["#191C23", "#101116", "#08090D"]
            : ["#E9ECF2", "#F1F3F6", "#F5F6F8"]
        }
        locations={[0, 0.4, 1]}
        start={{ x: 1, y: 0 }}
        end={{ x: 0.2, y: 1 }}
        style={StyleSheet.absoluteFill}
      />

      <Svg
        width={420}
        height={420}
        style={styles.glow}
      >
        <Defs>
          <RadialGradient id="silverGlow" cx="50%" cy="50%" rx="50%" ry="50%">
            <Stop
              offset="0%"
              stopColor={mode === "dark" ? "#AEB8CA" : "#FFFFFF"}
              stopOpacity={mode === "dark" ? 0.24 : 0.85}
            />
            <Stop
              offset="45%"
              stopColor={mode === "dark" ? "#8D98AD" : "#FFFFFF"}
              stopOpacity={mode === "dark" ? 0.10 : 0.35}
            />
            <Stop
              offset="100%"
              stopColor={mode === "dark" ? "#8D98AD" : "#FFFFFF"}
              stopOpacity={0}
            />
          </RadialGradient>
        </Defs>

        <Rect width="420" height="420" fill="url(#silverGlow)" />
      </Svg>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    overflow: "hidden",
  },

  glow: {
    position: "absolute",
    top: -140,
    right: -140,
  },
});
