import React, { useState } from "react";
import { Pressable, Text, TextInput, View } from "react-native";
import { Pencil, TriangleAlert } from "lucide-react-native";

import { useDashboardTheme } from "./useDashboardTheme";
import { saveBudgetPlan } from "../../services/budgetService";
import { SessionExpiredError } from "../../services/apiClient";
import {
  BudgetRow,
  DashboardData,
  SAVINGS_CATEGORY,
  buildBudgetRows,
  formatAED,
  formatPercent,
  planTotal,
  validatePlan,
} from "../../utils/dashboard";

type Props = {
  data: DashboardData | null;
  apiBaseUrl: string;
  onSaved: (data: DashboardData) => void;
};

// Share of the budget at which a bar turns amber
const WARNING_RATIO = 0.8;

export default function BudgetTracker({ data, apiBaseUrl, onSaved }: Props) {
  const { styles, palette } = useDashboardTheme();

  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const allocations = data?.ideal_budget?.allocations;

  if (!data || !allocations) return null;

  const rows = buildBudgetRows(allocations);
  const overCount = rows.filter((row) => row.over).length;
  const hasIncome = data.income !== null;
  const savings = allocations.find((item) => item.category === SAVINGS_CATEGORY);
  const total = planTotal(draft);

  const startEditing = () => {
    setDraft(Object.fromEntries(allocations.map((item) => [item.category, String(item.percentage)])));
    setError("");
    setEditing(true);
  };

  const save = async () => {
    if (saving) return;

    const problem = validatePlan(draft);

    if (problem) {
      setError(problem);
      return;
    }

    setSaving(true);
    setError("");

    try {
      const percentages = Object.fromEntries(
        Object.entries(draft).map(([category, value]) => [category, Number(value)])
      );
      onSaved(await saveBudgetPlan(apiBaseUrl, data.year, data.month, percentages));
      setEditing(false);
    } catch (err) {
      if (!(err instanceof SessionExpiredError)) {
        setError("Could not save your budget. Please try again.");
      }
    } finally {
      setSaving(false);
    }
  };

  const renderRow = (row: BudgetRow) => {
    const ratio = row.ratio ?? 0;
    const fillStyle = row.over
      ? styles.budgetFillDanger
      : ratio >= WARNING_RATIO
        ? styles.budgetFillWarning
        : null;

    return (
      <View key={row.category}>
        <View style={styles.budgetHeaderRow}>
          <Text style={styles.budgetName} numberOfLines={1}>
            {row.category}
          </Text>

          {row.target === null ? (
            <Text style={styles.budgetFigures}>
              <Text style={styles.budgetFiguresStrong}>{formatAED(row.spent)}</Text>
              {` · ${row.percentage}% of income`}
            </Text>
          ) : (
            <Text style={styles.budgetFigures}>
              <Text style={[styles.budgetFiguresStrong, row.over && styles.statusDanger]}>
                {formatAED(row.spent)}
              </Text>
              {` / ${formatAED(row.target)}`}
            </Text>
          )}
        </View>

        {row.target !== null && (
          <View
            style={styles.budgetTrack}
            accessibilityRole="progressbar"
            accessibilityLabel={`${row.category} budget used`}
            accessibilityValue={{
              min: 0,
              max: 100,
              now: Math.min(100, Math.round(Number.isFinite(ratio) ? ratio * 100 : 100)),
              text: row.over ? `Over budget by ${formatAED(row.overBy)}` : `${formatPercent(ratio * 100)} used`,
            }}
          >
            <View
              style={[
                styles.budgetFill,
                fillStyle,
                { width: `${Math.min(100, Number.isFinite(ratio) ? ratio * 100 : 100)}%` },
              ]}
            />
          </View>
        )}

        {row.over && (
          <View style={styles.overBadge}>
            <TriangleAlert size={12} color={palette.danger} strokeWidth={2.4} />
            <Text style={styles.overBadgeText}>Over by {formatAED(row.overBy)}</Text>
          </View>
        )}
      </View>
    );
  };

  return (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <View style={styles.cardTitleBlock}>
          <Text style={styles.cardLabel}>Budget tracker</Text>
          <Text style={[styles.cardSubtitle, hasIncome && (overCount > 0 ? styles.statusDanger : styles.statusOk)]}>
            {!hasIncome
              ? "Your budget split"
              : overCount > 0
                ? `${overCount} ${overCount === 1 ? "category" : "categories"} over budget`
                : "All categories within budget"}
          </Text>
        </View>

        {!editing && (
          <Pressable
            onPress={startEditing}
            style={({ pressed }) => [styles.pill, pressed && styles.buttonDisabled]}
            accessibilityRole="button"
            accessibilityLabel="Edit budget split"
          >
            <Pencil size={13} color={palette.accent} strokeWidth={2.2} />
            <Text style={styles.pillText}>Edit split</Text>
          </Pressable>
        )}
      </View>

      {editing ? (
        <View>
          <Text style={[styles.mutedText, styles.editorIntro]}>
            Set the share of your monthly income for each category. The total must be 100%.
          </Text>

          <View style={styles.splitGrid}>
            {allocations.map((item) => (
              <View key={item.category} style={styles.splitItem}>
                <Text style={styles.splitName} numberOfLines={1}>
                  {item.category}
                </Text>
                <TextInput
                  value={draft[item.category] ?? ""}
                  onChangeText={(value) =>
                    setDraft((current) => ({ ...current, [item.category]: value.replace(/[^0-9]/g, "") }))
                  }
                  keyboardType="number-pad"
                  maxLength={3}
                  editable={!saving}
                  style={styles.splitInput}
                  accessibilityLabel={`${item.category} percentage of income`}
                />
                <Text style={styles.splitPercent}>%</Text>
              </View>
            ))}
          </View>

          <Text style={[styles.splitTotal, total === 100 ? styles.statusOk : styles.statusDanger]}>
            Total: {total}% of income
          </Text>

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
              <Text style={styles.primaryButtonText}>{saving ? "Saving…" : "Save split"}</Text>
            </Pressable>
          </View>

          {!!error && <Text style={styles.formError}>{error}</Text>}
        </View>
      ) : (
        <>
          {!hasIncome && (
            <Text style={[styles.mutedText, styles.trackerHint]}>
              Add your monthly income above to turn this split into AED budgets.
            </Text>
          )}

          <View style={styles.budgetList}>{rows.map(renderRow)}</View>

          <View style={styles.budgetFooter}>
            {savings && (
              <Text style={styles.mutedText}>
                {SAVINGS_CATEGORY}: {savings.percentage}% of income
                {savings.target !== null ? ` (${formatAED(savings.target)})` : ""} planned.
              </Text>
            )}
            <Text style={styles.mutedText}>
              Expenses in other categories count toward Other.
            </Text>
          </View>
        </>
      )}
    </View>
  );
}
