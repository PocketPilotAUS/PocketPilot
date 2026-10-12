import React from "react";
import { ActivityIndicator, Pressable } from "react-native";
import { Alert, Text, View } from "../../preferences/LocalizedNative";
import { Trash2 } from "lucide-react-native";

import BottomSheet from "./BottomSheet";
import CategoryIcon from "./CategoryIcon";
import { useTransactionsTheme } from "./useTransactionsTheme";
import { formatAED } from "../../utils/dashboard";
import { Transaction, formatLongDate } from "../../utils/transactions";

type Props = {
  transaction: Transaction | null;
  deleting: boolean;
  onClose: () => void;
  onDelete: (transaction: Transaction) => void;
};

export default function TransactionDetail({ transaction, deleting, onClose, onDelete }: Props) {
  const { tx, palette } = useTransactionsTheme();

  const confirmDelete = (item: Transaction) => {
    Alert.alert(
      "Delete transaction?",
      `${item.category} · ${formatAED(item.amount)} will be permanently removed. This can't be undone.`,
      [
        { text: "Cancel", style: "cancel" },
        { text: "Delete", style: "destructive", onPress: () => onDelete(item) },
      ]
    );
  };

  return (
    <BottomSheet visible={transaction !== null} title="Transaction" onClose={onClose}>
      {transaction && (
        <>
          <View style={tx.detailHero}>
            <CategoryIcon category={transaction.category} size="large" />
            <Text style={tx.detailCategory}>{transaction.category}</Text>
            <Text style={tx.detailAmount}>{formatAED(transaction.amount)}</Text>
          </View>

          <View style={tx.detailList}>
            <View style={tx.detailRow}>
              <Text style={tx.detailLabel}>Date</Text>
              <Text style={tx.detailValue}>{formatLongDate(transaction.date)}</Text>
            </View>

            <View style={[tx.detailRow, tx.rowDivider]}>
              <Text style={tx.detailLabel}>Description</Text>
              <Text style={tx.detailValue}>
                {transaction.description?.trim() ? <Text localize={false}>{transaction.description.trim()}</Text> : "No description"}
              </Text>
            </View>

            <View style={[tx.detailRow, tx.rowDivider]}>
              <Text style={tx.detailLabel}>Category</Text>
              <Text style={tx.detailValue}>{transaction.category}</Text>
            </View>
          </View>

          <Pressable
            onPress={() => confirmDelete(transaction)}
            disabled={deleting}
            style={({ pressed }) => [tx.deleteButton, (pressed || deleting) && tx.rowPressed]}
            accessibilityRole="button"
            accessibilityLabel="Delete transaction"
          >
            {deleting ? (
              <ActivityIndicator color={palette.danger} />
            ) : (
              <Trash2 size={18} color={palette.danger} strokeWidth={2.2} />
            )}
            <Text style={tx.deleteText}>{deleting ? "Deleting…" : "Delete transaction"}</Text>
          </Pressable>
        </>
      )}
    </BottomSheet>
  );
}
