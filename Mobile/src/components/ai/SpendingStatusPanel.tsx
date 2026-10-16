import React, { useEffect, useRef, useState } from "react";
import { ActivityIndicator, Pressable } from "react-native";
import { AlertCircle, Sparkles, TriangleAlert } from "lucide-react-native";
import { Alert, Text, TextInput, View } from "../../preferences/LocalizedNative";
import { useAITheme } from "./useAITheme";
import { createPlanningStyles, RISK_ORANGE } from "../../styles/PlanningStyles";
import type { AdjustmentProposal, PlanSuggestion, SpendingStatus } from "../../types/plans";
import { acceptAdjustment, proposeAdjustment } from "../../services/planningService";
import { SessionExpiredError } from "../../services/apiClient";
import { statusMessage } from "../../utils/spendingStatus";
import { formatAED } from "../../utils/dashboard";
import { formatPlanningDate } from "../../utils/planningDate";
import { newRequestKey } from "../../utils/addExpense";

type Props = {
  status: SpendingStatus | null;
  apiBaseUrl?: string;
  // compact: a short status with a link to the full panel (Overview)
  compact?: boolean;
  onOpen?: () => void;
  autoStart?: boolean;
  onStatusChange?: (status: SpendingStatus) => void;
  // Opens the existing plan editor, prefilled with a suggested contribution or deadline; applied only there
  onEditPlan?: (suggestion?: PlanSuggestion) => void;
  // The savings plan being viewed, for its recovery options
  planId?: string;
};

