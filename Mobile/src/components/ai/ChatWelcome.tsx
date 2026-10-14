import React from "react";
import { Pressable } from "react-native";
import { Text, View } from "../../preferences/LocalizedNative";
import { LinearGradient } from "expo-linear-gradient";
import { CreditCard, PiggyBank, Scissors, ShieldCheck, Sparkles, Target } from "lucide-react-native";

import { useAITheme } from "./useAITheme";

export const SUGGESTIONS = [
  {
    title: "Pay off debt",
    description: "Plan repayments and see what to tackle first",
    prompt: "Help me make a plan to pay off my debt faster.",
    Icon: CreditCard,
  },
  {
    title: "Save monthly",
    description: "Find a realistic amount to save each month",
    prompt: "Based on my spending, how much could I realistically save each month?",
    Icon: PiggyBank,
  },
  {
    title: "Save for a goal",
    description: "Reach a target amount by a deadline",
    prompt: "Help me plan how to save for a goal by a specific date.",
    Icon: Target,
  },
  {
    title: "Spend less",
    description: "Spot categories where I could cut back",
    prompt: "Where could I cut my spending this month?",
    Icon: Scissors,
  },
] as const;

type Props = {
  disabled: boolean;
  onSuggestion: (prompt: string) => void;
};

export default function ChatWelcome({ disabled, onSuggestion }: Props) {
  const { ai, palette, mode } = useAITheme();

  return (
    <View>
      <View style={ai.welcome}>
        <LinearGradient
          colors={mode === "dark" ? ["#5FF0CE", "#1FA88A"] : ["#2CC9A6", "#0B8A71"]}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={ai.orb}
        >
          <Sparkles size={28} color={palette.onAccent} strokeWidth={2.2} />
        </LinearGradient>

        <Text style={ai.welcomeTitle}>How can I help with your money?</Text>
        <Text style={ai.welcomeText}>
          Ask about budgeting, saving or debt. Goal planning uses your saved income and planned
          monthly budget. Recorded spending is separate.
        </Text>
      </View>

      <View style={ai.suggestionGrid}>
        {SUGGESTIONS.map(({ title, description, prompt, Icon }) => (
          <Pressable
            key={title}
            onPress={() => onSuggestion(prompt)}
            disabled={disabled}
            style={({ pressed }) => [ai.suggestion, (pressed || disabled) && ai.pressed]}
            accessibilityRole="button"
            accessibilityLabel={`${title}. Asks: ${prompt}`}
          >
            <View style={ai.suggestionIcon}>
              <Icon size={18} color={palette.accent} strokeWidth={2.2} />
            </View>
            <Text style={ai.suggestionTitle}>{title}</Text>
            <Text style={ai.suggestionText}>{description}</Text>
          </Pressable>
        ))}
      </View>

      <View style={ai.disclaimer}>
        <ShieldCheck size={15} color={palette.textMuted} strokeWidth={2} />
        <Text style={ai.disclaimerText}>
          AI answers can be wrong, so check important figures. Nothing is saved to your account
          unless you confirm it.
        </Text>
      </View>
    </View>
  );
}
