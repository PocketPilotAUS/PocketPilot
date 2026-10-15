import React, { useRef, useState } from "react";
import { Modal } from "react-native";
import AddTransactionScreen from "./AddTransactionScreen";
import TransactionHistoryScreen from "./TransactionHistoryScreen";
import StatementImportScreen from "./StatementImportScreen";

type Props = { apiBaseUrl: string; budgetCategories?: string[] };

export default function TransactionsScreen({ apiBaseUrl, budgetCategories }: Props) {
  const [adding, setAdding] = useState(false);
  const [importing, setImporting] = useState(false);
  const [revision, setRevision] = useState(0);
  const saving = useRef(false);
  const close = () => {
    if (saving.current) return;
    setAdding(false);
  };
  return <>
    <TransactionHistoryScreen apiBaseUrl={apiBaseUrl} refreshKey={revision} onAddExpense={() => setAdding(true)} onImportStatement={() => setImporting(true)} />
    <Modal visible={importing} animationType="slide" presentationStyle="pageSheet" onRequestClose={() => { if (!saving.current) setImporting(false); }}>
      {importing && <StatementImportScreen apiBaseUrl={apiBaseUrl} budgetCategories={budgetCategories} onClose={() => { if (!saving.current) setImporting(false); }} onBusyChange={value => { saving.current = value; }} onImported={() => { saving.current = false; setImporting(false); setRevision(value => value + 1); }} />}
    </Modal>
    <Modal visible={adding} animationType="slide" presentationStyle="pageSheet" onRequestClose={close}>
      {adding && <AddTransactionScreen
        apiBaseUrl={apiBaseUrl} budgetCategories={budgetCategories} onBack={close}
        onBusyChange={(busy) => { saving.current = busy; }}
        onSaved={() => { saving.current = false; setRevision(value => value + 1); close(); }}
      />}
    </Modal>
  </>;
}
