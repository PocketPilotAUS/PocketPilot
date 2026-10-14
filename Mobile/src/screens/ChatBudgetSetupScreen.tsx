import React, { useEffect, useRef, useState } from "react";
import { ActivityIndicator, Pressable } from "react-native";
import { Text, View } from "../preferences/LocalizedNative";
import { SafeAreaView } from "react-native-safe-area-context";
import BackButton from "../components/BackButton";
import KeyboardFormScrollView from "../components/KeyboardFormScrollView";
import BudgetSetupForm from "../components/dashboard/BudgetSetupForm";
import { useDashboardTheme } from "../components/dashboard/useDashboardTheme";
import { apiFetch } from "../services/apiClient";
import type { DashboardData } from "../utils/dashboard";
type Props = { apiBaseUrl: string; onCancel: () => void; onSaved: (data: DashboardData) => void };
export default function ChatBudgetSetupScreen({ apiBaseUrl, onCancel, onSaved }: Props) {
  const { styles: s, palette } = useDashboardTheme();
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  const [saving, setSaving] = useState(false);
  const mounted = useRef(true);
  useEffect(() => {
    let active = true; mounted.current = true; setError("");
    const now = new Date(Date.now() + 4 * 60 * 60 * 1000);
    apiFetch(apiBaseUrl, `/budget/monthly?year=${now.getUTCFullYear()}&month=${now.getUTCMonth() + 1}`)
      .then(async response => { if (!response.ok) throw new Error("Could not load your budget. Please try again."); return response.json(); })
      .then(value => { if (active) setData(value); }).catch(e => { if (active) setError(e.message); });
    return () => { active = false; mounted.current = false; };
  }, [apiBaseUrl, revision]);
  return <SafeAreaView style={s.screen} edges={["top", "left", "right"]}><KeyboardFormScrollView contentContainerStyle={s.content}>
    <View style={s.header}><BackButton onPress={onCancel} disabled={saving} label="Back to AI Chat" /><View style={s.headerText}><Text style={s.title}>Budget tracker</Text></View></View>
    {data ? <BudgetSetupForm data={data} apiBaseUrl={apiBaseUrl} onBusyChange={setSaving} onSaved={value => { if (mounted.current) onSaved(value); }} onCancel={onCancel} /> : error ? <><Text style={s.formError}>{error}</Text><Pressable onPress={() => setRevision(value => value + 1)} style={s.primaryButton}><Text style={s.primaryButtonText}>Try again</Text></Pressable></> : <ActivityIndicator color={palette.accent} />}
  </KeyboardFormScrollView></SafeAreaView>;
}
