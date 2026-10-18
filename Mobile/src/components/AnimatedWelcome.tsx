
import React, { useEffect, useRef } from "react";
import { Animated, Easing, Image, Pressable, ScrollView, useWindowDimensions } from "react-native";
import { View, Text } from "../preferences/LocalizedNative";

import { useDashboardTheme } from "./dashboard/useDashboardTheme";
import { createWelcomeStyles } from "../styles/WelcomeStyles";

type Props = {
  onGetStarted: () => void;
};

export default function AnimatedWelcome({
  onGetStarted,
}: Props) {
  const { palette, styles: dashboardStyles } = useDashboardTheme();
  const { width, height } = useWindowDimensions();
  const logoSize = Math.max(1, Math.min(220, width - 36, height * 0.32) * 0.8);
  const styles = createWelcomeStyles(palette, logoSize);

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
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      <Animated.View
        style={{
          opacity: logoOpacity,
          transform: [{ scale: logoScale }],
          ...styles.logo,
        }}
      >
        <Image
          source={require("../../assets/pocketpilot-logo.png")}
          style={styles.logoImage}
          resizeMode="contain"
          accessibilityLabel="PocketPilot logo"
        />
      </Animated.View>

      <Animated.View
        style={{
          opacity: contentOpacity,
          transform: [{ translateY: contentTranslate }],
          ...styles.body,
        }}
      >
        <Text style={styles.title}>PocketPilot</Text>

        <Text style={styles.subtitle}>
          Your personal finance companion
        </Text>

        <View style={styles.welcomeButtonContainer}>
          <Pressable
            onPress={onGetStarted}
            accessibilityRole="button"
            style={({ pressed }) => [
              dashboardStyles.primaryButton,
              styles.button,
              pressed && styles.pressed,
            ]}
          >
            <Text style={dashboardStyles.primaryButtonText}>Get Started →</Text>
          </Pressable>
        </View>
      </Animated.View>
    </ScrollView>
  );
}
