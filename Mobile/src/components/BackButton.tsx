import React from "react";
import { Pressable } from "react-native";
import { ArrowLeft } from "lucide-react-native";
import { useDashboardTheme } from "./dashboard/useDashboardTheme";
import { localize } from "../preferences/localize";
import { usePreferences } from "../preferences/PreferencesContext";
import { BackButtonColors, createBackButtonStyles } from "../styles/NavigationStyles";

type Props = { onPress: () => void; disabled?: boolean; label?: string; colors?: BackButtonColors };
export default function BackButton({ onPress, disabled = false, label = "Back", colors }: Props) {
  const { palette } = useDashboardTheme();
  const { language } = usePreferences();
  const buttonColors = colors ?? { text: palette.text, surface: palette.cardRaised, border: palette.border };
  const s = createBackButtonStyles(buttonColors);
  return <Pressable onPress={onPress} disabled={disabled} accessibilityRole="button" accessibilityLabel={localize(label, language)} accessibilityState={{ disabled }} style={({ pressed }) => [s.button, disabled && s.disabled, pressed && s.pressed]}>
    <ArrowLeft size={22} color={buttonColors.text} />
  </Pressable>;
}
