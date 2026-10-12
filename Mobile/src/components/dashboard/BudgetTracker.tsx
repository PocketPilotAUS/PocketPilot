import React, { useState } from "react";
import { Pressable } from "react-native";
import { Text, View } from "../../preferences/LocalizedNative";
import { Pencil, Sparkles, TriangleAlert } from "lucide-react-native";
import { useDashboardTheme } from "./useDashboardTheme";
import BudgetSetupForm from "./BudgetSetupForm";
import { DashboardData, buildBudgetRows, formatAED } from "../../utils/dashboard";

type Props = { data: DashboardData | null; apiBaseUrl: string; onSaved: (data: DashboardData) => void; onReview: () => void; aiBusy: boolean };
export default function BudgetTracker({ data, apiBaseUrl, onSaved, onReview, aiBusy }: Props) {
  const { styles: s, palette } = useDashboardTheme();
  const [editing, setEditing] = useState(false);
  if (!data) return null;
  if (editing) return <BudgetSetupForm data={data} apiBaseUrl={apiBaseUrl} onSaved={saved => { onSaved(saved); setEditing(false); }} onCancel={() => setEditing(false)} />;
  const budget = data.ideal_budget;
  if (!budget) return <View style={s.card}>
    <Text style={s.cardLabel}>Create your budget</Text>
    <Text style={s.cardSubtitle}>Set your own category amounts before tracking your spending. You can review the saved budget with AI afterwards.</Text>
    <Pressable style={[s.primaryButton, s.budgetSetupAction]} onPress={() => setEditing(true)} accessibilityRole="button"><Text style={s.primaryButtonText}>Set up my budget</Text></Pressable>
  </View>;
  const rows = buildBudgetRows(budget.allocations, budget.mode === "amounts");
  const overCount = rows.filter(row => row.over).length;
  const planned = budget.allocations.reduce((sum, row) => sum + (row.target ?? 0), 0);
  const left = data.income == null ? null : data.income - planned;
  return <View style={s.card}>
    <View style={s.cardHeader}>
      <View style={s.cardTitleBlock}><Text style={s.cardLabel}>Budget tracker</Text><Text style={[s.cardSubtitle, overCount > 0 && s.statusDanger]}>{overCount > 0 ? `${overCount} categories over budget` : "Your saved monthly budget"}</Text></View>
      <Pressable style={s.pill} onPress={() => setEditing(true)} accessibilityRole="button" accessibilityLabel="Edit my budget"><Pencil size={13} color={palette.accent} /><Text style={s.pillText}>Edit budget</Text></Pressable>
    </View>
    <View style={s.budgetList}>{rows.map(row => {
      const ratio = row.ratio ?? 0;
      const percent = Math.min(100, Number.isFinite(ratio) ? ratio * 100 : 100);
      return <View key={row.category}>
        <View style={s.budgetHeaderRow}><Text style={s.budgetName}>{row.category}</Text><Text style={s.budgetFigures}><Text style={[s.budgetFiguresStrong, row.over && s.statusDanger]}>{formatAED(row.spent)}</Text>{row.target != null ? ` / ${formatAED(row.target)}` : ""}</Text></View>
        {row.target != null && <View style={s.budgetTrack} accessibilityRole="progressbar" accessibilityLabel={`${row.category} budget used`} accessibilityValue={{ min: 0, max: 100, now: Math.round(percent), text: `${formatAED(row.spent)} / ${formatAED(row.target)}` }}>
          <View style={[s.budgetFill, row.over ? s.budgetFillDanger : ratio >= .8 ? s.budgetFillWarning : null, { width: `${percent}%` }]} />
        </View>}
        {row.over && <View style={s.overBadge}><TriangleAlert size={12} color={palette.danger} /><Text style={s.overBadgeText}>Over by {formatAED(row.overBy)}</Text></View>}
      </View>;
    })}</View>
    <View style={s.budgetFooter}>
      <Text style={s.mutedText}>Planned monthly spending: {formatAED(planned)}</Text>
      {left !== null && <Text style={left < 0 ? s.statusDanger : s.mutedText}>{left < 0 ? "Budget exceeds income by" : "Income left after your budget"}: {formatAED(Math.abs(left))}</Text>}
      {!!budget.unbudgeted?.length && <>
        <Text style={s.statusDanger}>Spending without a budget category</Text>
        {budget.unbudgeted.map(row => <Text key={row.category} style={s.mutedText}>{row.category}: {formatAED(row.spent)}</Text>)}
        <Text style={s.mutedText}>Edit your budget to add these categories. This spending still counts in your total.</Text>
      </>}
    </View>
    <Pressable disabled={aiBusy} onPress={onReview} style={[s.budgetReviewButton, aiBusy && s.buttonDisabled]} accessibilityRole="button"><Sparkles color={palette.accent} size={17} /><Text style={s.pillText}>{aiBusy ? "PocketPilot is replying" : "Review my budget with AI"}</Text></Pressable>
  </View>;
}
