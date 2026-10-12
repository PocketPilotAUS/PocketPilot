import React, { useRef, useState } from "react";
import { Modal } from "react-native";
import AddTransactionScreen from "./AddTransactionScreen";
import TransactionHistoryScreen from "./TransactionHistoryScreen";

type Props = { apiBaseUrl: string; budgetCategories?: string[]; initiallyAdding?: boolean };

export default function TransactionsScreen({ apiBaseUrl, budgetCategories, initiallyAdding = false }: Props) {
  const [adding, setAdding] = useState(initiallyAdding);
  const [revision, setRevision] = useState(0);
  const saving = useRef(false);
  const close = () => { if (!saving.current) setAdding(false); };
  return <>
    <TransactionHistoryScreen apiBaseUrl={apiBaseUrl} refreshKey={revision} onAddExpense={() => setAdding(true)} />
    <Modal visible={adding} animationType="slide" presentationStyle="pageSheet" onRequestClose={close}>
      {adding && <AddTransactionScreen
        apiBaseUrl={apiBaseUrl} budgetCategories={budgetCategories} onBack={close}
        onBusyChange={(busy) => { saving.current = busy; }}
        onSaved={() => { saving.current = false; setAdding(false); setRevision(value => value + 1); }}
      />}
    </Modal>
  </>;
}
