import React, { useState } from "react";
import { Pressable, ScrollView } from "react-native";
import { Text, TextInput, View } from "../../preferences/LocalizedNative";
import { ArrowUpDown, CalendarDays, Check, ChevronDown, Layers, RotateCcw, Wallet } from "lucide-react-native";

import BottomSheet from "./BottomSheet";
import DateRangeCalendar from "./DateRangeCalendar";
import { useTransactionsTheme } from "./useTransactionsTheme";
import {
  AmountFilter,
  DEFAULT_FILTERS,
  DateFilter,
  Filters,
  SORT_LABELS,
  SortOrder,
  activeFilterCount,
  amountFilterLabel,
  dateFilterLabel,
  parseAmountFilter,
} from "../../utils/transactions";

type Sheet = "date" | "category" | "amount" | "sort" | null;

type Props = {
  filters: Filters;
  categories: string[];
  today: Date;
  onChange: (filters: Filters) => void;
};

const DATE_OPTIONS: { kind: Exclude<DateFilter["kind"], "custom">; label: string }[] = [
  { kind: "all", label: "All time" },
  { kind: "thisWeek", label: "This week" },
  { kind: "thisMonth", label: "This month" },
  { kind: "lastMonth", label: "Last month" },
];

const AMOUNT_MODES: { kind: AmountFilter["kind"]; label: string }[] = [
  { kind: "any", label: "Any" },
  { kind: "above", label: "Above" },
  { kind: "below", label: "Below" },
  { kind: "between", label: "Between" },
];

