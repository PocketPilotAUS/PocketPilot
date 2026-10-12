import React from "react";
import { KeyboardAvoidingView, Modal, Platform, Pressable, ScrollView } from "react-native";
import { Text, View } from "../../preferences/LocalizedNative";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { X } from "lucide-react-native";

import { useTransactionsTheme } from "./useTransactionsTheme";

type Props = {
  visible: boolean;
  title: string;
  onClose: () => void;
  children: React.ReactNode;
  footer?: React.ReactNode;
};

// Slide-up panel used for filters and transaction details
export default function BottomSheet({ visible, title, onClose, children, footer }: Props) {
  const { tx, palette } = useTransactionsTheme();
  const insets = useSafeAreaInsets();

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <KeyboardAvoidingView
        style={tx.sheetBackdrop}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        {/* Tapping outside the sheet closes it */}
        <Pressable style={tx.sheetDismissArea} onPress={onClose} accessibilityLabel="Close" />

        <View style={[tx.sheet, { paddingBottom: Math.max(insets.bottom, 16) + 8 }]}>
          <View style={tx.sheetHandle} />

          <View style={tx.sheetHeader}>
            <Text style={tx.sheetTitle}>{title}</Text>
            <Pressable
              onPress={onClose}
              style={tx.sheetClose}
              accessibilityRole="button"
              accessibilityLabel="Close"
              hitSlop={8}
            >
              <X size={18} color={palette.textSecondary} strokeWidth={2.2} />
            </Pressable>
          </View>

          <ScrollView keyboardShouldPersistTaps="handled" bounces={false}>
            {children}
          </ScrollView>

          {footer}
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}
