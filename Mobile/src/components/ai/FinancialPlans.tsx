import React, { useEffect, useState } from "react";
import { Pressable, ScrollView } from "react-native";
import { Alert, Text, View } from "../../preferences/LocalizedNative";
import { useAITheme } from "./useAITheme";
import { createPlanningStyles } from "../../styles/PlanningStyles";
import FinancialPlanCard from "./FinancialPlanCard";
import PlanningForm from "./PlanningForm";
import { FinancialPlan, PlanningContext, PlanningProfile } from "../../types/plans";
import { getPlanningContext, getPlans, planningRequest, savePlan } from "../../services/planningService";
import { SessionExpiredError } from "../../services/apiClient";

type Props = { apiBaseUrl: string; onPreview: (plan: FinancialPlan) => void; onStartPlanning: () => void; initialProfile?: PlanningProfile };
export default function FinancialPlans({ apiBaseUrl, onPreview, onStartPlanning, initialProfile }: Props) {
 const { palette } = useAITheme(); const s = createPlanningStyles(palette);
 const [plans, setPlans] = useState<FinancialPlan[]>([]);
 const [context, setContext] = useState<PlanningContext | null>(null);
 const [editing, setEditing] = useState<{ profile?: PlanningProfile; id?: string } | null>(initialProfile ? { profile: initialProfile } : null);
 const [preview, setPreview] = useState<FinancialPlan | null>(null);
 const [busy, setBusy] = useState(false); const [error, setError] = useState(""); const [revision, setRevision] = useState(0);
 useEffect(() => {
  let cancelled = false; setBusy(true); setError("");
  Promise.all([getPlans(apiBaseUrl), getPlanningContext(apiBaseUrl)]).then(([rows, data]) => { if (!cancelled) { setPlans(rows); setContext(data); } }).catch(err => { if (!cancelled && !(err instanceof SessionExpiredError)) setError(err.message); }).finally(() => { if (!cancelled) setBusy(false); });
  return () => { cancelled = true; };
 }, [apiBaseUrl, revision]);
 const save = async () => {
  if (!preview || busy) return; setBusy(true); setError("");
  try { const saved = await savePlan(apiBaseUrl, preview.profile, editing?.id); onPreview(saved); setPlans(rows => [...rows.filter(row => row.id !== saved.id), saved]); setEditing(null); setPreview(null); setRevision(n => n + 1); }
  catch (err) { if (!(err instanceof SessionExpiredError)) setError((err as Error).message); }
  finally { setBusy(false); }
 };
 const remove = (id: string) => Alert.alert("Delete this plan?", "Recorded expenses and income will remain.", [{ text: "Cancel", style: "cancel" }, { text: "Delete", style: "destructive", onPress: () => {
  if (busy) return; setBusy(true);
  planningRequest(apiBaseUrl, `/plans/${id}`, "DELETE").then(() => setPlans(rows => rows.filter(row => row.id !== id))).catch(err => { if (!(err instanceof SessionExpiredError)) setError(err.message); }).finally(() => setBusy(false));
 } }]);
 if (editing && context && !preview) return <PlanningForm apiBaseUrl={apiBaseUrl} context={context} initial={editing.profile} onCancel={() => setEditing(null)} onPreview={plan => { setPreview(plan); onPreview(plan); }} />;
 return <ScrollView contentContainerStyle={s.content}>
  {!!error && <Text style={s.error}>{error}</Text>}
  {preview ? <><FinancialPlanCard plan={preview} busy={busy} onSave={() => { void save(); }} /><Pressable style={[s.button, s.secondary]} disabled={busy} onPress={() => { setEditing(current => ({ ...current, profile: preview.profile })); setPreview(null); }}><Text style={s.secondaryText}>Adjust Details</Text></Pressable><Pressable disabled={busy} onPress={() => { setEditing(null); setPreview(null); }}><Text style={s.text}>Back to plans</Text></Pressable></> : <>
   <View style={s.card}><Text style={s.title}>My Financial Plans</Text><Text style={s.text}>Build a plan around your household, spending history and main goal. Review suggested cuts before deciding what works for you.</Text>
    <Pressable disabled={busy || !context} style={[s.button, (busy || !context) && s.muted]} onPress={() => setEditing({})}><Text style={s.buttonText}>{busy ? "Loading�" : "Create a Plan"}</Text></Pressable>
    <Pressable style={[s.button, s.secondary]} onPress={onStartPlanning}><Text style={s.secondaryText}>Plan with AI Chat</Text></Pressable>
    {!!error && <Pressable onPress={() => setRevision(n => n + 1)}><Text style={s.text}>Retry loading</Text></Pressable>}
   </View>
   {plans.map(plan => <FinancialPlanCard key={plan.id} plan={plan} busy={busy} onEdit={() => setEditing({ profile: plan.profile, id: plan.id })} onDelete={() => remove(plan.id!)} />)}
   {!busy && !plans.length && <Text style={s.text}>No saved plans yet. Create one here or save a draft from chat.</Text>}
  </>}
 </ScrollView>;
}