export default function TransactionFilters({ filters, categories, today, onChange }: Props) {
  const { styles, tx, palette } = useTransactionsTheme();

  const [sheet, setSheet] = useState<Sheet>(null);

  // Drafts are only applied when the user confirms
  const [customStart, setCustomStart] = useState<string | null>(null);
  const [customEnd, setCustomEnd] = useState<string | null>(null);
  const [showCalendar, setShowCalendar] = useState(false);
  const [amountKind, setAmountKind] = useState<AmountFilter["kind"]>("any");
  const [minDraft, setMinDraft] = useState("");
  const [maxDraft, setMaxDraft] = useState("");
  const [amountError, setAmountError] = useState("");

  const update = (changes: Partial<Filters>) => onChange({ ...filters, ...changes });

  const openDate = () => {
    const custom = filters.date.kind === "custom" ? filters.date : null;
    setCustomStart(custom?.start ?? null);
    setCustomEnd(custom?.end ?? null);
    setShowCalendar(custom !== null);
    setSheet("date");
  };

  const openAmount = () => {
    const amount = filters.amount;
    setAmountKind(amount.kind);
    setMinDraft(amount.kind === "above" || amount.kind === "between" ? String(amount.min) : "");
    setMaxDraft(amount.kind === "below" || amount.kind === "between" ? String(amount.max) : "");
    setAmountError("");
    setSheet("amount");
  };

  const applyAmount = () => {
    const result = parseAmountFilter(amountKind, minDraft, maxDraft);

    if (typeof result === "string") {
      setAmountError(result);
      return;
    }

    update({ amount: result });
    setSheet(null);
  };

  const applyCustomRange = () => {
    if (!customStart) return;
    update({ date: { kind: "custom", start: customStart, end: customEnd ?? customStart } });
    setSheet(null);
  };

  const chips = [
    {
      key: "date",
      label: dateFilterLabel(filters.date, today),
      active: filters.date.kind !== "all",
      Icon: CalendarDays,
      onPress: openDate,
    },
    {
      key: "category",
      label: filters.category ?? "All categories",
      active: filters.category !== null,
      Icon: Layers,
      onPress: () => setSheet("category"),
    },
    {
      key: "amount",
      label: amountFilterLabel(filters.amount),
      active: filters.amount.kind !== "any",
      Icon: Wallet,
      onPress: openAmount,
    },
    {
      key: "sort",
      label: SORT_LABELS[filters.sort],
      active: filters.sort !== "newest",
      Icon: ArrowUpDown,
      onPress: () => setSheet("sort"),
    },
  ];

  const option = (label: string, selected: boolean, onPress: () => void) => (
    <Pressable
      key={label}
      onPress={onPress}
      style={({ pressed }) => [tx.optionRow, pressed && tx.rowPressed]}
      accessibilityRole="button"
      accessibilityState={{ selected }}
    >
      <Text style={[tx.optionText, selected && tx.optionTextSelected]} numberOfLines={1}>
        {label}
      </Text>
      {selected && <Check size={18} color={palette.accent} strokeWidth={2.5} />}
    </Pressable>
  );

  const resetCount = activeFilterCount(filters) + (filters.sort !== "newest" ? 1 : 0);

  return (
    <>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={tx.chipScroll}
        contentContainerStyle={tx.chipRow}
      >
        {chips.map(({ key, label, active, Icon, onPress }) => (
          <Pressable
            key={key}
            onPress={onPress}
            style={({ pressed }) => [tx.chip, active && tx.chipActive, pressed && tx.rowPressed]}
            accessibilityRole="button"
            accessibilityLabel={`${key} filter: ${label}`}
          >
            <Icon size={14} color={active ? palette.accent : palette.textSecondary} strokeWidth={2.2} />
            <Text style={[tx.chipText, active && tx.chipTextActive]} numberOfLines={1}>
              {label}
            </Text>
            <ChevronDown size={14} color={active ? palette.accent : palette.textMuted} strokeWidth={2.2} />
          </Pressable>
        ))}

        {resetCount > 0 && (
          <Pressable
            onPress={() => onChange({ ...DEFAULT_FILTERS, search: filters.search })}
            style={({ pressed }) => [tx.chip, pressed && tx.rowPressed]}
            accessibilityRole="button"
            accessibilityLabel="Reset filters"
          >
            <RotateCcw size={14} color={palette.textSecondary} strokeWidth={2.2} />
            <Text style={tx.chipText}>Reset</Text>
          </Pressable>
        )}
      </ScrollView>

      {/* Date */}
      <BottomSheet
        visible={sheet === "date"}
        title="Date"
        onClose={() => setSheet(null)}
        footer={
          showCalendar ? (
            <View style={styles.buttonRow}>
              <Pressable
                onPress={applyCustomRange}
                disabled={!customStart}
                style={[styles.primaryButton, !customStart && styles.buttonDisabled]}
                accessibilityRole="button"
              >
                <Text style={styles.primaryButtonText}>Apply range</Text>
              </Pressable>
            </View>
          ) : null
        }
      >
        {DATE_OPTIONS.map(({ kind, label }) =>
          option(label, filters.date.kind === kind && !showCalendar, () => {
            update({ date: { kind } as DateFilter });
            setSheet(null);
          })
        )}
        {option("Custom range", showCalendar, () => setShowCalendar(true))}

        {showCalendar && (
          <DateRangeCalendar
            start={customStart}
            end={customEnd}
            today={today}
            onChange={(start, end) => {
              setCustomStart(start);
              setCustomEnd(end);
            }}
          />
        )}
      </BottomSheet>

      {/* Category */}
      <BottomSheet visible={sheet === "category"} title="Category" onClose={() => setSheet(null)}>
        {option("All categories", filters.category === null, () => {
          update({ category: null });
          setSheet(null);
        })}
        {categories.map((category) =>
          option(category, filters.category === category, () => {
            update({ category });
            setSheet(null);
          })
        )}
      </BottomSheet>

      {/* Amount */}
      <BottomSheet
        visible={sheet === "amount"}
        title="Amount"
        onClose={() => setSheet(null)}
        footer={
          <>
            {!!amountError && <Text style={styles.formError}>{amountError}</Text>}
            <View style={styles.buttonRow}>
              <Pressable onPress={applyAmount} style={styles.primaryButton} accessibilityRole="button">
                <Text style={styles.primaryButtonText}>Apply</Text>
              </Pressable>
            </View>
          </>
        }
      >
        <View style={tx.segmented}>
          {AMOUNT_MODES.map(({ kind, label }) => (
            <Pressable
              key={kind}
              onPress={() => { setAmountKind(kind); setAmountError(""); }}
              style={[tx.segment, amountKind === kind && tx.segmentActive]}
              accessibilityRole="button"
              accessibilityState={{ selected: amountKind === kind }}
            >
              <Text style={[tx.segmentText, amountKind === kind && tx.segmentTextActive]}>{label}</Text>
            </Pressable>
          ))}
        </View>

        {amountKind === "any" ? (
          <Text style={styles.mutedText}>Show transactions of every amount.</Text>
        ) : (
          <View style={tx.amountInputs}>
            {(amountKind === "above" || amountKind === "between") && (
              <View style={tx.amountField}>
                <Text style={styles.editorLabel}>{amountKind === "between" ? "Minimum" : "At least"}</Text>
                <View style={styles.inputRow}>
                  <Text style={styles.inputPrefix}>AED</Text>
                  <TextInput
                    value={minDraft}
                    onChangeText={setMinDraft}
                    keyboardType="decimal-pad"
                    placeholder="0.00"
                    placeholderTextColor={palette.textMuted}
                    style={styles.input}
                    accessibilityLabel="Minimum amount in AED"
                  />
                </View>
              </View>
            )}

            {(amountKind === "below" || amountKind === "between") && (
              <View style={tx.amountField}>
                <Text style={styles.editorLabel}>{amountKind === "between" ? "Maximum" : "At most"}</Text>
                <View style={styles.inputRow}>
                  <Text style={styles.inputPrefix}>AED</Text>
                  <TextInput
                    value={maxDraft}
                    onChangeText={setMaxDraft}
                    keyboardType="decimal-pad"
                    placeholder="0.00"
                    placeholderTextColor={palette.textMuted}
                    style={styles.input}
                    accessibilityLabel="Maximum amount in AED"
                  />
                </View>
              </View>
            )}
          </View>
        )}
      </BottomSheet>

      {/* Sort */}
      <BottomSheet visible={sheet === "sort"} title="Sort by" onClose={() => setSheet(null)}>
        {(Object.keys(SORT_LABELS) as SortOrder[]).map((sort) =>
          option(
            { newest: "Newest first", oldest: "Oldest first", highest: "Highest amount", lowest: "Lowest amount" }[sort],
            filters.sort === sort,
            () => {
              update({ sort });
              setSheet(null);
            }
          )
        )}
      </BottomSheet>
    </>
  );
}