// This month's spending status for a plan, with an optional AI adjustment
// that is only applied after the user accepts it.
export default function SpendingStatusPanel({ status, apiBaseUrl, compact, onOpen, autoStart, onStatusChange, onEditPlan, planId }: Props) {
  const { palette } = useAITheme();
  const s = createPlanningStyles(palette);
  const [proposal, setProposal] = useState<AdjustmentProposal | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [revising, setRevising] = useState(false);
  const [instructions, setInstructions] = useState("");
  const requestKey = useRef("");
  const started = useRef(false);
  const message = statusMessage(status);

  const request = async (text?: string) => {
    if (!apiBaseUrl || loading) return;
    setLoading(true); setError("");
    try {
      const draft = await proposeAdjustment(apiBaseUrl, text, planId);
      requestKey.current = newRequestKey(); setProposal(draft); setRevising(false); setInstructions("");
    } catch (e) { if (!(e instanceof SessionExpiredError)) setError((e as Error).message); }
    finally { setLoading(false); }
  };
  // Opened from Overview's AI action: start the request once
  const hasMessage = !!message;
  useEffect(() => {
    if (autoStart && hasMessage && !compact && !started.current) { started.current = true; void request(); }
  }, [autoStart, hasMessage, compact]);

  const accept = () => {
    if (!proposal || !apiBaseUrl || loading) return;
    Alert.alert("Set these spending limits?", "PocketPilot will track your spending against these limits for the rest of the month. A category budget is only lowered where the limit is below it; budgets are never raised, and recorded transactions stay unchanged.", [
      { text: "Cancel", style: "cancel" },
      { text: "Set limits", onPress: async () => {
        setLoading(true); setError("");
        try { const next = await acceptAdjustment(apiBaseUrl, proposal, requestKey.current); setProposal(null); onStatusChange?.(next); Alert.alert("Limits set", "Your projection now assumes you keep to these limits. Your savings and transactions are unchanged."); }
        catch (e) { if (!(e instanceof SessionExpiredError)) setError((e as Error).message); }
        finally { setLoading(false); }
      } },
    ]);
  };

  // Level 2 from a small buffer (not from the projection)
  const lowBuffer = !!proposal?.risk_reasons?.includes("low_buffer") && !proposal?.risk_reasons?.includes("projection");
  const shortfall = (label: string, value: number | undefined, positive = false) => value == null ? null
    : <View style={s.proposalLine}><Text style={[s.caption, s.proposalLabel]}>{label}</Text><Text style={[s.text, positive ? s.accentText : value > 0.005 ? s.dangerText : null]}>{formatAED(value)}</Text></View>;
  // Verified figures: income - expected spending = left; left - savings goals = left after savings
  const breakdown = (draft: AdjustmentProposal) => {
    const figures = draft.affordability;
    if (figures.left_after_spending == null) return null;
    const line = (label: string, value: number) => <View style={s.proposalLine}><Text style={s.caption}>{label}</Text><Text style={s.text}>{formatAED(value)}</Text></View>;
    return <View style={s.proposalRow}>
      {figures.income != null && line("Monthly income", figures.income)}
      {line("Expected spending", figures.expected_spending ?? 0)}
      {line("Left after spending", figures.left_after_spending)}
      {(figures.required_contributions ?? 0) > 0 && line("Savings goals", figures.required_contributions ?? 0)}
      {(figures.required_contributions ?? 0) > 0 && line("Left after savings", figures.left_after_savings ?? 0)}
    </View>;
  };
  if (!message) return null;
  const level = status!.level;
  const Icon = level === 1 ? AlertCircle : TriangleAlert;
  const tone = level === 3 ? palette.danger : level === 2 ? RISK_ORANGE : palette.textSecondary;
  const box = [s.statusBox, level === 2 && s.statusWarn, level === 3 && s.statusDanger];
  const strong = level >= 2;
  const action = (label: string, onPress: () => void) => <Pressable disabled={loading} onPress={onPress} accessibilityRole="button" style={[s.statusAction, strong && s.statusActionStrong, loading && s.muted]}>
    <Sparkles size={14} color={strong ? palette.onAccent : palette.accent} /><Text style={[s.statusActionText, strong && s.statusActionTextStrong]}>{label}</Text>
  </Pressable>;

  return <View style={box}>
    <View style={s.statusHeading}><Icon size={17} color={tone} /><Text style={s.statusTitle}>{message.title}</Text></View>
    {message.lines.map(line => <Text key={line} style={s.text}>{line}</Text>)}
    {compact ? (onOpen && action(message.action, onOpen)) : <>
      {!proposal && !loading && action(message.action, () => { void request(); })}
      {loading && <View style={s.statusHeading}><ActivityIndicator color={palette.accent} /><Text style={s.caption}>PocketPilot is preparing suggestions…</Text></View>}
      {!!error && <Text style={s.error} accessibilityRole="alert">{error}</Text>}
      {proposal && !loading && proposal.mode === "advice" && <View>
        <Text style={s.label}>How this month looks</Text>
        {breakdown(proposal)}
        <Text style={[s.text, s.accentText]}>Your savings goal is still affordable. No budget or savings changes are needed.</Text>
        {proposal.tips.map(tip => <Text key={tip} localize={false} style={s.text}>• {tip}</Text>)}
        <View style={s.proposalButtons}><Pressable onPress={() => setProposal(null)} style={[s.proposalButton, s.secondary]} accessibilityRole="button"><Text style={s.secondaryText}>Close</Text></Pressable></View>
      </View>}
      {proposal && !loading && proposal.mode !== "advice" && <View>
        <Text style={s.label}>Suggested spending limits for the next {proposal.days_left} days</Text>
        {proposal.changes.length === 0
          ? <Text style={s.text}>No realistic spending reductions were found in your remaining spending.</Text>
          : proposal.changes.map(change => <View key={change.category} style={s.proposalRow}>
              <View style={s.proposalLine}><Text style={s.label}>{change.category}</Text><Text style={s.text}>Limit <Text style={s.accentText}>{formatAED(change.limit)}</Text></Text></View>
              <Text style={s.caption}>{`Budget ${formatAED(change.budget)} · Spent ${formatAED(change.spent)} · Projected ${formatAED(change.forecast)}`}</Text>
              <Text style={s.text}>{`${formatAED(change.remaining_allowance)} left to spend in ${proposal.days_left} days; could avoid about ${formatAED(change.avoided)} of future spending.`}</Text>
              {!!change.reason && <Text localize={false} style={s.caption}>{change.reason}</Text>}
            </View>)}
        <View style={s.proposalRow}>
          {lowBuffer ? <>
            {/* Small buffer: what the budget still needs vs what can be spent before savings are affected */}
            {shortfall("Your budget still needs this month", proposal.still_needed ?? undefined)}
            {shortfall("You can spend before savings are affected", Math.max(0, proposal.buffer ?? 0), true)}
            {shortfall("Spending gap", proposal.spending_gap ?? undefined)}
          </> : <>
            {proposal.mode === "recovery" && shortfall("Shortfall from recorded spending and bills", proposal.current_shortfall)}
            {shortfall(proposal.forecast_reliable ? "Shortfall from projected spending" : "Shortfall from projected spending (uncertain)", proposal.forecast_shortfall)}
          </>}
          {proposal.changes.length > 0 && shortfall("Possible reduction from these limits", proposal.potential_reduction, true)}
          {shortfall(lowBuffer ? "Gap remaining after these limits" : "Shortfall remaining after these limits", proposal.remaining_shortfall)}
        </View>
        {lowBuffer && proposal.buffer != null && <Text style={s.text}>{`To protect your savings goal, keep all remaining spending this month under ${formatAED(Math.max(0, proposal.buffer))}: about ${formatAED(proposal.daily_allowance ?? 0)} a day for the next ${proposal.days_left} days.`}</Text>}
        <Text style={[s.text, proposal.covers ? s.accentText : s.dangerText]}>{proposal.covers
          ? lowBuffer ? "If you keep to these limits, the rest of the month fits within what you can spend." : "If you keep to these limits, projected spending leaves enough for your savings goal."
          : proposal.changes.length ? "These limits alone don't leave enough for your savings goal this month." : "Spending reductions alone can't close this gap."}</Text>
        {!proposal.covers && proposal.max_this_month != null && proposal.required_contributions > 0 && <Text style={s.text}>{`At projected spending, about ${formatAED(proposal.max_this_month)} can go to savings this month.`}</Text>}
        {proposal.options.map(option => <View key={option.kind} style={s.proposalRow}>
          <Text style={s.label}>{option.kind === "catch_up" ? "Keep your deadline" : "Extend your deadline"}</Text>
          <Text style={s.text}>{option.kind === "catch_up"
            ? `If you save ${formatAED(option.this_month)} this month, you'd need ${formatAED(option.monthly)} a month for the remaining ${option.months} months to finish by ${formatPlanningDate(option.deadline)}. You can update the plan's monthly amount in Adjust My Plan next month.`
            : `Move the deadline to ${formatPlanningDate(option.deadline)}: your plan would need ${formatAED(option.plan_monthly ?? option.monthly)} a month over ${option.months} months, or ${formatAED(option.monthly)} a month from next month if you save ${formatAED(option.this_month)} this month.`}</Text>
          {option.kind === "extend" && onEditPlan && <Pressable onPress={() => onEditPlan({ deadline: option.deadline })} accessibilityRole="button" style={s.statusAction}><Text style={s.statusActionText}>Adjust My Plan</Text></Pressable>}
        </View>)}
        {proposal.options.length > 0 && <Text style={s.caption}>Nothing changes until you review and save it in Adjust My Plan.</Text>}
        <Text style={s.caption}>{proposal.assumption}</Text>
        {proposal.tips.map(tip => <Text key={tip} localize={false} style={s.caption}>• {tip}</Text>)}
        {proposal.notes.map(note => <Text key={note} localize={false} style={s.caption}>{note}</Text>)}
        {revising && <View style={s.dateField}>
          <TextInput value={instructions} onChangeText={setInstructions} maxLength={500} placeholder="For example: Don't reduce Transport. Reduce Shopping instead." placeholderTextColor={palette.textMuted} style={s.input} accessibilityLabel="What should change?" />
        </View>}
        <View style={s.proposalButtons}>
          {revising
            ? <>
                <Pressable onPress={() => setRevising(false)} style={[s.proposalButton, s.secondary]} accessibilityRole="button"><Text style={s.secondaryText}>Cancel</Text></Pressable>
                <Pressable disabled={!instructions.trim()} onPress={() => { void request(instructions.trim()); }} style={[s.proposalButton, s.button, !instructions.trim() && s.muted]} accessibilityRole="button"><Text style={s.buttonText}>Get revised plan</Text></Pressable>
              </>
            : <>
                <Pressable onPress={() => setProposal(null)} style={[s.proposalButton, s.secondary]} accessibilityRole="button"><Text style={s.secondaryText}>Dismiss</Text></Pressable>
                <Pressable onPress={() => setRevising(true)} style={[s.proposalButton, s.secondary]} accessibilityRole="button"><Text style={s.secondaryText}>Change suggestions</Text></Pressable>
                {proposal.changes.length > 0 && <Pressable onPress={accept} style={[s.proposalButton, s.button]} accessibilityRole="button"><Text style={s.buttonText}>Accept limits</Text></Pressable>}
              </>}
        </View>
      </View>}
    </>}
  </View>;
}
