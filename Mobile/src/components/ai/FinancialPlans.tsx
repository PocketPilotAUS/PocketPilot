import React, { useEffect, useRef, useState } from "react";
import { ActivityIndicator, FlatList, Pressable, ScrollView } from "react-native";
import { ChevronRight, Target } from "lucide-react-native";
import { Alert, Text, View } from "../../preferences/LocalizedNative";
import { useAITheme } from "./useAITheme";
import { createPlanningStyles } from "../../styles/PlanningStyles";
import { navigationStyles } from "../../styles/NavigationStyles";
import BackButton from "../BackButton";
import FinancialPlanCard from "./FinancialPlanCard";
import PlanningForm from "./PlanningForm";
import BudgetPlanEditor from "./BudgetPlanEditor";
import { FinancialPlan, PlanningContext, PlanningProfile, PlanSuggestion, SpendingStatus } from "../../types/plans";
import { getPlanningContext, getPlans, getSpendingStatus, planningRequest, savePlan, confirmBudgetPlan } from "../../services/planningService";
import { SessionExpiredError } from "../../services/apiClient";

type Props = { apiBaseUrl: string; onPreview: (plan: FinancialPlan) => void; onStartPlanning: () => void; initialProfile?: PlanningProfile; focusPlanId?: string };
export default function FinancialPlans({ apiBaseUrl, onPreview, onStartPlanning, initialProfile, focusPlanId }: Props) {
  const { palette, styles } = useAITheme();
  const s = createPlanningStyles(palette);
  const [plans, setPlans] = useState<FinancialPlan[]>([]);
  const [context, setContext] = useState<PlanningContext | null>(null);
  const [selected, setSelected] = useState<FinancialPlan | null>(null);
  const [editing, setEditing] = useState<{ profile?: PlanningProfile; id?: string; suggestion?: PlanSuggestion } | null>(initialProfile ? { profile: initialProfile } : null);
  const [preview, setPreview] = useState<FinancialPlan | null>(null);
  const [busy, setBusy] = useState(false);
  const [formBusy, setFormBusy] = useState(false);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  const focused = useRef(false);
  // This month's verified spending status; optional, so plans still load without it
  const [status, setStatus] = useState<SpendingStatus | null>(null);
  useEffect(() => {
    let cancelled = false;
    getSpendingStatus(apiBaseUrl).then(value => { if (!cancelled) setStatus(value); }).catch(() => undefined);
    return () => { cancelled = true; };
  }, [apiBaseUrl, revision]);
  useEffect(() => {
    let cancelled = false; setBusy(true); setError("");
    Promise.all([getPlans(apiBaseUrl), getPlanningContext(apiBaseUrl)]).then(([rows, data]) => {
      if (!cancelled) {
        setPlans(rows); setContext(data);
        // Opened from a savings goal: show that plan's details once
        if (focusPlanId && !focused.current) { focused.current = true; setSelected(rows.find(row => row.id === focusPlanId) ?? null); }
      }
    }).catch(err => { if (!cancelled && !(err instanceof SessionExpiredError)) setError(err.message); }).finally(() => { if (!cancelled) setBusy(false); });
    return () => { cancelled = true; };
  }, [apiBaseUrl, revision]);
  const save = async () => {
    if (!preview || busy) return; setBusy(true); setError("");
    try {
      const saved = preview.budgetGoalSource ? await confirmBudgetPlan(apiBaseUrl, preview, editing?.id) : await savePlan(apiBaseUrl, preview.profile, editing?.id);
      onPreview(saved); setPlans(rows => [...rows.filter(row => row.id !== saved.id), saved]);
      setSelected(saved); setEditing(null); setPreview(null);
    } catch (err) { if (!(err instanceof SessionExpiredError)) setError((err as Error).message); }
    finally { setBusy(false); }
  };
  const remove = (id: string) => Alert.alert("Delete this plan?", "This plan will be permanently deleted. Your savings, expenses, income and budgets are kept; savings assigned to this plan become general savings.", [{ text: "Cancel", style: "cancel" }, { text: "Delete", style: "destructive", onPress: () => {
    if (busy) return; setBusy(true); setError("");
    // Back to My Financial Plans, reloaded from the server
    planningRequest(apiBaseUrl, "/plans/" + id, "DELETE").then(() => { setPlans(rows => rows.filter(row => row.id !== id)); setSelected(null); setRevision(n => n + 1); }).catch(err => { if (!(err instanceof SessionExpiredError)) setError(err.message); }).finally(() => setBusy(false));
  } }]);
  const back = () => {
    if (busy || formBusy) return;
    setError("");
    if (editing && !preview) { setEditing(null); return; }
    setEditing(null); setPreview(null); setSelected(null);
  };
  const inDetails = !!selected || !!preview;
  const inForm = !!editing && !preview;
  const header = <View style={[styles.header, s.plansHeader, navigationStyles.header]}>
    {(inDetails || inForm) && <BackButton onPress={back} disabled={busy || formBusy} label={inForm && selected ? "Back to plan" : "Back to plans"} />}
    <View style={styles.cardTitleBlock}><Text style={styles.eyebrow}>Your finances</Text><Text style={styles.title}>{inForm ? editing?.id ? "Edit plan" : "Create a Plan" : inDetails ? "Plan details" : "My Financial Plans"}</Text></View>
  </View>;
  if (inForm && selected?.budgetGoalSource) return <View style={s.plansContainer}>{header}<ScrollView contentContainerStyle={s.content}><BudgetPlanEditor plan={selected} suggestion={editing?.suggestion} apiBaseUrl={apiBaseUrl} onBusyChange={setFormBusy} onCancel={() => { setEditing(null); setError(""); }} onPreview={plan => { setPreview(plan); onPreview(plan); }} /></ScrollView></View>;
  if (inForm && context) return <View style={s.plansContainer}>
    {header}
    <PlanningForm key={editing?.id ?? "new"} apiBaseUrl={apiBaseUrl} context={context} initial={editing?.profile} onBusyChange={setFormBusy} onCancel={() => { setEditing(null); setError(""); }} onPreview={plan => { setPreview(plan); onPreview(plan); }} />
  </View>;
  if (inDetails) {
    const plan = preview ?? selected!;
    return <View style={s.plansContainer}>{header}<ScrollView key={preview ? "preview" : plan.id} contentContainerStyle={s.content}>
      {!!error && <Text style={s.error} accessibilityRole="alert">{error}</Text>}
      <FinancialPlanCard key={preview ? "draft" : plan.id} plan={plan} busy={busy}
        onSave={preview ? () => { void save(); } : undefined}
        onEdit={!preview && context ? (suggestion?: PlanSuggestion) => { setError(""); setEditing({ profile: plan.profile, id: plan.id, suggestion }); } : undefined}
        onDelete={!preview && plan.id ? () => remove(plan.id!) : undefined}
        status={preview ? null : status} apiBaseUrl={apiBaseUrl} onStatusChange={setStatus} />
      {preview && <Pressable style={[s.button, s.secondary, busy && s.muted]} disabled={busy} onPress={() => { setEditing(current => ({ ...current, profile: preview.profile })); setPreview(null); }}><Text style={s.secondaryText}>Adjust Details</Text></Pressable>}
    </ScrollView></View>;
  }
  return <View style={s.plansContainer}>{header}<FlatList data={inForm ? [] : plans} keyExtractor={plan => plan.id!} contentContainerStyle={s.content}
    ListHeaderComponent={<View style={s.listIntro}>
      <Text style={s.text}>Tap a plan to view its details, charts and recommendations.</Text>
      {!!error && <Text style={s.error} accessibilityRole="alert">{error}</Text>}
      <View style={s.listActions}>
        <Pressable disabled={busy || !context} style={[s.button, s.listAction, (busy || !context) && s.muted]} onPress={() => { setError(""); setEditing({}); }}><Text style={s.buttonText}>Create a Plan</Text></Pressable>
        <Pressable style={[s.button, s.secondary, s.listAction]} onPress={onStartPlanning}><Text style={s.secondaryText}>Plan with AI Chat</Text></Pressable>
      </View>
      {busy && <ActivityIndicator color={palette.accent} />}
      {!!error && <Pressable style={[s.button, s.secondary]} onPress={() => setRevision(n => n + 1)}><Text style={s.secondaryText}>Retry loading</Text></Pressable>}
    </View>}
    renderItem={({ item: plan }) => <Pressable disabled={busy} onPress={() => { setError(""); setSelected(plan); }} accessibilityRole="button" accessibilityHint="Open plan details" style={({ pressed }) => [s.planListRow, pressed && s.planListPressed, busy && s.muted]}>
      <View style={s.planListIcon}><Target size={21} color={palette.accent} /></View>
      <View style={s.planListBody}><Text localize={false} style={s.planListTitle} numberOfLines={2}>{plan.title}</Text><Text style={s.planListStatus}>Saved plan</Text></View>
      <ChevronRight size={20} color={palette.textMuted} />
    </Pressable>}
    ListEmptyComponent={!busy && !error && !inForm ? <Text style={s.text}>No saved plans yet. Create one here or save a draft from chat.</Text> : null} />
  </View>;
}
