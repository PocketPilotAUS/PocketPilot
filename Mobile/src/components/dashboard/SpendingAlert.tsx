import React, { useEffect, useState } from "react";
import { Pressable } from "react-native";
import { ChevronRight, TriangleAlert } from "lucide-react-native";
import { Text, View } from "../../preferences/LocalizedNative";
import { useDashboardTheme } from "./useDashboardTheme";
import { createHomeSectionsStyles } from "../../styles/HomeSectionsStyles";
import { getSpendingStatus } from "../../services/planningService";
import type { SpendingStatus } from "../../types/plans";
import { statusMessage } from "../../utils/spendingStatus";
import { formatAED } from "../../utils/dashboard";
import { RISK_ORANGE } from "../../styles/PlanningStyles";

// One-line Home warning when a savings goal is at risk (levels 2 and 3 only);
// details live in My Financial Plans.
export default function SpendingAlert({ apiBaseUrl, refreshKey, onOpen }: { apiBaseUrl: string; refreshKey: unknown; onOpen: () => void }) {
  const { palette } = useDashboardTheme();
  const s = createHomeSectionsStyles(palette);
  const [status, setStatus] = useState<SpendingStatus | null>(null);
  useEffect(() => {
    let active = true;
    getSpendingStatus(apiBaseUrl).then(value => { if (active) setStatus(value); }).catch(() => undefined);
    return () => { active = false; };
  }, [apiBaseUrl, refreshKey]);
  const message = statusMessage(status);
  if (!status || !message || status.level < 2) return null;
  const color = status.level === 3 ? palette.danger : RISK_ORANGE;
  // Level 2 from a small buffer: say exactly how much more can be spent
  const detail = status.level === 2 && status.risk_reasons.includes("low_buffer") && status.buffer != null && status.required_contributions > 0
    ? `You can spend about ${formatAED(Math.max(0, status.buffer))} more this month before your savings goal becomes unaffordable.`
    : "Open My Financial Plans for details and an AI plan.";
  return <Pressable onPress={onOpen} accessibilityRole="button" accessibilityHint="Opens My Financial Plans" style={({ pressed }) => [s.alert, status.level === 3 ? s.alertDanger : s.alertWarn, { borderColor: color }, pressed && s.alertPressed]}>
    <TriangleAlert size={17} color={color} />
    <View style={s.alertBody}><Text style={s.alertTitle}>{message.title}</Text><Text style={s.alertText}>{detail}</Text></View>
    <ChevronRight size={18} color={palette.textMuted} />
  </Pressable>;
}
