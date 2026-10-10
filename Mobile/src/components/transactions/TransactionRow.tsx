import React from "react";
import { Pressable, Text, View } from "react-native";

import CategoryIcon from "./CategoryIcon";
import { useTransactionsTheme } from "./useTransactionsTheme";
import { formatAED } from "../../utils/dashboard";
import { Transaction, formatShortDate } from "../../utils/transactions";

type Props = {
  transaction: Transaction;
  today: Date;
  first: boolean;
  onPress: (transaction: Transaction) => void;
};

export default function TransactionRow({ transaction, today, first, onPress }: Props) {
  const { tx } = useTransactionsTheme();

  const date = formatShortDate(transaction.date, today);
  const description = transaction.description?.trim();

  return (
    <Pressable
      onPress={() => onPress(transaction)}
      style={({ pressed }) => [tx.row, !first && tx.rowDivider, pressed && tx.rowPressed]}
      accessibilityRole="button"
      accessibilityLabel={`${transaction.category}, ${formatAED(transaction.amount)}, ${date}${description ? `, ${description}` : ""}`}
      accessibilityHint="Opens transaction details"
    >
      <CategoryIcon category={transaction.category} />

      <View style={tx.rowText}>
        <Text style={tx.rowTitle} numberOfLines={1}>
          {transaction.category}
        </Text>
        <Text style={tx.rowSubtitle} numberOfLines={1}>
          {/* Date first, so a long description never hides it */}
          {description ? `${date} · ${description}` : date}
        </Text>
      </View>

      <Text style={tx.rowAmount}>{formatAED(transaction.amount)}</Text>
    </Pressable>
  );
}
