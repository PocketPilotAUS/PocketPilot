import React from "react";
import { Pressable, Text, View } from "react-native";
import { ChevronLeft, ChevronRight } from "lucide-react-native";

import { useInsightsTheme } from "./useInsightsTheme";
import { monthName } from "../../utils/dashboard";

type Props = {
  month: Date;
  canGoBack: boolean;
  canGoForward: boolean;
  onChange: (offset: number) => void;
};

export default function MonthSelector({ month, canGoBack, canGoForward, onChange }: Props) {
  const { ins, palette } = useInsightsTheme();

  const previous = new Date(month.getFullYear(), month.getMonth() - 1, 1);

  return (
    <View style={ins.monthSelector}>
      <Pressable
        onPress={() => onChange(-1)}
        disabled={!canGoBack}
        style={[ins.monthButton, !canGoBack && ins.monthButtonDisabled]}
        accessibilityRole="button"
        accessibilityLabel="Previous month"
        hitSlop={6}
      >
        <ChevronLeft size={20} color={palette.text} strokeWidth={2.2} />
      </Pressable>

      <View style={ins.monthCenter} accessibilityLiveRegion="polite">
        <Text style={ins.monthTitle}>
          {monthName(month.getMonth() + 1)} {month.getFullYear()}
        </Text>
        <Text style={ins.monthCaption}>Compared with {monthName(previous.getMonth() + 1)}</Text>
      </View>

      <Pressable
        onPress={() => onChange(1)}
        disabled={!canGoForward}
        style={[ins.monthButton, !canGoForward && ins.monthButtonDisabled]}
        accessibilityRole="button"
        accessibilityLabel="Next month"
        accessibilityState={{ disabled: !canGoForward }}
        hitSlop={6}
      >
        <ChevronRight size={20} color={palette.text} strokeWidth={2.2} />
      </Pressable>
    </View>
  );
}
