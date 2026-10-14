import { displayProfile, baseProfile } from "../../preferences/currency";
import React, { useEffect, useState } from "react";
import { Pressable } from "react-native";
import { Text, TextInput, View } from "../../preferences/LocalizedNative";
import KeyboardFormScrollView from "../KeyboardFormScrollView";
import { useAITheme } from "./useAITheme";
import { createPlanningStyles } from "../../styles/PlanningStyles";
import {
  PLAN_CATEGORIES,
  FinancialPlan,
  PlanningContext,
  PlanningProfile,
} from "../../types/plans";
import { planningRequest } from "../../services/planningService";
import { SessionExpiredError } from "../../services/apiClient";
import { formatAED } from "../../utils/dashboard";
import PlanningDateField from "./PlanningDateField";
import {
  formatPlanningDate,
  parsePlanningDate,
  planningDateError,
} from "../../utils/planningDate";
// New plans start fresh, except for monthly income.
// Existing plans use the initial profile passed for editing.
export const initialProfile = (context: PlanningContext): PlanningProfile => ({
  income:
    context.saved_budget?.income ??
    context.current_income ??
    context.profile.income ??
    null,
  other_income: null,
  household_size: 1,
  goal: null,
  goal_kind: "savings",
  target_amount: null,
  current_amount: null,
  preferred_monthly_savings: null,
  deadline: null,
  expenses: context.saved_budget
    ? { ...context.saved_budget.expenses }
    : {},
  typical_months: [],
  protected_categories: [],
});
type Props = {
  apiBaseUrl: string;
  context: PlanningContext;
  initial?: PlanningProfile;
  onPreview: (plan: FinancialPlan) => void;
  onCancel: () => void;
  onBusyChange?: (busy: boolean) => void;
};
export default function PlanningForm({
  apiBaseUrl,
  context,
  initial,
  onPreview,
  onCancel,
  onBusyChange,
}: Props) {
  const { palette } = useAITheme();
  const s = createPlanningStyles(palette);
  const startingProfile = initial ?? initialProfile(context);
  const expenseCategories = Array.from(
    new Set([
      ...PLAN_CATEGORIES,
      ...Object.keys(startingProfile.expenses),
    ])
  );
  const [profile, setProfile] = useState<PlanningProfile>(
    () => displayProfile(startingProfile)
  );
  const [deadlineText, setDeadlineText] = useState(
    () => formatPlanningDate(startingProfile.deadline)
  );
  const [dateError, setDateError] = useState<string | null>(null);
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [showExpenses, setShowExpenses] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  useEffect(() => {
    onBusyChange?.(busy);
    return () => {
      onBusyChange?.(false);
    };
  }, [busy, onBusyChange]);
  const change = (key: keyof PlanningProfile, value: unknown) => {
    setProfile(current => ({
      ...current,
      [key]: value,
    }));
  };
  const updateDeadline = (text: string) => {
    setDeadlineText(text);
    setDateError(null);
    setProfile(current => ({
      ...current,
      deadline: parsePlanningDate(text),
    }));
  };
  const field = (
    label: string,
    key: keyof PlanningProfile,
    numeric = true,
    hint?: string
  ) => (
    <View key={key} style={{ gap: 8 }}>
      <Text style={s.label}>{label}</Text>
      {!!hint && <Text style={s.text}>{hint}</Text>}
      <TextInput
        style={s.input}
        accessibilityLabel={label}
        placeholder={numeric ? "Enter amount" : "Enter here"}
        placeholderTextColor={palette.textMuted}
        keyboardType={numeric ? "decimal-pad" : "default"}
        value={profile[key] == null ? "" : String(profile[key])}
        editable={!busy}
        onChangeText={value =>
          change(
            key,
            value === ""
              ? null
              : key === "household_size"
                ? Number(value)
                : value
          )
        }
      />
    </View>
  );
  // Expense priority:
  // 1. Manually entered estimate
  // 2. Average from selected typical months
  // 3. Unknown expense
  const expenseSummary = expenseCategories.map(category => {
    const entered = profile.expenses[category];
    if (entered !== null && entered !== undefined && entered !== "") {
      const amount = Number(entered);
      if (Number.isFinite(amount) && amount >= 0) {
        return {
          category,
          amount,
          source: "estimate",
          known: true,
        };
      }
      return {
        category,
        amount: 0,
        source: "invalid",
        known: false,
      };
    }
    const selectedMonths = profile.typical_months.filter(
      month => context.past_months[month] !== undefined
    );
    if (selectedMonths.length > 0) {
      const total = selectedMonths.reduce(
        (sum, month) =>
          sum + (context.past_months[month][category] ?? 0),
        0
      );
      return {
        category,
        amount: total / selectedMonths.length,
        source: "history",
        known: true,
      };
    }
    return {
      category,
      amount: 0,
      source: "unknown",
      known: false,
    };
  });
  const monthlyExpenses = expenseSummary.reduce(
    (sum, item) => sum + (item.known ? item.amount : 0),
    0
  );
  const missingCategories = expenseSummary
    .filter(item => !item.known)
    .map(item => item.category);
  const totalIncome =
    Number(profile.income ?? 0) +
    Number(profile.other_income ?? 0);
  const availableAmount = totalIncome - monthlyExpenses;
  const hasValidIncome =
    profile.income !== null &&
    profile.income !== "" &&
    Number.isFinite(totalIncome) &&
    totalIncome >= 0;
  const preview = async () => {
    const invalidDate = planningDateError(deadlineText);
    if (invalidDate) {
      setDateError(invalidDate);
      setStep(0);
      return;
    }
    await submitProfile(profile);
  };
  const previewSpending = async () => {
    await submitProfile({
      ...profile,
      current_amount: 0,
      preferred_monthly_savings: null,
      deadline: null,
    });
  };
  const submitProfile = async (submittedProfile: PlanningProfile) => {
    setBusy(true);
    setError("");
    try {
      const normalizedProfile: PlanningProfile = {
        ...submittedProfile,
        household_size: submittedProfile.household_size ?? 1,
        other_income: submittedProfile.other_income ?? 0,
        current_amount: submittedProfile.current_amount ?? 0,
        preferred_monthly_savings:
          submittedProfile.goal_kind === "savings"
            ? submittedProfile.preferred_monthly_savings ?? null
            : null,
      };
      const result = await planningRequest<
        FinancialPlan & { missing?: string[] }
      >(
        apiBaseUrl,
        "/profile",
        "PUT",
        baseProfile(normalizedProfile, startingProfile)
      );
      if (!result.ready) {
        setError(
          `Still needed: ${result.missing?.join(", ") ?? "more financial details"
          }. Enter 0 only when an expense truly does not apply.`
        );
        if (missingCategories.length > 0) {
          setShowExpenses(true);
        }
        return;
      }
      onPreview(result);
    } catch (err) {
      if (!(err instanceof SessionExpiredError)) {
        setError((err as Error).message);
      }
    } finally {
      setBusy(false);
    }
  };
  return (
    <KeyboardFormScrollView contentContainerStyle={s.content}>
      <View style={s.card}>
        <Text style={s.title}>
          {step === 0 ? "Your Goal" : "Monthly Expenses"}
        </Text>
        <Text style={s.text}>
          {step === 0
            ? "Set your goal and review your finances."
            : "Review your monthly spending before generating your plan."}
        </Text>
        {/* STEP 1: GOAL AND FINANCES */}
        {step === 0 && (
          <>
            {field("Plan Name", "goal", false)}
            <View style={s.row}>
              {(["savings", "debt", "spending"] as const).map(kind => (
                <Pressable
                  key={kind}
                  style={[
                    s.chip,
                    profile.goal_kind === kind && s.selected,
                  ]}
                  disabled={busy}
                  onPress={() =>
                    setProfile(current => ({
                      ...current,
                      goal_kind: kind,
                      preferred_monthly_savings:
                        kind === "savings" ? current.preferred_monthly_savings ?? null : null,
                    }))
                  }
                >
                  <Text style={s.text}>
                    {kind === "savings"
                      ? "Save Money"
                      : kind === "debt"
                        ? "Pay Off Debt"
                        : "Control Spending"}
                  </Text>
                </Pressable>
              ))}
            </View>
            {profile.goal_kind === "spending" ? (
              field("Monthly Spending Limit", "target_amount")
            ) : (
              <View style={{ flexDirection: "row", gap: 10 }}>
                <View style={{ flex: 1 }}>
                  {field("Target Amount", "target_amount")}
                </View>
                <View style={{ flex: 1 }}>
                  {field(
                    profile.goal_kind === "debt"
                      ? "Already Paid"
                      : "Already Saved",
                    "current_amount"
                  )}
                </View>
              </View>
            )}
            {profile.goal_kind === "savings" && (
              <View style={{ gap: 8 }}>
                {field(
                  "Preferred Monthly Savings (Optional)",
                  "preferred_monthly_savings",
                  true,
                  "How much would you like to save each month? Leave blank and PocketPilot will calculate the amount needed for your deadline."
                )}
              </View>
            )}
            {profile.goal_kind !== "spending" && (
              <PlanningDateField
                value={deadlineText}
                onChange={updateDeadline}
                error={dateError}
                disabled={busy}
              />
            )}
            <View
              style={{
                marginTop: 8,
                paddingTop: 16,
                borderTopWidth: 1,
                borderTopColor: palette.textMuted,
                gap: 12,
              }}
            >
              <Text style={s.title}>Your Finances</Text>
              <View style={{ flexDirection: "row", gap: 10 }}>
                <View style={{ flex: 1 }}>
                  {field("Monthly Income", "income")}
                </View>
                <View style={{ flex: 1 }}>
                  {field("Other Income", "other_income")}
                </View>
              </View>
            </View>
          </>
        )}
        {/* STEP 2: MONTHLY EXPENSES */}
        {step === 2 && (
          <>
            <View style={{ gap: 8, marginBottom: 12 }}>
              <Text style={s.label}>
                Estimated Monthly Spending
              </Text>
              <Text style={s.title}>
                {formatAED(monthlyExpenses)}
              </Text>
              <Text style={s.text}>
                {missingCategories.length === 0
                  ? "All expense categories have an estimate."
                  : `${missingCategories.length} expense categories still need estimates.`}
              </Text>
              {!!profile.typical_months.length && (
                <Text style={s.text}>
                  Includes averages from your selected complete months
                  for categories without manual estimates.
                </Text>
              )}
            </View>
            {/* FINANCIAL SUMMARY */}
            <View
              style={{
                borderTopWidth: 1,
                borderTopColor: palette.textMuted,
                paddingTop: 16,
                gap: 12,
                marginBottom: 12,
              }}
            >
              <Text style={s.label}>Monthly Overview</Text>
              <View
                style={{
                  flexDirection: "row",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <Text style={s.text}>Total Income</Text>
                <Text style={s.label}>
                  {hasValidIncome
                    ? formatAED(totalIncome)
                    : "Not entered"}
                </Text>
              </View>
              <View
                style={{
                  flexDirection: "row",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <Text style={s.text}>Known Expenses</Text>
                <Text style={s.label}>
                  {formatAED(monthlyExpenses)}
                </Text>
              </View>
              <View
                style={{
                  borderTopWidth: 1,
                  borderTopColor: palette.textMuted,
                  paddingTop: 12,
                }}
              >
                <View
                  style={{
                    flexDirection: "row",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <Text style={s.label}>
                    Available to Save
                  </Text>
                  <Text style={s.label}>
                    {hasValidIncome &&
                      missingCategories.length === 0
                      ? formatAED(availableAmount)
                      : "Pending"}
                  </Text>
                </View>
              </View>
            </View>
            {/* EDIT EXPENSES */}
            <Pressable
              style={[s.button, s.secondary]}
              disabled={busy}
              accessibilityRole="button"
              accessibilityState={{ expanded: showExpenses }}
              onPress={() =>
                setShowExpenses(current => !current)
              }
            >
              <Text style={s.secondaryText}>
                {showExpenses
                  ? "Hide Expense Details"
                  : `Edit Expenses${missingCategories.length
                    ? ` (${missingCategories.length} missing)`
                    : ""
                  }`}
              </Text>
            </Pressable>
            {showExpenses && (
              <View
                style={{
                  flexDirection: "row",
                  flexWrap: "wrap",
                  columnGap: 10,
                  rowGap: 16,
                  marginTop: 12,
                }}
              >
                {expenseCategories.map(category => {
                  const summary = expenseSummary.find(
                    item => item.category === category
                  );
                  return (
                    <View
                      key={category}
                      style={{
                        width: "48%",
                        gap: 8,
                        minHeight: 112,
                        paddingHorizontal: 0,
                      }}
                    >
                      <Text style={s.label}>
                        {category === "Debt payments"
                          ? "Minimum Debt Payments"
                          : category}
                      </Text>
                      <TextInput
                        style={s.input}
                        accessibilityLabel={`${category} monthly estimate`}
                        placeholder={
                          summary?.source === "history"
                            ? `History average: ${formatAED(
                              summary.amount
                            )}`
                            : "Enter amount or 0 if none"
                        }
                        placeholderTextColor={palette.textMuted}
                        keyboardType="decimal-pad"
                        value={
                          profile.expenses[category] == null
                            ? ""
                            : String(profile.expenses[category])
                        }
                        editable={!busy}
                        onChangeText={value =>
                          setProfile(current => ({
                            ...current,
                            expenses: {
                              ...current.expenses,
                              [category]:
                                value === "" ? null : value,
                            },
                          }))
                        }
                      />
                      {[
                        "Entertainment",
                        "Shopping",
                        "Subscriptions",
                      ].includes(category) ? (
                        <Pressable
                          style={[
                            s.chip,
                            profile.protected_categories.includes(
                              category
                            ) && s.selected,
                          ]}
                          disabled={busy}
                          onPress={() =>
                            change(
                              "protected_categories",
                              profile.protected_categories.includes(
                                category
                              )
                                ? profile.protected_categories.filter(
                                  key => key !== category
                                )
                                : [
                                  ...profile.protected_categories,
                                  category,
                                ]
                            )
                          }
                        >
                          <Text style={s.text}>
                            {profile.protected_categories.includes(
                              category
                            )
                              ? "✓ Essential expense"
                              : "Mark as essential"}
                          </Text>
                        </Pressable>
                      ) : (
                        <Text
                          style={[
                            s.text,
                            {
                              fontSize: 11,
                              marginTop: -2,
                              lineHeight: 20,
                            },
                          ]}
                        >
                          {category === "Rent" ||
                            category === "Bills"
                            ? "Fixed expense"
                            : category === "Debt payments"
                              ? "Required payment"
                              : category === "Food" ||
                                category === "Transport"
                                ? "Regular expense"
                                : "Other expense"}
                        </Text>
                      )}
                    </View>
                  );
                })}
                <Pressable
                  style={[
                    s.button,
                    s.secondary,
                    {
                      width: "100%",
                      marginTop: 8,
                    },
                  ]}
                  onPress={() => setShowExpenses(false)}
                  disabled={busy}
                  accessibilityRole="button"
                >
                  <Text style={s.secondaryText}>
                    Done Editing
                  </Text>
                </Pressable>
              </View>
            )}
            {/* PREVIOUS SPENDING */}
            <View
              style={{
                marginTop: 16,
                paddingTop: 16,
                borderTopWidth: 1,
                borderTopColor: palette.textMuted,
                gap: 12,
              }}
            >
              <Pressable
                disabled={busy}
                accessibilityRole="button"
                accessibilityState={{ expanded: showHistory }}
                onPress={() =>
                  setShowHistory(current => !current)
                }
              >
                <Text style={s.label}>
                  {showHistory ? "▼" : "▶"} Previous Spending
                </Text>
              </Pressable>
              {showHistory && (
                <View style={{ gap: 12 }}>
                  <Text style={s.text}>
                    Select only months that are fully recorded
                    and typical of your spending. Blank expense
                    categories will use averages from those months.
                  </Text>
                  {Object.entries(context.past_months).map(
                    ([month, categories]) => (
                      <View key={month} style={{ gap: 6 }}>
                        <Pressable
                          style={[
                            s.chip,
                            profile.typical_months.includes(
                              month
                            ) && s.selected,
                          ]}
                          disabled={busy}
                          onPress={() =>
                            change(
                              "typical_months",
                              profile.typical_months.includes(month)
                                ? profile.typical_months.filter(
                                  m => m !== month
                                )
                                : [
                                  ...profile.typical_months,
                                  month,
                                ]
                            )
                          }
                        >
                          <Text style={s.text}>
                            {profile.typical_months.includes(month)
                              ? "✓ "
                              : ""}
                            {month} ·{" "}
                            {formatAED(
                              Object.values(categories).reduce(
                                (sum, amount) => sum + amount,
                                0
                              )
                            )}
                          </Text>
                        </Pressable>
                        <Text style={s.text}>
                          {Object.entries(categories)
                            .map(
                              ([key, amount]) =>
                                `${key}: ${formatAED(amount)}`
                            )
                            .join(" · ")}
                        </Text>
                      </View>
                    )
                  )}
                  {!Object.keys(context.past_months).length && (
                    <Text style={s.text}>
                      No previous spending months recorded yet.
                    </Text>
                  )}
                  {!!Object.keys(
                    context.recurring_obligations
                  ).length && (
                      <>
                        <Text style={s.label}>
                          Recurring Commitments
                        </Text>
                        <Text style={s.text}>
                          {Object.entries(
                            context.recurring_obligations
                          )
                            .map(
                              ([key, amount]) =>
                                `${key}: ${formatAED(amount)}`
                            )
                            .join(" · ")}
                        </Text>
                        <Pressable
                          style={[s.button, s.secondary]}
                          disabled={busy}
                          onPress={() =>
                            setProfile(current => ({
                              ...current,
                              expenses: {
                                ...displayProfile({
                                  expenses:
                                    context.recurring_obligations,
                                }).expenses,
                                ...current.expenses,
                              },
                            }))
                          }
                        >
                          <Text style={s.secondaryText}>
                            Use Recurring Estimates
                          </Text>
                        </Pressable>
                      </>
                    )}
                </View>
              )}
            </View>
          </>
        )}
        {!!error && (
          <Text accessibilityRole="alert" style={s.error}>
            {error}
          </Text>
        )}
        {/* NAVIGATION */}
        {step === 0 ? (
          <Pressable
            style={s.button}
            disabled={busy}
            onPress={() => {
              setError("");
              if (profile.goal_kind !== "spending") {
                const invalidDate =
                  planningDateError(deadlineText);
                if (invalidDate) {
                  setDateError(invalidDate);
                  return;
                }
              }
              setStep(2);
            }}
          >
            <Text style={s.buttonText}>Continue</Text>
          </Pressable>
        ) : (
          <Pressable
            style={[s.button, busy && s.muted]}
            disabled={busy}
            onPress={() => {
              if (profile.goal_kind === "spending") {
                void previewSpending();
              } else {
                void preview();
              }
            }}
          >
            <Text style={s.buttonText}>
              {busy ? "Checking…" : "Review My Plan"}
            </Text>
          </Pressable>
        )}
        {step > 0 && (
          <Pressable
            disabled={busy}
            style={[s.button, s.secondary]}
            onPress={() => {
              setError("");
              setStep(0);
            }}
          >
            <Text style={s.secondaryText}>Back</Text>
          </Pressable>
        )}
        <Pressable disabled={busy} onPress={onCancel}>
          <Text style={s.text}>Cancel</Text>
        </Pressable>
      </View>
    </KeyboardFormScrollView>
  );
}