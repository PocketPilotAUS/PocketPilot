import React, { useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  Text,
  TextInput,
  View,
} from "react-native";
import { Pencil, Plus } from "lucide-react-native";

import { useDashboardTheme } from "./useDashboardTheme";
import { saveMonthlyIncome } from "../../services/budgetService";
import { SessionExpiredError } from "../../services/apiClient";
import {
  DashboardData,
  formatAED,
  formatPercent,
  monthName,
  validateIncome,
} from "../../utils/dashboard";

type Props = {
  data: DashboardData | null;
  loading: boolean;
  apiBaseUrl: string;
  onSaved: (data: DashboardData) => void;
};

export default function FinancialOverview({ data, loading, apiBaseUrl, onSaved }: Props) {
  const { styles, palette } = useDashboardTheme();

  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const income = data?.income ?? null;
  const remaining = data?.remaining ?? null;
  const over = remaining !== null && remaining < 0;
  const spentPercentage = data?.spent_percentage ?? null;

  const startEditing = () => {
    setDraft(income === null ? "" : String(income));
    setError("");
    setEditing(true);
  };

  const save = async () => {
    if (!data || saving) return;

    const problem = validateIncome(draft);

    if (problem) {
      setError(problem);
      return;
    }

    setSaving(true);
    setError("");

    try {
      onSaved(await saveMonthlyIncome(apiBaseUrl, data.year, data.month, draft.trim()));
      setEditing(false);
    } catch (err) {
      if (!(err instanceof SessionExpiredError)) {
        setError("Could not save your income. Please try again.");
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <View style={styles.cardTitleBlock}>
          <Text style={styles.cardLabel}>Financial overview</Text>
          {data && (
            <Text style={styles.cardSubtitle}>
              {monthName(data.month)} {data.year}
            </Text>
          )}
        </View>

        {data && !editing && (
          <Pressable
            onPress={startEditing}
            style={({ pressed }) => [styles.pill, pressed && styles.buttonDisabled]}
            accessibilityRole="button"
            accessibilityLabel={income === null ? "Add monthly income" : "Edit monthly income"}
          >
            {income === null ? (
              <Plus size={14} color={palette.accent} strokeWidth={2.5} />
            ) : (
              <Pencil size={13} color={palette.accent} strokeWidth={2.2} />
            )}
            <Text style={styles.pillText}>{income === null ? "Add income" : "Edit income"}</Text>
          </Pressable>
        )}
      </View>

      {loading && !data ? (
        <ActivityIndicator color={palette.accent} style={styles.loader} />
      ) : !data ? (
        <Text style={styles.mutedText}>Your overview is unavailable right now.</Text>
      ) : (
        <>
          {/* Without income, what's left is unknown, so spending leads */}
          <Text style={styles.heroLabel}>
            {remaining === null ? "Spent this month" : over ? "Over your income by" : "Left to spend"}
          </Text>

          <Text
            style={[
              styles.heroAmount,
              remaining !== null && (over ? styles.heroAmountDanger : styles.heroAmountAccent),
            ]}
            adjustsFontSizeToFit
            numberOfLines={1}
          >
            {formatAED(remaining === null ? data.spent : Math.abs(remaining))}
          </Text>

          {remaining === null && (
            <Text style={styles.heroHint}>Add your monthly income to see what’s left to spend.</Text>
          )}

          {spentPercentage !== null && (
            <>
              <View
                style={styles.progressTrack}
                accessibilityRole="progressbar"
                accessibilityLabel="Share of monthly income spent"
                accessibilityValue={{
                  min: 0,
                  max: 100,
                  now: Math.min(100, Math.round(spentPercentage)),
                  text: `${formatPercent(spentPercentage)} spent`,
                }}
              >
                <View
                  style={[
                    styles.progressFill,
                    over && styles.progressFillDanger,
                    { width: `${Math.min(100, Math.max(0, spentPercentage))}%` },
                  ]}
                />
              </View>
              <Text style={styles.progressCaption}>{formatPercent(spentPercentage)} of income spent</Text>
            </>
          )}

          <View style={styles.statRow}>
            <View style={styles.statTile}>
              <Text style={styles.statLabel}>Income</Text>
              <Text
                style={[styles.statValue, income === null && styles.statValueMuted]}
                adjustsFontSizeToFit
                numberOfLines={1}
              >
                {income === null ? "Not set" : formatAED(income)}
              </Text>
            </View>

            {remaining === null ? (
              <View style={styles.statTile}>
                <Text style={styles.statLabel}>Remaining</Text>
                <Text style={[styles.statValue, styles.statValueMuted]}>Add income</Text>
              </View>
            ) : (
              <View style={styles.statTile}>
                <Text style={styles.statLabel}>Spent</Text>
                <Text style={styles.statValue} adjustsFontSizeToFit numberOfLines={1}>
                  {formatAED(data.spent)}
                </Text>
              </View>
            )}
          </View>

          {editing && (
            <View style={styles.editor}>
              <Text style={styles.editorLabel}>
                Monthly income for {monthName(data.month)}
              </Text>

              <View style={styles.inputRow}>
                <Text style={styles.inputPrefix}>AED</Text>
                <TextInput
                  value={draft}
                  onChangeText={setDraft}
                  placeholder="0.00"
                  placeholderTextColor={palette.textMuted}
                  keyboardType="decimal-pad"
                  style={styles.input}
                  editable={!saving}
                  autoFocus
                  returnKeyType="done"
                  onSubmitEditing={() => { void save(); }}
                  accessibilityLabel="Monthly income in AED"
                />
              </View>

              <View style={styles.buttonRow}>
                <Pressable
                  onPress={() => { setEditing(false); setError(""); }}
                  disabled={saving}
                  style={[styles.secondaryButton, saving && styles.buttonDisabled]}
                  accessibilityRole="button"
                >
                  <Text style={styles.secondaryButtonText}>Cancel</Text>
                </Pressable>

                <Pressable
                  onPress={() => { void save(); }}
                  disabled={saving}
                  style={[styles.primaryButton, saving && styles.buttonDisabled]}
                  accessibilityRole="button"
                >
                  <Text style={styles.primaryButtonText}>{saving ? "Saving…" : "Save income"}</Text>
                </Pressable>
              </View>

              {!!error && <Text style={styles.formError}>{error}</Text>}
            </View>
          )}
        </>
      )}
    </View>
  );
}
