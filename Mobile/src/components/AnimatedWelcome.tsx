
import React, { useEffect, useRef } from "react";
import { Animated, Easing, View, Text } from "react-native";

import PocketPilotLogo from "./PocketPilotLogo";
import AmbientBackground from "./AmbientBackground";
import MetallicGlassCard from "./MetallicGlassCard";
import MetallicGlassButton from "./MetallicGlassButton";
import { useAppTheme } from "../theme/ThemeContext";
import { createAppStyles } from "../styles/AppStyles";

type Props = {
  onGetStarted: () => void;
};

export default function AnimatedWelcome({
  onGetStarted,
}: Props) {
  const { colors } = useAppTheme();
  const styles = createAppStyles(colors);

  const logoScale = useRef(new Animated.Value(0.85)).current;
  const logoOpacity = useRef(new Animated.Value(0)).current;
  const contentOpacity = useRef(new Animated.Value(0)).current;
  const contentTranslate = useRef(new Animated.Value(20)).current;

  useEffect(() => {
    Animated.sequence([
      Animated.parallel([
        Animated.timing(logoOpacity, {
          toValue: 1,
          duration: 700,
          useNativeDriver: true,
        }),
        Animated.timing(logoScale, {
          toValue: 1,
          duration: 900,
          easing: Easing.out(Easing.cubic),
          useNativeDriver: true,
        }),
      ]),

      Animated.parallel([
        Animated.timing(contentOpacity, {
          toValue: 1,
          duration: 700,
          useNativeDriver: true,
        }),
        Animated.timing(contentTranslate, {
          toValue: 0,
          duration: 700,
          easing: Easing.out(Easing.cubic),
          useNativeDriver: true,
        }),
      ]),
    ]).start();
  }, []);

  return (
    <>
      <AmbientBackground />

      <View style={styles.welcomeContent}>
        <Animated.View
          style={{
            opacity: logoOpacity,
            transform: [{ scale: logoScale }],
            marginBottom: 30,
          }}
        >
            <PocketPilotLogo />
        </Animated.View>

        <Animated.View
          style={{
            opacity: contentOpacity,
            transform: [{ translateY: contentTranslate }],
            alignItems: "center",
            width: "100%",
          }}
        >
          <Text style={styles.title}>PocketPilot</Text>

          <Text style={styles.subtitle}>
            Your personal finance companion
          </Text>

          <Text style={styles.description}>
            Take control of your spending, build smarter budgets,
            and make confident financial decisions.
          </Text>

          <View style={styles.welcomeButtonContainer}>
            <MetallicGlassButton
              title="Get Started  →"
              onPress={onGetStarted}
            />
          </View>
        </Animated.View>
      </View>
    </>
  );
}
