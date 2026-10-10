import React, { useEffect, useState } from "react";
import { Animated, View } from "react-native";

import { useAITheme } from "./useAITheme";

// Three pulsing dots shown while the AI is replying
export default function TypingIndicator() {
  const { ai } = useAITheme();
  // Created once and kept for the component's lifetime
  const [dots] = useState(() => [0, 1, 2].map(() => new Animated.Value(0.3)));

  useEffect(() => {
    const animations = dots.map((dot, index) =>
      Animated.loop(
        Animated.sequence([
          Animated.delay(index * 160),
          Animated.timing(dot, { toValue: 1, duration: 360, useNativeDriver: true }),
          Animated.timing(dot, { toValue: 0.3, duration: 360, useNativeDriver: true }),
          Animated.delay((2 - index) * 160),
        ])
      )
    );

    animations.forEach((animation) => animation.start());

    return () => animations.forEach((animation) => animation.stop());
  }, [dots]);

  return (
    <View style={ai.typing} accessibilityLabel="PocketPilot is replying">
      {dots.map((dot, index) => (
        <Animated.View key={index} style={[ai.dot, { opacity: dot }]} />
      ))}
    </View>
  );
}
